"""The TypeScript package's recorded Stats answers, run through this package.

tests/fixtures/stats_api_ts is bca-mcp-ts test/fixtures/stats_api, copied
unchanged (SOURCE.txt there). Its expected outputs were written from the
design's reference rules, not from either package's code. Each answer runs
through its tool here with the same fixed marker id and call id, and the
parsed text block must equal the TypeScript expected output, so the two
packages are shown to give the same answer (design 4.2, layer 3), and this
package's own expected outputs are not its only check.
"""

from __future__ import annotations

import hashlib
import json
import socket
from pathlib import Path
from typing import Any

import pytest

from bca_mcp import _outside, server
from bca_mcp.client import BcaClient, set_client
from bca_mcp.server import call_tool
from bca_mcp.tools import stats

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "stats_api_ts"
CALLS = sorted(p.stem for p in (FIXTURES / "answers").glob("*.json"))
MARK = "0123456789abcdef"
CALL_ID = "fedcba9876543210"
WALLET = pytest.mark.skipif(not stats.WALLET_LOOKUP_TOOL, reason="owner switch 2 leaves lookup_stats_wallet out")


def _read(path: str) -> Any:
    return json.loads((FIXTURES / path).read_text("utf-8"))


@pytest.fixture(autouse=True)
def _setup(monkeypatch):
    def refuse(*_args, **_kwargs):
        raise AssertionError("a Stats test tried to open a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(_outside, "new_marker_id", lambda: MARK)
    monkeypatch.setattr(server, "_new_call_id", lambda: CALL_ID)
    set_client(BcaClient(base_url="https://api.blockchainacademics.com", api_key="k"))


def test_the_copied_files_match_their_checksums() -> None:
    listed = {}
    for line in (FIXTURES / "SHA256SUMS").read_text("utf-8").splitlines():
        digest, path = line.split("  ", 1)
        listed[path] = digest
    on_disk = {f"{folder}/{p.name}" for folder in ("answers", "expected_outputs", "shards")
               for p in (FIXTURES / folder).glob("*.json")}
    assert set(listed) == on_disk
    for path, digest in listed.items():
        assert hashlib.sha256((FIXTURES / path).read_bytes()).hexdigest() == digest, path
    assert len(CALLS) == 55  # 38 in 0.7.0, the 9 yield and rate paid calls of 0.8.0, the 8 chain calls of the API's dump at 02e19b8
    assert {_read(f"answers/{c}.json")["tool"] for c in CALLS} == {
        "search_stats", "list_stats_measures", "rank_stats", "get_stats_record", "compare_stats_records",
        "lookup_stats_wallet", "get_stats_method", "list_stats_changes",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "call",
    [pytest.param(c, marks=WALLET) if c.startswith("lookup_") else c for c in CALLS],
)
async def test_each_typescript_answer_gives_the_typescript_expected_output(httpx_mock, call: str) -> None:
    case = _read(f"answers/{call}.json")
    envelope = case["envelope"] if "envelope" in case else _read(case["envelope_file"])
    httpx_mock.add_response(json=envelope, status_code=case.get("status", 200))
    result = await call_tool(case["tool"], case["args"])
    request = httpx_mock.get_request()
    assert request.url.path == case["request"]["path"]
    assert dict(request.url.params) == case["request"].get("query", {})
    out = json.loads(result.content[0].text)
    assert out == _read(f"expected_outputs/{call}.json")
