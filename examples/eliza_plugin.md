# Eliza integration

[Eliza](https://github.com/elizaOS/eliza) is a TypeScript agent framework with a plugin system that includes native Model Context Protocol (MCP) client support. `bca-mcp` plugs into Eliza as a **stdio-transport MCP server** — Eliza spawns the Python process and speaks MCP over stdin/stdout.

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

Sign up at **https://brain.blockchainacademics.com/pricing**. The free tier (1,000 calls/month) is enough to test and ship most agents.

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

Once wired, the 8 tools appear in the agent's tool pool exactly as they appear in Claude Desktop:

- `search_news`
- `get_article`
- `get_entity`
- `list_entity_mentions`
- `list_topics`
- `get_explainer`
- `get_price`
- `get_market_overview`

Eliza auto-routes tool calls based on the agent's planning prompt — no additional glue needed beyond the plugin registration above.

## Attribution contract

Eliza agents that surface BCA content to users **must** preserve the `cite_url` from each response's `attribution` block. The BCA license covers free redistribution of summary + link; full-body republication requires the Enterprise tier. Pass `cite_url` to your agent's response template so every BCA-sourced claim ships with its source link.

## Troubleshooting

**"BCA_API_KEY is not set" at startup** — The server fails fast on missing key. Make sure the key is in the `env` block of the MCP server config (Eliza does NOT inherit the character's general env, only what you declare per-server).

**Timeouts** — Default is 20s. The BCA API is typically <500ms for corpus reads, longer for market-data aggregation. If you see `BCA_NETWORK` timeouts frequently, check your host's outbound network policy — Eliza agents sometimes run in restrictive network namespaces.

**Stale data** — Every response ships `as_of`. If your agent's outputs look old, compare `as_of` to wall-clock; most corpus endpoints refresh every ~20min. Market endpoints refresh continuously.

## Future work

The TS sibling (`@blockchainacademics/mcp` v0.2.2) exposes 99 tools including on-chain analytics, sentiment indicators, and agent-backed research generation. The Python build will expand in v0.2 — track https://github.com/blockchainacademics/bca-mcp-python.
