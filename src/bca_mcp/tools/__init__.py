"""BCA MCP tool modules — v0.1 scaffold with 8 read-only tools.

v0.1 ships narrow on purpose: the 8 most-used corpus + market tools,
identical in shape to the TS sibling's `@blockchainacademics/mcp@0.1`.
Later versions port the remaining ~91 tools from `@blockchainacademics/mcp@0.2.2`.

Category map for the full target surface (parity with TS v0.2.2):

    content    — search_news [*], get_article [*], get_entity [*],
                 list_entity_mentions [*], list_topics [*], get_explainer [*],
                 get_as_of_snapshot
    market     — get_price [*], get_market_overview [*], get_ohlc,
                 get_pair_data
    sentiment  — get_fear_greed, get_sentiment, get_social_pulse
    indicators — get_coverage_index, get_narrative_strength, get_risk_score,
                 get_sentiment_velocity, get_editorial_premium,
                 get_kol_influence
    onchain    — get_wallet_profile, get_tx, get_token_holders,
                 get_defi_protocol
    agent_jobs — generate_due_diligence, generate_tokenomics_model,
                 summarize_whitepaper, translate_contract, monitor_keyword,
                 get_agent_job
    extended   — 60+ directories, fundamentals, chain-specific,
                 microstructure, narrative, regulatory, security, services,
                 history, memos, theses, social signals, currencies

[*] = shipped in v0.1.
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
