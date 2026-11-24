// INTERIM COPY for the bca-mcp-python tests: bca-mcp-ts src/demo_banner.ts of
// release/0.6.4 with the 0.7.0 counts of design-final.md section 2 (25 tools
// without a key, 60 on a free key), made while task T2 was not built.
// Replace it with bca-mcp-ts src/demo_banner.ts of 0.7.0, copied unchanged.
//
// Stderr banner emitted once at server startup when the client falls back
// to the demo key (no BCA_API_KEY env var). Stdout is owned by the MCP stdio
// transport, so this MUST stay on stderr.
//
// Three lines, ASCII-only, each terminated with \n. The Python sibling at
// src/bca_mcp/_demo_banner.py must match byte-for-byte. The 25 tools are the
// API's demo allowlist (app/api/v1/_demo_allowlist.py), listed in README.md.
// The 60 are the free tier: every other tool names its paid tier (Starter,
// Pro or Team) in its description (test/docs.test.ts counts them).

export const DEMO_BANNER =
  "[bca-mcp] Running in DEMO mode: 25 tools work without a key, under a shared daily cap.\n" +
  "[bca-mcp] A free key opens 60 tools and paid plans open the rest: https://blockchainacademics.com/crypto-api/signup?ref=mcp-first-run\n" +
  "[bca-mcp] Set: export BCA_API_KEY=bca_...   (or add to your client config)\n";
