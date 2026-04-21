# BCA MCP Python Port Manifest — Task #122

**Generated:** 2026-04-21
**Status:** Port planning document (READ-ONLY exploration — no code changes)
**Source of truth:** `~/bca-mcp-ts/src/index.ts` (99 tools registered via `entry()` calls)

## Tool count

- **TypeScript total:** 99 tools
- **Python v0.1.0 ported:** 8 tools
- **Remaining to port:** 91 tools

## Already ported (8)

| Tool | Python module | TS parity |
|---|---|---|
| `search_news` | `tools/search_news.py` | ✓ |
| `get_article` | `tools/content.py` | ✓ |
| `get_entity` | `tools/get_entity.py` | ✓ |
| `list_entity_mentions` | `tools/content.py` | ✓ |
| `list_topics` | `tools/content.py` | ✓ |
| `get_explainer` | `tools/get_explainer.py` | ✓ |
| `get_price` | `tools/market.py` | ✓ |
| `get_market_overview` | `tools/market.py` | ✓ |

No schema drift vs. TS.

## Category breakdown (unported)

| Category | TS count | Ported | Delta |
|---|---|---|---|
| News & Entities | 3 | 3 | 0 |
| Content & Corpus | 4 | 4 | 0 |
| Market Data | 4 | 2 | **2** |
| On-Chain | 4 | 0 | **4** |
| Sentiment | 3 | 0 | **3** |
| Indicators | 6 | 0 | **6** |
| Agent Jobs | 6 | 0 | **6** |
| Directories | 13 | 0 | **13** |
| Fundamentals | 6 | 0 | **6** |
| Chain-Specific | 4 | 0 | **4** |
| Compute/AI | 2 | 0 | **2** |
| Memes | 4 | 0 | **4** |
| Microstructure | 5 | 0 | **5** |
| Narrative | 5 | 0 | **5** |
| Regulatory | 4 | 0 | **4** |
| Security | 4 | 0 | **4** |
| Services (POST) | 3 | 0 | **3** |
| History/Time-Series | 4 | 0 | **4** |
| Corpus Meta | 7 | 0 | **7** |
| Memos/Theses | 4 | 0 | **4** |
| Social Signals | 2 | 0 | **2** |
| Currencies | 2 | 0 | **2** |
| **Total** | **99** | **8** | **91** |

## Unported tools by category

**Market (2):** `get_ohlc`, `get_pair_data`

**On-Chain (4):** `get_wallet_profile`, `get_tx`, `get_token_holders`, `get_defi_protocol`

**Sentiment (3):** `get_sentiment`, `get_social_pulse` (⚠ integration_pending), `get_fear_greed`

**Indicators (6 — all share `entity_slug` + `window` pattern):** `get_coverage_index`, `get_narrative_strength`, `get_sentiment_velocity`, `get_editorial_premium`, `get_kol_influence`, `get_risk_score`

**Agent Jobs (6 — async POST + polling):** `generate_due_diligence`, `generate_tokenomics_model`, `summarize_whitepaper`, `translate_contract`, `monitor_keyword`, `get_agent_job`

**Directories (13):** `list_stablecoins`, `list_nft_communities`, `list_yields`, `list_aggregators`, `list_mcps`, `list_trading_bots`, `list_vcs`, `list_jobs`, `list_smart_contract_templates`, `get_smart_contract_template`, `list_marketing_templates`, `get_marketing_template`, `build_custom_indicator`

**Fundamentals (6):** `get_tokenomics`, `get_audit_reports`, `get_team_info`, `get_roadmap`, `compare_protocols`, `check_rugpull_risk`

**Chain-Specific (4):** `get_solana_ecosystem`, `get_l2_comparison`, `get_bitcoin_l2_status`, `get_ton_ecosystem`

**Compute/AI (2):** `get_compute_pricing`, `get_ai_crypto_metrics`

**Memes (4):** `track_pumpfun`, `track_bonkfun`, `check_memecoin_risk`, `get_degen_leaderboard`

**Microstructure (5):** `get_funding_rates`, `get_options_flow`, `get_liquidation_heatmap`, `get_exchange_flows`, `predict_listing`

**Narrative (5):** `track_narrative`, `get_ai_agent_tokens`, `get_depin_projects`, `get_rwa_tokens`, `get_prediction_markets`

**Regulatory (4):** `get_regulatory_status`, `track_sec_filings`, `get_mica_status`, `get_tax_rules`

**Security (4):** `check_exploit_history`, `check_phishing_domain`, `get_bug_bounty_programs`, `scan_contract`

**Services (3, POST):** `book_kol_campaign`, `request_custom_research`, `submit_listing`

**History (4):** `get_history_prices`, `get_history_sentiment`, `get_history_correlation`, `get_history_coverage`

**Corpus Meta (7):** `list_entities`, `get_topic`, `search_academy`, `get_trending`, `get_unified_feed`, `list_sources`, `get_recent_stories`

**Memos/Theses (4):** `list_memos`, `get_memo`, `list_theses`, `get_thesis`

**Social Signals (2):** `get_social_signals`, `get_social_signals_detail`

**Currencies (2):** `list_currencies`, `get_currency_feed`

## Shared patterns (Python reusable primitives)

- **Window enum:** `Literal['1d', '7d', '30d', '90d']` (or subset). Factor into `types.py`.
- **Entity slug:** `str` validated by regex `^[a-z0-9]+(?:-[a-z0-9]+)*$`. Shared validator.
- **Chain enum:** 7 tools share same chain list (eth, solana, arbitrum, base, optimism, polygon, bnb). Factor.
- **Ticker/symbol:** common across sentiment + microstructure + history.
- **Async job pattern:** agent-jobs return `{job_id, status_url}`; `get_agent_job` polls. Single base class.
- **Untrusted-content wrapping:** TS wraps third-party content in `<untrusted_content>` tags — mirror in Python.

## Batched execution plan

| Batch | Tools | LOC est. | Categories | Notes |
|---|---|---|---|---|
| 1 | 4 | 150–180 | market, onchain core | Simplest endpoints, high-demand |
| 2 | 5 | 120–150 | sentiment, social_signals | 1 integration_pending |
| 3 | 7 | 140–170 | indicators, onchain token_holders | Shared window+slug pattern |
| 4 | 7 | 160–200 | fundamentals, onchain defi | |
| 5 | 6 | 180–220 | agent_jobs (async POST + poll) | New pattern class |
| 6 | 16 | 250–320 | directories, services | Largest batch; all list-shaped |
| 7 | 15 | 200–250 | narrative, regulatory, security, compute | |
| 8 | 17 | 180–220 | chain-specific, memes, microstructure, history | |
| 9 | 13 | 150–180 | corpus_meta, memos_theses, currencies | |

**Total:** 9 batches, 91 tools, ~1,630–1,890 LOC + tests.

## Recommended Batch 1 targets (start here)

1. `get_ohlc` — `GET /v1/market/ohlc` | params: id, days, vs
2. `get_pair_data` — `GET /v1/market/pair` | params: chain, pair
3. `get_wallet_profile` — on-chain research foundation
4. `get_tx` — transaction decoding
5. `get_token_holders` — concentration risk

Unblocks ~30% of downstream use cases; zero cross-batch dependencies.

## Integration risks (full audit)

- **Only one tool flagged** as `integration_pending`: `get_social_pulse` (Twitter/Reddit OAuth pending). Its Python port is the same shape — backend returns envelope `{data: null, status: "integration_pending"}` unchanged.
- Schema fidelity across `extended.ts` (31 KB, 812 lines) is consistent — no sketchy zod declarations.
- No missing implementation details in TS source.
- `client.py` in Python MCP already supports GET + POST patterns needed.

## Open decisions for Wael before executing batches

1. **Version gate:** `pyproject.toml` currently reads `0.2.0`. Options: (a) roll back to `0.2.0.dev0` and bump to `0.2.0` only when all 91 land, (b) keep `0.2.0` and ship batches as `0.2.0.post1`, `0.2.0.post2`, etc.
2. **0.1.0 release artifact:** currently un-pushed, un-tagged. Ship `v0.1.0` to PyPI first so we have an 8-tool baseline in the wild? Or go straight to 0.2.0 with 99 tools?
3. **CLI flag:** `--list-tools` isn't implemented. Add as part of batch 1, or keep `python -m bca_mcp --list-tools` as the contract?

Defaults if no answer: roll to `0.2.0.dev0`, skip 0.1.0 release, add `--list-tools` in batch 1.
