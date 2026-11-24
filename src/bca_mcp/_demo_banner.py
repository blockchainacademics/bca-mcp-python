# Stderr banner emitted once at server startup when the client falls back
# to the demo key (no BCA_API_KEY env var). Stdout is owned by the MCP stdio
# transport, so this MUST stay on stderr.
#
# Three lines, ASCII-only, each terminated with \n. The TS sibling at
# src/demo_banner.ts must match byte-for-byte. The tools that work without a
# key are the API's demo allowlist (app/api/v1/_demo_allowlist.py): get_price,
# get_trending, get_fear_greed, get_market_overview, search_news,
# get_article, get_sentiment, get_entity, get_explainer, get_recent_stories,
# get_topic, search_grants, get_grant, list_jobs, get_job, search_academy,
# get_as_of_snapshot, and the 8 Stats tools while owner decision 1 opens them
# to the demo key (DEMO_KEY_OPENS_STATS in tools/stats.py): 25 in all, or 17.
# "60 tools" is the free tier: every other tool names its paid tier (Starter,
# Pro or Team) in its description (tests/test_copy.py counts them).

from bca_mcp.tools.stats import DEMO_KEY_OPENS_STATS

_WITHOUT_A_KEY = 25 if DEMO_KEY_OPENS_STATS else 17

DEMO_BANNER = (
    f"[bca-mcp] Running in DEMO mode: {_WITHOUT_A_KEY} tools work without a key, under a shared daily cap.\n"
    "[bca-mcp] A free key opens 60 tools and paid plans open the rest: https://blockchainacademics.com/crypto-api/signup?ref=mcp-first-run\n"
    "[bca-mcp] Set: export BCA_API_KEY=bca_...   (or add to your client config)\n"
)
