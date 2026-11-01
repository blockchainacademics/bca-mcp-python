"""Request shapes the API actually accepts (F34, F38, shared decision 4).

The three service tools mirror the API request models in
blockchainacademics-api app/api/v1/services.py, translate_contract sends
the API's `code` field, and get_as_of_snapshot (new in the Python package)
calls the same route as the TS sibling. Every HTTP call is mocked.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from bca_mcp.client import BcaClient, set_client
from bca_mcp.server import TOOLS
from bca_mcp.tools.agent_jobs import TranslateContractInput, run_translate_contract
from bca_mcp.tools.content import run_get_as_of_snapshot
from bca_mcp.tools.extended import (
    BookKolCampaignInput,
    RequestCustomResearchInput,
    SubmitListingInput,
    _run_book_kol_campaign,
    _run_request_custom_research,
    _run_submit_listing,
)

BASE = "https://api.blockchainacademics.com"
CREATED = {
    "data": {"request_id": "42", "status": "new", "next_step": "We will email you."}
}


@pytest.fixture(autouse=True)
def _client():
    set_client(BcaClient(api_key="k"))
    yield


def _description(name: str) -> str:
    return next(t.description for t in TOOLS if t.name == name)


# --- book_kol_campaign -----------------------------------------------------

KOL_OK = {
    "contact_email": "ops@example.com",
    "project_name": "Example Protocol",
    "campaign_type": "thread",
    "budget_usd": 500,
}


def test_book_kol_campaign_requires_the_api_fields() -> None:
    for missing in ("contact_email", "project_name", "campaign_type", "budget_usd"):
        payload = {k: v for k, v in KOL_OK.items() if k != missing}
        with pytest.raises(ValidationError):
            BookKolCampaignInput.model_validate(payload)
    with pytest.raises(ValidationError):
        BookKolCampaignInput.model_validate({**KOL_OK, "budget_usd": 499})
    with pytest.raises(ValidationError):
        BookKolCampaignInput.model_validate({**KOL_OK, "budget_usd": 2_000_001})
    with pytest.raises(ValidationError):
        BookKolCampaignInput.model_validate({**KOL_OK, "campaign_type": "tweet"})
    with pytest.raises(ValidationError):
        BookKolCampaignInput.model_validate({**KOL_OK, "objective": "old 0.6.2 field"})
    for kind in ("thread", "video", "space", "podcast", "hybrid"):
        BookKolCampaignInput.model_validate({**KOL_OK, "campaign_type": kind})


@pytest.mark.asyncio
async def test_book_kol_campaign_posts_only_api_fields(httpx_mock) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/v1/services/book-kol-campaign", method="POST",
        status_code=201, json=CREATED,
    )
    out = await _run_book_kol_campaign(
        {**KOL_OK, "target_chains": ["solana", "base"], "notes": "Launch in May."}
    )
    assert out["data"]["request_id"] == "42"
    sent = json.loads(httpx_mock.get_request().content)
    assert sent == {
        "contact_email": "ops@example.com",
        "project_name": "Example Protocol",
        "campaign_type": "thread",
        "budget_usd": 500,
        "target_chains": ["solana", "base"],
        "notes": "Launch in May.",
    }


def test_book_kol_campaign_description() -> None:
    d = _description("book_kol_campaign")
    for word in ("project_name", "campaign_type", "budget_usd", "request_id", "next_step"):
        assert word in d
    assert "Pro tier" not in d and "campaign_id" not in d


# --- submit_listing --------------------------------------------------------

LISTING_OK = {
    "contact_email": "team@example.com",
    "directory": "trading_bots",
    "listing_name": "Example Bot",
    "listing_url": "https://example.com",
    "description": "A grid trading bot for Solana DEXs.",
}


def test_submit_listing_requires_the_api_fields() -> None:
    for missing in ("contact_email", "directory", "listing_name", "listing_url", "description"):
        payload = {k: v for k, v in LISTING_OK.items() if k != missing}
        with pytest.raises(ValidationError):
            SubmitListingInput.model_validate(payload)
    with pytest.raises(ValidationError):  # hyphen slugs were the 0.6.2 bug
        SubmitListingInput.model_validate({**LISTING_OK, "directory": "trading-bots"})
    with pytest.raises(ValidationError):
        SubmitListingInput.model_validate({**LISTING_OK, "description": "too short"})
    with pytest.raises(ValidationError):
        SubmitListingInput.model_validate({**LISTING_OK, "listing_url": "ftp://example.com"})
    with pytest.raises(ValidationError):
        SubmitListingInput.model_validate({**LISTING_OK, "entity": "example"})
    for d in ("vcs", "aggregators", "trading_bots", "mcps", "nft_communities",
              "jobs", "stablecoins", "trading_yields"):
        SubmitListingInput.model_validate({**LISTING_OK, "directory": d})


@pytest.mark.asyncio
async def test_submit_listing_posts_only_api_fields(httpx_mock) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/v1/services/submit-listing", method="POST",
        status_code=201, json=CREATED,
    )
    await _run_submit_listing({**LISTING_OK, "tags": ["solana"]})
    sent = json.loads(httpx_mock.get_request().content)
    assert sent == {**LISTING_OK, "tags": ["solana"]}


# --- request_custom_research -----------------------------------------------


def test_request_custom_research_topic_needs_four_characters() -> None:
    base = {"contact_email": "a@example.com"}
    with pytest.raises(ValidationError):
        RequestCustomResearchInput.model_validate({**base, "topic": "BTC"})
    with pytest.raises(ValidationError):
        RequestCustomResearchInput.model_validate({**base, "topic": "x" * 241})
    with pytest.raises(ValidationError):  # never read by the API
        RequestCustomResearchInput.model_validate({**base, "topic": "Restaking", "deadline_days": 7})
    v = RequestCustomResearchInput.model_validate({**base, "topic": "Restaking"})
    assert v.depth == "standard" and v.target_wordcount == 3000


@pytest.mark.asyncio
async def test_request_custom_research_posts_api_fields(httpx_mock) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/v1/services/custom-research", method="POST",
        status_code=201, json=CREATED,
    )
    await _run_request_custom_research(
        {"contact_email": "a@example.com", "topic": "Restaking risk", "deadline": "within 2 weeks"}
    )
    sent = json.loads(httpx_mock.get_request().content)
    assert sent == {
        "contact_email": "a@example.com",
        "topic": "Restaking risk",
        "depth": "standard",
        "target_wordcount": 3000,
        "deadline": "within 2 weeks",
    }


def test_service_descriptions_drop_pro_tier_and_old_ids() -> None:
    for name in ("book_kol_campaign", "request_custom_research", "submit_listing"):
        d = _description(name)
        assert "Pro tier" not in d, name
        assert "order_id" not in d and "campaign_id" not in d, name
        assert "request_id, status and next_step" in d, name


# --- translate_contract (F38) ----------------------------------------------


def test_translate_contract_takes_code() -> None:
    with pytest.raises(ValidationError):
        TranslateContractInput.model_validate(
            {"source_code": "contract A {}", "source_language": "solidity", "target_language": "vyper"}
        )
    v = TranslateContractInput.model_validate(
        {"code": "contract A {}", "source_language": "solidity", "target_language": "vyper"}
    )
    assert v.code == "contract A {}"
    assert "Required: code," in _description("translate_contract")


@pytest.mark.asyncio
async def test_translate_contract_sends_code(httpx_mock) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/v1/agent-jobs/translate-contract", method="POST",
        status_code=202, json={"data": {"job_id": "j1", "status_url": "/v1/agent-jobs/j1"}},
    )
    await run_translate_contract(
        {"code": "contract A {}", "source_language": "solidity", "target_language": "move"}
    )
    sent = json.loads(httpx_mock.get_request().content)
    assert sent == {
        "code": "contract A {}",
        "source_language": "solidity",
        "target_language": "move",
    }


# --- get_as_of_snapshot (F38) ----------------------------------------------


@pytest.mark.asyncio
async def test_get_as_of_snapshot_calls_article_search(httpx_mock) -> None:
    httpx_mock.add_response(
        url=(
            f"{BASE}/v1/articles/search?as_of=2026-10-15T00%3A00%3A00Z"
            "&q=binance&entity=binance&limit=5"
        ),
        json={"data": {"articles": [{"slug": "a"}], "total": 1}},
    )
    out = await run_get_as_of_snapshot(
        {"as_of": "2026-10-15T00:00:00Z", "query": "binance", "entity": "binance", "limit": 5}
    )
    assert out["data"]["total"] == 1


@pytest.mark.asyncio
async def test_get_as_of_snapshot_defaults(httpx_mock) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/v1/articles/search?as_of=2026-01-01&limit=20",
        json={"data": {"articles": [], "total": 0}},
    )
    await run_get_as_of_snapshot({"as_of": "2026-01-01"})
    with pytest.raises(ValidationError):
        await run_get_as_of_snapshot({"query": "x"})  # as_of is required
