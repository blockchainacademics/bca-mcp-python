"""Tests for batch-3 proprietary-indicator tools + get_defi_protocol.

Covers the six indicator tools (`get_coverage_index`,
`get_narrative_strength`, `get_sentiment_velocity`,
`get_editorial_premium`, `get_kol_influence`, `get_risk_score`) and the
DeFi snapshot tool (`get_defi_protocol`, which lives in onchain.py but
was ported alongside this batch).

Mocks the httpx transport via `pytest-httpx` — never hits upstream.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bca_mcp.client import BcaClient, set_client
from bca_mcp.tools.indicators import (
    GetCoverageIndexInput,
    GetEditorialPremiumInput,
    GetKolInfluenceInput,
    GetNarrativeStrengthInput,
    GetRiskScoreInput,
    GetSentimentVelocityInput,
    run_get_coverage_index,
    run_get_editorial_premium,
    run_get_kol_influence,
    run_get_narrative_strength,
    run_get_risk_score,
    run_get_sentiment_velocity,
)
from bca_mcp.tools.onchain import GetDefiProtocolInput, run_get_defi_protocol


# --- get_coverage_index ----------------------------------------------------


@pytest.mark.asyncio
async def test_get_coverage_index_defaults_window_to_7d(httpx_mock) -> None:
    httpx_mock.add_response(
        url=(
            "https://api.blockchainacademics.com/v1/indicators/coverage"
            "?entity_slug=ethereum&window=7d"
        ),
        json={
            "data": {
                "entity_slug": "ethereum",
                "indicator": "coverage",
                "window": "7d",
                "value": 0.82,
            }
        },
        status_code=200,
    )
    set_client(BcaClient(api_key="k"))
    out = await run_get_coverage_index({"entity_slug": "ethereum"})
    assert out.get("data", {}).get("value") == 0.82


def test_get_coverage_index_rejects_bad_slug_and_window() -> None:
    with pytest.raises(ValidationError):
        GetCoverageIndexInput.model_validate({"entity_slug": "Bad!"})
    with pytest.raises(ValidationError):
        GetCoverageIndexInput.model_validate(
            {"entity_slug": "ethereum", "window": "2d"}
        )


# --- get_narrative_strength ------------------------------------------------


@pytest.mark.asyncio
async def test_get_narrative_strength_accepts_30d_window(httpx_mock) -> None:
    httpx_mock.add_response(
        url=(
            "https://api.blockchainacademics.com/v1/indicators/narrative"
            "?entity_slug=ai-agents&window=30d"
        ),
        json={"data": {"value": 0.91}},
        status_code=200,
    )
    set_client(BcaClient(api_key="k"))
    out = await run_get_narrative_strength(
        {"entity_slug": "ai-agents", "window": "30d"}
    )
    assert out.get("data", {}).get("value") == 0.91


def test_get_narrative_strength_default_window() -> None:
    assert (
        GetNarrativeStrengthInput.model_validate(
            {"entity_slug": "modular"}
        ).window
        == "7d"
    )


# --- get_sentiment_velocity ------------------------------------------------


@pytest.mark.asyncio
async def test_get_sentiment_velocity_hits_expected_path(httpx_mock) -> None:
    httpx_mock.add_response(
        url=(
            "https://api.blockchainacademics.com/v1/indicators/sentiment-velocity"
            "?entity_slug=solana&window=7d"
        ),
        json={"data": {"value": 0.12}},
        status_code=200,
    )
    set_client(BcaClient(api_key="k"))
    out = await run_get_sentiment_velocity({"entity_slug": "solana"})
    assert out.get("data", {}).get("value") == 0.12


def test_get_sentiment_velocity_default_window() -> None:
    assert (
        GetSentimentVelocityInput.model_validate(
            {"entity_slug": "solana"}
        ).window
        == "7d"
    )


# --- get_editorial_premium (default 30d) -----------------------------------


@pytest.mark.asyncio
async def test_get_editorial_premium_defaults_window_to_30d(
    httpx_mock,
) -> None:
    httpx_mock.add_response(
        url=(
            "https://api.blockchainacademics.com/v1/indicators/editorial-premium"
            "?entity_slug=bitcoin&window=30d"
        ),
        json={"data": {"value": 0.44}},
        status_code=200,
    )
    set_client(BcaClient(api_key="k"))
    out = await run_get_editorial_premium({"entity_slug": "bitcoin"})
    assert out.get("data", {}).get("value") == 0.44


def test_get_editorial_premium_default_window_is_30d() -> None:
    assert (
        GetEditorialPremiumInput.model_validate(
            {"entity_slug": "bitcoin"}
        ).window
        == "30d"
    )


# --- get_kol_influence (default 30d) ---------------------------------------


@pytest.mark.asyncio
async def test_get_kol_influence_defaults_window_to_30d(httpx_mock) -> None:
    httpx_mock.add_response(
        url=(
            "https://api.blockchainacademics.com/v1/indicators/kol-influence"
            "?entity_slug=vitalik-buterin&window=30d"
        ),
        json={"data": {"value": 0.97}},
        status_code=200,
    )
    set_client(BcaClient(api_key="k"))
    out = await run_get_kol_influence({"entity_slug": "vitalik-buterin"})
    assert out.get("data", {}).get("value") == 0.97


def test_get_kol_influence_default_window_is_30d() -> None:
    assert (
        GetKolInfluenceInput.model_validate(
            {"entity_slug": "vitalik-buterin"}
        ).window
        == "30d"
    )


# --- get_risk_score (no window) --------------------------------------------


@pytest.mark.asyncio
async def test_get_risk_score_has_no_window_param(httpx_mock) -> None:
    httpx_mock.add_response(
        url=(
            "https://api.blockchainacademics.com/v1/indicators/risk"
            "?entity_slug=terra-luna"
        ),
        json={"data": {"entity_slug": "terra-luna", "score": 0.85}},
        status_code=200,
    )
    set_client(BcaClient(api_key="k"))
    out = await run_get_risk_score({"entity_slug": "terra-luna"})
    assert out.get("data", {}).get("score") == 0.85


def test_get_risk_score_rejects_extra_window_field() -> None:
    # model_config = forbid — window is NOT allowed on risk (composite
    # is as-of-latest).
    with pytest.raises(ValidationError):
        GetRiskScoreInput.model_validate(
            {"entity_slug": "terra-luna", "window": "7d"}
        )


# --- get_defi_protocol -----------------------------------------------------


@pytest.mark.asyncio
async def test_get_defi_protocol_hits_expected_path(httpx_mock) -> None:
    httpx_mock.add_response(
        url=(
            "https://api.blockchainacademics.com/v1/onchain/defi"
            "?protocol=aave"
        ),
        json={"data": {"protocol": "aave", "tvl": 12345678.0}},
        status_code=200,
    )
    set_client(BcaClient(api_key="k"))
    out = await run_get_defi_protocol({"protocol": "aave"})
    assert out.get("data", {}).get("protocol") == "aave"


def test_get_defi_protocol_rejects_non_slug_protocol() -> None:
    with pytest.raises(ValidationError):
        GetDefiProtocolInput.model_validate({"protocol": "Aave V3!"})
    with pytest.raises(ValidationError):
        GetDefiProtocolInput.model_validate({"protocol": ""})
