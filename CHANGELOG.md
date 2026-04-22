# Changelog

All notable changes to `bca-mcp` are documented here.

This project follows [Semantic Versioning](https://semver.org/) and [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.3.1] — 2026-04-22

### Security
- **H-1 — `BCA_API_BASE` SSRF + credential exfil.** The base URL is now pinned to a strict allowlist (prod `https://api.blockchainacademics.com`, staging `https://staging-api.blockchainacademics.com`, or loopback `http://localhost[:port]` / `http://127.0.0.1[:port]`). Any other value — HTTPS included — is rejected at client construction with `ValueError`. The prior HTTPS-only gate let an attacker with env control point the client at `https://attacker.controlled/` and harvest `X-API-Key` on the first outbound request.
- **H-2 — Prompt-injection fencing on tool responses.** The MCP `call_tool` handler now wraps every tool response's `data` payload in an `<untrusted_content source="bca-api">` block before serialization. Upstream news titles, article bodies, and entity text are now framed as data, not instructions, for the host LLM. `attribution` and `meta` remain structured — they're our own tool metadata, not attacker-influenced. Fence bytes are identical to the TypeScript sibling.
- **H-3 — Webhook SSRF in `monitor_keyword`.** The `webhook_url` parameter is now validated before any outbound call: HTTPS only (no `http://` / `ftp://` / `file://`), no bare IP literals, and every IP that the hostname resolves to (A + AAAA) must be public. Private / loopback / link-local / reserved / multicast / unspecified ranges are all rejected, and all returned IPs are checked (DNS-rebinding defense). Cloud metadata targets such as `169.254.169.254` are blocked.

### Changed
- `BCA_ALLOW_INSECURE_BASE` is no longer consulted — loopback bases are explicitly allowlisted, so the escape hatch is redundant.

### Tests
- 110 passing (was 94): added H-1 allowlist coverage, H-2 fence-bytes regression, and H-3 webhook SSRF battery (IPv4, IPv6, RFC1918, IMDS, dual-stack DNS rebind, end-to-end `run_monitor_keyword`).

## [0.3.0] — 2026-04-22

### Changed — BREAKING
- **Canonical response envelope adopted across all tool outputs.** The MCP server now emits the JSON:API-inspired envelope that the REST API locked on 2026-04-22, matching the TypeScript sibling. Every tool response is now shaped as:

  ```json
  {
    "data": { ... },
    "attribution": { "citations": [ {"cite_url": "...", "as_of": "...", "source_hash": "sha256:..."} ] },
    "meta": {
      "status": "complete" | "unseeded" | "partial" | "stale",
      "request_id": "req_...",
      "pageInfo": { "hasNextPage": false, "hasPreviousPage": false, "startCursor": null, "endCursor": null },
      "diagnostic": { }
    }
  }
  ```

- `attribution.citations[]` is **array-only** — the legacy singular `{cite_url, as_of, source_hash}` shorthand has been removed.
- `meta.status` enum is now `complete | unseeded | partial | stale`. The legacy `"error"` value has been removed — error conditions surface as raises (`BcaError` subclasses), never as successful-looking bodies.
- `meta.request_id` is always a string.
- Rate-limit metadata moved to HTTP response headers (previously leaked into the body on `BcaRateLimitError` paths — still the case for the raise, but the successful envelope no longer carries it).
- Server `call_tool` handler no longer re-shapes tool output — it serializes the canonical envelope the client hands back directly. The old flat→nested transform at `server.py:374-397` has been removed.
- Client (`src/bca_mcp/client.py`) now canonicalizes upstream bodies: already-canonical responses pass through untouched; legacy flat `{data, cite_url, as_of, source_hash, status}` responses are upgraded in place (with a one-time warning logged to `bca_mcp.client`) during the rollout window.

### MIGRATION

Before (v0.2.x):

```json
{
  "data": { "articles": [] },
  "status": "complete",
  "attribution": {
    "cite_url": "https://blockchainacademics.com/articles/foo",
    "as_of": "2026-04-21T00:00:00Z",
    "source_hash": null
  },
  "meta": null
}
```

After (v0.3.0):

```json
{
  "data": { "articles": [] },
  "attribution": {
    "citations": [
      {
        "cite_url": "https://blockchainacademics.com/articles/foo",
        "as_of": "2026-04-21T00:00:00Z",
        "source_hash": null
      }
    ]
  },
  "meta": {
    "status": "complete",
    "request_id": "req_7a3f2b1c9d4e8f01",
    "pageInfo": { "hasNextPage": false, "hasPreviousPage": false, "startCursor": null, "endCursor": null }
  }
}
```

Downstream MCP clients / agents must migrate from `response.attribution.cite_url` → `response.attribution.citations[0].cite_url`, and from `response.status` → `response.meta.status`. A temporary compatibility shim in the HTTP client layer auto-upgrades legacy upstream bodies so tools keep working during the rollout; the shim will be removed in a future minor.

### Added
- `bca_mcp.types.Citation`, `PageInfo`, `EnvelopeMeta`, `Attribution` TypedDicts codifying the canonical shape.
- `bca_mcp.types.default_page_info()` helper for non-paginated payloads.
- `bca_mcp.client.reset_legacy_envelope_warning()` — testing aid for the flat→canonical shim.
- Canonical-envelope contract test in `tests/test_envelope_shape.py` asserting the full shape on a mocked tool call.

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
