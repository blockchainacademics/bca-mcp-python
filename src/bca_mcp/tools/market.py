"""Market data tools (category 2).

Wraps `/v1/market/*` — aggregated via CoinGecko + DexScreener free tiers.
Shapes match backend query-string API, not path API. Ports
`src/tools/market.ts` subset — `get_price` + `get_market_overview` only in
the v0.1 scaffold.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from bca_mcp.client import get_client
from bca_mcp.types import ResponseEnvelope

# --- get_price -------------------------------------------------------------

GET_PRICE_TOOL_NAME = "get_price"

GET_PRICE_TOOL_DESCRIPTION = (
    "Spot price + 24h / 7d / 30d change for one or more tokens, via "
    "CoinGecko. Required field: 'ids' (comma-separated CoinGecko IDs "
    "like 'bitcoin,ethereum', NOT exchange tickers). Optional 'vs' "
    "quote currency defaults to usd."
)


class GetPriceInput(BaseModel):
    model_config = {"extra": "forbid"}

    ids: str = Field(
        min_length=1,
        description="CoinGecko id(s), comma-separated. E.g. 'bitcoin,ethereum'.",
    )
    vs: str = Field(
        default="usd",
        description="Quote currency (default usd).",
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
    "Top-N tokens by market cap with volume, 24h change, and category "
    "tags. No required fields; optional 'limit' defaults to 20 (max 100). "
    "Use for market-wide context (bull/bear posture, mover spotting)."
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
