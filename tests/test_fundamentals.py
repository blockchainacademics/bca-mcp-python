"""Tests for batch-4 fundamentals tools.

Covers `get_tokenomics`, `compare_protocols`, `check_rugpull_risk`.
Mocks httpx via `pytest-httpx`. Asserts URL shape, query arg passthrough,
and pydantic validation bounds.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bca_mcp.client import BcaClient, set_client
from bca_mcp.tools.fundamentals import (
    CompareProtocolsInput,
    GetTokenomicsInput,
    run_check_rugpull_risk,
    run_compare_protocols,
    run_get_tokenomics,
)


# --- get_tokenomics -------------------------------------------------------


@pytest.mark.asyncio
async def test_get_tokenomics_hits_expected_path(httpx_mock) -> None:
    httpx_mock.add_response(
        url=(
            "https://api.blockchainacademics.com/v1/fundamentals/tokenomics"
            "?entity_slug=ethereum"
        ),
        json={"data": {"circulating": 120_000_000}},
        status_code=200,
    )
    set_client(BcaClient(api_key="k"))
    out = await run_get_tokenomics({"entity_slug": "ethereum"})
    assert out.get("data", {}).get("circulating") == 120_000_000


def test_get_tokenomics_rejects_bad_slug() -> None:
    with pytest.raises(ValidationError):
        GetTokenomicsInput.model_validate({"entity_slug": "Not A Slug!"})
    with pytest.raises(ValidationError):
        GetTokenomicsInput.model_validate({})


# --- compare_protocols ---------------------------------------------------


@pytest.mark.asyncio
async def test_compare_protocols_accepts_csv_slugs(httpx_mock) -> None:
    httpx_mock.add_response(
        url=(
            "https://api.blockchainacademics.com/v1/fundamentals/compare"
            "?entity_slugs=aave,compound,morpho-blue"
        ),
        json={"data": {"rows": []}},
        status_code=200,
    )
    set_client(BcaClient(api_key="k"))
    out = await run_compare_protocols(
        {"entity_slugs": "aave,compound,morpho-blue"}
    )
    assert "rows" in out.get("data", {})


def test_compare_protocols_rejects_malformed_csv() -> None:
    # trailing comma not allowed by regex
    with pytest.raises(ValidationError):
        CompareProtocolsInput.model_validate({"entity_slugs": "aave,"})
    # spaces not allowed
    with pytest.raises(ValidationError):
        CompareProtocolsInput.model_validate({"entity_slugs": "aave, compound"})


# --- check_rugpull_risk --------------------------------------------------


@pytest.mark.asyncio
async def test_check_rugpull_risk_hits_expected_path(httpx_mock) -> None:
    httpx_mock.add_response(
        url=(
            "https://api.blockchainacademics.com/v1/fundamentals/rugpull"
            "?entity_slug=dogecoin"
        ),
        json={"data": {"risk_score": 0.42}},
        status_code=200,
    )
    set_client(BcaClient(api_key="k"))
    out = await run_check_rugpull_risk({"entity_slug": "dogecoin"})
    assert out.get("data", {}).get("risk_score") == 0.42
