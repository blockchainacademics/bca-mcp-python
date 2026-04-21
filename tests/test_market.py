"""Tests for batch-1 market tools: `get_ohlc` + `get_pair_data`.

Mocks the httpx transport via `pytest-httpx` so no live network calls are
made. Pair each tool with (1) a happy path exercising the exact expected
query string, and (2) a validation error path that rejects malformed input
before any HTTP call fires.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bca_mcp.client import BcaClient, set_client
from bca_mcp.tools.market import (
    GetOhlcInput,
    GetPairDataInput,
    run_get_ohlc,
    run_get_pair_data,
)


# --- get_ohlc --------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_ohlc_hits_expected_path_and_defaults(httpx_mock) -> None:
    httpx_mock.add_response(
        url=(
            "https://api.blockchainacademics.com/v1/market/ohlc"
            "?id=bitcoin&days=30&vs=usd"
        ),
        json={"data": [[1700000000000, 1.0, 2.0, 0.5, 1.5]]},
        status_code=200,
    )
    set_client(BcaClient(api_key="k"))
    out = await run_get_ohlc({"id": "bitcoin"})
    assert out.get("data") == [[1700000000000, 1.0, 2.0, 0.5, 1.5]]


def test_get_ohlc_rejects_non_kebab_id() -> None:
    # Capitalized / snake_case / dot-separated ids must all fail before
    # we ever touch the network — mirror the TS zod regex.
    with pytest.raises(ValidationError):
        GetOhlcInput.model_validate({"id": "Bitcoin"})
    with pytest.raises(ValidationError):
        GetOhlcInput.model_validate({"id": "bitcoin_cash"})
    # days out-of-range also bounces.
    with pytest.raises(ValidationError):
        GetOhlcInput.model_validate({"id": "bitcoin", "days": 1000})


# --- get_pair_data ---------------------------------------------------------


@pytest.mark.asyncio
async def test_get_pair_data_hits_expected_path(httpx_mock) -> None:
    httpx_mock.add_response(
        url=(
            "https://api.blockchainacademics.com/v1/market/pair"
            "?chain=ethereum&pair=0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        ),
        json={
            "data": {
                "baseToken": {"symbol": "X"},
                "priceUsd": "0.001",
                "liquidity": {"usd": 5000},
            }
        },
        status_code=200,
    )
    set_client(BcaClient(api_key="k"))
    out = await run_get_pair_data(
        {"chain": "ethereum", "pair": "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"}
    )
    assert out.get("data", {}).get("priceUsd") == "0.001"


def test_get_pair_data_rejects_non_alphanumeric_pair() -> None:
    with pytest.raises(ValidationError):
        # hyphens / 0x-minus / invalid chars in pair address
        GetPairDataInput.model_validate({"chain": "ethereum", "pair": "not-a-pair!"})
    with pytest.raises(ValidationError):
        # missing required pair
        GetPairDataInput.model_validate({"chain": "ethereum"})
    with pytest.raises(ValidationError):
        # uppercase/bad chain slug
        GetPairDataInput.model_validate({"chain": "Ethereum", "pair": "abc123"})
