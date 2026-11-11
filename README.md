# bca-mcp

<!-- mcp-name: io.github.blockchainacademics/mcp -->

Python edition of the Blockchain Academics crypto MCP server for AI agents: cited news, prices, onchain data, sentiment and indicators. 3,800+ editorial articles, about 150 entity dossiers, 38 academy lessons in 8 courses and live market data, as MCP tools your agent can call.

Sibling of [`@blockchainacademics/mcp`](https://www.npmjs.com/package/@blockchainacademics/mcp) (TypeScript). Same REST API. Same attribution contract. Use whichever fits your stack.

**v0.6 ships the full 105-tool catalog plus the `bca` CLI.** The tool names match the TypeScript package one for one, and the CLI gives you a terminal-first way to explore the same API.

## Why

Every answer says where it came from and how complete it is. `attribution.citations[]` lists the sources, primary source first (`cite_url`, `as_of`, `source_hash`), and `meta.status` says whether the answer is complete, partial, stale or unseeded. An agent can cite each fact and tell a full answer from a thin one. The server works in Claude Desktop, LangChain, LlamaIndex, Eliza and any other MCP client.

## Not financial advice

The tools return data, analysis and their sources. Nothing they return is financial, investment or tax advice, or a recommendation to buy or sell anything.

## Install

```bash
pip install bca-mcp
# or, isolated:
pipx install bca-mcp
# or, ephemeral:
uvx bca-mcp
```

## Zero-config first run (no API key needed)

`uvx bca-mcp` works out of the box. The package ships with a public demo key, and 17 tools work without a key of your own:

`get_price`, `get_trending`, `get_fear_greed`, `get_market_overview`, `search_news`, `get_article`, `get_sentiment`, `get_entity` (slug form), `get_explainer`, `get_recent_stories`, `get_topic`, `search_grants`, `get_grant`, `list_jobs`, `get_job`, `search_academy`, `get_as_of_snapshot`.

Every other tool answers without a key with a clean upgrade message (`BCA_TIER_LOCKED`) that links the free signup. The demo key is shared: 100 calls a day across all demo users, 20 a day per IP address, 1 per second. On startup the server prints a one-time banner on stderr while demo mode is active.

## Configure an API key

Get a free API key at **https://blockchainacademics.com/crypto-api/signup** (2,000 calls/month per user). A free key opens 52 tools. Paid plans open the rest, such as agent-backed research generation, crypto Twitter intelligence and the proprietary indicators, and raise the rate limits; each tool's description names its tier when it is not free.

Set the env var before launching the server:

```bash
export BCA_API_KEY="bca_live_xxxxxxxxxxxxxxxx"
# optional: override the default https://api.blockchainacademics.com
export BCA_API_BASE="https://api.blockchainacademics.com"
# BCA_API_BASE_URL is also accepted as a legacy alias
```

> When `BCA_API_KEY` is set, the demo banner is suppressed and your key's plan decides which tools answer: 52 on a free key, the rest on paid plans. When it's unset, every response carries `meta.tier: "demo"` and `meta.upgrade_url` so your agent can detect the demo path.

## Privacy

- Each tool call sends its arguments (for example a search phrase, a coin name, or a wallet or contract address you ask about) and your key, if you set one, over HTTPS to api.blockchainacademics.com, our own API, or to the staging or local base you set in `BCA_API_BASE`. The server sends nothing to any other host; `monitor_keyword` only looks up the webhook's host name in DNS to refuse private addresses.
- The MCP server stores nothing on your computer. The `bca` CLI keeps your key in `~/.bca/config.toml` (readable only by you) after `bca login`. The API counts calls per key per day and does not log request bodies or query parameters that could contain personal data.
- Full policy, retention and your rights: [blockchainacademics.com/privacy](https://blockchainacademics.com/privacy), section 12 (Crypto API and MCP Server). Privacy requests: [privacy@blockchainacademics.com](mailto:privacy@blockchainacademics.com).

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

With your own key (a free key from blockchainacademics.com/crypto-api/signup opens 52 tools; paid plans open the rest):

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

LangChain ships MCP support as `langchain.mcp` (beta, `pip install "langchain[mcp]>=1.4.0"`; it replaces the archived `langchain-mcp-adapters`). `MCPAdapter` starts the server and turns its tools into LangChain tools:

```python
import asyncio, os
from langchain.agents import create_agent
from langchain.mcp import MCPAdapter

config = {
    "mcpServers": {
        "bca": {
            "command": "uvx",
            "args": ["bca-mcp"],
            "env": {"BCA_API_KEY": os.environ.get("BCA_API_KEY", "")},
        }
    }
}

async def main() -> None:
    async with MCPAdapter(config) as adapter:
        tools = await adapter.list_tools()
        agent = create_agent("<your chat model>", tools)
        result = await agent.ainvoke(
            {"messages": [("user", "What happened with Ethereum this week? Cite sources.")]}
        )
        print(result["messages"][-1].content)

asyncio.run(main())
```

An empty `BCA_API_KEY` runs the 17 tools that need no key. Worked example in [`examples/langchain_agent.py`](./examples/langchain_agent.py). Raw MCP client loop (no LangChain) in [`examples/generic_agent.py`](./examples/generic_agent.py).

## Use from Eliza

See [`examples/eliza_plugin.md`](./examples/eliza_plugin.md) for integration notes: `bca-mcp` plugs into Eliza's MCP plugin surface as a stdio-transport server.

## The `bca` CLI

`pip install bca-mcp` also registers a terminal-first CLI. It talks to the same REST API as the MCP server, which makes it handy for debugging, quick lookups, and shell pipelines.

```bash
bca login                                # store API key in ~/.bca/config.toml (chmod 600)
bca news search "bitcoin etf" -n 5       # recent articles, rich table + links
bca entity ethereum                      # dossier panel
bca price bitcoin,ethereum,solana        # spot + 24h change table (CoinGecko ids)
bca market overview -n 10                # top-N by market cap
bca indicator coverage-index bitcoin -w 30d
bca explainer defi-fundamentals          # a course or a lesson, rendered markdown
bca agent summarize-whitepaper --url https://bitcoin.org/bitcoin.pdf
bca version                              # CLI + live API version
```

Every command accepts `--json` for unformatted output suitable for `jq` pipelines. Env vars (`BCA_API_KEY`, `BCA_API_BASE`) take precedence over `~/.bca/config.toml`.

## Tool catalog (a selection; all 105 at https://blockchainacademics.com/crypto-api/tools)

| Tool | Category | Endpoint | Tier | Without a key |
|---|---|---|---|---|
| `search_news` | content | `GET /v1/articles/search` | Free | yes |
| `get_article` | content | `GET /v1/articles/{slug}` | Free | yes |
| `get_entity` | content | `GET /v1/entities/{slug}` | Free | yes |
| `list_entity_mentions` | content | `GET /v1/entities/{slug}/mentions` | Free | no |
| `list_topics` | content | `GET /v1/topics` | Free | no |
| `get_explainer` | content | `GET /v1/academy/{slug}` | Free | yes |
| `get_price` | market | `GET /v1/market/price` | Free | yes |
| `get_market_overview` | market | `GET /v1/market/overview` | Free | yes |

All eight work with a free API key. "Without a key" marks the ones open in demo mode.

### Tool details

#### `search_news`
Required: `query` (1–512 chars). Optional: `entity`, `ticker`, `since` (ISO 8601), `topic`, `limit` (1–50, default 10), `offset` (paging).

#### `get_article`
Required: `slug` (1–240 chars).

#### `get_entity`
Required: **exactly one** of `slug` (e.g. `"vitalik-buterin"`) or `ticker` (e.g. `"ETH"`, case-insensitive). Aliases in slug form resolve to the canonical entity (`cz` → `changpeng-zhao`, `maker` → `makerdao`, `bsc` → `bnb-chain`), and the answer names the alias in `resolved_from_alias`. The ticker form returns every entity that matches the ticker and needs an API key; the slug form works without one.

#### `list_entity_mentions`
Required: `slug` (entity). Optional: `since` (ISO 8601), `limit` (1–100, default 50), `offset` (paging).

#### `list_topics`
No arguments.

#### `get_explainer`
Required: **exactly one** of `slug` (a course slug such as `"defi-fundamentals"` returns the course and its lessons; a lesson slug such as `"decentralized-exchanges"` returns the lesson text) or `topic` (keyword, e.g. `"defi"`).

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
        "cite_url": "https://www.coingecko.com/en/coins/bitcoin",
        "as_of": "2026-11-01T12:34:56Z",
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

`attribution.citations[0]` is the primary source: the upstream page the data came from when there is one (an article's publisher, CoinGecko, DefiLlama, Etherscan), otherwise the BCA page for the record. A BCA link is included only where blockchainacademics.com has a page for the data; when there is neither, the one citation points at the tool's entry in the API reference.

**When your agent surfaces BCA content to a user, link `citations[0].cite_url`.** `as_of` and `source_hash` let downstream systems spot stale or changed data. Fields are preserved as `null` (not dropped) when upstream omits them, so agents can detect missing provenance explicitly.

The MCP server returns `data` inside an `<untrusted_content source="bca-api">` fence so the host model reads upstream text as data, not instructions. `attribution` and `meta` stay structured.

## Reading `meta.status`

The API says how complete each answer is. **The MCP server passes every status through as a successful tool response**, so your agent sees it and decides how to surface it:

| `meta.status` | Meaning | `meta.diagnostic` |
|---|---|---|
| `complete` | The answer the tool promises. | absent |
| `partial` | Data is returned, but some of it is missing or defaulted. | `missing` names what is absent (when an upstream source failed: `vendor` and `upstream_status` instead) |
| `stale` | Data is returned, but it is older than the tool promises. | `as_of` (when the data was produced) and `age_seconds` |
| `unseeded` | No real data yet: an empty source, placeholder rows, or a feed that is not connected. | `reason` and `eta` |

`diagnostic.reason` explains every non-complete answer. Lists that page by offset (`search_news`, `search_grants`, `list_entities`, `list_entity_mentions`, `search_academy`) set `meta.pageInfo.hasNextPage` when more results exist. Several tools usually answer `unseeded` or `partial` today, and their descriptions say so (for example `get_kol_influence`, `check_memecoin_risk`, `get_exchange_flows`, the memo and thesis tools, and the X-based tools while the X reader is paused). The legacy `integration_pending` and `upstream_error` statuses of older API deploys arrive as `unseeded` and `partial`. This matches the TS sibling's behavior.

## Errors

The server never crashes the stdio process. Every failed tool call is an MCP tool result with `isError: true` and a JSON body (a malformed JSON-RPC request, such as arguments that are not an object, gets the MCP SDK's JSON-RPC error instead):

```json
{ "error": { "code": "BCA_BAD_REQUEST", "message": "Invalid arguments for book_kol_campaign: budget_usd: Input should be greater than or equal to 500" } }
```

Invalid arguments are rejected before any request is sent, with one `field: problem` pair per issue, separated by `; `. When the API itself rejects a request (HTTP 4xx), the message adds the API's explanation (up to 500 characters), fenced as untrusted content. 5xx errors stay generic.

| Code | Meaning |
|---|---|
| `BCA_AUTH` | Invalid `BCA_API_KEY` (HTTP 401/403), or a key that cannot be sent as a header value (a line break inside it); the key itself is never repeated in the message |
| `BCA_TIER_LOCKED` | Tool not in your current tier's allowlist (HTTP 403 without a key, HTTP 402 with a key on a lower plan). Without a key this is the answer on 88 of the 105 tools; the message includes the signup URL, or the pricing URL for a key on a lower plan. |
| `BCA_RATE_LIMIT` | Rate limit exceeded (HTTP 429; honor `Retry-After`) |
| `BCA_UPSTREAM` | BCA API returned 5xx or malformed JSON |
| `BCA_NETWORK` | Network failure or 20s timeout exceeded |
| `BCA_BAD_REQUEST` | Invalid tool arguments, or a 4xx response from the API (other than 401, 402, 403 and 429) |
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
