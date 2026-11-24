"""What must not be in the Stats files of the package (design-final.md 3.4, AGENTS-09).

The Stats tool code reaches the network through the shared client alone, holds
no link, no setting and no key, and opens no file. The two link prefixes it
may cite sit in a constants file that holds those two strings and nothing
else. No Stats argument is a link, a host, a path or a file name.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from bca_mcp.client import _is_allowed_base
from bca_mcp.server import TOOLS

SRC = Path(__file__).resolve().parent.parent / "src" / "bca_mcp"
GUARDED = (SRC / "tools" / "stats.py", SRC / "_outside.py")
FORBIDDEN = (
    "http://", "https://", "process.env", "os.environ", "node:dns", "node:net", "node:fs",
    "child_process", "subprocess", "socket", "fetch(", "httpx", ".post(", "open(",
)
STATS_NAMES = {
    "search_stats", "list_stats_measures", "rank_stats", "get_stats_record",
    "compare_stats_records", "lookup_stats_wallet", "get_stats_method", "list_stats_changes",
}


@pytest.mark.parametrize("path", GUARDED, ids=lambda p: p.name)
@pytest.mark.parametrize("needle", FORBIDDEN)
def test_stats_files_hold_none_of_the_forbidden_strings(path: Path, needle: str) -> None:
    assert needle not in path.read_text("utf-8"), f"{path.name} contains {needle!r}"


def test_the_constants_file_holds_the_two_prefixes_and_nothing_else() -> None:
    tree = ast.parse((SRC / "_stats_constants.py").read_text("utf-8"))
    strings = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    assert strings == ["https://data.blockchainacademics.com/", "https://blockchainacademics.com/"]
    assert all(isinstance(node, ast.Assign) for node in tree.body)
    assert [t.id for node in tree.body for t in node.targets] == ["DATA_PREFIX", "SITE_PREFIX"]


def test_the_data_address_is_not_a_base_the_client_takes() -> None:
    # A key is never sent to the data address: the packages do not call it.
    assert not _is_allowed_base("https://data.blockchainacademics.com")
    assert _is_allowed_base("https://api.blockchainacademics.com")


def _walk(schema):
    if isinstance(schema, dict):
        yield schema
        for value in schema.values():
            yield from _walk(value)
    elif isinstance(schema, list):
        for value in schema:
            yield from _walk(value)


def test_no_stats_argument_is_a_link_a_host_a_path_or_a_file() -> None:
    stats = [t for t in TOOLS if t.name in STATS_NAMES]
    assert {t.name for t in stats} == STATS_NAMES
    for tool in stats:
        for name in tool.input_schema["properties"]:
            assert name not in ("url", "host", "path", "file", "uri", "link"), f"{tool.name}.{name}"
        for node in _walk(tool.input_schema):
            assert node.get("format") not in ("uri", "url", "hostname", "iri"), tool.name
        assert "http" not in json.dumps(tool.input_schema), tool.name


def test_stats_tools_are_read_only() -> None:
    from bca_mcp.annotations import WRITE_TOOLS, tool_annotations

    for name in STATS_NAMES:
        assert name not in WRITE_TOOLS
        assert tool_annotations(name)["readOnlyHint"] is True
