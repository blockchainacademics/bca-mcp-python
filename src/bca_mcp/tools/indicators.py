"""Proprietary BCA composite indicators (category 5, batch 3 port).

Wraps `/v1/indicators/*`. Ports six tools from `src/tools/indicators.ts`:
`get_coverage_index`, `get_narrative_strength`, `get_sentiment_velocity`,
`get_editorial_premium`, `get_kol_influence`, `get_risk_score`.

All six share the `(entity_slug, window)` shape except `get_risk_score`
which takes `entity_slug` only (no window — composite is as-of-latest).

`get_editorial_premium` + `get_kol_influence` default window to `"30d"`
rather than `"7d"` because the backend only computes 30d + 90d rollups
today — defaulting to 7d would return a 404 for clients that don't pass
a window.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from bca_mcp.client import get_client
from bca_mcp.types import SLUG_REGEX, ResponseEnvelope, Window


# --- shared base models ----------------------------------------------------
#
# Defined here (not in types.py) because they're *tool-input* shapes, not
# response shapes — types.py is response-only to keep the TypedDict / pydantic
# separation clean.


class _EntityWindowInput(BaseModel):
    """Base input for indicator tools that take `(entity_slug, window)`."""

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


class _EntityWindow30dInput(BaseModel):
    """Same as _EntityWindowInput but default window is '30d'.

    Backed endpoints (`editorial-premium`, `kol-influence`) only have 30d
    / 90d rollups pre-computed server-side. 7d default would 404.
    """

    model_config = {"extra": "forbid"}

    entity_slug: str = Field(
        min_length=1,
        max_length=240,
        pattern=SLUG_REGEX,
        description="Entity slug.",
    )
    window: Window = Field(
        default="30d",
        description="Rolling window. Supported windows: 30d, 90d.",
    )


async def _run_indicator(
    path: str,
    parsed: _EntityWindowInput | _EntityWindow30dInput,
) -> ResponseEnvelope[Any]:
    return await get_client().request(
        path,
        {"entity_slug": parsed.entity_slug, "window": parsed.window},
    )


# --- get_coverage_index ----------------------------------------------------

GET_COVERAGE_INDEX_TOOL_NAME = "get_coverage_index"

GET_COVERAGE_INDEX_TOOL_DESCRIPTION = (
    "BCA Coverage Index: mention velocity x source diversity x editorial "
    "weight. Pro tier. High = accumulation signal before price."
)


class GetCoverageIndexInput(_EntityWindowInput):
    pass


def get_coverage_index_input_schema() -> dict[str, Any]:
    return GetCoverageIndexInput.model_json_schema()


async def run_get_coverage_index(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetCoverageIndexInput.model_validate(args)
    return await _run_indicator("/v1/indicators/coverage", parsed)


# --- get_narrative_strength ------------------------------------------------

GET_NARRATIVE_STRENGTH_TOOL_NAME = "get_narrative_strength"

GET_NARRATIVE_STRENGTH_TOOL_DESCRIPTION = (
    "Co-mention graph centrality: which narratives are consolidating vs "
    "fading. Pro tier. Uses eigenvector centrality in rolling windows."
)


class GetNarrativeStrengthInput(_EntityWindowInput):
    pass


def get_narrative_strength_input_schema() -> dict[str, Any]:
    return GetNarrativeStrengthInput.model_json_schema()


async def run_get_narrative_strength(
    args: dict[str, Any],
) -> ResponseEnvelope[Any]:
    parsed = GetNarrativeStrengthInput.model_validate(args)
    return await _run_indicator("/v1/indicators/narrative", parsed)


# --- get_sentiment_velocity ------------------------------------------------

GET_SENTIMENT_VELOCITY_TOOL_NAME = "get_sentiment_velocity"

GET_SENTIMENT_VELOCITY_TOOL_DESCRIPTION = (
    "d/dt of sentiment bucket with smoothing. Pro tier. Early "
    "reversal-detection signal."
)


class GetSentimentVelocityInput(_EntityWindowInput):
    pass


def get_sentiment_velocity_input_schema() -> dict[str, Any]:
    return GetSentimentVelocityInput.model_json_schema()


async def run_get_sentiment_velocity(
    args: dict[str, Any],
) -> ResponseEnvelope[Any]:
    parsed = GetSentimentVelocityInput.model_validate(args)
    return await _run_indicator("/v1/indicators/sentiment-velocity", parsed)


# --- get_editorial_premium -------------------------------------------------

GET_EDITORIAL_PREMIUM_TOOL_NAME = "get_editorial_premium"

GET_EDITORIAL_PREMIUM_TOOL_DESCRIPTION = (
    "Correlation of price return to coverage delta (lagged -1 to +3 "
    "days). Pro tier. Measures pre-coverage accumulation edge. "
    "Supported windows: 30d, 90d."
)


class GetEditorialPremiumInput(_EntityWindow30dInput):
    pass


def get_editorial_premium_input_schema() -> dict[str, Any]:
    return GetEditorialPremiumInput.model_json_schema()


async def run_get_editorial_premium(
    args: dict[str, Any],
) -> ResponseEnvelope[Any]:
    parsed = GetEditorialPremiumInput.model_validate(args)
    return await _run_indicator("/v1/indicators/editorial-premium", parsed)


# --- get_kol_influence -----------------------------------------------------

GET_KOL_INFLUENCE_TOOL_NAME = "get_kol_influence"

GET_KOL_INFLUENCE_TOOL_DESCRIPTION = (
    "KOL influence score: reach x engagement x historical pick accuracy. "
    "Pro tier. Param: entity_slug (the KOL's canonical entity slug). "
    "Supported windows: 30d, 90d."
)


class GetKolInfluenceInput(_EntityWindow30dInput):
    pass


def get_kol_influence_input_schema() -> dict[str, Any]:
    return GetKolInfluenceInput.model_json_schema()


async def run_get_kol_influence(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetKolInfluenceInput.model_validate(args)
    return await _run_indicator("/v1/indicators/kol-influence", parsed)


# --- get_risk_score --------------------------------------------------------

GET_RISK_SCORE_TOOL_NAME = "get_risk_score"

GET_RISK_SCORE_TOOL_DESCRIPTION = (
    "Composite risk score: regulatory flags + liquidity tier + team "
    "risk + audit status. Starter tier. Single-number risk (0-1)."
)


class GetRiskScoreInput(BaseModel):
    model_config = {"extra": "forbid"}

    entity_slug: str = Field(
        min_length=1,
        max_length=240,
        pattern=SLUG_REGEX,
        description="Entity slug.",
    )


def get_risk_score_input_schema() -> dict[str, Any]:
    return GetRiskScoreInput.model_json_schema()


async def run_get_risk_score(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetRiskScoreInput.model_validate(args)
    return await get_client().request(
        "/v1/indicators/risk",
        {"entity_slug": parsed.entity_slug},
    )
