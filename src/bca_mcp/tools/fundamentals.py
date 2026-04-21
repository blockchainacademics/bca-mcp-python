"""Fundamentals tools (category 8a, batch 4 port).

Wraps `/v1/fundamentals/*` — tokenomics, audits, team, roadmap, compare,
rugpull risk. Ports `src/tools/extended.ts::Fundamentals` section.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from bca_mcp.client import get_client
from bca_mcp.types import SLUG_REGEX, ResponseEnvelope

# Shared comma-separated slug list regex (mirrors extended.ts:204).
_SLUGS_CSV_REGEX = (
    r"^[a-z0-9]+(?:-[a-z0-9]+)*(?:,[a-z0-9]+(?:-[a-z0-9]+)*)*$"
)


# --- get_tokenomics --------------------------------------------------------

GET_TOKENOMICS_TOOL_NAME = "get_tokenomics"

GET_TOKENOMICS_TOOL_DESCRIPTION = (
    "Supply, emission, vesting, unlock cliffs, circulating %. Pro tier. "
    "Single source replacing spreadsheet scraping."
)


class GetTokenomicsInput(BaseModel):
    model_config = {"extra": "forbid"}

    entity_slug: str = Field(
        min_length=1,
        max_length=240,
        pattern=SLUG_REGEX,
        description="Entity slug.",
    )


def get_tokenomics_input_schema() -> dict[str, Any]:
    return GetTokenomicsInput.model_json_schema()


async def run_get_tokenomics(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetTokenomicsInput.model_validate(args)
    return await get_client().request(
        "/v1/fundamentals/tokenomics",
        {"entity_slug": parsed.entity_slug},
    )


# --- get_audit_reports -----------------------------------------------------

GET_AUDIT_REPORTS_TOOL_NAME = "get_audit_reports"

GET_AUDIT_REPORTS_TOOL_DESCRIPTION = (
    "Aggregated audits from Trail of Bits, Certik, OpenZeppelin, Consensys "
    "Diligence, Code4rena + BCA review score."
)


class GetAuditReportsInput(BaseModel):
    model_config = {"extra": "forbid"}

    entity_slug: str = Field(
        min_length=1,
        max_length=240,
        pattern=SLUG_REGEX,
        description="Entity slug.",
    )


def get_audit_reports_input_schema() -> dict[str, Any]:
    return GetAuditReportsInput.model_json_schema()


async def run_get_audit_reports(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetAuditReportsInput.model_validate(args)
    return await get_client().request(
        "/v1/fundamentals/audits",
        {"entity_slug": parsed.entity_slug},
    )


# --- get_team_info ---------------------------------------------------------

GET_TEAM_INFO_TOOL_NAME = "get_team_info"

GET_TEAM_INFO_TOOL_DESCRIPTION = (
    "Founders, LinkedIn-verified backgrounds, prior exits, doxx status. "
    "Entity-graph backed. Pro tier."
)


class GetTeamInfoInput(BaseModel):
    model_config = {"extra": "forbid"}

    entity_slug: str = Field(
        min_length=1,
        max_length=240,
        pattern=SLUG_REGEX,
        description="Entity slug.",
    )


def get_team_info_input_schema() -> dict[str, Any]:
    return GetTeamInfoInput.model_json_schema()


async def run_get_team_info(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetTeamInfoInput.model_validate(args)
    return await get_client().request(
        "/v1/fundamentals/team",
        {"entity_slug": parsed.entity_slug},
    )


# --- get_roadmap -----------------------------------------------------------

GET_ROADMAP_TOOL_NAME = "get_roadmap"

GET_ROADMAP_TOOL_DESCRIPTION = (
    "Project roadmap with BCA editorial fact-check. Starter tier."
)


class GetRoadmapInput(BaseModel):
    model_config = {"extra": "forbid"}

    entity_slug: str = Field(
        min_length=1,
        max_length=240,
        pattern=SLUG_REGEX,
        description="Entity slug.",
    )


def get_roadmap_input_schema() -> dict[str, Any]:
    return GetRoadmapInput.model_json_schema()


async def run_get_roadmap(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetRoadmapInput.model_validate(args)
    return await get_client().request(
        "/v1/fundamentals/roadmap",
        {"entity_slug": parsed.entity_slug},
    )


# --- compare_protocols -----------------------------------------------------

COMPARE_PROTOCOLS_TOOL_NAME = "compare_protocols"

COMPARE_PROTOCOLS_TOOL_DESCRIPTION = (
    "Side-by-side comparison: TVL, fees, tokenomics, team, audits, risk. "
    "Pro tier."
)


class CompareProtocolsInput(BaseModel):
    model_config = {"extra": "forbid"}

    entity_slugs: str = Field(
        min_length=1,
        max_length=512,
        pattern=_SLUGS_CSV_REGEX,
        description="Comma-separated entity slugs (kebab-case).",
    )


def compare_protocols_input_schema() -> dict[str, Any]:
    return CompareProtocolsInput.model_json_schema()


async def run_compare_protocols(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = CompareProtocolsInput.model_validate(args)
    return await get_client().request(
        "/v1/fundamentals/compare",
        {"entity_slugs": parsed.entity_slugs},
    )


# --- check_rugpull_risk ----------------------------------------------------

CHECK_RUGPULL_RISK_TOOL_NAME = "check_rugpull_risk"

CHECK_RUGPULL_RISK_TOOL_DESCRIPTION = (
    "Composite rugpull risk: honeypot + LP lock + ownership renounce + "
    "contract verification + team risk. Required: entity_slug. Pro tier."
)


class CheckRugpullRiskInput(BaseModel):
    model_config = {"extra": "forbid"}

    entity_slug: str = Field(
        min_length=1,
        max_length=240,
        pattern=SLUG_REGEX,
        description="Target entity slug.",
    )


def check_rugpull_risk_input_schema() -> dict[str, Any]:
    return CheckRugpullRiskInput.model_json_schema()


async def run_check_rugpull_risk(
    args: dict[str, Any],
) -> ResponseEnvelope[Any]:
    parsed = CheckRugpullRiskInput.model_validate(args)
    return await get_client().request(
        "/v1/fundamentals/rugpull",
        {"entity_slug": parsed.entity_slug},
    )
