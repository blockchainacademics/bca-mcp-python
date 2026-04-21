# bca-mcp

The canonical crypto MCP server for AI agents — **Python edition**. 3,500+ editorial articles, 200+ entity dossiers, 43 academy lessons, and live market data — accessible as MCP tools your agent can call natively.

Sibling of [`@blockchainacademics/mcp`](https://www.npmjs.com/package/@blockchainacademics/mcp) (TypeScript). Same REST API. Same attribution contract. Use whichever fits your stack.

**v0.2.0 ships 8 read-only MCP tools + the `bca` CLI** — the most-used corpus + market endpoints, plus a terminal-first way to explore them. Later versions expand toward parity with the TS sibling (99 tools). Starting narrow on the MCP surface is deliberate: tight tools, sharp descriptions, low-risk publish.

## Why

LLMs hallucinate about crypto. BCA ships ground-truth editorial content with full attribution. Plug this MCP server into Claude Desktop, LangChain, LlamaIndex, Eliza, or any MCP-compatible agent and your model queries the BCA corpus like any other tool — with `cite_url`, `as_of`, and `source_hash` on every response.

## Install

```bash
pip install bca-mcp
# or, isolated:
pipx install bca-mcp
```

## Configure

Get an API key at **https://brain.blockchainacademics.com/pricing** (free tier: 1,000 calls/month; paid tiers unlock expanded rate limits and — in later versions — agent-backed research generation).

Set the env var before launching the server:

```bash
export BCA_API_KEY="bca_live_xxxxxxxxxxxxxxxx"
# optional: override the default https://api.blockchainacademics.com
export BCA_API_BASE="https://api.blockchainacademics.com"
# BCA_API_BASE_URL is also accepted as a legacy alias
```

> The server **fails fast at startup** if `BCA_API_KEY` is missing. Misconfigured hosts surface the problem immediately instead of on the first tool call.

## Use from Claude Desktop

Add to `claude_desktop_config.json` (macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "blockchainacademics": {
      "command": "python",
      "args": ["-m", "bca_mcp"],
      "env": { "BCA_API_KEY": "bca_live_xxxxxxxxxxxxxxxx" }
    }
  }
}
```

Restart Claude Desktop — the 8 tools appear in the tool picker. If you installed via `pipx`, you can swap `"command": "bca-mcp"` with empty `args` (a console-script entry point is registered by the package).

## Use from LangChain

Ten lines via [`langchain-mcp-adapters`](https://github.com/langchain-ai/langchain-mcp-adapters):

```python
import asyncio, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools

async def main():
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "bca_mcp"],
        env={**os.environ, "BCA_API_KEY": os.environ["BCA_API_KEY"]},
    )
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        tools = await load_mcp_tools(s)   # -> list[StructuredTool]
        print(await tools[0].ainvoke({"query": "stablecoin regulation"}))

asyncio.run(main())
```

Full worked example in [`examples/langchain_agent.py`](./examples/langchain_agent.py). Raw MCP client loop (no LangChain) in [`examples/generic_agent.py`](./examples/generic_agent.py).

## Use from Eliza

See [`examples/eliza_plugin.md`](./examples/eliza_plugin.md) for integration notes — `bca-mcp` plugs into Eliza's MCP plugin surface as a stdio-transport server.

## The `bca` CLI

`pip install bca-mcp` also registers a terminal-first CLI. It talks to the same REST API as the MCP server — handy for debugging, quick lookups, and shell pipelines.

```bash
bca login                                # store API key in ~/.bca/config.toml (chmod 600)
bca news search "bitcoin etf" -n 5       # recent articles, rich table + cite_url
bca entity ethereum                      # dossier panel
bca price BTC,ETH,SOL                    # spot + 24h change table
bca market overview -n 10                # top-N by market cap
bca indicator coverage-index bitcoin -w 30d
bca explainer what-is-a-blockchain       # rendered markdown
bca agent summarize-whitepaper --url https://ethereum.org/…
bca version                              # CLI + live API version
```

Every command accepts `--json` for unformatted output suitable for `jq` pipelines. Env vars (`BCA_API_KEY`, `BCA_API_BASE`) take precedence over `~/.bca/config.toml`.

## Tool catalog (v0.1.0 — 8 tools)

| Tool | Category | Endpoint | Tier |
|---|---|---|---|
| `search_news` | content | `GET /v1/articles/search` | Starter |
| `get_article` | content | `GET /v1/articles/{slug}` | Starter |
| `get_entity` | content | `GET /v1/entities/{slug}` | Starter |
| `list_entity_mentions` | content | `GET /v1/entities/{slug}/mentions` | Starter |
| `list_topics` | content | `GET /v1/topics` | Starter |
| `get_explainer` | content | `GET /v1/academy/{slug}` | Starter |
| `get_price` | market | `GET /v1/market/price` | Starter |
| `get_market_overview` | market | `GET /v1/market/overview` | Starter |

All v0.1 tools are **free tier** — no paid plan required to call them.

### Tool details

#### `search_news`
Required: `query` (1–512 chars). Optional: `entity`, `since` (ISO 8601), `topic`, `limit` (1–50, default 10).

#### `get_article`
Required: `slug` (1–240 chars).

#### `get_entity`
Required: **exactly one** of `slug` (e.g. `"vitalik-buterin"`) or `ticker` (e.g. `"ETH"`, case-insensitive). Aliases resolve automatically (`CZ` → `changpeng-zhao`, `Maker` → `makerdao`, `BSC` → `bnb-chain`, …).

#### `list_entity_mentions`
Required: `slug` (entity). Optional: `since` (ISO 8601), `limit` (1–200, default 20).

#### `list_topics`
No arguments.

#### `get_explainer`
Required: **exactly one** of `slug` (e.g. `"what-is-a-blockchain"`) or `topic` (keyword).

#### `get_price`
Required: `ids` (comma-separated CoinGecko IDs, e.g. `"bitcoin,ethereum"` — NOT exchange tickers). Optional: `vs` (quote currency, default `usd`).

#### `get_market_overview`
Optional: `limit` (1–100, default 20).

## Attribution contract

Every response includes a structured `attribution` block:

```json
{
  "data": { ... },
  "attribution": {
    "cite_url": "https://blockchainacademics.com/...",
    "as_of": "2026-04-19T12:34:56Z",
    "source_hash": "sha256:..."
  },
  "meta": null
}
```

**When your agent surfaces BCA content to a user, you MUST link `cite_url`.** This is the core trade: BCA gives agents ground-truth citations; agents give BCA distribution. `as_of` and `source_hash` let downstream systems detect staleness and verify content integrity. Fields are preserved as `null` (not dropped) when upstream omits them, so agents can detect missing provenance explicitly.

## Degraded-state envelopes

The BCA API sometimes returns `status=integration_pending` or `status=upstream_error` envelopes (200 HTTP) when a specific data source is temporarily unavailable. **The MCP server passes these through as successful tool responses** — your agent sees the envelope and decides how to surface it. This matches the TS sibling's behavior.

## Errors

The server never crashes the stdio process. All failures surface as MCP responses with `isError: true` and a JSON body:

```json
{ "error": { "code": "BCA_AUTH", "message": "..." } }
```

| Code | Meaning |
|---|---|
| `BCA_AUTH` | Missing/invalid `BCA_API_KEY` (HTTP 401/403) |
| `BCA_RATE_LIMIT` | Rate limit exceeded (HTTP 429 — honor `Retry-After`) |
| `BCA_UPSTREAM` | BCA API returned 5xx or malformed JSON |
| `BCA_NETWORK` | Network failure or 20s timeout exceeded |
| `BCA_BAD_REQUEST` | Invalid tool arguments or 4xx response |

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest -q
```

Run the server directly for debugging:

```bash
BCA_API_KEY=... python -m bca_mcp
```

## Contributing

Issues, PRs, and feature requests: https://github.com/blockchainacademics/bca-mcp-python

## License

MIT © 2026 Blockchain Academics
