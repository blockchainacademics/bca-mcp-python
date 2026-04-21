"""Tests for batch-2 sentiment + social-signal tools.

Covers `get_sentiment`, `get_social_pulse` (integration_pending
passthrough), `get_fear_greed`, `get_social_signals`,
`get_social_signals_detail`. Mocks the httpx transport via
`pytest-httpx` — never hits a live upstream.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bca_mcp.client import BcaClient, set_client
from bca_mcp.tools.sentiment import (
    GetFearGreedInput,
    GetSentimentInput,
    GetSocialPulseInput,
    GetSocialSignalsDetailInput,
    GetSocialSignalsInput,
    run_get_fear_greed,
    run_get_sentiment,
    run_get_social_pulse,
    run_get_social_signals,
    run_get_social_signals_detail,
)


# --- get_sentiment ---------------------------------------------------------


@pytest.mark.asyncio
async def test_get_sentiment_defaults_window_to_7d(httpx_mock) -> None:
    httpx_mock.add_response(
        url=(
            "https://api.blockchainacademics.com/v1/sentiment"
            "?entity_slug=ethereum&window=7d"
        ),
        json={
            "data": {
                "entity_slug": "ethereum",
                "window": "7d",
                "bucket": "bullish",
            }
        },
        status_code=200,
    )
    set_client(BcaClient(api_key="k"))
    out = await run_get_sentiment({"entity_slug": "ethereum"})
    assert out.get("data", {}).get("bucket") == "bullish"


def test_get_sentiment_rejects_invalid_slug_and_window() -> None:
    with pytest.raises(ValidationError):
        GetSentimentInput.model_validate({"entity_slug": "Bad Slug!"})
    with pytest.raises(ValidationError):
        GetSentimentInput.model_validate(
            {"entity_slug": "ethereum", "window": "2d"}
        )


# --- get_social_pulse (integration_pending passthrough) --------------------


@pytest.mark.asyncio
async def test_get_social_pulse_passes_through_integration_pending(
    httpx_mock,
) -> None:
    """The backend currently returns an integration_pending envelope —
    the Python client should pass it through unchanged (mirrors TS)."""
    httpx_mock.add_response(
        url=(
            "https://api.blockchainacademics.com/v1/sentiment/social"
            "?entity_slug=solana&window=7d"
        ),
        json={
            "data": None,
            "status": "integration_pending",
            "cite_url": None,
        },
        status_code=200,
    )
    set_client(BcaClient(api_key="k"))
    out = await run_get_social_pulse({"entity_slug": "solana"})
    assert out.get("status") == "integration_pending"
    assert out.get("data") is None


def test_get_social_pulse_input_validates_slug() -> None:
    with pytest.raises(ValidationError):
        GetSocialPulseInput.model_validate({"entity_slug": "BAD"})


# --- get_fear_greed --------------------------------------------------------


@pytest.mark.asyncio
async def test_get_fear_greed_defaults_days_to_30(httpx_mock) -> None:
    httpx_mock.add_response(
        url=(
            "https://api.blockchainacademics.com/v1/sentiment/fear-greed"
            "?days=30"
        ),
        json={"data": {"current": 55, "label": "Greed"}},
        status_code=200,
    )
    set_client(BcaClient(api_key="k"))
    out = await run_get_fear_greed({})
    assert out.get("data", {}).get("label") == "Greed"


def test_get_fear_greed_rejects_out_of_range_days() -> None:
    with pytest.raises(ValidationError):
        GetFearGreedInput.model_validate({"days": 0})
    with pytest.raises(ValidationError):
        GetFearGreedInput.model_validate({"days": 500})


# --- get_social_signals ----------------------------------------------------


@pytest.mark.asyncio
async def test_get_social_signals_defaults_limit_to_50(httpx_mock) -> None:
    httpx_mock.add_response(
        url="https://api.blockchainacademics.com/v1/social-signals?limit=50",
        json={"data": []},
        status_code=200,
    )
    set_client(BcaClient(api_key="k"))
    out = await run_get_social_signals({})
    assert isinstance(out.get("data"), list)


def test_get_social_signals_rejects_oversize_limit() -> None:
    with pytest.raises(ValidationError):
        GetSocialSignalsInput.model_validate({"limit": 500})


# --- get_social_signals_detail ---------------------------------------------


@pytest.mark.asyncio
async def test_get_social_signals_detail_hits_path_with_symbol(
    httpx_mock,
) -> None:
    httpx_mock.add_response(
        url="https://api.blockchainacademics.com/v1/social-signals/BTC",
        json={"data": {"symbol": "BTC", "signal": "strong"}},
        status_code=200,
    )
    set_client(BcaClient(api_key="k"))
    out = await run_get_social_signals_detail({"symbol": "BTC"})
    assert out.get("data", {}).get("symbol") == "BTC"


def test_get_social_signals_detail_rejects_invalid_symbol() -> None:
    # Non-alphanumeric rejected.
    with pytest.raises(ValidationError):
        GetSocialSignalsDetailInput.model_validate({"symbol": "BTC-USD"})
    # Empty rejected.
    with pytest.raises(ValidationError):
        GetSocialSignalsDetailInput.model_validate({"symbol": ""})
    # Too long (>12) rejected.
    with pytest.raises(ValidationError):
        GetSocialSignalsDetailInput.model_validate({"symbol": "A" * 20})
