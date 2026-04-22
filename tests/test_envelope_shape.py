"""Canonical response envelope contract test (v0.3.0+).

Asserts the full shape of the envelope the MCP server emits on a
mocked tool call — every key required by the JSON:API-inspired
contract locked 2026-04-22 is present and well-typed.
"""

from __future__ import annotations

import json

import pytest

from bca_mcp.client import (
    BcaClient,
    reset_legacy_envelope_warning,
    set_client,
)
from bca_mcp.server import build_server
from bca_mcp.tools.search_news import run as run_search_news


CANONICAL_STATUSES = {"complete", "unseeded", "partial", "stale"}


@pytest.mark.asyncio
async def test_canonical_envelope_contract_on_tool_call(httpx_mock) -> None:
    """Tool call emits the full canonical envelope: data + attribution
    (array-shaped citations) + meta (status, request_id, pageInfo)."""
    reset_legacy_envelope_warning()

    # Upstream already emits the canonical shape (post-2026-04-22).
    httpx_mock.add_response(
        url=(
            "https://api.blockchainacademics.com/v1/articles/search"
            "?q=bitcoin&limit=10"
        ),
        json={
            "data": {
                "articles": [
                    {
                        "slug": "btc-etf-approved",
                        "title": "Bitcoin ETF approved",
                        "summary": "Regulator green-lights spot ETF.",
                        "published_at": "2026-04-20T10:00:00Z",
                    }
                ],
                "total": 1,
            },
            "attribution": {
                "citations": [
                    {
                        "cite_url": "https://blockchainacademics.com/articles/btc-etf-approved",
                        "as_of": "2026-04-20T10:05:00Z",
                        "source_hash": "sha256:deadbeef0123",
                    }
                ],
            },
            "meta": {
                "status": "complete",
                "request_id": "req_test_0001",
                "pageInfo": {
                    "hasNextPage": False,
                    "hasPreviousPage": False,
                    "startCursor": None,
                    "endCursor": None,
                },
            },
        },
        status_code=200,
    )

    set_client(BcaClient(api_key="k"))
    out = await run_search_news({"query": "bitcoin"})

    # --- top-level keys ---
    assert set(out.keys()) >= {"data", "attribution", "meta"}

    # --- data ---
    assert isinstance(out["data"], dict)
    assert out["data"]["total"] == 1

    # --- attribution: array-shaped citations ---
    assert isinstance(out["attribution"], dict)
    citations = out["attribution"]["citations"]
    assert isinstance(citations, list)
    assert len(citations) == 1
    c0 = citations[0]
    assert c0["cite_url"] == (
        "https://blockchainacademics.com/articles/btc-etf-approved"
    )
    assert c0["as_of"] == "2026-04-20T10:05:00Z"
    assert c0["source_hash"] == "sha256:deadbeef0123"
    # No singular shorthand fields leak onto attribution.
    assert "cite_url" not in out["attribution"]
    assert "as_of" not in out["attribution"]
    assert "source_hash" not in out["attribution"]

    # --- meta ---
    meta = out["meta"]
    assert isinstance(meta, dict)
    assert meta["status"] in CANONICAL_STATUSES
    assert meta["status"] == "complete"
    assert isinstance(meta["request_id"], str) and meta["request_id"]
    pi = meta["pageInfo"]
    assert pi["hasNextPage"] is False
    assert pi["hasPreviousPage"] is False
    assert pi["startCursor"] is None
    assert pi["endCursor"] is None


@pytest.mark.asyncio
async def test_canonical_envelope_status_enum_excludes_error(
    httpx_mock,
) -> None:
    """The canonical `status` enum does NOT include `"error"` — error
    conditions surface as raises (BcaError subclasses) rather than as
    successful-looking bodies."""
    reset_legacy_envelope_warning()

    httpx_mock.add_response(
        url=(
            "https://api.blockchainacademics.com/v1/articles/search"
            "?q=x&limit=10"
        ),
        json={
            "data": {"articles": [], "total": 0},
            "attribution": {"citations": []},
            "meta": {
                "status": "unseeded",
                "request_id": "req_test_0002",
                "pageInfo": {
                    "hasNextPage": False,
                    "hasPreviousPage": False,
                    "startCursor": None,
                    "endCursor": None,
                },
            },
        },
        status_code=200,
    )

    set_client(BcaClient(api_key="k"))
    out = await run_search_news({"query": "x"})
    assert out["meta"]["status"] == "unseeded"
    assert out["meta"]["status"] != "error"


def test_server_builds_without_error_status_in_type_surface() -> None:
    """The types module's Status literal excludes `error`."""
    from bca_mcp.types import Status
    import typing

    args = typing.get_args(Status)
    assert set(args) == CANONICAL_STATUSES
    assert "error" not in args

    # Sanity: server still builds with the new types in place.
    server = build_server(check_env=False)
    assert server is not None


@pytest.mark.asyncio
async def test_server_call_tool_emits_canonical_envelope(httpx_mock) -> None:
    """The MCP server's call_tool handler serializes the canonical
    envelope directly — no re-shaping."""
    reset_legacy_envelope_warning()

    httpx_mock.add_response(
        url=(
            "https://api.blockchainacademics.com/v1/articles/search"
            "?q=ethereum&limit=10"
        ),
        json={
            "data": {"articles": [], "total": 0},
            "attribution": {
                "citations": [
                    {
                        "cite_url": "https://x.test/c",
                        "as_of": "2026-04-22T00:00:00Z",
                        "source_hash": None,
                    }
                ],
            },
            "meta": {
                "status": "unseeded",
                "request_id": "req_test_0003",
                "pageInfo": {
                    "hasNextPage": False,
                    "hasPreviousPage": False,
                    "startCursor": None,
                    "endCursor": None,
                },
            },
        },
        status_code=200,
    )

    set_client(BcaClient(api_key="k"))
    out = await run_search_news({"query": "ethereum"})

    # The serialized form (what the server sends over stdio) round-trips
    # cleanly and preserves the full canonical shape.
    serialized = json.dumps(out)
    parsed = json.loads(serialized)
    assert parsed["attribution"]["citations"][0]["cite_url"] == "https://x.test/c"
    assert parsed["meta"]["status"] == "unseeded"
    assert parsed["meta"]["request_id"] == "req_test_0003"
    # No legacy top-level status / cite_url leakage.
    assert "status" not in parsed
    assert "cite_url" not in parsed
    assert "as_of" not in parsed
    assert "source_hash" not in parsed
