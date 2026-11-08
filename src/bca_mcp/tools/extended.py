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
    ISO2_COUNTRY_REGEX,
    SLUG_REGEX,
    TICKER_REGEX,
    EvmChain,
    OnchainChain,
    ResponseEnvelope,
    SocialWindow,
    Window,
)

# Shared literals reused across multiple tools -----------------------------
from typing import Literal

WindowExt = Literal["1d", "7d", "30d"]
# The windows /v1/narrative/track computes (1d is never computed).
NarrativeWindow = Literal["7d", "30d", "90d"]
AggregatorKind = Literal["dex", "bridge", "yield"]
ResearchDepth = Literal["light", "standard", "deep"]
# /v1/theses accepts these statuses; all means no status filter.
ThesisStatus = Literal["active", "closed", "invalidated", "pending", "all"]
# The kinds the API accepts. protocol, exchange and fund hold no entities
# yet and answer unseeded (kind_not_populated).
EntityKind = Literal[
    "chain", "project", "person", "ticker", "protocol", "exchange", "fund"
]
ListingExchange = Literal["binance", "coinbase", "upbit"]
PumpfunMode = Literal["trending", "new"]
PredictionVenue = Literal["polymarket", "kalshi", "all"]
HistoryGranularity = Literal["hourly", "daily"]

# Regex helpers -------------------------------------------------------------
_SLUGS_CSV_REGEX = r"^[a-z0-9]+(?:-[a-z0-9]+)*(?:,[a-z0-9]+(?:-[a-z0-9]+)*)*$"
_SOLANA_MINT_REGEX = r"^[1-9A-HJ-NP-Za-km-z]{32,48}$"
_DOMAIN_REGEX = (
    r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)
# GPU model, e.g. A100 (the API ignores case and spaces, so RTX4090 works).
_GPU_REGEX = r"^[A-Za-z0-9]{1,32}$"
# Symbols of the microstructure routes (funding, liquidations, flows): 2+.
_SYMBOL2_REGEX = r"^[A-Za-z0-9]{2,12}$"
# Stock tickers of track_sec_filings: letters only.
_STOCK_TICKER_REGEX = r"^[A-Za-z]{1,12}$"
# Deribit options: BTC, ETH or SOL (any case).
_OPTION_ASSET_REGEX = r"^[A-Za-z]{3}$"
# 13NOV26 or 2026-11-13.
_EXPIRY_REGEX = r"^(?:[0-9]{1,2}[A-Za-z]{3}[0-9]{2}|[0-9]{4}-[0-9]{2}-[0-9]{2})$"
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
    chain: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=32,
        pattern=SLUG_REGEX,
        description="Chain filter (e.g. 'ethereum', 'arbitrum').",
    )
    # The API's min_apy_pct; it accepts min_apy as an alias.
    min_apy: Optional[float] = Field(
        default=None,
        ge=0,
        le=1000,
        description="Minimum APY in percent (0 to 1000); with it, results are ranked by APY.",
    )
    limit: int = Field(default=20, ge=1, le=100)


async def _run_list_yields(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = ListYieldsInput.model_validate(args)
    # The API's name for the minimum is min_apy_pct (it also reads min_apy).
    return await _gc().request(
        "/v1/directories/yields",
        {"chain": p.chain, "min_apy_pct": p.min_apy, "limit": p.limit},
    )


class ListAggregatorsInput(BaseModel):
    model_config = {"extra": "forbid"}
    kind: AggregatorKind = Field(description="Required. Aggregator kind: dex|bridge|yield.")
    chain: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=32,
        pattern=SLUG_REGEX,
        description="Optional chain filter (e.g. 'ethereum').",
    )
    limit: Optional[int] = Field(
        default=None,
        ge=1,
        le=200,
        description="Max rows (1 to 200, default 50).",
    )


async def _run_list_aggregators(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = ListAggregatorsInput.model_validate(args)
    return await _gc().request(
        "/v1/directories/aggregators",
        {"kind": p.kind, "chain": p.chain, "limit": p.limit},
    )


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
    focus: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Sector focus, e.g. 'defi' or 'Layer 2' (the API's sector).",
    )
    stage: Optional[str] = Field(
        default=None,
        max_length=64,
        pattern=r"^[A-Za-z0-9_ -]+$",
        description="Stage, e.g. 'seed' or 'Series A'.",
    )
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
    company_slug: Optional[str] = Field(default=None, pattern=SLUG_REGEX, min_length=1, max_length=160)
    include_description: bool = False
    limit: int = Field(default=25, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


async def _run_list_jobs(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = ListJobsInput.model_validate(args)
    return await _gc().request("/v1/directories/jobs", p.model_dump(exclude_none=True))


class GetJobInput(BaseModel):
    model_config = {"extra": "forbid"}
    slug: str = Field(pattern=SLUG_REGEX, min_length=1, max_length=240)


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
    slug: str = Field(pattern=SLUG_REGEX, min_length=1, max_length=160)


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
    slug: str = Field(pattern=SLUG_REGEX, min_length=1, max_length=240)


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
    slug: str = Field(pattern=SLUG_REGEX, min_length=1, max_length=200)


async def _run_get_marketing_template(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetMarketingTemplateInput.model_validate(args)
    return await _gc().request(
        f"/v1/directories/marketing-templates/{quote(p.slug, safe='')}"
    )


class BuildCustomIndicatorInput(BaseModel):
    model_config = {"extra": "forbid"}
    formula: str = Field(
        min_length=3,
        max_length=256,
        description=(
            "Formula over data primitives, e.g. "
            "'coverage_index(ethereum)/price_change_7d(ethereum)'. Functions: "
            "coverage_index, sentiment_velocity, price_change_7d, risk_score "
            "(each takes an entity slug); operators + - * /."
        ),
    )
    target: Optional[str] = Field(
        default=None,
        max_length=256,
        description="Not read by the API: name the entity slugs inside the formula instead.",
    )


async def _run_build_custom_indicator(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = BuildCustomIndicatorInput.model_validate(args)
    # Only the formula is sent: the API has no target parameter.
    return await _gc().request(
        "/v1/directories/custom-indicator", {"formula": p.formula}
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
        description="GPU model filter (e.g. 'A100', 'H100', 'RTX4090').",
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
    mode: Optional[PumpfunMode] = Field(
        default=None,
        description="trending (most 24h volume, the default) or new (newest launches).",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Coins to return; the API returns at most 60 per call.",
    )


async def _run_track_pumpfun(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = TrackPumpfunInput.model_validate(args)
    return await _gc().request(
        "/v1/memes/pumpfun", {"mode": p.mode, "limit": p.limit}
    )


class TrackBonkfunInput(BaseModel):
    model_config = {"extra": "forbid"}
    limit: int = Field(default=20, ge=1, le=100)


async def _run_track_bonkfun(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = TrackBonkfunInput.model_validate(args)
    return await _gc().request("/v1/memes/bonkfun", {"limit": p.limit})


class CheckMemecoinRiskInput(BaseModel):
    model_config = {"extra": "forbid"}
    mint: str = Field(
        min_length=32,
        max_length=48,
        pattern=_SOLANA_MINT_REGEX,
        description="Required. Solana token mint address (base58, 32 to 48 characters).",
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
        min_length=2,
        max_length=12,
        pattern=_SYMBOL2_REGEX,
        description="e.g. 'BTC', 'ETH'.",
    )
    exchanges: Optional[str] = Field(
        default=None,
        max_length=256,
        description="Comma-separated exchange list. Accepted, not applied yet: every venue is returned.",
    )


async def _run_get_funding_rates(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetFundingRatesInput.model_validate(args)
    return await _gc().request(
        "/v1/microstructure/funding-rates",
        {"symbol": p.symbol, "exchanges": p.exchanges},
    )


class GetOptionsFlowInput(BaseModel):
    model_config = {"extra": "forbid"}
    # Sent as `symbol`, which the API reads as an alias of its `currency`.
    symbol: str = Field(
        min_length=3,
        max_length=3,
        pattern=_OPTION_ASSET_REGEX,
        description="BTC, ETH or SOL.",
    )
    limit: Optional[int] = Field(
        default=None,
        ge=1,
        le=200,
        description="Instruments returned, largest open interest first (1 to 200, default 50).",
    )
    expiry: Optional[str] = Field(
        default=None,
        min_length=7,
        max_length=10,
        pattern=_EXPIRY_REGEX,
        description="Only this expiry, as 13NOV26 or 2026-11-13.",
    )


async def _run_get_options_flow(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetOptionsFlowInput.model_validate(args)
    return await _gc().request(
        "/v1/microstructure/options-flow",
        {"symbol": p.symbol, "limit": p.limit, "expiry": p.expiry},
    )


class GetLiquidationHeatmapInput(BaseModel):
    model_config = {"extra": "forbid"}
    symbol: str = Field(min_length=2, max_length=12, pattern=_SYMBOL2_REGEX)


async def _run_get_liquidation_heatmap(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetLiquidationHeatmapInput.model_validate(args)
    return await _gc().request(
        "/v1/microstructure/liquidation-heatmap", {"symbol": p.symbol}
    )


class GetExchangeFlowsInput(BaseModel):
    model_config = {"extra": "forbid"}
    symbol: str = Field(min_length=2, max_length=12, pattern=_SYMBOL2_REGEX)
    window: Optional[WindowExt] = Field(
        default=None,
        description="Accepted but not applied yet: there is no flows source to pass it to.",
    )


async def _run_get_exchange_flows(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetExchangeFlowsInput.model_validate(args)
    return await _gc().request(
        "/v1/microstructure/exchange-flows",
        {"symbol": p.symbol, "window": p.window},
    )


class PredictListingInput(BaseModel):
    model_config = {"extra": "forbid"}
    entity_slug: str = Field(pattern=SLUG_REGEX, min_length=1, max_length=240)
    exchange: Optional[ListingExchange] = Field(
        default=None,
        description="Exchange to check: binance (default), coinbase or upbit.",
    )


async def _run_predict_listing(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = PredictListingInput.model_validate(args)
    return await _gc().request(
        "/v1/microstructure/predict-listing",
        {"entity_slug": p.entity_slug, "exchange": p.exchange},
    )


# ==========================================================================
# Narrative (5)
# ==========================================================================

class TrackNarrativeInput(BaseModel):
    model_config = {"extra": "forbid"}
    narrative: str = Field(
        pattern=SLUG_REGEX,
        min_length=2,
        max_length=80,
        description="e.g. 'ai-agents', 'rwa', 'depin', 'modular'.",
    )
    window: NarrativeWindow = Field(
        default="7d",
        description="7d, 30d or 90d.",
    )


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
    venue: Optional[PredictionVenue] = Field(
        default=None,
        description="polymarket, kalshi or all (both, the default).",
    )
    topic: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=64,
        pattern=SLUG_REGEX,
        description=(
            "crypto (the default), bitcoin, ethereum, solana, any other "
            "Polymarket tag slug, or all for no filter. Kalshi covers the "
            "four crypto topics only."
        ),
    )
    limit: int = Field(default=50, ge=1, le=100, description="Markets per venue.")


async def _run_get_prediction_markets(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetPredictionMarketsInput.model_validate(args)
    return await _gc().request(
        "/v1/narrative/prediction-markets",
        {"venue": p.venue, "topic": p.topic, "limit": p.limit},
    )


# ==========================================================================
# Regulatory (4)
# ==========================================================================

class GetRegulatoryStatusInput(BaseModel):
    model_config = {"extra": "forbid"}
    country: str = Field(
        min_length=2,
        max_length=2,
        pattern=ISO2_COUNTRY_REGEX,
        description="ISO 3166 alpha-2 country code (e.g. 'US', 'DE'); EL and UK are read as GR and GB.",
    )


async def _run_get_regulatory_status(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetRegulatoryStatusInput.model_validate(args)
    return await _gc().request("/v1/regulatory/status", {"country": p.country})


class TrackSecFilingsInput(BaseModel):
    model_config = {"extra": "forbid"}
    ticker: str = Field(
        min_length=1,
        max_length=12,
        pattern=_STOCK_TICKER_REGEX,
        description="Stock ticker, letters only: MSTR, COIN, HOOD, MARA, RIOT, CLSK, BKKT or GALAXY.",
    )


async def _run_track_sec_filings(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = TrackSecFilingsInput.model_validate(args)
    return await _gc().request("/v1/regulatory/sec-filings", {"ticker": p.ticker})


class GetMicaStatusInput(BaseModel):
    model_config = {"extra": "forbid"}
    country: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=2,
        pattern=ISO2_COUNTRY_REGEX,
        description="Optional ISO 3166 alpha-2 country code (e.g. 'FR'). Omit, or send EU, for every EU Member State.",
    )
    # Kept for callers of 0.6.2, where it was required. The API ignores it
    # (there is no per project MiCA data) and says so in a note.
    entity_slug: Optional[str] = Field(
        default=None,
        pattern=SLUG_REGEX,
        min_length=1,
        max_length=240,
        description="Optional. Not used yet: there is no per project MiCA data, and the answer is partial with a note.",
    )


async def _run_get_mica_status(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetMicaStatusInput.model_validate(args)
    return await _gc().request(
        "/v1/regulatory/mica",
        {"country": p.country, "entity_slug": p.entity_slug},
    )


class GetTaxRulesInput(BaseModel):
    model_config = {"extra": "forbid"}
    country: str = Field(
        min_length=2,
        max_length=2,
        pattern=ISO2_COUNTRY_REGEX,
        description="ISO 3166 alpha-2 country code (e.g. 'US', 'DE'); EL and UK are read as GR and GB.",
    )


async def _run_get_tax_rules(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetTaxRulesInput.model_validate(args)
    return await _gc().request("/v1/regulatory/tax-rules", {"country": p.country})


# ==========================================================================
# Security (4)
# ==========================================================================

# Chain filter of the security routes: letters, digits and hyphens.
_SECURITY_CHAIN_REGEX = r"^[A-Za-z0-9-]+$"


class CheckExploitHistoryInput(BaseModel):
    model_config = {"extra": "forbid"}
    entity_slug: str = Field(pattern=SLUG_REGEX, min_length=1, max_length=240)
    chain: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=32,
        pattern=_SECURITY_CHAIN_REGEX,
        description="Optional chain filter (e.g. 'Ethereum', 'BSC').",
    )
    min_usd_loss: Optional[int] = Field(
        default=None,
        ge=0,
        description="Optional minimum loss in USD.",
    )
    limit: Optional[int] = Field(
        default=None,
        ge=1,
        le=200,
        description="Max hacks (1 to 200, default 50).",
    )


async def _run_check_exploit_history(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = CheckExploitHistoryInput.model_validate(args)
    return await _gc().request(
        "/v1/security/exploits",
        {
            "entity_slug": p.entity_slug,
            "chain": p.chain,
            "min_usd_loss": p.min_usd_loss,
            "limit": p.limit,
        },
    )


class CheckPhishingDomainInput(BaseModel):
    model_config = {"extra": "forbid"}
    domain: str = Field(min_length=3, max_length=253, pattern=_DOMAIN_REGEX)


async def _run_check_phishing_domain(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = CheckPhishingDomainInput.model_validate(args)
    return await _gc().request("/v1/security/phishing", {"domain": p.domain})


class GetBugBountyProgramsInput(BaseModel):
    model_config = {"extra": "forbid"}
    chain: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=32,
        pattern=_SECURITY_CHAIN_REGEX,
        description="Optional chain filter (e.g. 'ethereum').",
    )
    min_payout: Optional[float] = Field(
        default=None,
        ge=0,
        description="Minimum top bounty in USD.",
    )
    limit: int = Field(default=50, ge=1, le=100)


async def _run_get_bug_bounty_programs(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetBugBountyProgramsInput.model_validate(args)
    return await _gc().request(
        "/v1/security/bug-bounties",
        {"chain": p.chain, "min_payout": p.min_payout, "limit": p.limit},
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
# human to review, and answers 201 {request_id, status, next_step}. Optional
# fields the caller left out are not sent; the advertised defaults (depth,
# target_wordcount) are, and they equal the API's own.

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
        max_length=256,
        description="Required. What to research (4 to 256 characters).",
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
        description="Required. Where the editorial team replies.",
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

# The history routes cap days at 365 (a 422 above it).
_HISTORY_MAX_DAYS = 365


class GetHistoryPricesInput(BaseModel):
    model_config = {"extra": "forbid"}
    symbol: str = Field(min_length=1, max_length=12, pattern=TICKER_REGEX)
    days: int = Field(default=365, ge=1, le=_HISTORY_MAX_DAYS)
    granularity: Optional[HistoryGranularity] = Field(
        default=None,
        description="hourly or daily. Default: hourly up to 30 days, daily for longer windows.",
    )


async def _run_get_history_prices(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetHistoryPricesInput.model_validate(args)
    return await _gc().request(
        f"/v1/history/prices/{quote(p.symbol, safe='')}",
        {"days": p.days, "granularity": p.granularity},
    )


class GetHistorySentimentInput(BaseModel):
    model_config = {"extra": "forbid"}
    symbol: str = Field(min_length=1, max_length=12, pattern=TICKER_REGEX)
    days: int = Field(default=365, ge=1, le=_HISTORY_MAX_DAYS)


async def _run_get_history_sentiment(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetHistorySentimentInput.model_validate(args)
    return await _gc().request(
        f"/v1/history/sentiment/{quote(p.symbol, safe='')}",
        {"days": p.days},
    )


class GetHistoryCorrelationInput(BaseModel):
    model_config = {"extra": "forbid"}
    symbol: str = Field(min_length=1, max_length=12, pattern=TICKER_REGEX)
    peer: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=12,
        pattern=TICKER_REGEX,
        description="Optional peer symbol (e.g. 'ETH'): adds the correlation of the two coins' daily price changes.",
    )
    days: int = Field(default=365, ge=7, le=_HISTORY_MAX_DAYS)


async def _run_get_history_correlation(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetHistoryCorrelationInput.model_validate(args)
    return await _gc().request(
        f"/v1/history/correlation/{quote(p.symbol, safe='')}",
        {"peer": p.peer, "days": p.days},
    )


class GetHistoryCoverageInput(BaseModel):
    model_config = {"extra": "forbid"}
    entity_slug: str = Field(pattern=SLUG_REGEX, min_length=1, max_length=240)
    days: int = Field(default=365, ge=1, le=_HISTORY_MAX_DAYS)


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
    kind: Optional[EntityKind] = Field(
        default=None,
        description="chain, project, person or ticker; protocol, exchange and fund hold no entities yet.",
    )
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(
        default=0,
        ge=0,
        description="Entities to skip, for paging (default 0). meta.pageInfo.hasNextPage says whether more exist.",
    )


async def _run_list_entities(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = ListEntitiesInput.model_validate(args)
    return await _gc().request(
        "/v1/entities", {"kind": p.kind, "limit": p.limit, "offset": p.offset}
    )


class GetTopicInput(BaseModel):
    model_config = {"extra": "forbid"}
    slug: str = Field(pattern=SLUG_REGEX, min_length=1, max_length=240)


async def _run_get_topic(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = GetTopicInput.model_validate(args)
    return await _gc().request(f"/v1/topics/{quote(p.slug, safe='')}")


class SearchAcademyInput(BaseModel):
    model_config = {"extra": "forbid"}
    q: str = Field(min_length=2, max_length=512, description="Search query (2 to 512 characters).")
    limit: int = Field(default=10, ge=1, le=50)
    offset: int = Field(
        default=0,
        ge=0,
        description="Hits to skip, for paging (default 0). meta.pageInfo.hasNextPage says whether more exist.",
    )


async def _run_search_academy(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = SearchAcademyInput.model_validate(args)
    return await _gc().request(
        "/v1/academy/search", {"q": p.q, "limit": p.limit, "offset": p.offset}
    )


class GetTrendingInput(BaseModel):
    model_config = {"extra": "forbid"}
    window: SocialWindow = Field(
        default="24h",
        description="Time window: 1h, 6h, 24h or 7d.",
    )
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


class ListSourcesInput(BaseModel):
    model_config = {"extra": "forbid"}
    type: Optional[str] = Field(
        default=None,
        max_length=32,
        pattern=r"^(?:rss|twitter|reddit)(?:,(?:rss|twitter|reddit))*$",
        description="Optional type filter, comma-separated: rss, twitter, reddit.",
    )
    limit: Optional[int] = Field(
        default=None,
        ge=1,
        le=500,
        description="Max sources (1 to 500; default 500, the whole registry).",
    )
    offset: Optional[int] = Field(
        default=None,
        ge=0,
        description="Sources to skip, for paging (default 0).",
    )


async def _run_list_sources(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    p = ListSourcesInput.model_validate(args)
    return await _gc().request(
        "/v1/sources",
        {"type": p.type, "limit": p.limit, "offset": p.offset},
    )


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
    status: ThesisStatus = Field(
        default="active",
        description="active, closed, invalidated, pending, or all for no status filter.",
    )
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
    limit: int = Field(default=100, ge=1, le=200)


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
        "Stablecoins from DefiLlama in its order: peg type and mechanism, circulating supply in USD, price and chains, plus BCA's risk score and notes where BCA has rated the coin (null otherwise).",
        ListStablecoinsInput, _run_list_stablecoins,
    ),
    _entry(
        "list_nft_communities",
        "Curated NFT communities (chain, links, tags). Floor price, holders and rank are not collected yet, so the answer is partial.",
        ListNftCommunitiesInput, _run_list_nft_communities,
    ),
    _entry(
        "list_yields",
        "Yield pools from DefiLlama with at least 100,000 USD TVL: project, chain, symbol, TVL, APY (base and reward), stablecoin and IL risk flags, plus BCA's risk tier where rated. Highest APY first; with a minimum APY, every matching pool is ranked by APY. Starter tier.",
        ListYieldsInput, _run_list_yields,
    ),
    _entry(
        "list_aggregators",
        "Swap and bridge aggregators (1inch, Jumper, LI.FI, Rubic, ParaSwap and others) ranked by 30 day volume from DefiLlama, with 24h, 7d and 30d volume in USD; fees are not included. Yield aggregators have no volume source, so they answer partial. Required: kind (dex, bridge or yield); optional chain and limit.",
        ListAggregatorsInput, _run_list_aggregators,
    ),
    _entry(
        "list_mcps",
        "Directory of MCP servers (Blockchain Academics, well-known crypto servers, reference servers) with transport, auth requirement and official repository. Answers unseeded until the registry is seeded.",
        ListMcpsInput, _run_list_mcps,
    ),
    _entry(
        "list_trading_bots",
        "Curated trading bots and terminals (Telegram snipers, Solana terminals and others): website, chains, pricing model, description and tags, by name. Starter tier.",
        ListTradingBotsInput, _run_list_trading_bots,
    ),
    _entry(
        "list_vcs",
        "Crypto VC directory: website, X, HQ, stages, sectors, AUM in USD and portfolio entities; filter by focus (sector) and stage. Answers unseeded until VC records are published. Starter tier.",
        ListVcsInput, _run_list_vcs,
    ),
    _entry(
        "list_jobs",
        "Live crypto jobs (1,300+ open roles at 50+ crypto companies: Coinbase, Binance, OKX, Ripple, Circle, Phantom, Uniswap...) collected every 6h from the companies' own job boards. Filter by role, remote, location, company, keyword. Apply links go to the company's own application page. Works without an API key.",
        ListJobsInput, _run_list_jobs,
    ),
    _entry(
        "get_job",
        "One crypto job in full: description, company, location, remote, salary when published, apply link, BCA job page URL. Errors once the role is filled. Works without an API key.",
        GetJobInput, _run_get_job,
    ),
    _entry(
        "search_grants",
        "Live crypto, web3, AI and public-funding grants (200+ programs) with amounts, deadlines, eligibility and apply links. Verified against each funder's page weekly; expired rounds never returned. Soonest deadline first. Works without an API key.",
        SearchGrantsInput, _run_search_grants,
    ),
    _entry(
        "get_grant",
        "One grant program in full: funder, amount range, deadline, focus areas, geography, application complexity, summary, apply link, last verified date. Works without an API key.",
        GetGrantInput, _run_get_grant,
    ),
    _entry(
        "list_smart_contract_templates",
        "Solidity template catalog (ERC20, ERC721, Vesting, Multisig, Staking, Airdrop) from OpenZeppelin references and BCA academy assets: name, category, version, description and the canonical source_url. The code itself is not hosted.",
        ListSmartContractTemplatesInput, _run_list_smart_contract_templates,
    ),
    _entry(
        "get_smart_contract_template",
        "Catalog entry for one smart contract template: name, category, version, description and the canonical source_url. The code itself is not hosted, so the answer is partial with source_code missing.",
        GetSmartContractTemplateInput, _run_get_smart_contract_template,
    ),
    _entry(
        "list_marketing_templates",
        "Campaign templates: TGE checklist, airdrop ops, NFT mint script, influencer brief, press kit. Answers unseeded while the template bodies are placeholders. Starter tier.",
        ListMarketingTemplatesInput, _run_list_marketing_templates,
    ),
    _entry(
        "get_marketing_template",
        "Fetch a specific marketing template by slug. Unseeded, with body_md null, while its body is a placeholder. Starter tier.",
        GetMarketingTemplateInput, _run_get_marketing_template,
    ),
    _entry(
        "build_custom_indicator",
        "Evaluate a formula over BCA indicator values: coverage_index, sentiment_velocity, price_change_7d and risk_score of entity slugs, combined with + - * /. Returns one value with its component values, not a time series. Unseeded when an input is not computed yet. Pro tier.",
        BuildCustomIndicatorInput, _run_build_custom_indicator,
    ),

    # chains (4)
    _entry(
        "get_solana_ecosystem",
        "Solana overview: DefiLlama chain TVL plus a curated highlights list (Jito, Jupiter, Marinade, Raydium, Drift, Kamino, Tensor, Helium).",
        _EmptyInput, _run_get_solana_ecosystem,
    ),
    _entry(
        "get_l2_comparison",
        "L2 side-by-side: DefiLlama chain TVL plus rollup kind and stack for Base, Arbitrum, Optimism, zkSync, Starknet, Linea, Scroll, Mantle, Blast. Partial when a row has no TVL.",
        _EmptyInput, _run_get_l2_comparison,
    ),
    _entry(
        "get_bitcoin_l2_status",
        "BTC L2s: Stacks, Rootstock, BOB, Babylon, Merlin, Bitlayer, with DefiLlama chain TVL and kind. Babylon's row is the Babylon Genesis chain TVL, not the BTC staked through the Babylon protocol. Starter tier.",
        _EmptyInput, _run_get_bitcoin_l2_status,
    ),
    _entry(
        "get_ton_ecosystem",
        "TON overview: DefiLlama chain TVL plus Telegram mini-app highlights (Notcoin, Hamster Kombat, STON.fi, DeDust, Tonstakers, tgBTC).",
        _EmptyInput, _run_get_ton_ecosystem,
    ),

    # compute (2)
    _entry(
        "get_compute_pricing",
        "GPU rental prices in USD per GPU hour from Akash (live); io.net and Render are listed as pending, so the answer is partial. Optional gpu filter, for example H100.",
        GetComputePricingInput, _run_get_compute_pricing,
    ),
    _entry(
        "get_ai_crypto_metrics",
        "Bittensor subnet metrics from Taostats (unseeded when its API key is not configured); Ritual and Prime Intellect are listed as pending. Starter tier.",
        _EmptyInput, _run_get_ai_crypto_metrics,
    ),

    # memes (4)
    _entry(
        "track_pumpfun",
        "pump.fun coins, trending by 24h volume or newest launches (mode), with price, FDV, liquidity, 24h volume and trades (via GeckoTerminal). Up to 60 per call.",
        TrackPumpfunInput, _run_track_pumpfun,
    ),
    _entry(
        "track_bonkfun",
        "bonk.fun trending launches. Answers unseeded: the feed is not wired yet.",
        TrackBonkfunInput, _run_track_bonkfun,
    ),
    _entry(
        "check_memecoin_risk",
        "Memecoin risk checks for a Solana mint (bundler, sniper, dev sells, LP burn, mint authority) are not computed yet: the tool answers unseeded and lists the planned checks. Required: mint (Solana token mint address). Pro tier.",
        CheckMemecoinRiskInput, _run_check_memecoin_risk,
    ),
    _entry(
        "get_degen_leaderboard",
        "Top PnL wallets on memes. Answers unseeded: the wallet scoring pipeline is not built yet. Pro tier.",
        GetDegenLeaderboardInput, _run_get_degen_leaderboard,
    ),

    # microstructure (5)
    _entry(
        "get_funding_rates",
        "Perpetual funding rates for a symbol on Binance, Bybit and Hyperliquid (USDT pairs): each venue's raw rate with its funding interval (1, 4 or 8 hours), the rate on an 8 hour basis and annualized, mark price and next funding time, plus the mean of the 8 hour rates of the venues whose interval is known. dYdX is listed as pending, so the answer is partial. Pro tier.",
        GetFundingRatesInput, _run_get_funding_rates,
    ),
    _entry(
        "get_options_flow",
        "Deribit options book for BTC, ETH or SOL: the top instruments by open interest with strike, expiry, call or put, mark IV and 24h volume, plus open interest per expiry and the put/call open interest ratio. Lyra and Aevo are not wired. Pro tier.",
        GetOptionsFlowInput, _run_get_options_flow,
    ),
    _entry(
        "get_liquidation_heatmap",
        "Where leveraged positions get wiped (CoinGlass liquidation heatmap). Answers unseeded while no CoinGlass key is configured on the API. Pro tier.",
        GetLiquidationHeatmapInput, _run_get_liquidation_heatmap,
    ),
    _entry(
        "get_exchange_flows",
        "Net inflows and outflows of an asset on centralized exchanges (CoinGlass). Answers unseeded today: no flows source is connected, and window is not applied yet. Pro tier.",
        GetExchangeFlowsInput, _run_get_exchange_flows,
    ),
    _entry(
        "predict_listing",
        "Listing probability (0 to 1) for Binance, Coinbase or Upbit: a BCA editorial heuristic over coverage, risk and dossier inputs. Answers listed true with no probability when the asset already trades there (CoinGecko tickers), unseeded when indicator inputs are missing, partial when some inputs or the listing check are unknown. Pro tier.",
        PredictListingInput, _run_predict_listing,
    ),

    # narrative (5)
    _entry(
        "track_narrative",
        "Narrative strength (AI agents, RWA, DePIN, modular, memes, Bitcoin L2s, SocialFi, GameFi): the mean Narrative Strength score of the narrative's member entities over 7d, 30d or 90d, with each member's score. Partial when some members are unscored, unseeded when none is; an unknown narrative is an error that lists the known slugs. Starter tier.",
        TrackNarrativeInput, _run_track_narrative,
    ),
    _entry(
        "get_ai_agent_tokens",
        "AI agent tokens (Virtuals, elizaOS (formerly ai16z), aixbt, Griffain, Zerebro, Bittensor, Fetch.ai) with CoinGecko price, market cap, 24h volume and change, ranked by market cap.",
        GetAiAgentTokensInput, _run_get_ai_agent_tokens,
    ),
    _entry(
        "get_depin_projects",
        "DePIN tokens (Helium, Render, Filecoin, Akash, IoTeX, DIMO, Hivemapper) with CoinGecko price, market cap, 24h volume and change, ranked by market cap.",
        GetDepinProjectsInput, _run_get_depin_projects,
    ),
    _entry(
        "get_rwa_tokens",
        "Real-world asset tokens (Ondo, Maple, Centrifuge, Goldfinch, Pendle) with CoinGecko price, market cap, 24h volume and change, ranked by market cap. Starter tier.",
        GetRwaTokensInput, _run_get_rwa_tokens,
    ),
    _entry(
        "get_prediction_markets",
        "Prediction market odds from Polymarket and Kalshi (venue): each market's outcomes as a list of {outcome, price}, the price being the implied probability (0 to 1). Partial when a requested venue fails or does not cover the topic (missing names the venue).",
        GetPredictionMarketsInput, _run_get_prediction_markets,
    ),

    # regulatory (4)
    _entry(
        "get_regulatory_status",
        "Crypto regulation state for a country (ISO-2 code): overall status, whether trading, mining and stablecoins are legal, key regulators, key laws, MiCA applicability and notes. Partial while the row has no key laws (all rows today), unseeded for a country without a row. Starter tier.",
        GetRegulatoryStatusInput, _run_get_regulatory_status,
    ),
    _entry(
        "track_sec_filings",
        "Recent SEC EDGAR filings (form, filing date, description, document link) for crypto-related listed companies: MSTR, COIN, HOOD, MARA, RIOT, CLSK, BKKT and GALAXY. Starter tier.",
        TrackSecFilingsInput, _run_track_sec_filings,
    ),
    _entry(
        "get_mica_status",
        "EU MiCA applicability by country (the 27 EU Member States, and EEA states once seeded), with national authorities. Without a country (or with EU), every Member State, partial while some have no row; a country outside the EU and EEA lists answers unseeded unless BCA has a reviewed row for it. Per project status is not tracked yet. Pro tier.",
        GetMicaStatusInput, _run_get_mica_status,
    ),
    _entry(
        "get_tax_rules",
        "Crypto tax rules for a country (ISO-2 code) with a link to the official guidance. Not tax advice. Answers unseeded while BCA has no reviewed tax summary for the country. Starter tier.",
        GetTaxRulesInput, _run_get_tax_rules,
    ),

    # security (4)
    _entry(
        "check_exploit_history",
        "Hack history from DefiLlama's hacks dataset for an entity slug (whole word match on the hack name), newest first: name, date, amount lost and funds returned in USD, chains, classification, technique and source link. Optionally filter by chain and minimum loss.",
        CheckExploitHistoryInput, _run_check_exploit_history,
    ),
    _entry(
        "check_phishing_domain",
        "Checks a domain against MetaMask's phishing list (blocklist, allowlist, lookalikes) plus a pattern heuristic; verdict blocklisted, suspicious, allowlisted or clean_local.",
        CheckPhishingDomainInput, _run_check_phishing_domain,
    ),
    _entry(
        "get_bug_bounty_programs",
        "Active Immunefi bug bounty programs, largest top bounty first, filterable by chain and minimum payout (USD). Answers unseeded until the Immunefi feed is switched on in the API.",
        GetBugBountyProgramsInput, _run_get_bug_bounty_programs,
    ),
    _entry(
        "scan_contract",
        "Etherscan verified-source check for an EVM contract on Ethereum: verified, contract name, compiler, proxy and implementation address, license and a source preview. No honeypot or exploit test. Required: address (0x EVM address). Starter tier.",
        ScanContractInput, _run_scan_contract,
    ),

    # services: POST (3)
    _entry(
        "book_kol_campaign",
        "Send a KOL campaign brief to BCA Studio. Required: contact_email, project_name, campaign_type (thread, video, space, podcast or hybrid) and budget_usd (500 to 2,000,000 USD). Needs an API key (the free tier is enough). Each brief alerts BCA Studio, who reply to contact_email by hand with a recommended KOL slate and quote (nothing is emailed automatically). Returns request_id, status and next_step.",
        BookKolCampaignInput, _run_book_kol_campaign,
    ),
    _entry(
        "request_custom_research",
        "Request a custom research report from BCA Research. Required: contact_email and topic (4 to 256 characters). Needs an API key (the free tier is enough). Each request alerts BCA Research, who reply to contact_email by hand with scope and a quote. Returns request_id, status and next_step.",
        RequestCustomResearchInput, _run_request_custom_research,
    ),
    _entry(
        "submit_listing",
        "Submit a listing to a BCA directory: vcs, aggregators, trading_bots, mcps, nft_communities, jobs, stablecoins or trading_yields. Required: contact_email, directory, listing_name, listing_url and description (20 to 2,000 characters). Needs an API key (the free tier is enough). Each submission alerts the editors, who review it for fit and reply to contact_email by hand. Returns request_id, status and next_step.",
        SubmitListingInput, _run_submit_listing,
    ),

    # history (4)
    _entry(
        "get_history_prices",
        "Historical price series for a coin symbol from BCA's hourly price snapshots (CoinGecko), up to 365 days: hourly up to 30 days and daily beyond unless granularity says otherwise; snapshot_at is the newest snapshot. Partial when days in the window have no snapshot, stale when the newest is over 3 hours old.",
        GetHistoryPricesInput, _run_get_history_prices,
    ),
    _entry(
        "get_history_sentiment",
        "Historical daily sentiment index for a coin symbol, up to 365 days, from the news BCA ingests. tweet_count is null for days after the newest collected X post, and the answer is partial while the X reader is off.",
        GetHistorySentimentInput, _run_get_history_sentiment,
    ),
    _entry(
        "get_history_correlation",
        "Pearson correlation of a coin's daily price change against its daily BCA sentiment and, with peer, against the peer's daily price change, with the aligned daily series (each row carries peer_price_change_pct when peer is given). Partial below 7 paired days, for a flat series, or when an input is missing for part of the window.",
        GetHistoryCorrelationInput, _run_get_history_correlation,
    ),
    _entry(
        "get_history_coverage",
        "Historical BCA coverage series per entity: article count and average sentiment per day for the currency the entity maps to, up to 365 days. Unseeded for entities with no tracked currency.",
        GetHistoryCoverageInput, _run_get_history_coverage,
    ),

    # corpus meta (7)
    _entry(
        "list_entities",
        "Browse the BCA entity universe (about 150 entities), most mentioned first. Filter by kind: chain, project, person or ticker (protocol, exchange and fund hold no entities yet and answer unseeded); page with offset.",
        ListEntitiesInput, _run_list_entities,
    ),
    _entry(
        "get_topic",
        "Fetch a topic from the taxonomy: live article count, child topics and up to 5 recent articles. Partial when no article carries the topic yet. Works without an API key.",
        GetTopicInput, _run_get_topic,
    ),
    _entry(
        "search_academy",
        "Full text search across academy lessons. Each hit has the course and lesson slugs, title, summary, publish date and site_url, the lesson's page on blockchainacademics.com (the slugs are not page URLs). Unseeded when nothing matches. Works without an API key.",
        SearchAcademyInput, _run_search_academy,
    ),
    _entry(
        "get_trending",
        "Trending coins by mentions over 1h, 6h, 24h or 7d: article and X post mention counts and average sentiment per coin (no articles in the answer). Partial with tweets missing while the X reader is paused. Works without an API key.",
        GetTrendingInput, _run_get_trending,
    ),
    _entry(
        "get_unified_feed",
        "Chronological news feed from the RSS and Reddit sources BCA ingests, newest first: title, link, snippet, source, publish time, currency tags, category and sentiment per article.",
        GetUnifiedFeedInput, _run_get_unified_feed,
    ),
    _entry(
        "list_sources",
        "Every news source BCA ingests (RSS feeds, X accounts, Reddit) with type, URL and trust tier, plus whether BCA collects it now (collecting, not_collecting_reason) and when it last stored an item from it (last_fetched_at). X accounts stay listed but answer collecting false (x_reader_off) while the X reader is off. Returns the whole registry by default (up to 500); has_more and next_offset say when to page.",
        ListSourcesInput, _run_list_sources,
    ),
    _entry(
        "get_recent_stories",
        "Recent clustered stories: related articles from the last 24 hours grouped into one story each (deduped across sources), with any X signals attached. Works without an API key.",
        GetRecentStoriesInput, _run_get_recent_stories,
    ),

    # memos + theses (4)
    _entry(
        "list_memos",
        "Browse public investment memos (paid fields redacted). Answers unseeded today: the only public rows are test fixtures, flagged fixture true. Starter tier.",
        ListMemosInput, _run_list_memos,
    ),
    _entry(
        "get_memo",
        "Fetch a specific investment memo by slug. Answers unseeded for the test fixture rows, the only public memos today. Starter tier.",
        GetMemoInput, _run_get_memo,
    ),
    _entry(
        "list_theses",
        "Browse public trade theses (entry / invalidation / targets) by status. Answers unseeded today: the only public rows are test fixtures, flagged fixture true. Starter tier.",
        ListThesesInput, _run_list_theses,
    ),
    _entry(
        "get_thesis",
        "Fetch a specific trade thesis by slug. Answers unseeded for the test fixture rows, the only public theses today. Starter tier.",
        GetThesisInput, _run_get_thesis,
    ),

    # currencies (2)
    _entry(
        "list_currencies",
        "All tracked currencies: symbol, name and CoinGecko id, sorted by symbol.",
        ListCurrenciesInput, _run_list_currencies,
    ),
    _entry(
        "get_currency_feed",
        "Chronological feed of the articles and X posts that mention a single currency, newest first. An unknown symbol is an error.",
        GetCurrencyFeedInput, _run_get_currency_feed,
    ),
)
