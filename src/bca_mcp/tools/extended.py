"""Extended tool surface — full parity port of ``src/tools/extended.ts``.

Wraps the remaining /v1/* endpoints beyond the core 37 tools. Each tool is a
(Pydantic input model, async runner) pair. The module exports a flat
``EXTENDED_TOOL_ENTRIES`` tuple of ``(name, description, schema, runner)`` that
``server.py`` splats into the ``TOOLS`` registry.

Packed densely (mirroring the TS sibling) — one file per category would be
~13 files of near-identical boilerplate. Input validation mirrors TS zod
schemas verbatim: same regex, same enums, same defaults.
"""

from __future__ import annotations

from typing import Annotated, Any, Awaitable, Callable, Optional
from urllib.parse import quote

from pydantic import BaseModel, Field

from bca_mcp.client import get_client
from bca_mcp.types import (
    ALNUM_REGEX,
    EVM_ADDRESS_REGEX,
    SLUG_REGEX,
    TICKER_REGEX,
    EvmChain,
    OnchainChain,
    ResponseEnvelope,
    Window,
)

# Shared literals reused across multiple tools -----------------------------
from typing import Literal

WindowExt = Literal["1d", "7d", "30d"]
TrendingWindow = Literal["1h", "24h", "7d"]
AggregatorKind = Literal["dex", "bridge", "yield"]
ResearchDepth = Literal["light", "standard", "deep"]
ThesisStatus = Literal["active", "closed", "all"]
EntityKind = Literal[
    "chain", "project", "person", "ticker", "protocol", "exchange", "fund"
]

# Regex helpers -------------------------------------------------------------
_SLUGS_CSV_REGEX = r"^[a-z0-9]+(?:-[a-z0-9]+)*(?:,[a-z0-9]+(?:-[a-z0-9]+)*)*$"
_SOLANA_MINT_REGEX = r"^[1-9A-HJ-NP-Za-km-z]+$"
_DOMAIN_REGEX = (
    r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)
_COUNTRY_REGEX = r"^[A-Za-z][A-Za-z \-']*$"
_GPU_REGEX = r"^[A-Za-z0-9]{1,32}$"
# RFC-5322-lite — forbid spaces/quotes; good enough without pulling in
# email-validator as a hard dep.
_EMAIL_REGEX = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"

Runner = Callable[[dict[str, Any]], Awaitable[ResponseEnvelope[Any]]]


def _entry(
    name: str,
    description: str,
    model_cls: type[BaseModel],
    runner: Runner,
) -> tuple[str, str, dict[str, Any], Runner]:
    """Pack a ToolEntry tuple. server.py wraps these into ``ToolEntry``."""
    return (name, description, model_cls.model_json_schema(), runner)


def _gc():
    return get_client()


# ==========================================================================
# Directories (13)
# ==========================================================================

class ListStablecoinsInput(BaseModel):
    model_config = {"extra": "forbid"}
    limit: int = Field(default=20, ge=1, le=100)


async def _run_list_stablecoins(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = ListStablecoinsInput.model_validate(args)
    return await _gc().request("/v1/directories/stablecoins", {"limit": p.limit})


class ListNftCommunitiesInput(BaseModel):
    model_config = {"extra": "forbid"}
    limit: int = Field(default=20, ge=1, le=100)


async def _run_list_nft_communities(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = ListNftCommunitiesInput.model_validate(args)
    return await _gc().request("/v1/directories/nft-communities", {"limit": p.limit})


class ListYieldsInput(BaseModel):
    model_config = {"extra": "forbid"}
    chain: Optional[str] = Field(default=None, pattern=SLUG_REGEX, max_length=240)
    min_apy: Optional[float] = None
    limit: int = Field(default=20, ge=1, le=100)


async def _run_list_yields(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = ListYieldsInput.model_validate(args)
    return await _gc().request(
        "/v1/directories/yields",
        {"chain": p.chain, "min_apy": p.min_apy, "limit": p.limit},
    )


class ListAggregatorsInput(BaseModel):
    model_config = {"extra": "forbid"}
    kind: AggregatorKind = Field(description="Required. Aggregator kind: dex|bridge|yield.")


async def _run_list_aggregators(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = ListAggregatorsInput.model_validate(args)
    return await _gc().request("/v1/directories/aggregators", {"kind": p.kind})


class ListMcpsInput(BaseModel):
    model_config = {"extra": "forbid"}


async def _run_list_mcps(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    ListMcpsInput.model_validate(args)
    return await _gc().request("/v1/directories/mcps")


class ListTradingBotsInput(BaseModel):
    model_config = {"extra": "forbid"}
    limit: int = Field(default=20, ge=1, le=100)


async def _run_list_trading_bots(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = ListTradingBotsInput.model_validate(args)
    return await _gc().request("/v1/directories/trading-bots", {"limit": p.limit})


class ListVcsInput(BaseModel):
    model_config = {"extra": "forbid"}
    focus: Optional[str] = Field(default=None, max_length=128)
    stage: Optional[str] = Field(default=None, max_length=64)
    limit: int = Field(default=50, ge=1, le=100)


async def _run_list_vcs(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = ListVcsInput.model_validate(args)
    return await _gc().request(
        "/v1/directories/vcs",
        {"focus": p.focus, "stage": p.stage, "limit": p.limit},
    )


class ListJobsInput(BaseModel):
    model_config = {"extra": "forbid"}
    q: Optional[str] = Field(default=None, min_length=2, max_length=100)
    tag: Optional[Literal[
        "engineering", "security", "data", "research", "product", "design", "marketing",
        "sales-bd", "legal-compliance", "finance", "trading", "support", "operations", "other",
    ]] = None
    remote: Optional[bool] = None
    location: Optional[str] = Field(default=None, min_length=2, max_length=100)
    employment_type: Optional[Literal["full_time", "part_time", "contract", "internship"]] = None
    company_slug: Optional[str] = Field(default=None, pattern=SLUG_REGEX, max_length=160)
    include_description: bool = False
    limit: int = Field(default=25, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


async def _run_list_jobs(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = ListJobsInput.model_validate(args)
    return await _gc().request("/v1/directories/jobs", p.model_dump(exclude_none=True))


class GetJobInput(BaseModel):
    model_config = {"extra": "forbid"}
    slug: str = Field(pattern=SLUG_REGEX, max_length=240)


async def _run_get_job(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetJobInput.model_validate(args)
    return await _gc().request(f"/v1/directories/jobs/{quote(p.slug, safe='')}")


class ListSmartContractTemplatesInput(BaseModel):
    model_config = {"extra": "forbid"}


async def _run_list_smart_contract_templates(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    ListSmartContractTemplatesInput.model_validate(args)
    return await _gc().request("/v1/directories/smart-contract-templates")


class GetSmartContractTemplateInput(BaseModel):
    model_config = {"extra": "forbid"}
    slug: str = Field(pattern=SLUG_REGEX, min_length=1, max_length=240)


# Grants: the live directory behind blockchainacademics.com/grants. Agents
# check every listing against its source page daily; expired deadlines are
# never returned.
class SearchGrantsInput(BaseModel):
    model_config = {"extra": "forbid"}
    q: Optional[str] = Field(default=None, min_length=2, max_length=100)
    ecosystem: Optional[Literal["web3", "ai", "web2_cloud", "gov", "edu"]] = None
    country: Optional[str] = Field(default=None, max_length=64)
    min_amount: Optional[int] = Field(default=None, ge=0)
    max_complexity: Optional[int] = Field(default=None, ge=1, le=5)
    deadline_before: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    has_deadline: Optional[bool] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


async def _run_search_grants(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = SearchGrantsInput.model_validate(args)
    return await _gc().request("/v1/grants", p.model_dump(exclude_none=True))


class GetGrantInput(BaseModel):
    model_config = {"extra": "forbid"}
    slug: str = Field(pattern=SLUG_REGEX, max_length=240)


async def _run_get_grant(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetGrantInput.model_validate(args)
    return await _gc().request(f"/v1/grants/{quote(p.slug, safe='')}")


async def _run_get_smart_contract_template(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetSmartContractTemplateInput.model_validate(args)
    return await _gc().request(
        f"/v1/directories/smart-contract-templates/{quote(p.slug, safe='')}"
    )


class ListMarketingTemplatesInput(BaseModel):
    model_config = {"extra": "forbid"}


async def _run_list_marketing_templates(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    ListMarketingTemplatesInput.model_validate(args)
    return await _gc().request("/v1/directories/marketing-templates")


class GetMarketingTemplateInput(BaseModel):
    model_config = {"extra": "forbid"}
    slug: str = Field(pattern=SLUG_REGEX, min_length=1, max_length=240)


async def _run_get_marketing_template(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetMarketingTemplateInput.model_validate(args)
    return await _gc().request(
        f"/v1/directories/marketing-templates/{quote(p.slug, safe='')}"
    )


class BuildCustomIndicatorInput(BaseModel):
    model_config = {"extra": "forbid"}
    formula: str = Field(
        min_length=1,
        max_length=512,
        description=(
            "Formula over data primitives, e.g. "
            "'coverage_index(X)/price_change_7d(X)'."
        ),
    )
    target: Optional[str] = Field(default=None, max_length=256)


async def _run_build_custom_indicator(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = BuildCustomIndicatorInput.model_validate(args)
    return await _gc().request(
        "/v1/directories/custom-indicator",
        {"formula": p.formula, "target": p.target},
    )


# ==========================================================================
# Chain-specific (4)
# ==========================================================================

class _EmptyInput(BaseModel):
    model_config = {"extra": "forbid"}


async def _run_get_solana_ecosystem(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    _EmptyInput.model_validate(args)
    return await _gc().request("/v1/chains/solana")


async def _run_get_l2_comparison(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    _EmptyInput.model_validate(args)
    return await _gc().request("/v1/chains/l2-comparison")


async def _run_get_bitcoin_l2_status(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    _EmptyInput.model_validate(args)
    return await _gc().request("/v1/chains/bitcoin-l2")


async def _run_get_ton_ecosystem(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    _EmptyInput.model_validate(args)
    return await _gc().request("/v1/chains/ton")


# ==========================================================================
# Compute / AI crypto (2)
# ==========================================================================

class GetComputePricingInput(BaseModel):
    model_config = {"extra": "forbid"}
    gpu: Optional[str] = Field(
        default=None,
        max_length=32,
        pattern=_GPU_REGEX,
        description="GPU type filter (e.g. 'A100', 'H100').",
    )


async def _run_get_compute_pricing(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetComputePricingInput.model_validate(args)
    return await _gc().request("/v1/compute/pricing", {"gpu": p.gpu})


async def _run_get_ai_crypto_metrics(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    _EmptyInput.model_validate(args)
    return await _gc().request("/v1/compute/ai-metrics")


# ==========================================================================
# Memes (4)
# ==========================================================================

class TrackPumpfunInput(BaseModel):
    model_config = {"extra": "forbid"}
    limit: int = Field(default=20, ge=1, le=100)


async def _run_track_pumpfun(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = TrackPumpfunInput.model_validate(args)
    return await _gc().request("/v1/memes/pumpfun", {"limit": p.limit})


class TrackBonkfunInput(BaseModel):
    model_config = {"extra": "forbid"}
    limit: int = Field(default=20, ge=1, le=100)


async def _run_track_bonkfun(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = TrackBonkfunInput.model_validate(args)
    return await _gc().request("/v1/memes/bonkfun", {"limit": p.limit})


class CheckMemecoinRiskInput(BaseModel):
    model_config = {"extra": "forbid"}
    mint: str = Field(
        min_length=1,
        max_length=64,
        pattern=_SOLANA_MINT_REGEX,
        description="Required. Solana token mint address.",
    )


async def _run_check_memecoin_risk(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = CheckMemecoinRiskInput.model_validate(args)
    return await _gc().request("/v1/memes/risk", {"mint": p.mint})


class GetDegenLeaderboardInput(BaseModel):
    model_config = {"extra": "forbid"}
    window: WindowExt = "7d"
    limit: int = Field(default=50, ge=1, le=100)


async def _run_get_degen_leaderboard(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetDegenLeaderboardInput.model_validate(args)
    return await _gc().request(
        "/v1/memes/leaderboard",
        {"window": p.window, "limit": p.limit},
    )


# ==========================================================================
# Microstructure (5)
# ==========================================================================

class GetFundingRatesInput(BaseModel):
    model_config = {"extra": "forbid"}
    symbol: str = Field(
        min_length=1,
        max_length=12,
        pattern=TICKER_REGEX,
        description="e.g. 'BTC', 'ETH'.",
    )
    exchanges: Optional[str] = Field(
        default=None,
        max_length=256,
        description="Comma-separated exchange list.",
    )


async def _run_get_funding_rates(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetFundingRatesInput.model_validate(args)
    return await _gc().request(
        "/v1/microstructure/funding-rates",
        {"symbol": p.symbol, "exchanges": p.exchanges},
    )


class GetOptionsFlowInput(BaseModel):
    model_config = {"extra": "forbid"}
    symbol: str = Field(min_length=1, max_length=12, pattern=TICKER_REGEX)


async def _run_get_options_flow(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetOptionsFlowInput.model_validate(args)
    return await _gc().request("/v1/microstructure/options-flow", {"symbol": p.symbol})


class GetLiquidationHeatmapInput(BaseModel):
    model_config = {"extra": "forbid"}
    symbol: str = Field(min_length=1, max_length=12, pattern=TICKER_REGEX)


async def _run_get_liquidation_heatmap(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetLiquidationHeatmapInput.model_validate(args)
    return await _gc().request(
        "/v1/microstructure/liquidation-heatmap", {"symbol": p.symbol}
    )


class GetExchangeFlowsInput(BaseModel):
    model_config = {"extra": "forbid"}
    symbol: str = Field(min_length=1, max_length=12, pattern=TICKER_REGEX)
    window: WindowExt = "7d"


async def _run_get_exchange_flows(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetExchangeFlowsInput.model_validate(args)
    return await _gc().request(
        "/v1/microstructure/exchange-flows",
        {"symbol": p.symbol, "window": p.window},
    )


class PredictListingInput(BaseModel):
    model_config = {"extra": "forbid"}
    entity_slug: str = Field(pattern=SLUG_REGEX, min_length=1, max_length=240)


async def _run_predict_listing(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = PredictListingInput.model_validate(args)
    return await _gc().request(
        "/v1/microstructure/predict-listing", {"entity_slug": p.entity_slug}
    )


# ==========================================================================
# Narrative (5)
# ==========================================================================

class TrackNarrativeInput(BaseModel):
    model_config = {"extra": "forbid"}
    narrative: str = Field(
        pattern=SLUG_REGEX,
        min_length=1,
        max_length=240,
        description="e.g. 'ai-agents', 'rwa', 'depin', 'modular'.",
    )
    window: WindowExt = "7d"


async def _run_track_narrative(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = TrackNarrativeInput.model_validate(args)
    return await _gc().request(
        "/v1/narrative/track",
        {"narrative": p.narrative, "window": p.window},
    )


class GetAiAgentTokensInput(BaseModel):
    model_config = {"extra": "forbid"}
    limit: int = Field(default=50, ge=1, le=100)


async def _run_get_ai_agent_tokens(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetAiAgentTokensInput.model_validate(args)
    return await _gc().request("/v1/narrative/ai-agents", {"limit": p.limit})


class GetDepinProjectsInput(BaseModel):
    model_config = {"extra": "forbid"}
    limit: int = Field(default=50, ge=1, le=100)


async def _run_get_depin_projects(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetDepinProjectsInput.model_validate(args)
    return await _gc().request("/v1/narrative/depin", {"limit": p.limit})


class GetRwaTokensInput(BaseModel):
    model_config = {"extra": "forbid"}
    limit: int = Field(default=50, ge=1, le=100)


async def _run_get_rwa_tokens(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetRwaTokensInput.model_validate(args)
    return await _gc().request("/v1/narrative/rwa", {"limit": p.limit})


class GetPredictionMarketsInput(BaseModel):
    model_config = {"extra": "forbid"}
    topic: Optional[str] = Field(
        default=None, pattern=SLUG_REGEX, max_length=240
    )
    limit: int = Field(default=50, ge=1, le=100)


async def _run_get_prediction_markets(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetPredictionMarketsInput.model_validate(args)
    return await _gc().request(
        "/v1/narrative/prediction-markets",
        {"topic": p.topic, "limit": p.limit},
    )


# ==========================================================================
# Regulatory (4)
# ==========================================================================

class GetRegulatoryStatusInput(BaseModel):
    model_config = {"extra": "forbid"}
    country: str = Field(
        min_length=2,
        max_length=64,
        pattern=_COUNTRY_REGEX,
        description="ISO country code or name.",
    )


async def _run_get_regulatory_status(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetRegulatoryStatusInput.model_validate(args)
    return await _gc().request("/v1/regulatory/status", {"country": p.country})


class TrackSecFilingsInput(BaseModel):
    model_config = {"extra": "forbid"}
    ticker: str = Field(
        min_length=1,
        max_length=12,
        pattern=TICKER_REGEX,
        description="e.g. MSTR, COIN, HOOD.",
    )


async def _run_track_sec_filings(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = TrackSecFilingsInput.model_validate(args)
    return await _gc().request("/v1/regulatory/sec-filings", {"ticker": p.ticker})


class GetMicaStatusInput(BaseModel):
    model_config = {"extra": "forbid"}
    entity_slug: str = Field(pattern=SLUG_REGEX, min_length=1, max_length=240)


async def _run_get_mica_status(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetMicaStatusInput.model_validate(args)
    return await _gc().request("/v1/regulatory/mica", {"entity_slug": p.entity_slug})


class GetTaxRulesInput(BaseModel):
    model_config = {"extra": "forbid"}
    country: str = Field(min_length=2, max_length=64, pattern=_COUNTRY_REGEX)


async def _run_get_tax_rules(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetTaxRulesInput.model_validate(args)
    return await _gc().request("/v1/regulatory/tax-rules", {"country": p.country})


# ==========================================================================
# Security (4)
# ==========================================================================

class CheckExploitHistoryInput(BaseModel):
    model_config = {"extra": "forbid"}
    entity_slug: str = Field(pattern=SLUG_REGEX, min_length=1, max_length=240)


async def _run_check_exploit_history(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = CheckExploitHistoryInput.model_validate(args)
    return await _gc().request(
        "/v1/security/exploits", {"entity_slug": p.entity_slug}
    )


class CheckPhishingDomainInput(BaseModel):
    model_config = {"extra": "forbid"}
    domain: str = Field(min_length=1, max_length=253, pattern=_DOMAIN_REGEX)


async def _run_check_phishing_domain(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = CheckPhishingDomainInput.model_validate(args)
    return await _gc().request("/v1/security/phishing", {"domain": p.domain})


class GetBugBountyProgramsInput(BaseModel):
    model_config = {"extra": "forbid"}
    min_payout: Optional[float] = None
    limit: int = Field(default=50, ge=1, le=100)


async def _run_get_bug_bounty_programs(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetBugBountyProgramsInput.model_validate(args)
    return await _gc().request(
        "/v1/security/bug-bounties",
        {"min_payout": p.min_payout, "limit": p.limit},
    )


class ScanContractInput(BaseModel):
    model_config = {"extra": "forbid"}
    address: str = Field(
        pattern=EVM_ADDRESS_REGEX,
        description="Required. EVM contract address (0x + 40 hex chars).",
    )


async def _run_scan_contract(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = ScanContractInput.model_validate(args)
    return await _gc().request("/v1/security/scan-contract", {"address": p.address})


# ==========================================================================
# Services: POST (3)
# ==========================================================================
#
# Each input model mirrors the API request model in
# blockchainacademics-api app/api/v1/services.py (KOLCampaignRequest,
# CustomResearchRequest, ListingSubmissionRequest): same field names, same
# required set, same bounds and enums, so a call that passes here is not
# rejected upstream with a 422 (0.6.2 sent fields the API does not read and
# missed required ones). Field order, bounds and wording match the TS
# sibling's extended.ts. Each endpoint is free to call with any real key
# (the demo key is not on the demo allowlist), files a service request for a
# human to review, and answers 201 {request_id, status, next_step}. Only the
# fields the caller set are sent; the API applies its own defaults.

CampaignType = Literal["thread", "video", "space", "podcast", "hybrid"]
ListingDirectory = Literal[
    "vcs", "aggregators", "trading_bots", "mcps",
    "nft_communities", "jobs", "stablecoins", "trading_yields",
]
_HTTP_URL_REGEX = r"^https?://"
# One target chain or tag: 1..64 characters.
_ShortText = Annotated[str, Field(min_length=1, max_length=64)]


def _service_body(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(exclude_none=True)


def _contact_name_field() -> Any:
    return Field(default=None, max_length=200, description="Optional contact name.")


def _company_field() -> Any:
    return Field(default=None, max_length=200, description="Optional company name.")


def _notes_field(what: str) -> Any:
    return Field(
        default=None,
        max_length=4000,
        description=f"Optional {what} (up to 4,000 characters).",
    )


class BookKolCampaignInput(BaseModel):
    model_config = {"extra": "forbid"}
    contact_email: str = Field(
        pattern=_EMAIL_REGEX,
        max_length=254,
        description="Required. Where BCA Studio sends the recommended KOL slate and quote.",
    )
    project_name: str = Field(
        min_length=2,
        max_length=200,
        description="Required. Project or brand name (2 to 200 characters).",
    )
    campaign_type: CampaignType = Field(
        description="Required. Campaign format: thread, video, space, podcast or hybrid.",
    )
    budget_usd: int = Field(
        ge=500,
        le=2_000_000,
        description="Required. Budget in whole US dollars, 500 to 2,000,000.",
    )
    contact_name: Optional[str] = _contact_name_field()
    company: Optional[str] = _company_field()
    project_slug: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=240,
        pattern=SLUG_REGEX,
        description="Optional BCA entity slug for the project (e.g. 'ethereum').",
    )
    target_chains: Optional[list[_ShortText]] = Field(
        default=None,
        max_length=12,
        description="Optional chains the campaign targets, up to 12 (e.g. ['solana', 'base']).",
    )
    notes: Optional[str] = _notes_field("brief: goals, audience, timing")


async def _run_book_kol_campaign(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = BookKolCampaignInput.model_validate(args)
    return await _gc().post("/v1/services/book-kol-campaign", _service_body(p))


class RequestCustomResearchInput(BaseModel):
    model_config = {"extra": "forbid"}
    contact_email: str = Field(
        pattern=_EMAIL_REGEX,
        max_length=254,
        description="Required. Where BCA Research sends the scope and quote.",
    )
    topic: str = Field(
        min_length=4,
        max_length=240,
        description="Required. What to research (4 to 240 characters).",
    )
    depth: ResearchDepth = Field(
        default="standard",
        description="Report depth: light, standard or deep.",
    )
    target_wordcount: int = Field(
        default=3000,
        ge=500,
        le=20_000,
        description="Target report length in words, 500 to 20,000.",
    )
    deadline: Optional[str] = Field(
        default=None,
        max_length=40,
        description=(
            "Optional deadline: an ISO date or free text such as "
            "'within 2 weeks' (up to 40 characters)."
        ),
    )
    contact_name: Optional[str] = _contact_name_field()
    company: Optional[str] = _company_field()
    notes: Optional[str] = _notes_field("notes for the research team")


async def _run_request_custom_research(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = RequestCustomResearchInput.model_validate(args)
    return await _gc().post("/v1/services/custom-research", _service_body(p))


class SubmitListingInput(BaseModel):
    model_config = {"extra": "forbid"}
    contact_email: str = Field(
        pattern=_EMAIL_REGEX,
        max_length=254,
        description="Required. Where the editorial team replies with featured listing pricing.",
    )
    directory: ListingDirectory = Field(description="Required. Target directory.")
    listing_name: str = Field(
        min_length=2,
        max_length=200,
        description="Required. Display name for the listing (2 to 200 characters).",
    )
    listing_url: str = Field(
        max_length=2083,
        pattern=_HTTP_URL_REGEX,
        description="Required. Public http or https URL of the project or product.",
    )
    description: str = Field(
        min_length=20,
        max_length=2000,
        description="Required. What the listing is (20 to 2,000 characters).",
    )
    contact_name: Optional[str] = _contact_name_field()
    tags: Optional[list[_ShortText]] = Field(
        default=None,
        max_length=24,
        description="Optional tags, up to 24.",
    )


async def _run_submit_listing(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = SubmitListingInput.model_validate(args)
    return await _gc().post("/v1/services/submit-listing", _service_body(p))


# ==========================================================================
# History (4) — time series
# ==========================================================================

class GetHistoryPricesInput(BaseModel):
    model_config = {"extra": "forbid"}
    symbol: str = Field(min_length=1, max_length=12, pattern=TICKER_REGEX)
    days: int = Field(default=365, ge=1, le=3650)


async def _run_get_history_prices(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetHistoryPricesInput.model_validate(args)
    return await _gc().request(
        f"/v1/history/prices/{quote(p.symbol, safe='')}",
        {"days": p.days},
    )


class GetHistorySentimentInput(BaseModel):
    model_config = {"extra": "forbid"}
    symbol: str = Field(min_length=1, max_length=12, pattern=TICKER_REGEX)
    days: int = Field(default=365, ge=1, le=3650)


async def _run_get_history_sentiment(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetHistorySentimentInput.model_validate(args)
    return await _gc().request(
        f"/v1/history/sentiment/{quote(p.symbol, safe='')}",
        {"days": p.days},
    )


class GetHistoryCorrelationInput(BaseModel):
    model_config = {"extra": "forbid"}
    symbol: str = Field(min_length=1, max_length=12, pattern=TICKER_REGEX)
    peer: str = Field(
        min_length=1,
        max_length=12,
        pattern=TICKER_REGEX,
        description="Peer symbol to correlate against.",
    )
    days: int = Field(default=365, ge=7, le=3650)


async def _run_get_history_correlation(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetHistoryCorrelationInput.model_validate(args)
    return await _gc().request(
        f"/v1/history/correlation/{quote(p.symbol, safe='')}",
        {"peer": p.peer, "days": p.days},
    )


class GetHistoryCoverageInput(BaseModel):
    model_config = {"extra": "forbid"}
    entity_slug: str = Field(pattern=SLUG_REGEX, min_length=1, max_length=240)
    days: int = Field(default=365, ge=1, le=3650)


async def _run_get_history_coverage(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetHistoryCoverageInput.model_validate(args)
    return await _gc().request(
        "/v1/history/coverage",
        {"entity_slug": p.entity_slug, "days": p.days},
    )


# ==========================================================================
# Entities / topics / sources / stories / trending / feed (7)
# ==========================================================================

class ListEntitiesInput(BaseModel):
    model_config = {"extra": "forbid"}
    kind: Optional[EntityKind] = None
    limit: int = Field(default=50, ge=1, le=200)


async def _run_list_entities(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = ListEntitiesInput.model_validate(args)
    return await _gc().request(
        "/v1/entities", {"kind": p.kind, "limit": p.limit}
    )


class GetTopicInput(BaseModel):
    model_config = {"extra": "forbid"}
    slug: str = Field(pattern=SLUG_REGEX, min_length=1, max_length=240)


async def _run_get_topic(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetTopicInput.model_validate(args)
    return await _gc().request(f"/v1/topics/{quote(p.slug, safe='')}")


class SearchAcademyInput(BaseModel):
    model_config = {"extra": "forbid"}
    q: str = Field(min_length=1, max_length=512)
    limit: int = Field(default=10, ge=1, le=50)


async def _run_search_academy(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = SearchAcademyInput.model_validate(args)
    return await _gc().request(
        "/v1/academy/search", {"q": p.q, "limit": p.limit}
    )


class GetTrendingInput(BaseModel):
    model_config = {"extra": "forbid"}
    window: TrendingWindow = "24h"
    limit: int = Field(default=20, ge=1, le=50)


async def _run_get_trending(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetTrendingInput.model_validate(args)
    return await _gc().request(
        "/v1/trending", {"window": p.window, "limit": p.limit}
    )


class GetUnifiedFeedInput(BaseModel):
    model_config = {"extra": "forbid"}
    limit: int = Field(default=50, ge=1, le=100)


async def _run_get_unified_feed(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetUnifiedFeedInput.model_validate(args)
    return await _gc().request("/v1/feed", {"limit": p.limit})


async def _run_list_sources(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    _EmptyInput.model_validate(args)
    return await _gc().request("/v1/sources")


class GetRecentStoriesInput(BaseModel):
    model_config = {"extra": "forbid"}
    limit: int = Field(default=20, ge=1, le=50)


async def _run_get_recent_stories(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetRecentStoriesInput.model_validate(args)
    return await _gc().request("/v1/stories/recent", {"limit": p.limit})


# ==========================================================================
# Memos + theses (4)
# ==========================================================================

class ListMemosInput(BaseModel):
    model_config = {"extra": "forbid"}
    limit: int = Field(default=20, ge=1, le=100)


async def _run_list_memos(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = ListMemosInput.model_validate(args)
    return await _gc().request("/v1/memos", {"limit": p.limit})


class GetMemoInput(BaseModel):
    model_config = {"extra": "forbid"}
    slug: str = Field(pattern=SLUG_REGEX, min_length=1, max_length=240)


async def _run_get_memo(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetMemoInput.model_validate(args)
    return await _gc().request(f"/v1/memos/{quote(p.slug, safe='')}")


class ListThesesInput(BaseModel):
    model_config = {"extra": "forbid"}
    status: ThesisStatus = "active"
    limit: int = Field(default=20, ge=1, le=100)


async def _run_list_theses(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = ListThesesInput.model_validate(args)
    return await _gc().request(
        "/v1/theses", {"status": p.status, "limit": p.limit}
    )


class GetThesisInput(BaseModel):
    model_config = {"extra": "forbid"}
    slug: str = Field(pattern=SLUG_REGEX, min_length=1, max_length=240)


async def _run_get_thesis(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetThesisInput.model_validate(args)
    return await _gc().request(f"/v1/theses/{quote(p.slug, safe='')}")


# ==========================================================================
# Currencies (2)
# ==========================================================================

class ListCurrenciesInput(BaseModel):
    model_config = {"extra": "forbid"}
    limit: int = Field(default=100, ge=1, le=500)


async def _run_list_currencies(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = ListCurrenciesInput.model_validate(args)
    return await _gc().request("/v1/currencies", {"limit": p.limit})


class GetCurrencyFeedInput(BaseModel):
    model_config = {"extra": "forbid"}
    symbol: str = Field(min_length=1, max_length=12, pattern=TICKER_REGEX)
    limit: int = Field(default=50, ge=1, le=100)


async def _run_get_currency_feed(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetCurrencyFeedInput.model_validate(args)
    return await _gc().request(
        f"/v1/currencies/{quote(p.symbol, safe='')}/feed",
        {"limit": p.limit},
    )


# ==========================================================================
# Registry — exported to server.py
# ==========================================================================

EXTENDED_TOOL_ENTRIES: tuple[tuple[str, str, dict[str, Any], Runner], ...] = (
    # directories (13)
    _entry(
        "list_stablecoins",
        "Ranked stablecoins by TVL / peg stability / audit status / chain coverage. Composite of DefiLlama + BCA risk scoring.",
        ListStablecoinsInput, _run_list_stablecoins,
    ),
    _entry(
        "list_nft_communities",
        "Top NFT communities ranked by floor, holders, Discord activity, OG status.",
        ListNftCommunitiesInput, _run_list_nft_communities,
    ),
    _entry(
        "list_yields",
        "Best staking / LP / vault opportunities by chain and risk tier. DefiLlama yields + BCA risk overlay. Starter tier.",
        ListYieldsInput, _run_list_yields,
    ),
    _entry(
        "list_aggregators",
        "DEX, bridge, or yield aggregators ranked by volume, fees, chain support. Required: kind ∈ {dex, bridge, yield}.",
        ListAggregatorsInput, _run_list_aggregators,
    ),
    _entry(
        "list_mcps",
        "Directory of crypto MCP servers (meta: the MCP-of-MCPs). Discover peer MCPs with their tool surfaces.",
        ListMcpsInput, _run_list_mcps,
    ),
    _entry(
        "list_trading_bots",
        "Ranked trading bots / copy-trade platforms with fees, exchanges, track record.",
        ListTradingBotsInput, _run_list_trading_bots,
    ),
    _entry(
        "list_vcs",
        "Crypto VC directory: focus, ticket size, stage, portfolio count, recent deals. Starter tier.",
        ListVcsInput, _run_list_vcs,
    ),
    _entry(
        "list_jobs",
        "Live crypto jobs (1,300+ open roles at 50+ crypto companies: Coinbase, Binance, OKX, Ripple, Circle, Phantom, Uniswap...) collected every 6h from the companies' own job boards. Filter by role, remote, location, company, keyword. Apply links go to the company's own application page.",
        ListJobsInput, _run_list_jobs,
    ),
    _entry(
        "get_job",
        "One crypto job in full: description, company, location, remote, salary when published, apply link, BCA job page URL. Errors once the role is filled.",
        GetJobInput, _run_get_job,
    ),
    _entry(
        "search_grants",
        "Live crypto, web3, AI and public-funding grants (200+ programs) with amounts, deadlines, eligibility and apply links. Verified against each funder's page weekly; expired rounds never returned. Soonest deadline first.",
        SearchGrantsInput, _run_search_grants,
    ),
    _entry(
        "get_grant",
        "One grant program in full: funder, amount range, deadline, focus areas, geography, application complexity, summary, apply link, last verified date.",
        GetGrantInput, _run_get_grant,
    ),
    _entry(
        "list_smart_contract_templates",
        "Audited Solidity templates: ERC20, ERC721, Vesting, Multisig, Staking, Airdrop. OpenZeppelin + BCA academy assets.",
        ListSmartContractTemplatesInput, _run_list_smart_contract_templates,
    ),
    _entry(
        "get_smart_contract_template",
        "Fetch a specific smart contract template by slug. Includes attributed header.",
        GetSmartContractTemplateInput, _run_get_smart_contract_template,
    ),
    _entry(
        "list_marketing_templates",
        "Campaign templates: TGE checklist, airdrop ops, NFT mint script, influencer brief, press kit. Starter tier.",
        ListMarketingTemplatesInput, _run_list_marketing_templates,
    ),
    _entry(
        "get_marketing_template",
        "Fetch a specific marketing template by slug.",
        GetMarketingTemplateInput, _run_get_marketing_template,
    ),
    _entry(
        "build_custom_indicator",
        "Define a custom indicator formula over BCA primitives. Returns time-series. Pro tier.",
        BuildCustomIndicatorInput, _run_build_custom_indicator,
    ),

    # chains (4)
    _entry(
        "get_solana_ecosystem",
        "Solana metrics + top projects + SPL activity.",
        _EmptyInput, _run_get_solana_ecosystem,
    ),
    _entry(
        "get_l2_comparison",
        "L2 side-by-side: Base, Arbitrum, Optimism, zkSync, Starknet, Linea, Scroll, Mantle, Blast.",
        _EmptyInput, _run_get_l2_comparison,
    ),
    _entry(
        "get_bitcoin_l2_status",
        "BTC L2s: Stacks, Rootstock, BOB, Babylon, Merlin, Bitlayer. Starter tier.",
        _EmptyInput, _run_get_bitcoin_l2_status,
    ),
    _entry(
        "get_ton_ecosystem",
        "TON + Telegram mini-apps ecosystem snapshot.",
        _EmptyInput, _run_get_ton_ecosystem,
    ),

    # compute (2)
    _entry(
        "get_compute_pricing",
        "Akash, Render, IO.net pricing per GPU type.",
        GetComputePricingInput, _run_get_compute_pricing,
    ),
    _entry(
        "get_ai_crypto_metrics",
        "Bittensor subnets, Ritual, Prime Intellect. Starter tier.",
        _EmptyInput, _run_get_ai_crypto_metrics,
    ),

    # memes (4)
    _entry(
        "track_pumpfun",
        "pump.fun trending + new launches.",
        TrackPumpfunInput, _run_track_pumpfun,
    ),
    _entry(
        "track_bonkfun",
        "Solana meme launcher: trending launches.",
        TrackBonkfunInput, _run_track_bonkfun,
    ),
    _entry(
        "check_memecoin_risk",
        "Memecoin-specific risk: bundler detection, dev sells, sniper detection. Required: mint (Solana token mint address). Pro tier.",
        CheckMemecoinRiskInput, _run_check_memecoin_risk,
    ),
    _entry(
        "get_degen_leaderboard",
        "Top PnL wallets on memes. Pro tier.",
        GetDegenLeaderboardInput, _run_get_degen_leaderboard,
    ),

    # microstructure (5)
    _entry(
        "get_funding_rates",
        "Perps funding across Binance / Bybit / dYdX / Hyperliquid / Drift. Pro tier.",
        GetFundingRatesInput, _run_get_funding_rates,
    ),
    _entry(
        "get_options_flow",
        "IV, strike heatmap, block trades (Deribit + Lyra + Aevo). Pro tier.",
        GetOptionsFlowInput, _run_get_options_flow,
    ),
    _entry(
        "get_liquidation_heatmap",
        "Where leveraged positions get wiped. Pro tier.",
        GetLiquidationHeatmapInput, _run_get_liquidation_heatmap,
    ),
    _entry(
        "get_exchange_flows",
        "Net in/out from CEXs, a smart money signal. Pro tier.",
        GetExchangeFlowsInput, _run_get_exchange_flows,
    ),
    _entry(
        "predict_listing",
        "Binance/Coinbase/Upbit listing probability score. Pro tier.",
        PredictListingInput, _run_predict_listing,
    ),

    # narrative (5)
    _entry(
        "track_narrative",
        "Real-time narrative strength (AI agents, RWA, DePIN, modular, memes, Bitcoin L2s, SocialFi, GameFi). Composite of BCA Narrative Strength Score. Starter tier.",
        TrackNarrativeInput, _run_track_narrative,
    ),
    _entry(
        "get_ai_agent_tokens",
        "AI agent tokens tracker: Virtuals, ai16z, Aixbt, Griffain, Zerebro.",
        GetAiAgentTokensInput, _run_get_ai_agent_tokens,
    ),
    _entry(
        "get_depin_projects",
        "DePIN ecosystem tracker.",
        GetDepinProjectsInput, _run_get_depin_projects,
    ),
    _entry(
        "get_rwa_tokens",
        "Real-world asset tokenization tracker. Starter tier.",
        GetRwaTokensInput, _run_get_rwa_tokens,
    ),
    _entry(
        "get_prediction_markets",
        "Polymarket + Kalshi + Azuro odds.",
        GetPredictionMarketsInput, _run_get_prediction_markets,
    ),

    # regulatory (4)
    _entry(
        "get_regulatory_status",
        "Country-by-country crypto regulation state. Starter tier.",
        GetRegulatoryStatusInput, _run_get_regulatory_status,
    ),
    _entry(
        "track_sec_filings",
        "SEC filings for listed crypto companies. Starter tier.",
        TrackSecFilingsInput, _run_track_sec_filings,
    ),
    _entry(
        "get_mica_status",
        "EU MiCA compliance tracker per project. Pro tier.",
        GetMicaStatusInput, _run_get_mica_status,
    ),
    _entry(
        "get_tax_rules",
        "Crypto tax rules per jurisdiction. Starter tier.",
        GetTaxRulesInput, _run_get_tax_rules,
    ),

    # security (4)
    _entry(
        "check_exploit_history",
        "Historical exploits per protocol (Rekt + DefiLlama hacks).",
        CheckExploitHistoryInput, _run_check_exploit_history,
    ),
    _entry(
        "check_phishing_domain",
        "Known phishing / scam domains + contracts.",
        CheckPhishingDomainInput, _run_check_phishing_domain,
    ),
    _entry(
        "get_bug_bounty_programs",
        "Active bounties (Immunefi + Hackerone crypto).",
        GetBugBountyProgramsInput, _run_get_bug_bounty_programs,
    ),
    _entry(
        "scan_contract",
        "Basic static analysis on any EVM address: bytecode verification, honeypot check. Required: address (0x EVM address). Starter tier.",
        ScanContractInput, _run_scan_contract,
    ),

    # services: POST (3)
    _entry(
        "book_kol_campaign",
        "Send a KOL campaign brief to BCA Studio. Required: contact_email, project_name, campaign_type (thread, video, space, podcast or hybrid) and budget_usd (500 to 2,000,000 USD). Free to submit; needs an API key (the free tier is enough). BCA Studio reviews the brief and emails a recommended KOL slate and quote within 2 business days. Returns request_id, status and next_step.",
        BookKolCampaignInput, _run_book_kol_campaign,
    ),
    _entry(
        "request_custom_research",
        "Request a custom research report from BCA Research. Required: contact_email and topic (4 to 240 characters). Free to submit; needs an API key (the free tier is enough). BCA Research replies with scope and a quote within 2 business days; payment is by Stripe invoice. Returns request_id, status and next_step.",
        RequestCustomResearchInput, _run_request_custom_research,
    ),
    _entry(
        "submit_listing",
        "Submit a listing to a BCA directory: vcs, aggregators, trading_bots, mcps, nft_communities, jobs, stablecoins or trading_yields. Required: contact_email, directory, listing_name, listing_url and description (20 to 2,000 characters). Free to submit (needs an API key; the free tier is enough), paid to be featured: the editorial team reviews each submission and emails featured listing pricing. Returns request_id, status and next_step.",
        SubmitListingInput, _run_submit_listing,
    ),

    # history (4)
    _entry(
        "get_history_prices",
        "Long-range historical price series for a symbol.",
        GetHistoryPricesInput, _run_get_history_prices,
    ),
    _entry(
        "get_history_sentiment",
        "Historical sentiment series for a symbol.",
        GetHistorySentimentInput, _run_get_history_sentiment,
    ),
    _entry(
        "get_history_correlation",
        "Correlation series between two symbols (price/sentiment). Useful for pair trades.",
        GetHistoryCorrelationInput, _run_get_history_correlation,
    ),
    _entry(
        "get_history_coverage",
        "Historical BCA coverage series per entity.",
        GetHistoryCoverageInput, _run_get_history_coverage,
    ),

    # corpus meta (7)
    _entry(
        "list_entities",
        "Browse the BCA entity universe (~200 entities). Filter by kind.",
        ListEntitiesInput, _run_list_entities,
    ),
    _entry(
        "get_topic",
        "Fetch a topic node from the taxonomy (articles under it, parents, siblings).",
        GetTopicInput, _run_get_topic,
    ),
    _entry(
        "search_academy",
        "Full-text search across academy lessons. Returns course + lesson anchor per hit.",
        SearchAcademyInput, _run_search_academy,
    ),
    _entry(
        "get_trending",
        "Trending entities + articles by window.",
        GetTrendingInput, _run_get_trending,
    ),
    _entry(
        "get_unified_feed",
        "Chronological cross-source news feed (articles + stories).",
        GetUnifiedFeedInput, _run_get_unified_feed,
    ),
    _entry(
        "list_sources",
        "All editorial news sources BCA ingests, with trust tier.",
        _EmptyInput, _run_list_sources,
    ),
    _entry(
        "get_recent_stories",
        "Recent clustered stories (deduped across sources).",
        GetRecentStoriesInput, _run_get_recent_stories,
    ),

    # memos + theses (4)
    _entry(
        "list_memos",
        "Browse public investment memos (paid fields redacted).",
        ListMemosInput, _run_list_memos,
    ),
    _entry(
        "get_memo",
        "Fetch a specific investment memo by slug.",
        GetMemoInput, _run_get_memo,
    ),
    _entry(
        "list_theses",
        "Browse public trade theses (entry / invalidation / targets).",
        ListThesesInput, _run_list_theses,
    ),
    _entry(
        "get_thesis",
        "Fetch a specific trade thesis by slug.",
        GetThesisInput, _run_get_thesis,
    ),

    # currencies (2)
    _entry(
        "list_currencies",
        "All tracked currencies with symbol, id, and chain metadata.",
        ListCurrenciesInput, _run_list_currencies,
    ),
    _entry(
        "get_currency_feed",
        "Chronological news feed for a single currency.",
        GetCurrencyFeedInput, _run_get_currency_feed,
    ),
)
