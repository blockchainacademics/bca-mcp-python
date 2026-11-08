"""Proprietary BCA composite indicators (category 5, batch 3 port).

Wraps `/v1/indicators/*`. Ports six tools from `src/tools/indicators.ts`:
`get_coverage_index`, `get_narrative_strength`, `get_sentiment_velocity`,
`get_editorial_premium`, `get_kol_influence`, `get_risk_score`.

All six share the `(entity_slug, window)` shape except `get_risk_score`
which takes `entity_slug` only (no window — composite is as-of-latest).

Each window enum lists the windows the API computes for that indicator
(the indicator classes in the API are the source); any other window is a
422 there:

    coverage_index, narrative_strength     7d, 30d, 90d
    sentiment_velocity                     7d, 30d
    editorial_premium, kol_influence       30d, 90d (default 30d)
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from bca_mcp.client import get_client
from bca_mcp.types import SLUG_REGEX, ResponseEnvelope

CoverageWindow = Literal["7d", "30d", "90d"]
VelocityWindow = Literal["7d", "30d"]
PremiumWindow = Literal["30d", "90d"]

# How every indicator answer reports what it measured (the API's
# indicators router).
_STATUS_NOTE = (
    "meta.status is unseeded when there is no measurement yet (data.value "
    "is a placeholder), partial when some inputs were defaulted, stale when "
    "the value is older than 48 hours; an unknown entity is an error."
)


# --- shared base models ----------------------------------------------------
#
# Defined here (not in types.py) because they're *tool-input* shapes, not
# response shapes — types.py is response-only to keep the TypedDict / pydantic
# separation clean.


def _entity_slug_field() -> Any:
    return Field(
        min_length=1,
        max_length=240,
        pattern=SLUG_REGEX,
        description="Entity slug.",
    )


async def _run_indicator(path: str, entity_slug: str, window: str) -> ResponseEnvelope[Any]:
    return await get_client().request(
        path,
        {"entity_slug": entity_slug, "window": window},
    )


# --- get_coverage_index ----------------------------------------------------

GET_COVERAGE_INDEX_TOOL_NAME = "get_coverage_index"

GET_COVERAGE_INDEX_TOOL_DESCRIPTION = (
    "BCA Coverage Index: a recency-weighted count of BCA article mentions "
    "of an entity over 7d, 30d or 90d. Unseeded when the entity had no "
    "mentions in the window. Pro tier. " + _STATUS_NOTE
)


class GetCoverageIndexInput(BaseModel):
    model_config = {"extra": "forbid"}

    entity_slug: str = _entity_slug_field()
    window: CoverageWindow = Field(
        default="7d",
        description="Rolling window: 7d, 30d or 90d.",
    )


def get_coverage_index_input_schema() -> dict[str, Any]:
    return GetCoverageIndexInput.model_json_schema()


async def run_get_coverage_index(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetCoverageIndexInput.model_validate(args)
    return await _run_indicator("/v1/indicators/coverage", parsed.entity_slug, parsed.window)


# --- get_narrative_strength ------------------------------------------------

GET_NARRATIVE_STRENGTH_TOOL_NAME = "get_narrative_strength"

GET_NARRATIVE_STRENGTH_TOOL_DESCRIPTION = (
    "Narrative Strength: an entity's eigenvector centrality in the article "
    "co-mention graph over 7d, 30d or 90d, showing which narratives are "
    "consolidating or fading. Unseeded when the entity is absent from the "
    "window's graph. Pro tier. " + _STATUS_NOTE
)


class GetNarrativeStrengthInput(BaseModel):
    model_config = {"extra": "forbid"}

    entity_slug: str = _entity_slug_field()
    window: CoverageWindow = Field(
        default="7d",
        description="Rolling window: 7d, 30d or 90d.",
    )


def get_narrative_strength_input_schema() -> dict[str, Any]:
    return GetNarrativeStrengthInput.model_json_schema()


async def run_get_narrative_strength(
    args: dict[str, Any],
) -> ResponseEnvelope[Any]:
    parsed = GetNarrativeStrengthInput.model_validate(args)
    return await _run_indicator("/v1/indicators/narrative", parsed.entity_slug, parsed.window)


# --- get_sentiment_velocity ------------------------------------------------

GET_SENTIMENT_VELOCITY_TOOL_NAME = "get_sentiment_velocity"

GET_SENTIMENT_VELOCITY_TOOL_DESCRIPTION = (
    "Rate of change of an entity's sentiment (the smoothed derivative of its "
    "daily sentiment) over 7d or 30d: positive while sentiment rises, negative "
    "while it falls. Unseeded until the window holds two daily sentiment "
    "samples. Pro tier. "
    + _STATUS_NOTE
)


class GetSentimentVelocityInput(BaseModel):
    model_config = {"extra": "forbid"}

    entity_slug: str = _entity_slug_field()
    window: VelocityWindow = Field(
        default="7d",
        description="Rolling window: 7d or 30d.",
    )


def get_sentiment_velocity_input_schema() -> dict[str, Any]:
    return GetSentimentVelocityInput.model_json_schema()


async def run_get_sentiment_velocity(
    args: dict[str, Any],
) -> ResponseEnvelope[Any]:
    parsed = GetSentimentVelocityInput.model_validate(args)
    return await _run_indicator(
        "/v1/indicators/sentiment-velocity", parsed.entity_slug, parsed.window
    )


# --- get_editorial_premium -------------------------------------------------

GET_EDITORIAL_PREMIUM_TOOL_NAME = "get_editorial_premium"

GET_EDITORIAL_PREMIUM_TOOL_DESCRIPTION = (
    "Correlation of price return to coverage change, lagged -1 to +3 days, "
    "over 30d or 90d: whether BCA coverage leads price. Unseeded until at "
    "least 8 paired days of price and coverage exist. Pro tier. "
    + _STATUS_NOTE
)


class GetEditorialPremiumInput(BaseModel):
    model_config = {"extra": "forbid"}

    entity_slug: str = _entity_slug_field()
    window: PremiumWindow = Field(
        default="30d",
        description="Rolling window: 30d or 90d.",
    )


def get_editorial_premium_input_schema() -> dict[str, Any]:
    return GetEditorialPremiumInput.model_json_schema()


async def run_get_editorial_premium(
    args: dict[str, Any],
) -> ResponseEnvelope[Any]:
    parsed = GetEditorialPremiumInput.model_validate(args)
    return await _run_indicator(
        "/v1/indicators/editorial-premium", parsed.entity_slug, parsed.window
    )


# --- get_kol_influence -----------------------------------------------------

GET_KOL_INFLUENCE_TOOL_NAME = "get_kol_influence"

GET_KOL_INFLUENCE_TOOL_DESCRIPTION = (
    "KOL influence score (reach x engagement x historical pick accuracy) "
    "for a KOL's canonical entity slug, over 30d or 90d. Answers unseeded "
    "on the hosted API today: its input, a private KOL roster, is not "
    "deployed there. Pro tier."
)


class GetKolInfluenceInput(BaseModel):
    model_config = {"extra": "forbid"}

    entity_slug: str = _entity_slug_field()
    window: PremiumWindow = Field(
        default="30d",
        description="Rolling window: 30d or 90d.",
    )


def get_kol_influence_input_schema() -> dict[str, Any]:
    return GetKolInfluenceInput.model_json_schema()


async def run_get_kol_influence(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetKolInfluenceInput.model_validate(args)
    return await _run_indicator(
        "/v1/indicators/kol-influence", parsed.entity_slug, parsed.window
    )


# --- get_risk_score --------------------------------------------------------

GET_RISK_SCORE_TOOL_NAME = "get_risk_score"

GET_RISK_SCORE_TOOL_DESCRIPTION = (
    "Composite risk score from 0 to 1 (higher is riskier) built from "
    "regulatory, liquidity, team and audit inputs; components.sources names "
    "where each input came from. Partial with the missing inputs in "
    "meta.diagnostic.missing (regulatory is usually missing). Starter tier. "
    + _STATUS_NOTE
)


class GetRiskScoreInput(BaseModel):
    model_config = {"extra": "forbid"}

    entity_slug: str = _entity_slug_field()


def get_risk_score_input_schema() -> dict[str, Any]:
    return GetRiskScoreInput.model_json_schema()


async def run_get_risk_score(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetRiskScoreInput.model_validate(args)
    return await get_client().request(
        "/v1/indicators/risk",
        {"entity_slug": parsed.entity_slug},
    )
