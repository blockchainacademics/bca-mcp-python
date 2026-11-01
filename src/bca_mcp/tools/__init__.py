"""BCA MCP tool modules: the 105 tools, the same names as the TS sibling.

Category map (server.py registers them in this order):

    content      search_news, get_article, get_entity, list_entity_mentions,
                 list_topics, get_explainer, get_as_of_snapshot
    market       get_price, get_market_overview, get_ohlc, get_pair_data
    onchain      get_wallet_profile, get_tx, get_token_holders,
                 get_defi_protocol
    sentiment    get_sentiment, get_social_pulse, get_fear_greed,
                 get_ct_pulse, get_x_signals, get_kol_consensus,
                 get_social_signals, get_social_signals_detail
    indicators   get_coverage_index, get_narrative_strength,
                 get_sentiment_velocity, get_editorial_premium,
                 get_kol_influence, get_risk_score
    fundamentals get_tokenomics, get_audit_reports, get_team_info,
                 get_roadmap, compare_protocols, check_rugpull_risk
    agent_jobs   generate_due_diligence, generate_tokenomics_model,
                 summarize_whitepaper, translate_contract, monitor_keyword,
                 get_agent_job
    extended     directories, chains, compute, memes, microstructure,
                 narrative, regulatory, security, services, history,
                 corpus meta, memos and theses, currencies

Each input model mirrors the API route it calls (mcp-fix/integration,
2026-11-01): the same parameter bounds, mapped to the API's query names
where a tool's name differs.
"""

from bca_mcp.tools import (
    content,
    get_entity,
    get_explainer,
    market,
    search_news,
)

__all__ = [
    "search_news",
    "get_entity",
    "get_explainer",
    "content",
    "market",
]
