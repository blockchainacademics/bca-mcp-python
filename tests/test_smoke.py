"""Smoke tests for the v0.1 8-tool scaffold.

Validates:
  * input schemas (defaults, bounds, xor constraints)
  * HTTP client (header injection, envelope parse, 401 -> BcaAuthError,
    non-enveloped JSON wrapped under `data`, integration_pending /
    upstream_error envelope passthrough)
  * server registers exactly 8 tools with unique names
  * server `build_server(check_env=False)` works without a live key
  * server `build_server()` fail-fast when BCA_API_KEY is missing

Uses `pytest-httpx` to mock the underlying httpx transport — no live
network calls. `respx` is listed as a dev dep for parity with the
TS sibling's test suite but is not required here.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bca_mcp.client import BcaClient, set_client
from bca_mcp.errors import BcaAuthError, BcaBadRequestError, BcaUpstreamError
from bca_mcp.server import TOOLS, build_server
from bca_mcp.tools.content import (
    GetArticleInput,
    ListEntityMentionsInput,
    ListTopicsInput,
    run_get_article,
    run_list_entity_mentions,
)
from bca_mcp.tools.get_entity import GetEntityInput
from bca_mcp.tools.get_explainer import GetExplainerInput
from bca_mcp.tools.market import GetMarketOverviewInput, GetPriceInput
from bca_mcp.tools.search_news import SearchNewsInput, run as run_search_news


# --- input schemas ---------------------------------------------------------


def test_search_news_defaults_limit_to_10() -> None:
    v = SearchNewsInput.model_validate({"query": "ethereum"})
    assert v.limit == 10


def test_search_news_rejects_empty_query() -> None:
    with pytest.raises(ValidationError):
        SearchNewsInput.model_validate({"query": ""})


def test_search_news_rejects_oversize_limit() -> None:
    with pytest.raises(ValidationError):
        SearchNewsInput.model_validate({"query": "x", "limit": 999})


def test_get_article_requires_slug() -> None:
    with pytest.raises(ValidationError):
        GetArticleInput.model_validate({})
    assert (
        GetArticleInput.model_validate({"slug": "circle-ipo"}).slug
        == "circle-ipo"
    )


def test_get_entity_requires_exactly_one_of_slug_or_ticker() -> None:
    with pytest.raises(ValidationError):
        GetEntityInput.model_validate({})
    with pytest.raises(ValidationError):
        GetEntityInput.model_validate({"slug": "x", "ticker": "Y"})
    assert GetEntityInput.model_validate({"slug": "ethereum"}).slug == "ethereum"
    assert GetEntityInput.model_validate({"ticker": "ETH"}).ticker == "ETH"


def test_list_entity_mentions_defaults_and_bounds() -> None:
    v = ListEntityMentionsInput.model_validate({"slug": "ethereum"})
    assert v.limit == 20
    assert v.since is None
    with pytest.raises(ValidationError):
        ListEntityMentionsInput.model_validate({})  # slug required
    with pytest.raises(ValidationError):
        ListEntityMentionsInput.model_validate({"slug": "ethereum", "limit": 500})


def test_list_topics_accepts_empty_args() -> None:
    ListTopicsInput.model_validate({})
    with pytest.raises(ValidationError):
        ListTopicsInput.model_validate({"bogus": 1})


def test_get_explainer_requires_exactly_one_of_slug_or_topic() -> None:
    with pytest.raises(ValidationError):
        GetExplainerInput.model_validate({})
    with pytest.raises(ValidationError):
        GetExplainerInput.model_validate({"slug": "a", "topic": "b"})
    assert GetExplainerInput.model_validate({"topic": "liquidity"}).topic == "liquidity"
    assert (
        GetExplainerInput.model_validate({"slug": "what-is-a-blockchain"}).slug
        == "what-is-a-blockchain"
    )


def test_get_price_requires_ids() -> None:
    with pytest.raises(ValidationError):
        GetPriceInput.model_validate({})
    v = GetPriceInput.model_validate({"ids": "bitcoin,ethereum"})
    assert v.vs == "usd"


def test_get_market_overview_defaults_limit_to_20() -> None:
    v = GetMarketOverviewInput.model_validate({})
    assert v.limit == 20
    with pytest.raises(ValidationError):
        GetMarketOverviewInput.model_validate({"limit": 500})


# --- client ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_client_injects_api_key_and_parses_envelope(httpx_mock) -> None:
    httpx_mock.add_response(
        url="https://api.blockchainacademics.com/v1/articles/search?q=ethereum&limit=10",
        json={
            "data": {"articles": [], "total": 0},
            "cite_url": "https://x.test/c",
            "as_of": "2026-04-19T00:00:00Z",
        },
        status_code=200,
    )

    c = BcaClient(api_key="test-key")
    set_client(c)
    out = await run_search_news({"query": "ethereum"})
    assert out.get("cite_url") == "https://x.test/c"
    assert out.get("as_of") == "2026-04-19T00:00:00Z"
    assert out.get("data", {}).get("total") == 0

    req = httpx_mock.get_request()
    assert req is not None
    assert req.headers.get("x-api-key") == "test-key"
    ua = req.headers.get("user-agent") or ""
    assert "bca-mcp" in ua


@pytest.mark.asyncio
async def test_client_maps_401_to_auth_error(httpx_mock) -> None:
    httpx_mock.add_response(
        url="https://api.blockchainacademics.com/v1/articles/search",
        status_code=401,
        text="nope",
    )
    c = BcaClient(api_key="bad")
    with pytest.raises(BcaAuthError):
        await c.request("/v1/articles/search")


@pytest.mark.asyncio
async def test_client_maps_4xx_to_bad_request(httpx_mock) -> None:
    httpx_mock.add_response(
        url="https://api.blockchainacademics.com/v1/articles/unknown",
        status_code=404,
        text="not found",
    )
    c = BcaClient(api_key="k")
    with pytest.raises(BcaBadRequestError):
        await c.request("/v1/articles/unknown")


@pytest.mark.asyncio
async def test_client_maps_5xx_to_upstream(httpx_mock) -> None:
    httpx_mock.add_response(
        url="https://api.blockchainacademics.com/v1/topics",
        status_code=502,
        text="bad gateway",
    )
    c = BcaClient(api_key="k")
    with pytest.raises(BcaUpstreamError):
        await c.request("/v1/topics")


@pytest.mark.asyncio
async def test_client_wraps_non_enveloped_json_under_data(httpx_mock) -> None:
    httpx_mock.add_response(
        url="https://api.blockchainacademics.com/v1/articles/search",
        json={"articles": [], "total": 0},
        status_code=200,
    )
    c = BcaClient(api_key="k")
    out = await c.request("/v1/articles/search")
    assert out.get("data", {}).get("total") == 0
    assert out.get("cite_url") is None


@pytest.mark.asyncio
async def test_integration_pending_envelope_passes_through(httpx_mock) -> None:
    """`status=integration_pending` bodies are treated as successful
    envelopes and returned verbatim; the MCP client decides how to
    surface them (mirrors the TS sibling)."""
    httpx_mock.add_response(
        url="https://api.blockchainacademics.com/v1/market/overview?limit=20",
        json={
            "data": None,
            "status": "integration_pending",
            "cite_url": None,
        },
        status_code=200,
    )
    c = BcaClient(api_key="k")
    set_client(c)
    from bca_mcp.tools.market import run_get_market_overview

    out = await run_get_market_overview({})
    assert out.get("status") == "integration_pending"
    assert out.get("data") is None


@pytest.mark.asyncio
async def test_get_article_encodes_slug(httpx_mock) -> None:
    httpx_mock.add_response(
        url="https://api.blockchainacademics.com/v1/articles/some%2Fweird%20slug",
        json={"data": {"slug": "some/weird slug", "title": "x"}},
        status_code=200,
    )
    c = BcaClient(api_key="k")
    set_client(c)
    out = await run_get_article({"slug": "some/weird slug"})
    assert out.get("data", {}).get("title") == "x"


@pytest.mark.asyncio
async def test_list_entity_mentions_hits_expected_path(httpx_mock) -> None:
    httpx_mock.add_response(
        url=(
            "https://api.blockchainacademics.com/v1/entities/ethereum/mentions"
            "?limit=5"
        ),
        json={"data": {"mentions": []}},
        status_code=200,
    )
    c = BcaClient(api_key="k")
    set_client(c)
    out = await run_list_entity_mentions({"slug": "ethereum", "limit": 5})
    assert out.get("data", {}).get("mentions") == []


def test_missing_api_key_raises_auth_error(monkeypatch) -> None:
    monkeypatch.delenv("BCA_API_KEY", raising=False)
    c = BcaClient()
    import asyncio

    with pytest.raises(BcaAuthError):
        asyncio.run(c.request("/v1/articles/search"))


# --- server registration ---------------------------------------------------


EXPECTED_TOOL_NAMES = {
    # content (6)
    "search_news",
    "get_article",
    "get_entity",
    "list_entity_mentions",
    "list_topics",
    "get_explainer",
    # market (4)
    "get_price",
    "get_market_overview",
    "get_ohlc",
    "get_pair_data",
    # onchain (4)
    "get_wallet_profile",
    "get_tx",
    "get_token_holders",
    "get_defi_protocol",
    # sentiment + social (5)
    "get_sentiment",
    "get_social_pulse",
    "get_fear_greed",
    "get_social_signals",
    "get_social_signals_detail",
    # indicators (6)
    "get_coverage_index",
    "get_narrative_strength",
    "get_sentiment_velocity",
    "get_editorial_premium",
    "get_kol_influence",
    "get_risk_score",
    # fundamentals (6)
    "get_tokenomics",
    "get_audit_reports",
    "get_team_info",
    "get_roadmap",
    "compare_protocols",
    "check_rugpull_risk",
    # agent_jobs (6)
    "generate_due_diligence",
    "generate_tokenomics_model",
    "summarize_whitepaper",
    "translate_contract",
    "monitor_keyword",
    "get_agent_job",
}


def test_server_registers_expected_tools_with_unique_names() -> None:
    names = [t.name for t in TOOLS]
    assert len(names) == 37, f"expected 37 tools, got {len(names)}: {names}"
    assert len(set(names)) == 37, f"duplicate tool name: {names}"
    assert set(names) == EXPECTED_TOOL_NAMES, (
        f"tool surface drifted: want {EXPECTED_TOOL_NAMES}, got {set(names)}"
    )


def test_build_server_without_env_check_succeeds_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("BCA_API_KEY", raising=False)
    # Should not raise — tests construct the server without a live key.
    build_server(check_env=False)


def test_build_server_with_env_check_raises_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("BCA_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="BCA_API_KEY"):
        build_server(check_env=True)


def test_build_server_with_env_check_succeeds_with_api_key(monkeypatch) -> None:
    monkeypatch.setenv("BCA_API_KEY", "test-key")
    build_server(check_env=True)
