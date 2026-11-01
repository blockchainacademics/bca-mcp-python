# bca-mcp

The canonical crypto MCP server for AI agents, **Python edition**: 3,500+ editorial articles, 200+ entity dossiers, 38 academy lessons in 8 courses, and live market data, as MCP tools your agent can call natively.

Sibling of [`@blockchainacademics/mcp`](https://www.npmjs.com/package/@blockchainacademics/mcp) (TypeScript). Same REST API. Same attribution contract. Use whichever fits your stack.

**v0.6 ships the full 105-tool catalog plus the `bca` CLI.** The tool names match the TypeScript package one for one, and the CLI gives you a terminal-first way to explore the same API.

## Why

LLMs hallucinate about crypto. BCA ships ground-truth editorial content with full attribution. Plug this MCP server into Claude Desktop, LangChain, LlamaIndex, Eliza, or any MCP-compatible agent and your model queries the BCA corpus like any other tool, with `cite_url`, `as_of`, and `source_hash` on every response.

## Install

```bash
pip install bca-mcp
# or, isolated:
pipx install bca-mcp
# or, ephemeral:
uvx bca-mcp
```

## Zero-config first run (no API key needed)

`uvx bca-mcp` works out of the box. The package ships with a public demo key, and 16 tools work without a key of your own:

`get_price`, `get_trending`, `get_fear_greed`, `get_market_overview`, `search_news`, `get_sentiment`, `get_entity`, `get_explainer`, `get_recent_stories`, `get_topic`, `search_grants`, `get_grant`, `list_jobs`, `get_job`, `search_academy`, `get_as_of_snapshot`.

Every other tool answers without a key with a clean upgrade message (`BCA_TIER_LOCKED`) that links the free signup. The demo key is shared: 100 calls a day across all demo users, 20 a day per IP address, 1 per second. On startup the server prints a one-time banner on stderr while demo mode is active.

## Configure (unlock all 105 tools)

Get a free API key at **https://blockchainacademics.com/crypto-api/signup** (free tier: 2,000 calls/month per user; paid tiers unlock expanded rate limits and agent-backed research generation).

Set the env var before launching the server:

```bash
export BCA_API_KEY="bca_live_xxxxxxxxxxxxxxxx"
# optional: override the default https://api.blockchainacademics.com
export BCA_API_BASE="https://api.blockchainacademics.com"
# BCA_API_BASE_URL is also accepted as a legacy alias
```

> When `BCA_API_KEY` is set, the demo banner is suppressed and all 105 tools are open to your key's tier (some need a paid tier). When it's unset, every response carries `meta.tier: "demo"` and `meta.upgrade_url` so your agent can detect the demo path.

## Use from Claude Desktop

Add to `claude_desktop_config.json` (macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`).

Zero-config demo path (no API key needed):

```json
{
  "mcpServers": {
    "blockchainacademics": {
      "command": "python",
      "args": ["-m", "bca_mcp"]
    }
  }
}
```

Full 105-tool surface (add your key from blockchainacademics.com/crypto-api/signup):

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

Restart Claude Desktop and the tools appear in the tool picker. If you installed via `pipx`, you can swap `"command": "bca-mcp"` with empty `args` (a console-script entry point is registered by the package).

Every tool carries MCP annotations: a readable `title`, `readOnlyHint: true` on the read tools, and `readOnlyHint: false` on the eight tools that create a record or start a job (`submit_listing`, `book_kol_campaign`, `request_custom_research`, `monitor_keyword`, `generate_due_diligence`, `generate_tokenomics_model`, `summarize_whitepaper`, `translate_contract`), so clients can ask before running those.

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

See [`examples/eliza_plugin.md`](./examples/eliza_plugin.md) for integration notes: `bca-mcp` plugs into Eliza's MCP plugin surface as a stdio-transport server.

## The `bca` CLI

`pip install bca-mcp` also registers a terminal-first CLI. It talks to the same REST API as the MCP server, which makes it handy for debugging, quick lookups, and shell pipelines.

```bash
bca login                                # store API key in ~/.bca/config.toml (chmod 600)
bca news search "bitcoin etf" -n 5       # recent articles, rich table + cite_url
bca entity ethereum                      # dossier panel
bca price BTC,ETH,SOL                    # spot + 24h change table
bca market overview -n 10                # top-N by market cap
bca indicator coverage-index bitcoin -w 30d
bca explainer defi-fundamentals          # rendered markdown
bca agent summarize-whitepaper --url https://ethereum.org/…
bca version                              # CLI + live API version
```

Every command accepts `--json` for unformatted output suitable for `jq` pipelines. Env vars (`BCA_API_KEY`, `BCA_API_BASE`) take precedence over `~/.bca/config.toml`.

## Tool catalog (a selection; all 105 at https://blockchainacademics.com/crypto-api/tools)

| Tool | Category | Endpoint | Tier | Without a key |
|---|---|---|---|---|
| `search_news` | content | `GET /v1/articles/search` | Free | yes |
| `get_article` | content | `GET /v1/articles/{slug}` | Free | no |
| `get_entity` | content | `GET /v1/entities/{slug}` | Free | yes |
| `list_entity_mentions` | content | `GET /v1/entities/{slug}/mentions` | Free | no |
| `list_topics` | content | `GET /v1/topics` | Free | no |
| `get_explainer` | content | `GET /v1/academy/{slug}` | Free | yes |
| `get_price` | market | `GET /v1/market/price` | Free | yes |
| `get_market_overview` | market | `GET /v1/market/overview` | Free | yes |

All eight work with a free API key. "Without a key" marks the ones open in demo mode.

### Tool details

#### `search_news`
Required: `query` (1–512 chars). Optional: `entity`, `since` (ISO 8601), `topic`, `limit` (1–50, default 10).

#### `get_article`
Required: `slug` (1–240 chars).

#### `get_entity`
Required: **exactly one** of `slug` (e.g. `"vitalik-buterin"`) or `ticker` (e.g. `"ETH"`, case-insensitive). Aliases resolve automatically (`CZ` → `changpeng-zhao`, `Maker` → `makerdao`, `BSC` → `bnb-chain`, …).

#### `list_entity_mentions`
Required: `slug` (entity). Optional: `since` (ISO 8601), `limit` (1–200, default 50).

#### `list_topics`
No arguments.

#### `get_explainer`
Required: **exactly one** of `slug` (an academy course slug, e.g. `"defi-fundamentals"`) or `topic` (keyword, e.g. `"defi"`).

#### `get_price`
Required: `ids` (comma-separated CoinGecko IDs, e.g. `"bitcoin,ethereum"`, not exchange tickers). Optional: `vs` (quote currency, default `usd`).

#### `get_market_overview`
Optional: `limit` (1–100, default 20).

## Attribution contract

Every response is the same envelope, with a structured `attribution` block:

```json
{
  "data": { ... },
  "attribution": {
    "citations": [
      {
        "cite_url": "https://blockchainacademics.com/...",
        "as_of": "2026-04-19T12:34:56Z",
        "source_hash": "sha256:..."
      }
    ]
  },
  "meta": {
    "status": "complete",
    "request_id": "req_...",
    "pageInfo": { "hasNextPage": false, "hasPreviousPage": false, "startCursor": null, "endCursor": null }
  }
}
```

**When your agent surfaces BCA content to a user, you MUST link the citation's `cite_url`.** This is the core trade: BCA gives agents ground-truth citations; agents give BCA distribution. `as_of` and `source_hash` let downstream systems detect staleness and verify content integrity. Fields are preserved as `null` (not dropped) when upstream omits them, so agents can detect missing provenance explicitly.

The MCP server returns `data` inside an `<untrusted_content source="bca-api">` fence so the host model reads upstream text as data, not instructions. `attribution` and `meta` stay structured.

## Degraded-state envelopes

When a data source is empty, stale or temporarily unavailable, the API still answers HTTP 200 and says so in `meta.status`: `unseeded`, `partial` or `stale` instead of `complete`. **The MCP server passes these through as successful tool responses**, so your agent sees the status and decides how to surface it. The legacy `integration_pending` and `upstream_error` statuses of older API deploys arrive as `unseeded` and `partial`. This matches the TS sibling's behavior.

## Errors

The server never crashes the stdio process. Every failure is an MCP tool result with `isError: true` and a JSON body:

```json
{ "error": { "code": "BCA_BAD_REQUEST", "message": "Invalid arguments for book_kol_campaign: budget_usd: Input should be greater than or equal to 500" } }
```

Invalid arguments are rejected before any request is sent, with one `field: problem` pair per issue, separated by `; `. When the API itself rejects a request (HTTP 4xx), the message adds the API's explanation (up to 500 characters), fenced as untrusted content. 5xx errors stay generic.

| Code | Meaning |
|---|---|
| `BCA_AUTH` | Invalid `BCA_API_KEY` (HTTP 401/403) |
| `BCA_TIER_LOCKED` | Tool not in your current tier's allowlist (HTTP 403). Without a key this is the answer on 89 of the 105 tools; the message includes the signup URL. |
| `BCA_RATE_LIMIT` | Rate limit exceeded (HTTP 429; honor `Retry-After`) |
| `BCA_UPSTREAM` | BCA API returned 5xx or malformed JSON |
| `BCA_NETWORK` | Network failure or 20s timeout exceeded |
| `BCA_BAD_REQUEST` | Invalid tool arguments, or a 4xx response from the API |
| `BCA_UNKNOWN` | Unexpected error inside the server (the process keeps running) |

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

## Getting help

- **Questions:** ask in [GitHub Discussions Q&A](https://github.com/blockchainacademics/bca-mcp/discussions/categories/q-a). The npm and Python packages share one Q&A, so every answer lives in one place. Search first, since someone may have asked already.
- **Bugs:** open an [issue](https://github.com/blockchainacademics/bca-mcp-python/issues).
- **Account and billing:** email [support@blockchainacademics.com](mailto:support@blockchainacademics.com).
- **Security reports:** email [security@blockchainacademics.com](mailto:security@blockchainacademics.com), never a public issue.

**Never post a full API key.** If we need to know which key, share only the key prefix, the part before the dots on your dashboard (for example `bca_1a2b3c4d`). Our team will never ask for your key or a seed phrase. Response times by plan are in [How to get help](https://github.com/blockchainacademics/bca-mcp/discussions/15).

## Contributing

Issues, PRs, and feature requests: https://github.com/blockchainacademics/bca-mcp-python

## License

MIT © 2026 Blockchain Academics
