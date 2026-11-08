"""Parity with the TypeScript sibling, @blockchainacademics/mcp 0.6.4.

The fixture (tests/fixtures/ts_tools_0_6_4.json) holds the 105 tool names of
the TS tools/list and, per tool, the JSON Schema constraints of its zod
schema (type, integer vs number, enum, minimum, maximum, default) and its
description. Both packages must advertise the same names and the same
constraints, and the descriptions rewritten for the directory review in 0.6.4
must read the same in both.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import mcp.types as mcp_types
import pytest
from mcp.types import ListToolsRequest

from bca_mcp.annotations import WRITE_TOOLS, tool_annotations, tool_title
from bca_mcp.server import TOOLS, build_server, tool_definitions

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "ts_tools_0_6_4.json").read_text("utf-8")
)
TS_NAMES: list[str] = FIXTURE["names"]
TS_CONSTRAINTS: dict[str, Any] = FIXTURE["constraints"]
TS_DESCRIPTIONS: dict[str, str] = FIXTURE["descriptions"]
KEYS = ("type", "enum", "minimum", "maximum", "default")

# Descriptions rewritten in 0.6.4 so they say what the tool does, returns and
# when it applies (directory-submissions.md 4.6, row A3). Same text in both
# packages, word for word.
SHARED_DESCRIPTIONS = (
    "search_news", "get_entity", "get_explainer", "get_article",
    "list_entity_mentions", "list_topics", "get_price", "get_market_overview",
    "get_wallet_profile", "get_token_holders", "get_x_signals",
    "generate_due_diligence", "generate_tokenomics_model",
    "summarize_whitepaper", "translate_contract", "book_kol_campaign",
    "request_custom_research", "submit_listing", "search_academy",
    "get_history_correlation",
)
# The two indicators share everything before each package's own meta.status
# sentence (_STATUS_NOTE here, STATUS_NOTE in the TS sibling).
SHARED_INDICATOR_PREFIXES = ("get_sentiment_velocity", "get_editorial_premium")


def _pick(prop: dict[str, Any]) -> dict[str, Any]:
    out = {k: prop[k] for k in KEYS if k in prop}
    items = prop.get("items")
    if isinstance(items, dict):
        sub = {k: items[k] for k in KEYS if k in items}
        if sub:
            out["items"] = sub
    return out


# --- names -----------------------------------------------------------------


def test_tool_names_equal_the_ts_tools_list() -> None:
    names = [t.name for t in TOOLS]
    assert len(TS_NAMES) == 105
    assert len(names) == 105, f"expected 105 tools, got {len(names)}"
    assert len(set(names)) == len(names), "duplicate tool name"
    missing = sorted(set(TS_NAMES) - set(names))
    extra = sorted(set(names) - set(TS_NAMES))
    assert not missing and not extra, f"missing={missing} extra={extra}"


# --- descriptions (0.6.4, directory review row A3) ---------------------------


@pytest.mark.parametrize("name", SHARED_DESCRIPTIONS)
def test_rewritten_descriptions_match_ts_word_for_word(name: str) -> None:
    tool = next(t for t in TOOLS if t.name == name)
    assert tool.description == TS_DESCRIPTIONS[name]


@pytest.mark.parametrize("name", SHARED_INDICATOR_PREFIXES)
def test_indicator_descriptions_match_ts_before_the_status_note(name: str) -> None:
    tool = next(t for t in TOOLS if t.name == name)
    ours = tool.description.split(" meta.status is ", 1)[0]
    theirs = TS_DESCRIPTIONS[name].split(" meta.status is ", 1)[0]
    assert ours == theirs
    assert ours.endswith("Pro tier.")


# --- schemas (F37) ---------------------------------------------------------


@pytest.mark.parametrize("name", TS_NAMES)
def test_schema_constraints_match_ts(name: str) -> None:
    tool = next(t for t in TOOLS if t.name == name)
    schema = tool.input_schema
    expected = TS_CONSTRAINTS[name]
    assert schema["type"] == "object"
    assert schema.get("additionalProperties") is False
    assert sorted(schema.get("properties", {})) == sorted(expected["properties"])
    assert sorted(schema.get("required", [])) == expected["required"]
    for prop, want in expected["properties"].items():
        assert _pick(schema["properties"][prop]) == want, f"{name}.{prop}"


def test_every_schema_has_properties() -> None:
    for t in TOOLS:
        assert isinstance(t.input_schema.get("properties"), dict), t.name


@pytest.mark.parametrize("name", ["get_entity", "get_explainer"])
def test_one_of_tools_advertise_their_inputs(name: str) -> None:
    # F05: the TS shim lost the inputs of the two .refine() tools. Here the
    # model validator never hides them.
    tool = next(t for t in TOOLS if t.name == name)
    props = tool.input_schema["properties"]
    other = "ticker" if name == "get_entity" else "topic"
    assert set(props) == {"slug", other}
    for p in props.values():
        assert p["type"] == "string" and p["description"]


def test_optional_fields_have_no_null_branch_or_titles() -> None:
    for t in TOOLS:
        assert "title" not in t.input_schema, t.name
        for name, prop in t.input_schema["properties"].items():
            assert "anyOf" not in prop, f"{t.name}.{name}"
            assert "title" not in prop, f"{t.name}.{name}"
            assert prop.get("default", "unset") is not None, f"{t.name}.{name}"
            assert "type" in prop, f"{t.name}.{name}"


def test_enum_sits_on_the_optional_property() -> None:
    tag = next(t for t in TOOLS if t.name == "list_jobs").input_schema["properties"]["tag"]
    assert tag["type"] == "string"
    assert "engineering" in tag["enum"]


# --- annotations (shared decision 2) ---------------------------------------


def test_write_tool_set() -> None:
    assert WRITE_TOOLS == {
        "submit_listing",
        "book_kol_campaign",
        "request_custom_research",
        "monitor_keyword",
        "generate_due_diligence",
        "generate_tokenomics_model",
        "summarize_whitepaper",
        "translate_contract",
    }
    assert WRITE_TOOLS <= set(TS_NAMES)


def test_tool_title() -> None:
    assert tool_title("get_price") == "Get price"
    assert tool_title("get_l2_comparison") == "Get l2 comparison"
    assert tool_title("list_mcps") == "List mcps"


@pytest.mark.parametrize("name", TS_NAMES)
def test_annotations_for_every_tool(name: str) -> None:
    ann = tool_annotations(name)
    assert ann["title"] == name.replace("_", " ")[:1].upper() + name.replace("_", " ")[1:]
    assert ann["openWorldHint"] is True
    if name in WRITE_TOOLS:
        assert ann["readOnlyHint"] is False
        assert ann["destructiveHint"] is False
        assert ann["idempotentHint"] is False
    else:
        assert ann == {"title": ann["title"], "readOnlyHint": True, "openWorldHint": True}


@pytest.mark.asyncio
@pytest.mark.skipif(
    not hasattr(mcp_types, "ToolAnnotations"),
    reason="installed mcp release predates tool annotations",
)
async def test_tools_list_wire_payload_carries_annotations(monkeypatch) -> None:
    monkeypatch.delenv("BCA_API_KEY", raising=False)
    server = build_server()
    result = await server.request_handlers[ListToolsRequest](
        ListToolsRequest(method="tools/list")
    )
    wire = result.model_dump(by_alias=True, mode="json", exclude_none=True)
    tools = {t["name"]: t for t in wire["tools"]}
    assert len(tools) == 105
    assert tools["get_price"]["annotations"] == {
        "title": "Get price",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
    assert tools["submit_listing"]["annotations"] == {
        "title": "Submit listing",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
    assert tools["get_entity"]["inputSchema"]["properties"]["slug"]["type"] == "string"


def test_tool_definitions_match_registry() -> None:
    defs = tool_definitions()
    assert [d.name for d in defs] == [t.name for t in TOOLS]
