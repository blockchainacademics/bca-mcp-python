"""Sentiment + social-signal tools (category 4, batch 2 port).

Wraps `/v1/sentiment/*` and `/v1/social-signals/*`. Ports five tools from
`src/tools/sentiment.ts` (`get_sentiment`, `get_social_pulse`,
`get_fear_greed`) and `src/tools/extended.ts::Social signals` section
(`get_social_signals`, `get_social_signals_detail`).

`get_social_pulse` is live as of 0.6.0 (crypto Twitter sentiment). The
client still passes an `integration_pending` envelope through unchanged
when a backend source is unconfigured (tested in
`tests/test_smoke.py::test_integration_pending_envelope_passes_through`).

0.6.0 adds the crypto Twitter intelligence tools (`get_ct_pulse`,
`get_x_signals`, `get_kol_consensus`), mirroring `src/tools/sentiment.ts`.
"""

from __future__ import annotations

from typing import Any, Literal
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
    "How crypto Twitter is talking about an entity: CT sentiment score "
    "(-1 to 1), label, mention trend, bull and bear points, narratives, and "
    "notable posts. BCA analysis in its own words, with X post URLs as "
    "citations. Pro tier."
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


# --- get_ct_pulse ----------------------------------------------------------

GET_CT_PULSE_TOOL_NAME = "get_ct_pulse"

GET_CT_PULSE_TOOL_DESCRIPTION = (
    "What crypto Twitter is saying in the last 24h: one-line takeaway, top "
    "stories, narratives heating or cooling, hard numbers with their source "
    "URL, and notable posts from credible accounts. Without a topic it "
    "returns the latest scheduled market snapshot. BCA analysis plus X post "
    "links, never reposted post text. Pro tier."
)


class GetCtPulseInput(BaseModel):
    model_config = {"extra": "forbid"}

    topic: str | None = Field(
        default=None,
        min_length=2,
        max_length=80,
        pattern=r"^[A-Za-z0-9 $.\-]+$",
        description=(
            "Optional focus: a token, sector or theme (e.g. 'solana', "
            "'restaking'). Omit for the whole market."
        ),
    )


def get_ct_pulse_input_schema() -> dict[str, Any]:
    return GetCtPulseInput.model_json_schema()


async def run_get_ct_pulse(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetCtPulseInput.model_validate(args)
    params = {"topic": parsed.topic} if parsed.topic else {}
    return await get_client().request("/v1/social/ct-pulse", params)


# --- get_x_signals ---------------------------------------------------------

GET_X_SIGNALS_TOOL_NAME = "get_x_signals"

GET_X_SIGNALS_TOOL_DESCRIPTION = (
    "Breaking crypto stories surfaced on X before news outlets, from vetted "
    "accounts (security researchers, exchanges, regulators, ETF analysts) "
    "plus an open keyword sweep. Each story: headline, summary, event type, "
    "the accounts and post URLs behind it, confidence, and whether on-chain "
    "evidence was cited. Pro tier."
)


class GetXSignalsInput(BaseModel):
    model_config = {"extra": "forbid"}

    lane: Literal["security", "news", "keyword"] | None = Field(
        default=None,
        description=(
            "security = hacks/exploits/drains; news = exchanges, regulators, "
            "ETF data; keyword = open search. Omit for all."
        ),
    )
    hours: int = Field(default=24, ge=1, le=168, description="Lookback window in hours.")
    limit: int = Field(default=50, ge=1, le=100, description="Max stories.")


def get_x_signals_input_schema() -> dict[str, Any]:
    return GetXSignalsInput.model_json_schema()


async def run_get_x_signals(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetXSignalsInput.model_validate(args)
    params: dict[str, Any] = {"hours": parsed.hours, "limit": parsed.limit}
    if parsed.lane:
        params["lane"] = parsed.lane
    return await get_client().request("/v1/social/x-signals", params)


# --- get_kol_consensus -----------------------------------------------------

GET_KOL_CONSENSUS_TOOL_NAME = "get_kol_consensus"

GET_KOL_CONSENSUS_TOOL_DESCRIPTION = (
    "Where credible crypto Twitter analysts, traders and researchers stand "
    "on the most-covered tokens over the last 24h: stance (bullish/bearish/"
    "mixed/neutral), bull and bear account counts, key points, and post "
    "links. Pro tier."
)


class GetKolConsensusInput(BaseModel):
    model_config = {"extra": "forbid"}

    token: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
        pattern=r"^[A-Za-z0-9]+$",
        description="Ticker (e.g. 'BTC'). Omit for every token in the latest snapshot.",
    )


def get_kol_consensus_input_schema() -> dict[str, Any]:
    return GetKolConsensusInput.model_json_schema()


async def run_get_kol_consensus(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetKolConsensusInput.model_validate(args)
    params = {"token": parsed.token} if parsed.token else {}
    return await get_client().request("/v1/social/kol-consensus", params)
