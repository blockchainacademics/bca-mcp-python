"""MCP stdio server — registers the BCA tool surface.

Mirrors the behavior of the TypeScript sibling:
  * `list_tools` advertises name/description/input JSON Schema
  * `call_tool` validates args, surfaces `attribution` on success,
    returns `isError: true` with `{code, message}` on failure — the
    process never dies on upstream errors.
  * Startup **fail-fast** on missing `BCA_API_KEY` so misconfigured
    hosts surface the problem immediately (not on first tool call).

Current tool surface (98 tools — full parity with TS v0.2.3):

    content      (6)  — search_news, get_article, get_entity,
                        list_entity_mentions, list_topics, get_explainer
    market       (4)  — get_price, get_market_overview, get_ohlc, get_pair_data
    onchain      (4)  — get_wallet_profile, get_tx, get_token_holders,
                        get_defi_protocol
    sentiment    (5)  — get_sentiment, get_social_pulse, get_fear_greed,
                        get_social_signals, get_social_signals_detail
    indicators   (6)  — get_coverage_index, get_narrative_strength,
                        get_sentiment_velocity, get_editorial_premium,
                        get_kol_influence, get_risk_score
    fundamentals (6)  — get_tokenomics, get_audit_reports, get_team_info,
                        get_roadmap, compare_protocols, check_rugpull_risk
    agent_jobs   (6)  — generate_due_diligence, generate_tokenomics_model,
                        summarize_whitepaper, translate_contract,
                        monitor_keyword, get_agent_job
    extended    (61)  — directories, chains, compute, memes,
                        microstructure, narrative, regulatory, security,
                        services POST, history, corpus meta, memos+theses,
                        currencies — mirrors ``src/tools/extended.ts``
"""

from __future__ import annotations

import json as _json
import os
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Sequence

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from bca_mcp.errors import BcaError
from bca_mcp.types import resolve_envelope_status
from bca_mcp.tools import agent_jobs as _agent_jobs
from bca_mcp.tools import content as _content
from bca_mcp.tools import extended as _extended
from bca_mcp.tools import fundamentals as _fundamentals
from bca_mcp.tools import get_entity as _get_entity
from bca_mcp.tools import get_explainer as _get_explainer
from bca_mcp.tools import indicators as _indicators
from bca_mcp.tools import market as _market
from bca_mcp.tools import onchain as _onchain
from bca_mcp.tools import search_news as _search_news
from bca_mcp.tools import sentiment as _sentiment


@dataclass(frozen=True)
class ToolEntry:
    name: str
    description: str
    input_schema: dict[str, Any]
    run: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


TOOLS: tuple[ToolEntry, ...] = (
    # --- content & corpus (6) ----------------------------------------------
    ToolEntry(
        name=_search_news.TOOL_NAME,
        description=_search_news.TOOL_DESCRIPTION,
        input_schema=_search_news.input_json_schema(),
        run=_search_news.run,
    ),
    ToolEntry(
        name=_content.GET_ARTICLE_TOOL_NAME,
        description=_content.GET_ARTICLE_TOOL_DESCRIPTION,
        input_schema=_content.get_article_input_schema(),
        run=_content.run_get_article,
    ),
    ToolEntry(
        name=_get_entity.TOOL_NAME,
        description=_get_entity.TOOL_DESCRIPTION,
        input_schema=_get_entity.input_json_schema(),
        run=_get_entity.run,
    ),
    ToolEntry(
        name=_content.LIST_ENTITY_MENTIONS_TOOL_NAME,
        description=_content.LIST_ENTITY_MENTIONS_TOOL_DESCRIPTION,
        input_schema=_content.list_entity_mentions_input_schema(),
        run=_content.run_list_entity_mentions,
    ),
    ToolEntry(
        name=_content.LIST_TOPICS_TOOL_NAME,
        description=_content.LIST_TOPICS_TOOL_DESCRIPTION,
        input_schema=_content.list_topics_input_schema(),
        run=_content.run_list_topics,
    ),
    ToolEntry(
        name=_get_explainer.TOOL_NAME,
        description=_get_explainer.TOOL_DESCRIPTION,
        input_schema=_get_explainer.input_json_schema(),
        run=_get_explainer.run,
    ),
    # --- market (4) --------------------------------------------------------
    ToolEntry(
        name=_market.GET_PRICE_TOOL_NAME,
        description=_market.GET_PRICE_TOOL_DESCRIPTION,
        input_schema=_market.get_price_input_schema(),
        run=_market.run_get_price,
    ),
    ToolEntry(
        name=_market.GET_MARKET_OVERVIEW_TOOL_NAME,
        description=_market.GET_MARKET_OVERVIEW_TOOL_DESCRIPTION,
        input_schema=_market.get_market_overview_input_schema(),
        run=_market.run_get_market_overview,
    ),
    ToolEntry(
        name=_market.GET_OHLC_TOOL_NAME,
        description=_market.GET_OHLC_TOOL_DESCRIPTION,
        input_schema=_market.get_ohlc_input_schema(),
        run=_market.run_get_ohlc,
    ),
    ToolEntry(
        name=_market.GET_PAIR_DATA_TOOL_NAME,
        description=_market.GET_PAIR_DATA_TOOL_DESCRIPTION,
        input_schema=_market.get_pair_data_input_schema(),
        run=_market.run_get_pair_data,
    ),
    # --- onchain (4) -------------------------------------------------------
    ToolEntry(
        name=_onchain.GET_WALLET_PROFILE_TOOL_NAME,
        description=_onchain.GET_WALLET_PROFILE_TOOL_DESCRIPTION,
        input_schema=_onchain.get_wallet_profile_input_schema(),
        run=_onchain.run_get_wallet_profile,
    ),
    ToolEntry(
        name=_onchain.GET_TX_TOOL_NAME,
        description=_onchain.GET_TX_TOOL_DESCRIPTION,
        input_schema=_onchain.get_tx_input_schema(),
        run=_onchain.run_get_tx,
    ),
    ToolEntry(
        name=_onchain.GET_TOKEN_HOLDERS_TOOL_NAME,
        description=_onchain.GET_TOKEN_HOLDERS_TOOL_DESCRIPTION,
        input_schema=_onchain.get_token_holders_input_schema(),
        run=_onchain.run_get_token_holders,
    ),
    ToolEntry(
        name=_onchain.GET_DEFI_PROTOCOL_TOOL_NAME,
        description=_onchain.GET_DEFI_PROTOCOL_TOOL_DESCRIPTION,
        input_schema=_onchain.get_defi_protocol_input_schema(),
        run=_onchain.run_get_defi_protocol,
    ),
    # --- sentiment + social (5) -------------------------------------------
    ToolEntry(
        name=_sentiment.GET_SENTIMENT_TOOL_NAME,
        description=_sentiment.GET_SENTIMENT_TOOL_DESCRIPTION,
        input_schema=_sentiment.get_sentiment_input_schema(),
        run=_sentiment.run_get_sentiment,
    ),
    ToolEntry(
        name=_sentiment.GET_SOCIAL_PULSE_TOOL_NAME,
        description=_sentiment.GET_SOCIAL_PULSE_TOOL_DESCRIPTION,
        input_schema=_sentiment.get_social_pulse_input_schema(),
        run=_sentiment.run_get_social_pulse,
    ),
    ToolEntry(
        name=_sentiment.GET_FEAR_GREED_TOOL_NAME,
        description=_sentiment.GET_FEAR_GREED_TOOL_DESCRIPTION,
        input_schema=_sentiment.get_fear_greed_input_schema(),
        run=_sentiment.run_get_fear_greed,
    ),
    ToolEntry(
        name=_sentiment.GET_SOCIAL_SIGNALS_TOOL_NAME,
        description=_sentiment.GET_SOCIAL_SIGNALS_TOOL_DESCRIPTION,
        input_schema=_sentiment.get_social_signals_input_schema(),
        run=_sentiment.run_get_social_signals,
    ),
    ToolEntry(
        name=_sentiment.GET_SOCIAL_SIGNALS_DETAIL_TOOL_NAME,
        description=_sentiment.GET_SOCIAL_SIGNALS_DETAIL_TOOL_DESCRIPTION,
        input_schema=_sentiment.get_social_signals_detail_input_schema(),
        run=_sentiment.run_get_social_signals_detail,
    ),
    # --- indicators (6) ---------------------------------------------------
    ToolEntry(
        name=_indicators.GET_COVERAGE_INDEX_TOOL_NAME,
        description=_indicators.GET_COVERAGE_INDEX_TOOL_DESCRIPTION,
        input_schema=_indicators.get_coverage_index_input_schema(),
        run=_indicators.run_get_coverage_index,
    ),
    ToolEntry(
        name=_indicators.GET_NARRATIVE_STRENGTH_TOOL_NAME,
        description=_indicators.GET_NARRATIVE_STRENGTH_TOOL_DESCRIPTION,
        input_schema=_indicators.get_narrative_strength_input_schema(),
        run=_indicators.run_get_narrative_strength,
    ),
    ToolEntry(
        name=_indicators.GET_SENTIMENT_VELOCITY_TOOL_NAME,
        description=_indicators.GET_SENTIMENT_VELOCITY_TOOL_DESCRIPTION,
        input_schema=_indicators.get_sentiment_velocity_input_schema(),
        run=_indicators.run_get_sentiment_velocity,
    ),
    ToolEntry(
        name=_indicators.GET_EDITORIAL_PREMIUM_TOOL_NAME,
        description=_indicators.GET_EDITORIAL_PREMIUM_TOOL_DESCRIPTION,
        input_schema=_indicators.get_editorial_premium_input_schema(),
        run=_indicators.run_get_editorial_premium,
    ),
    ToolEntry(
        name=_indicators.GET_KOL_INFLUENCE_TOOL_NAME,
        description=_indicators.GET_KOL_INFLUENCE_TOOL_DESCRIPTION,
        input_schema=_indicators.get_kol_influence_input_schema(),
        run=_indicators.run_get_kol_influence,
    ),
    ToolEntry(
        name=_indicators.GET_RISK_SCORE_TOOL_NAME,
        description=_indicators.GET_RISK_SCORE_TOOL_DESCRIPTION,
        input_schema=_indicators.get_risk_score_input_schema(),
        run=_indicators.run_get_risk_score,
    ),
    # --- fundamentals (6) --------------------------------------------------
    ToolEntry(
        name=_fundamentals.GET_TOKENOMICS_TOOL_NAME,
        description=_fundamentals.GET_TOKENOMICS_TOOL_DESCRIPTION,
        input_schema=_fundamentals.get_tokenomics_input_schema(),
        run=_fundamentals.run_get_tokenomics,
    ),
    ToolEntry(
        name=_fundamentals.GET_AUDIT_REPORTS_TOOL_NAME,
        description=_fundamentals.GET_AUDIT_REPORTS_TOOL_DESCRIPTION,
        input_schema=_fundamentals.get_audit_reports_input_schema(),
        run=_fundamentals.run_get_audit_reports,
    ),
    ToolEntry(
        name=_fundamentals.GET_TEAM_INFO_TOOL_NAME,
        description=_fundamentals.GET_TEAM_INFO_TOOL_DESCRIPTION,
        input_schema=_fundamentals.get_team_info_input_schema(),
        run=_fundamentals.run_get_team_info,
    ),
    ToolEntry(
        name=_fundamentals.GET_ROADMAP_TOOL_NAME,
        description=_fundamentals.GET_ROADMAP_TOOL_DESCRIPTION,
        input_schema=_fundamentals.get_roadmap_input_schema(),
        run=_fundamentals.run_get_roadmap,
    ),
    ToolEntry(
        name=_fundamentals.COMPARE_PROTOCOLS_TOOL_NAME,
        description=_fundamentals.COMPARE_PROTOCOLS_TOOL_DESCRIPTION,
        input_schema=_fundamentals.compare_protocols_input_schema(),
        run=_fundamentals.run_compare_protocols,
    ),
    ToolEntry(
        name=_fundamentals.CHECK_RUGPULL_RISK_TOOL_NAME,
        description=_fundamentals.CHECK_RUGPULL_RISK_TOOL_DESCRIPTION,
        input_schema=_fundamentals.check_rugpull_risk_input_schema(),
        run=_fundamentals.run_check_rugpull_risk,
    ),
    # --- agent jobs (6) ----------------------------------------------------
    ToolEntry(
        name=_agent_jobs.GENERATE_DUE_DILIGENCE_TOOL_NAME,
        description=_agent_jobs.GENERATE_DUE_DILIGENCE_TOOL_DESCRIPTION,
        input_schema=_agent_jobs.generate_due_diligence_input_schema(),
        run=_agent_jobs.run_generate_due_diligence,
    ),
    ToolEntry(
        name=_agent_jobs.GENERATE_TOKENOMICS_MODEL_TOOL_NAME,
        description=_agent_jobs.GENERATE_TOKENOMICS_MODEL_TOOL_DESCRIPTION,
        input_schema=_agent_jobs.generate_tokenomics_model_input_schema(),
        run=_agent_jobs.run_generate_tokenomics_model,
    ),
    ToolEntry(
        name=_agent_jobs.SUMMARIZE_WHITEPAPER_TOOL_NAME,
        description=_agent_jobs.SUMMARIZE_WHITEPAPER_TOOL_DESCRIPTION,
        input_schema=_agent_jobs.summarize_whitepaper_input_schema(),
        run=_agent_jobs.run_summarize_whitepaper,
    ),
    ToolEntry(
        name=_agent_jobs.TRANSLATE_CONTRACT_TOOL_NAME,
        description=_agent_jobs.TRANSLATE_CONTRACT_TOOL_DESCRIPTION,
        input_schema=_agent_jobs.translate_contract_input_schema(),
        run=_agent_jobs.run_translate_contract,
    ),
    ToolEntry(
        name=_agent_jobs.MONITOR_KEYWORD_TOOL_NAME,
        description=_agent_jobs.MONITOR_KEYWORD_TOOL_DESCRIPTION,
        input_schema=_agent_jobs.monitor_keyword_input_schema(),
        run=_agent_jobs.run_monitor_keyword,
    ),
    ToolEntry(
        name=_agent_jobs.GET_AGENT_JOB_TOOL_NAME,
        description=_agent_jobs.GET_AGENT_JOB_TOOL_DESCRIPTION,
        input_schema=_agent_jobs.get_agent_job_input_schema(),
        run=_agent_jobs.run_get_agent_job,
    ),
    # --- extended surface (61) --- full parity with TS v0.2.3 ---------------
    # Directories (13) · Chains (4) · Compute (2) · Memes (4) ·
    # Microstructure (5) · Narrative (5) · Regulatory (4) · Security (4) ·
    # Services POST (3) · History (4) · Corpus meta (7) ·
    # Memos + theses (4) · Currencies (2)
    *(
        ToolEntry(
            name=_name,
            description=_description,
            input_schema=_schema,
            run=_runner,
        )
        for (_name, _description, _schema, _runner) in _extended.EXTENDED_TOOL_ENTRIES
    ),
)


def _error_content(code: str, message: str) -> list[TextContent]:
    return [
        TextContent(
            type="text",
            text=_json.dumps({"error": {"code": code, "message": message}}, indent=2),
        )
    ]


def _assert_api_key_present() -> None:
    """Fail-fast if ``BCA_API_KEY`` is not set in the environment.

    This runs at server construction so misconfigured MCP hosts get an
    actionable error at startup instead of cryptic failures on the first
    tool call. Matches the TS sibling's behavior of throwing at first
    request — but we surface it earlier because stdio hosts buffer
    startup stderr to the user log.
    """
    if not os.environ.get("BCA_API_KEY"):
        raise RuntimeError(
            "BCA_API_KEY is not set. Get a key at "
            "https://brain.blockchainacademics.com/pricing and export it "
            "before launching the MCP server."
        )


def build_server(check_env: bool = True) -> Server:
    """Construct the MCP `Server` with the 98-tool surface wired up.

    Args:
        check_env: If True (default), raise at construction time when
            BCA_API_KEY is missing. Tests pass ``False`` to exercise
            the server without a live key.
    """
    if check_env:
        _assert_api_key_present()

    server: Server = Server("bca-mcp")

    @server.list_tools()
    async def _list_tools() -> list[Tool]:
        return [
            Tool(
                name=t.name,
                description=t.description,
                inputSchema=t.input_schema,
            )
            for t in TOOLS
        ]

    @server.call_tool()
    async def _call_tool(
        name: str,
        arguments: dict[str, Any] | None,
    ) -> Sequence[TextContent]:
        tool = next((t for t in TOOLS if t.name == name), None)
        if tool is None:
            return _error_content("BCA_BAD_REQUEST", f"Unknown tool: {name}")

        try:
            envelope = await tool.run(arguments or {})
            # Attribution surfacing: cite_url / as_of / source_hash always
            # present (null when upstream omits) so downstream agents can
            # detect provenance. `status` is always present on the wire —
            # middleware default-fills to "complete", auto-detects "unseeded"
            # on empty payloads, and respects explicit values set by tool
            # authors (e.g. "partial", "error"). Legacy upstream statuses
            # like "integration_pending" / "upstream_error" flow through
            # envelope.meta for the MCP client to surface as it sees fit.
            status = resolve_envelope_status(
                envelope.get("data"),
                envelope.get("status"),
            )
            payload = {
                "data": envelope.get("data"),
                "status": status,
                "attribution": {
                    "cite_url": envelope.get("cite_url"),
                    "as_of": envelope.get("as_of"),
                    "source_hash": envelope.get("source_hash"),
                },
                "meta": envelope.get("meta"),
            }
            return [
                TextContent(
                    type="text",
                    text=_json.dumps(payload, indent=2, default=str),
                )
            ]
        except BcaError as err:
            return _error_content(err.code, str(err))
        except Exception as err:  # pydantic ValidationError, etc.
            code = (
                "BCA_BAD_REQUEST"
                if err.__class__.__name__ == "ValidationError"
                else "BCA_UNKNOWN"
            )
            return _error_content(code, str(err))

    return server


async def run_stdio() -> None:
    server = build_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )
