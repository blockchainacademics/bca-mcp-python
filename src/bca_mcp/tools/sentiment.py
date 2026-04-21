"""Sentiment + social-signal tools (category 4, batch 2 port).

Wraps `/v1/sentiment/*` and `/v1/social-signals/*`. Ports five tools from
`src/tools/sentiment.ts` (`get_sentiment`, `get_social_pulse`,
`get_fear_greed`) and `src/tools/extended.ts::Social signals` section
(`get_social_signals`, `get_social_signals_detail`).

`get_social_pulse` is currently flagged `integration_pending` upstream —
the backend returns `{data: null, status: "integration_pending"}` and our
client passes that envelope through unchanged (tested in
`tests/test_smoke.py::test_integration_pending_envelope_passes_through`).
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from pydantic import BaseModel, Field

from bca_mcp.client import get_client
from bca_mcp.types import SLUG_REGEX, TICKER_REGEX, ResponseEnvelope, Window

# --- get_sentiment ---------------------------------------------------------

GET_SENTIMENT_TOOL_NAME = "get_sentiment"

GET_SENTIMENT_TOOL_DESCRIPTION = (
    "BCA editorial sentiment bucket (bullish/bearish/neutral/mixed) for "
    "an entity with bucket drivers."
)


class GetSentimentInput(BaseModel):
    model_config = {"extra": "forbid"}

    entity_slug: str = Field(
        min_length=1,
        max_length=240,
        pattern=SLUG_REGEX,
        description="Entity slug.",
    )
    window: Window = Field(
        default="7d",
        description="Rolling window.",
    )


def get_sentiment_input_schema() -> dict[str, Any]:
    return GetSentimentInput.model_json_schema()


async def run_get_sentiment(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetSentimentInput.model_validate(args)
    return await get_client().request(
        "/v1/sentiment",
        {"entity_slug": parsed.entity_slug, "window": parsed.window},
    )


# --- get_social_pulse ------------------------------------------------------

GET_SOCIAL_PULSE_TOOL_NAME = "get_social_pulse"

GET_SOCIAL_PULSE_TOOL_DESCRIPTION = (
    "Social velocity: mentions, engagement, sentiment across "
    "Twitter/Reddit/Discord. Pro tier. Returns BCA_NOT_IMPLEMENTED if "
    "social ingest not yet wired."
)


class GetSocialPulseInput(BaseModel):
    model_config = {"extra": "forbid"}

    entity_slug: str = Field(
        min_length=1,
        max_length=240,
        pattern=SLUG_REGEX,
        description="Entity slug.",
    )
    window: Window = Field(
        default="7d",
        description="Rolling window.",
    )


def get_social_pulse_input_schema() -> dict[str, Any]:
    return GetSocialPulseInput.model_json_schema()


async def run_get_social_pulse(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetSocialPulseInput.model_validate(args)
    return await get_client().request(
        "/v1/sentiment/social",
        {"entity_slug": parsed.entity_slug, "window": parsed.window},
    )


# --- get_fear_greed --------------------------------------------------------

GET_FEAR_GREED_TOOL_NAME = "get_fear_greed"

GET_FEAR_GREED_TOOL_DESCRIPTION = (
    "Crypto Fear & Greed Index (Alternative.me) — historical series + "
    "BCA interpretation."
)


class GetFearGreedInput(BaseModel):
    model_config = {"extra": "forbid"}

    days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Lookback days.",
    )


def get_fear_greed_input_schema() -> dict[str, Any]:
    return GetFearGreedInput.model_json_schema()


async def run_get_fear_greed(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetFearGreedInput.model_validate(args)
    return await get_client().request(
        "/v1/sentiment/fear-greed",
        {"days": parsed.days},
    )


# --- get_social_signals ----------------------------------------------------

GET_SOCIAL_SIGNALS_TOOL_NAME = "get_social_signals"

GET_SOCIAL_SIGNALS_TOOL_DESCRIPTION = "Cross-symbol social signal feed."


class GetSocialSignalsInput(BaseModel):
    model_config = {"extra": "forbid"}

    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Top-N signals to return.",
    )


def get_social_signals_input_schema() -> dict[str, Any]:
    return GetSocialSignalsInput.model_json_schema()


async def run_get_social_signals(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetSocialSignalsInput.model_validate(args)
    return await get_client().request(
        "/v1/social-signals",
        {"limit": parsed.limit},
    )


# --- get_social_signals_detail ---------------------------------------------

GET_SOCIAL_SIGNALS_DETAIL_TOOL_NAME = "get_social_signals_detail"

GET_SOCIAL_SIGNALS_DETAIL_TOOL_DESCRIPTION = (
    "Social signal detail for a single symbol."
)


class GetSocialSignalsDetailInput(BaseModel):
    model_config = {"extra": "forbid"}

    symbol: str = Field(
        min_length=1,
        max_length=12,
        pattern=TICKER_REGEX,
        description="Ticker symbol (1-12 alphanumerics, e.g. 'BTC').",
    )


def get_social_signals_detail_input_schema() -> dict[str, Any]:
    return GetSocialSignalsDetailInput.model_json_schema()


async def run_get_social_signals_detail(
    args: dict[str, Any],
) -> ResponseEnvelope[Any]:
    parsed = GetSocialSignalsDetailInput.model_validate(args)
    return await get_client().request(
        f"/v1/social-signals/{quote(parsed.symbol, safe='')}",
    )
