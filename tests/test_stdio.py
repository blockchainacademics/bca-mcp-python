"""End to end over stdio: spawn `python -m bca_mcp` with no key and talk to it
with the MCP client, the way a host does.

BCA_API_BASE points at a closed local port, so even an accidental request
cannot reach the live API (the demo key shares a daily cap with real users).
Only tools/list and calls with invalid arguments (rejected before any
request) are exercised.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import sys
import tempfile
from pathlib import Path

import mcp.types as mcp_types
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.server import Server

from bca_mcp import __version__
from bca_mcp._demo_banner import DEMO_BANNER

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "ts_tools_0_6_3.json").read_text("utf-8")
)

# Features of the installed mcp SDK (pyproject allows any 1.x release).
HAS_ANNOTATIONS = hasattr(mcp_types, "ToolAnnotations")
HAS_ERRLOG = "errlog" in inspect.signature(stdio_client).parameters
HAS_SERVER_VERSION = "version" in inspect.signature(Server.__init__).parameters


async def _session_run(errlog) -> dict:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "bca_mcp"],
        # get_default_environment() supplies PATH/HOME; no BCA_API_KEY.
        env={"BCA_API_BASE": "http://127.0.0.1:9"},
    )
    kwargs = {"errlog": errlog} if HAS_ERRLOG else {}
    async with stdio_client(params, **kwargs) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            listed = await session.list_tools()
            bad = await session.call_tool("get_entity", {"slug": "a", "ticker": "B"})
            unknown = await session.call_tool("nope", {})
    return {"init": init, "tools": listed.tools, "bad": bad, "unknown": unknown}


@pytest.mark.asyncio
async def test_stdio_server_without_key() -> None:
    with tempfile.TemporaryFile("w+", encoding="utf-8") as errlog:
        out = await asyncio.wait_for(_session_run(errlog), timeout=60)
        errlog.seek(0)
        stderr = errlog.read()

    assert out["init"].serverInfo.name == "bca-mcp"
    if HAS_SERVER_VERSION:
        assert out["init"].serverInfo.version == __version__

    tools = {t.name: t for t in out["tools"]}
    assert set(tools) == set(FIXTURE["names"]) and len(out["tools"]) == 105

    entity = tools["get_entity"].inputSchema["properties"]
    explainer = tools["get_explainer"].inputSchema["properties"]
    assert set(entity) == {"slug", "ticker"}
    assert set(explainer) == {"slug", "topic"}

    if HAS_ANNOTATIONS:
        for t in out["tools"]:
            assert t.annotations is not None, t.name
            assert t.annotations.title and t.annotations.openWorldHint is True, t.name
        assert tools["get_price"].annotations.readOnlyHint is True
        assert tools["submit_listing"].annotations.readOnlyHint is False
        assert tools["submit_listing"].annotations.destructiveHint is False

    for key in ("bad", "unknown"):
        result = out[key]
        assert result.isError is True, key
        body = json.loads(result.content[0].text)
        assert body["error"]["code"] == "BCA_BAD_REQUEST", key

    if HAS_ERRLOG:
        assert DEMO_BANNER in stderr
    listed_text = json.dumps([t.model_dump(mode="json") for t in out["tools"]], ensure_ascii=False)
    assert "—" not in listed_text
