"""Fundamentals tools (category 8a, batch 4 port).

Wraps `/v1/fundamentals/*` — tokenomics, audits, team, roadmap, compare,
rugpull risk. Ports `src/tools/extended.ts::Fundamentals` section.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from bca_mcp.client import get_client
from bca_mcp.types import SLUG_REGEX, ResponseEnvelope

# One to five comma-separated slugs: the API compares at most 5 entities.
_SLUGS_CSV_REGEX = (
    r"^[a-z0-9]+(?:-[a-z0-9]+)*(?:,[a-z0-9]+(?:-[a-z0-9]+)*){0,4}$"
)


# --- get_tokenomics --------------------------------------------------------

GET_TOKENOMICS_TOOL_NAME = "get_tokenomics"

GET_TOKENOMICS_TOOL_DESCRIPTION = (
    "Token supply for an entity: total, circulating and max supply, "
    "emission schedule, vesting cliffs, next unlock and its amount, FDV and "
    "6 month dilution. Unseeded when BCA has no tokenomics row for the "
    "entity; stale when the row could not be refreshed within 24 hours. "
    "Pro tier."
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
    "Audits on file for an entity: BCA-reviewed audits with findings and a "
    "BCA review score, plus audit links imported from DefiLlama protocol "
    "metadata (source defillama: firm parsed from the link, no date or "
    "findings). Unseeded with no audits on file, partial when only links "
    "are on file. Starter tier."
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
    "Team info from BCA's entity dossier: founders (name, role, X and "
    "GitHub handles), doxx status and team size. Backgrounds and prior "
    "exits are not tracked, so the answer is partial and lists them under "
    "missing. Pro tier."
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
    "Project roadmap milestones; each milestone's bca_verified flag marks "
    "BCA's editorial fact-check. Answers stale while the April 2026 seed "
    "is not refreshed, unseeded when there are no milestones. Starter tier."
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
    "Side-by-side comparison of 1 to 5 entities: TVL, fees and revenue "
    "(DefiLlama), market cap and FDV (CoinGecko), tokenomics, team, audits "
    "and BCA risk. Each row lists its empty sections under missing and "
    "tokenomics older than 30 days under stale; the answer is partial when "
    "any row misses a section or has stale tokenomics. Pro tier."
)


class CompareProtocolsInput(BaseModel):
    model_config = {"extra": "forbid"}

    entity_slugs: str = Field(
        min_length=1,
        max_length=512,
        pattern=_SLUGS_CSV_REGEX,
        description="Comma-separated entity slugs (kebab-case), 1 to 5.",
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
    "Six-check rugpull checklist for an entity covering Etherscan source "
    "verification, an audit on file, team doxx and the BCA risk score. LP "
    "lock and ownership renounce are not checked yet, and there is no "
    "honeypot test; unknown checks are left out of the score and listed "
    "under missing (partial). Required: entity_slug. Pro tier."
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
