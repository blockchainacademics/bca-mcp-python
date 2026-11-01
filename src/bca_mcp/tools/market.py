"""Market data tools (category 2).

Wraps `/v1/market/*` — aggregated via CoinGecko + DexScreener free tiers.
Shapes match backend query-string API, not path API. Ports
`src/tools/market.ts` — `get_price`, `get_market_overview`, `get_ohlc`,
`get_pair_data`.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from bca_mcp.client import get_client
from bca_mcp.types import ResponseEnvelope

# --- get_price -------------------------------------------------------------

GET_PRICE_TOOL_NAME = "get_price"

GET_PRICE_TOOL_DESCRIPTION = (
    "Spot price, market cap, 24h volume and 24h change for up to 50 "
    "tokens, via CoinGecko. Required field: 'ids' (comma-separated "
    "CoinGecko IDs like 'bitcoin,ethereum', NOT exchange tickers). "
    "Optional 'vs' quote currency defaults to usd. Works without an API key."
)

# The API's quote currency rule: 3 to 10 lower case letters (usd, eur, btc).
_VS_REGEX = r"^[a-z]{3,10}$"
# 1 to 50 comma-separated CoinGecko ids (the API's cap per call).
_COINGECKO_IDS_REGEX = r"^[a-z0-9]+(?:-[a-z0-9]+)*(?:,[a-z0-9]+(?:-[a-z0-9]+)*){0,49}$"


class GetPriceInput(BaseModel):
    model_config = {"extra": "forbid"}

    ids: str = Field(
        min_length=1,
        max_length=512,
        pattern=_COINGECKO_IDS_REGEX,
        description="CoinGecko id(s), comma-separated, up to 50. E.g. 'bitcoin,ethereum'.",
    )
    vs: str = Field(
        default="usd",
        min_length=3,
        max_length=10,
        pattern=_VS_REGEX,
        description="Quote currency, 3-10 lowercase letters (default usd).",
    )


def get_price_input_schema() -> dict[str, Any]:
    return GetPriceInput.model_json_schema()


async def run_get_price(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetPriceInput.model_validate(args)
    return await get_client().request(
        "/v1/market/price",
        {"ids": parsed.ids, "vs": parsed.vs},
    )


# --- get_market_overview ---------------------------------------------------

GET_MARKET_OVERVIEW_TOOL_NAME = "get_market_overview"

GET_MARKET_OVERVIEW_TOOL_DESCRIPTION = (
    "Top-N tokens by market cap from CoinGecko: price, market cap, 24h "
    "volume and 1h, 24h and 7d change. No required fields; optional "
    "'limit' defaults to 20 (max 100). Use for market-wide context "
    "(bull/bear posture, mover spotting). Works without an API key."
)


class GetMarketOverviewInput(BaseModel):
    model_config = {"extra": "forbid"}

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Top N by mcap.",
    )


def get_market_overview_input_schema() -> dict[str, Any]:
    return GetMarketOverviewInput.model_json_schema()


async def run_get_market_overview(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetMarketOverviewInput.model_validate(args)
    return await get_client().request(
        "/v1/market/overview",
        {"limit": parsed.limit},
    )


# --- get_ohlc --------------------------------------------------------------

GET_OHLC_TOOL_NAME = "get_ohlc"

GET_OHLC_TOOL_DESCRIPTION = (
    "OHLC candlestick history for a token from CoinGecko: rows of "
    "[timestamp, open, high, low, close] over 1 to 365 days. Starter tier. "
    "Useful for technical-setup agents and backtesting."
)


class GetOhlcInput(BaseModel):
    model_config = {"extra": "forbid"}

    id: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="CoinGecko id (e.g. 'bitcoin').",
    )
    days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Lookback days (1-365).",
    )
    vs: str = Field(
        default="usd",
        min_length=3,
        max_length=10,
        pattern=_VS_REGEX,
        description="Quote currency (default usd).",
    )


def get_ohlc_input_schema() -> dict[str, Any]:
    return GetOhlcInput.model_json_schema()


async def run_get_ohlc(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetOhlcInput.model_validate(args)
    return await get_client().request(
        "/v1/market/ohlc",
        {"id": parsed.id, "days": parsed.days, "vs": parsed.vs},
    )


# --- get_pair_data ---------------------------------------------------------

GET_PAIR_DATA_TOOL_NAME = "get_pair_data"

GET_PAIR_DATA_TOOL_DESCRIPTION = (
    "DEX pair analytics: liquidity, 24h volume, pair age, price. Via "
    "DexScreener. Starter tier."
)


class GetPairDataInput(BaseModel):
    model_config = {"extra": "forbid"}

    chain: str = Field(
        min_length=2,
        max_length=32,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="Chain slug (e.g. 'ethereum', 'solana', 'bsc').",
    )
    pair: str = Field(
        min_length=32,
        max_length=66,
        pattern=r"^[A-Za-z0-9]+$",
        description="Pair contract address (32 to 66 characters).",
    )


def get_pair_data_input_schema() -> dict[str, Any]:
    return GetPairDataInput.model_json_schema()


async def run_get_pair_data(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetPairDataInput.model_validate(args)
    return await get_client().request(
        "/v1/market/pair",
        {"chain": parsed.chain, "pair": parsed.pair},
    )
