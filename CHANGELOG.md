# Changelog

All notable changes to `bca-mcp` are documented here.

This project follows [Semantic Versioning](https://semver.org/) and [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] — 2026-04-21

### Added
- **`bca` CLI** bundled with the package — a Typer + Rich terminal UI over the same REST API the MCP server wraps. Registered as a console script (`pip install bca-mcp` gives you both `bca-mcp` and `bca`).
  - `bca login` — stores API key in `~/.bca/config.toml` (chmod 600).
  - `bca config show` — inspect config file location + masked key.
  - `bca news search <query>` — rich table of articles with `cite_url`.
  - `bca entity <slug>` — entity dossier panel.
  - `bca price <tickers>` — spot + 24h change table.
  - `bca market overview` — top-N by market cap.
  - `bca indicator <name> <entity> --window {7d,30d,90d}` — proprietary indicator reads.
  - `bca explainer <slug>` — academy lesson rendered as markdown.
  - `bca agent <skill>` — kicks off async agent-backed jobs and polls to completion.
  - `bca version` — shows CLI + live API version.
  - Every command accepts `--json` for pipe-friendly output.
- `BCA_API_BASE` is now the primary base-URL env var; `BCA_API_BASE_URL` is accepted as a legacy alias (matches the TypeScript sibling + `server.json` contract).

### Changed
- User-Agent bumped to `bca-mcp/0.2.0`.

## [0.1.0] — 2026-04-21

### Added
- Initial Python release with stdio transport — v0.1 scaffold, **8 read-only tools** (minimum viable parity with `@blockchainacademics/mcp` TS v0.1).
- **Content & corpus (6):** `search_news`, `get_article`, `get_entity`, `list_entity_mentions`, `list_topics`, `get_explainer`.
- **Market (2):** `get_price`, `get_market_overview`.
- Typed async HTTPS client (`httpx.AsyncClient`) with `BCA_API_KEY` header injection, 20s default timeout, and both `request()` (GET) and `post()` methods.
- Fail-fast at server construction if `BCA_API_KEY` is not set — misconfigured MCP hosts surface the error at startup, not on first tool call.
- Envelope passthrough for `status=integration_pending` / `status=upstream_error` bodies (pass as successful tool responses; MCP client decides how to surface).
- Structured error taxonomy (`BCA_AUTH`, `BCA_RATE_LIMIT`, `BCA_UPSTREAM`, `BCA_NETWORK`, `BCA_BAD_REQUEST`) mirroring the TypeScript sibling.
- Attribution surfacing (`cite_url`, `as_of`, `source_hash`) on every tool response; `null` preserved when upstream omits.
- Smoke test suite using `pytest` + `pytest-httpx` — schema + transport validation with no live API calls.
- LangChain integration via `langchain-mcp-adapters` in `examples/langchain_agent.py`.
- Eliza integration notes in `examples/eliza_plugin.md`.
- Sibling of the TypeScript `@blockchainacademics/mcp` package. v0.2 will expand the tool surface toward the 99-tool TS parity target.
