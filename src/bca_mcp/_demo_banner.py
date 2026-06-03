# Stderr banner emitted once at server startup when the client falls back
# to the demo key (no BCA_API_KEY env var). Stdout is owned by the MCP stdio
# transport, so this MUST stay on stderr.
#
# Three lines, ASCII-only, each terminated with \n. The TS sibling at
# src/demo_banner.ts must match byte-for-byte.

DEMO_BANNER = (
    "[bca-mcp] Running in DEMO mode. Limited to ~10 tools, shared rate cap.\n"
    "[bca-mcp] Get a free key for full access: https://brain.blockchainacademics.com/signup?ref=mcp-first-run\n"
    "[bca-mcp] Set: export BCA_API_KEY=bca_...   (or add to your client config)\n"
)
