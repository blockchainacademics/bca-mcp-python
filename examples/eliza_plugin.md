# Eliza integration

[Eliza](https://github.com/elizaOS/eliza) is a TypeScript agent framework with a plugin system that includes native Model Context Protocol (MCP) client support. `bca-mcp` plugs into Eliza as a **stdio-transport MCP server**: Eliza spawns the Python process and speaks MCP over stdin/stdout.

This is the Python sibling of [`@blockchainacademics/mcp`](https://www.npmjs.com/package/@blockchainacademics/mcp); Eliza users on Node-only stacks can use the TS package directly. Use this Python build when your Eliza deployment already has Python available (e.g. shared infra with LangChain / LlamaIndex agents) or when you want a single `pipx install` footprint.

## Install

On the host running Eliza:

```bash
pipx install bca-mcp
```

`pipx` puts the `bca-mcp` entry-point script on PATH and isolates the venv so Eliza's Node process can launch it without a Python sibling in the same venv.

Alternatively, without `pipx`:

```bash
pip install bca-mcp
# then the server is runnable as:  python -m bca_mcp
```

## Get an API key

Sign up at **https://blockchainacademics.com/crypto-api/pricing**. The free tier (2,000 calls/month) is enough to test and ship most agents. Without a key the server still starts in demo mode, with 17 tools open.

## Wire into Eliza's character config

Eliza exposes MCP servers through [`@elizaos/plugin-mcp`](https://github.com/elizaos-plugins/plugin-mcp). Add `bca-mcp` to your character's plugin config:

```json
{
  "name": "YourCryptoAgent",
  "plugins": ["@elizaos/plugin-mcp"],
  "settings": {
    "mcp": {
      "servers": {
        "blockchainacademics": {
          "type": "stdio",
          "command": "bca-mcp",
          "args": [],
          "env": {
            "BCA_API_KEY": "bca_live_xxxxxxxxxxxxxxxx"
          }
        }
      }
    }
  }
}
```

If `bca-mcp` isn't on Eliza's PATH (pipx sometimes installs to `~/.local/bin` which isn't picked up by systemd-launched processes), point at the Python module directly:

```json
{
  "command": "python",
  "args": ["-m", "bca_mcp"],
  "env": { "BCA_API_KEY": "..." }
}
```

## What Eliza sees

Once wired, all 105 tools appear in the agent's tool pool exactly as they appear in Claude Desktop, among them:

- `search_news`
- `get_article`
- `get_entity`
- `list_entity_mentions`
- `list_topics`
- `get_explainer`
- `get_price`
- `get_market_overview`

Eliza auto-routes tool calls based on the agent's planning prompt; no additional glue is needed beyond the plugin registration above.

## Attribution contract

Eliza agents that surface BCA content to users **must** preserve the source link from each response's `attribution` block: `attribution.citations[0].cite_url`, the primary source. The BCA license covers free redistribution of summary + link; full-body republication requires the Enterprise tier. Pass that `cite_url` to your agent's response template so every BCA-sourced claim ships with its source link. Each response also carries `meta.status` (`complete`, `partial`, `stale` or `unseeded`, with the reason in `meta.diagnostic`), so the agent can say when an answer is incomplete.

## Troubleshooting

**Only 17 tools answer; the rest return `BCA_TIER_LOCKED`.** The server did not get your key, so it runs in demo mode. Make sure the key is in the `env` block of the MCP server config (Eliza does NOT inherit the character's general env, only what you declare per-server).

**Timeouts.** Default is 20s. The BCA API is typically <500ms for corpus reads, longer for market-data aggregation. If you see `BCA_NETWORK` timeouts frequently, check your host's outbound network policy, since Eliza agents sometimes run in restrictive network namespaces.

**Stale data.** Every citation carries `as_of`, and an answer older than its tool promises comes back with `meta.status: "stale"` (`meta.diagnostic.as_of` and `age_seconds` say how old). The article corpus refreshes about every 30 minutes; market endpoints refresh continuously.

## TypeScript sibling

The TS sibling (`@blockchainacademics/mcp`) exposes the same 105 tools, including on-chain analytics, sentiment indicators, and agent-backed research generation, for Node-only stacks. Track the Python build at https://github.com/blockchainacademics/bca-mcp-python.
