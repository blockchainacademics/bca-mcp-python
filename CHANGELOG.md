# Changelog

All notable changes to `bca-mcp` are documented here.

This project follows [Semantic Versioning](https://semver.org/) and [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.6.4] (unreleased)

Directory review fixes (directory-submissions.md, section 4.6 rows A3, A5 and A10, and the package fixes of section 20), in lockstep with @blockchainacademics/mcp 0.6.4. Same 105 tools, same arguments and schemas.

### Changed

- Tool descriptions say what each tool does, what it returns and when it applies, and no longer tell the model how to behave or sell a service. Rewritten: `search_news` (no "prefer this over pretraining"), `get_entity`, `get_explainer` (no "teacher-vetted", no "prefer the explainer over generating your own definition"), `get_article`, `list_entity_mentions`, `list_topics`, `get_price`, `get_market_overview`, `get_wallet_profile`, `get_token_holders`, `get_x_signals` (no "before news outlets"), `get_sentiment_velocity` (says what the sign means instead of "an early reversal-detection signal"), `get_editorial_premium` (no "pre-coverage accumulation edge"), `get_history_correlation` (no "useful for pair trades"), `generate_due_diligence`, `generate_tokenomics_model`, `summarize_whitepaper` and `translate_contract` (get_agent_job returns the result, instead of "poll get_agent_job"), `book_kol_campaign`, `request_custom_research` and `submit_listing` (no "free to submit", featured listing pricing or payment method), and `search_academy` (site_url is the page, instead of "link to site_url"). The `submit_listing.contact_email` description drops the featured listing pricing too. Every tier mention stays: 52 tools are on the free tier, and each paid tool still names its tier.
- These descriptions read the same as in the TypeScript package, word for word (the two indicators keep this package's own `meta.status` sentence). The parity fixture is now `tests/fixtures/ts_tools_0_6_4.json`, dumped from the TS 0.6.4 build with the descriptions included; its names and constraints are unchanged from 0.6.3. A test fails if any tool or parameter description tells the model what to prefer, what to use, how to link or what to buy.
- README: the `mcp-name: io.github.blockchainacademics/mcp` line the official MCP Registry reads to confirm this PyPI package belongs to the server entry (server.json 0.6.4 lists `bca-mcp` next to the npm package), a "Not financial advice" note, a Privacy section (what each call sends, to which host, what is stored, and the policy link), "about 150 entity dossiers" (it said 150+, while `list_entities` says about 150), an opening line about the product instead of "the canonical crypto MCP server", and a "Why" section without the "ground-truth" claim.
- LangChain: the README example and `examples/langchain_agent.py` use `langchain.mcp` (`MCPAdapter`, LangChain 1.4 and later), since `langchain-mcp-adapters` is archived. Checked with langchain 1.4.7: `uvx bca-mcp` loads all 105 tools as LangChain tools, and `env` reaches the server.
- `examples/eliza_plugin.md` links `@elizaos/plugin-mcp` on npm (its old GitHub repo answers 404).
- Version 0.6.4 in pyproject, `__version__` and the User-Agent, and `tests/test_version.py` checks that they agree.
- PyPI classifiers name Python 3.11, 3.12 and 3.13, the versions CI tested when they were set (CI now runs 3.14 too; its classifier waits for a green run there). 3.10 was listed although `requires-python` is `>=3.11`; `tests/test_version.py` now rejects a classifier below that floor.

### Fixed

- A tool above the key's plan answers `BCA_TIER_LOCKED` instead of `BCA_BAD_REQUEST`, as in the TypeScript package. The API sends HTTP 402 to a valid key on a lower plan, and the client now gives it the code the README documents (it was only used for the HTTP 403 a call without a key gets). The message is "This tool requires a higher tier:" followed by the API's upgrade sentence with the pricing link, which stays inside an `untrusted_content` fence like any other API detail, cut at 500 characters. A 402 without a readable sentence gets a fixed one with the pricing link. `BcaError.status` is 402 and `BcaError.detail` holds the sentence. 404 and 422 are unchanged.
- A read the API turns away at its per-second limit (HTTP 429) is sent again instead of failing, so a second tool call made in the same moment waits a second or two and then answers, as in the TypeScript package. Up to two retries, each after `Retry-After` (1 second when the header is absent) plus 100 to 300 ms of jitter, at most 4.6 seconds in all. Only GET requests are repeated, and only when the 429 is the per-second limit: a `Retry-After` of 2 seconds or less together with `X-BCA-Error-Code: BCA_RATE_LIMIT`, or no `Retry-After` and a detail that names the limit. A daily cap, the job queue cap and a vendor limit still answer `BCA_RATE_LIMIT` at once, and `retry_after` is read only from a whole number of seconds (a negative value was passed through).
- A `BCA_RATE_LIMIT` error says which limit was hit, as in the TypeScript package. The message keeps the API's own reason (the per-second limit, a daily cap, the job queue cap, a vendor limit) and the signup link the API sends to a call without a key, up to 500 characters inside an `untrusted_content` fence like any other API detail. Every 429 used to read "Rate limit exceeded", so a daily cap looked the same as a one-second burst. `BcaRateLimitError.detail` holds the reason for programmatic callers, and the `bca` CLI prints it after the message.
- A `BCA_NETWORK` error names what failed. A timeout read `Network error contacting BCA API: ` with nothing after the colon, since httpx timeouts carry no text; it now reads `Network error contacting BCA API: ReadTimeout` (or `ConnectTimeout`), and other failures give the class and the text (`ConnectError: [Errno 61] Connection refused`), the way the TypeScript package prints an error. The time limits are unchanged.
- `bca login --api-base` accepts the bases the client accepts (`http://localhost[:port]` and `http://127.0.0.1[:port]` for local development) and refuses any other host before saving. It used to refuse localhost unless `BCA_ALLOW_INSECURE_BASE=1` was set (nothing else reads that variable) and to save any https host, after which every command failed with a traceback. A `BCA_API_BASE` the client refuses, from the environment or the config file, now gives one error message and exit code 1 in every command.

### Notes: plan for mcp 2.x (no code change in 0.6.4)

`mcp` 2.0.0 shipped on 2026-07-28 and 2.3.0 on 2026-10-02; 1.29.0 (2026-07-28) is the last 1.x release, so `mcp>=1.21.1,<2.0.0` stays for 0.6.4.

1. Port `server.py` in 0.7.0: the 2.x low level `Server` takes `on_list_tools` and `on_call_tool` in its constructor and has no `@server.list_tools()` decorator or `request_handlers` map, so register both handlers there and keep our own JSON Schemas, annotations, `isError` results and untrusted content fences.
2. Raise the pin to `mcp>=2.3.0,<3` in the same release, never before the port, and keep a 0.6.x line on 1.x for fixes until 0.7.0 is out.
3. Before release, run `tests/test_stdio.py` with a 1.x and a 2.x client, plus the parity and annotation tests, and check `serverInfo.version`, that the session survives a cancelled call and a malformed request (the reasons for the 1.21.1 floor), and that the `server/discover` request newer clients send first is answered (1.x logs it as an invalid request, then the session goes on through `initialize`).

## [0.6.3] (2026-11-02)

Fixes from the 2026-10-31 tool probe, in lockstep with @blockchainacademics/mcp 0.6.3. 104 → 105 tools.

### Added

- `get_as_of_snapshot`: article search pinned to the corpus as it stood at a past date, ported from the TypeScript package. Both packages now list the same 105 tools.
- MCP tool annotations on every tool: a `title` ("Get price"), `openWorldHint: true`, `readOnlyHint: true` on read tools, and `readOnlyHint: false`, `destructiveHint: false`, `idempotentHint: false` on the eight tools that create a record or start a job.

### Fixed

- Failed tool calls return `isError: true`. 0.6.2 sent the error body with `isError: false`, so clients read errors as results.
- Invalid arguments give `BCA_BAD_REQUEST` with `field: problem` pairs (`Invalid arguments for book_kol_campaign: budget_usd: Input should be greater than or equal to 500`) instead of a raw validation dump. A rejected `monitor_keyword` webhook is `BCA_BAD_REQUEST` too (was `BCA_UNKNOWN`).
- When the API rejects a request (4xx), the error message carries the API's explanation, up to 500 characters, fenced as untrusted content. 5xx errors stay generic.
- `translate_contract` sends the contract as `code`, the API's field name. 0.6.2 sent `source_code`, which the API rejected on every call.
- The service tools take the fields the API requires (changed parameters; the 0.6.2 shapes never worked):
  - `book_kol_campaign`: `contact_email`, `project_name`, `campaign_type` (thread, video, space, podcast, hybrid) and `budget_usd` (whole dollars, 500 to 2,000,000); optional `project_slug`, `contact_name`, `company`, `target_chains`, `notes`. `objective`, `target_audience` and `launch_window_days` are gone.
  - `submit_listing`: `contact_email`, `directory` (vcs, aggregators, trading_bots, mcps, nft_communities, jobs, stablecoins, trading_yields), `listing_name`, `listing_url` and `description` (20 to 2,000 characters); optional `contact_name`, `tags`. `entity` is gone.
  - `request_custom_research`: `topic` needs 4 to 240 characters; `deadline_days` (never read by the API) is replaced by the API's `deadline`, plus optional `target_wordcount`, `contact_name`, `company`, `notes`.
  - Descriptions say what the API returns (`request_id`, `status`, `next_step`) and that the tools are free to call with any API key from the free tier up, not "Pro tier".
- Tool schemas advertise type, enum and bounds directly on optional fields (no `anyOf` null branch, no generated titles). `generate_tokenomics_model` advertises its `scenarios` default, `generate_due_diligence` bounds each `focus` entry, and `list_entity_mentions` defaults `limit` to 50 like the TypeScript package.
- Demo banner: "17 tools work without a key" (was "~10 tools"), and "A free key opens 52 tools and paid plans open the rest" (it said a free key opened all tools). The README lists the 17 (the API's demo allowlist, `get_article` included, and its description says so), and the README and the LangChain submission copy say the same about the free key.
- `get_explainer`: 38 lessons in 8 courses (was 43 in 9), with examples that exist. `list_topics` names only topics in the taxonomy.
- The User-Agent and `serverInfo.version` report 0.6.3 (`serverInfo` showed the MCP SDK's version).
- A `BCA_API_KEY` with a stray space or newline around it (a pasted key) is trimmed, as the TypeScript package's fetch does, instead of failing every call with a `BCA_NETWORK` error that repeated the whole key to the host model. A key with a line break inside gives `BCA_AUTH`, and the message never repeats the key.
- Requires `mcp` 1.21.1 or later (was 1.0.0). Older 1.x releases end the session when the host cancels a call (before 1.12.3) or sends a malformed request (before 1.9.4), and releases up to 1.21.0 fail to import next to pydantic 2.14.

### Changed (the tools match the fixed API of 2026-11-01)

- New optional parameters the API honors: `granularity` (hourly or daily) on `get_history_prices`; `ticker` and `offset` on `search_news`; `offset` on `list_entities`, `list_entity_mentions` and `search_academy`; `limit` (1 to 200) and `expiry` (13NOV26 or 2026-11-13) on `get_options_flow`; `window` (1h, 6h, 24h, 7d) and `currencies` on `get_social_signals`; `window` on `get_social_signals_detail`; `type`, `limit` and `offset` on `list_sources`; `history_days` (0 to 90) on `get_defi_protocol`; `exchange` (binance, coinbase, upbit) on `predict_listing`; `mode` (trending, new) on `track_pumpfun`; `venue` (polymarket, kalshi, all) on `get_prediction_markets`; `country` (ISO-2) on `get_mica_status`; `chain`, `min_usd_loss` and `limit` on `check_exploit_history`; `chain` on `get_bug_bounty_programs`; `chain` and `limit` on `list_aggregators`; `unlock_shock_pct` on `generate_tokenomics_model`; `language` on `summarize_whitepaper`. When left out, nothing is sent and the API's own default applies.
- `get_history_correlation`: `peer` is optional (the answer then correlates price with sentiment only). `get_mica_status`: `entity_slug` is optional, since the API ignores it, and the tool needs no argument.
- Windows follow what the API computes: `get_coverage_index` and `get_narrative_strength` take 7d, 30d or 90d; `get_sentiment_velocity` 7d or 30d; `get_editorial_premium` and `get_kol_influence` 30d or 90d; `track_narrative` 7d, 30d or 90d (1d was never computed, 90d is); `get_trending` gains 6h. `list_theses` takes invalidated and pending, and all now means no status filter.
- Bounds equal the API's, so a value the API would reject is a `BCA_BAD_REQUEST` before any request is sent: history `days` up to 365 (was 3650); `limit` up to 100 on `list_entities` and `list_entity_mentions` (was 200) and up to 200 on `list_currencies` (was 500); `monitor_keyword` keyword 2 to 200 characters; `compare_protocols` 1 to 5 slugs; `search_academy` query at least 2 characters; `build_custom_indicator` formula 3 to 256 characters; `request_custom_research` topic up to 256 characters; at most 3 `scenarios`; `list_yields` `min_apy` 0 to 1000 and `chain` up to 32 characters; `get_bug_bounty_programs` `min_payout` at least 0; ISO-2 country codes only on `get_regulatory_status`, `get_tax_rules` and `get_mica_status` (names were a 422); BTC, ETH or SOL on `get_options_flow`; letters only on `track_sec_filings`; symbols of 2 or more characters on `get_funding_rates`, `get_liquidation_heatmap` and `get_exchange_flows`; 1 to 50 CoinGecko ids and a lower case quote currency (3 to 10 letters) on `get_price` and `get_ohlc`; and the API's address, hash and length rules on `get_ohlc`, `get_pair_data`, `get_wallet_profile`, `get_tx`, `get_token_holders`, `get_defi_protocol`, `check_memecoin_risk`, `check_phishing_domain`, `track_narrative`, `get_prediction_markets`, `get_smart_contract_template` and `get_marketing_template`.
- Slug inputs take the lower case kebab form the TS package takes (`get_entity`, `get_explainer`, `get_article`, `list_entity_mentions` and the `search_news` filters), so both packages accept the same arguments; aliases resolve in slug form (`cz`).
- `list_yields` sends its minimum as `min_apy_pct`, the API's name (the API also reads `min_apy`). `build_custom_indicator` sends only the formula (the API has no `target` parameter). `generate_tokenomics_model` no longer sends a default `scenarios` list, which the API reported as ignored on every call, and `get_exchange_flows` no longer sends a default `window`.
- `get_entity` keeps the ticker form on `/v1/entities?ticker=`: the slug route resolves slugs and aliases only, and the alias table holds no tickers. Its description now says the ticker form needs an API key.
- The per field untrusted content fences read the API's response shapes: `data.result` on `get_entity` (summary, and `data.results[]` for the ticker form) and `get_article` (summary, `body_md`), `data.results[]` on `search_news` (summary) and `list_entity_mentions` (`context_snippet`), and `data.result` on `get_agent_job`, including the strings inside the whitepaper summary object. They read the older keys too. The whole `data` payload was and stays fenced.
- Descriptions say what each tool returns today and when it usually answers `unseeded` or `partial`: no address labels on `get_wallet_profile`, Akash only (io.net and Render pending) on `get_compute_pricing`, no analyzer yet on `check_memecoin_risk`, no webhook delivery on `monitor_keyword`, no tweet counts while the X reader is off, Polymarket and Kalshi only on `get_prediction_markets`, no 7d or 30d change on `get_price`, no honeypot test on `scan_contract` or `check_rugpull_risk`, one value (not a time series) from `build_custom_indicator`, `get_as_of_snapshot` free and open without a key (not "Enterprise tier"), about 150 entities on `list_entities`, course and lesson slugs on `get_explainer`, `done` and `result` on `get_agent_job`, the collection state on `list_sources`, stale tokenomics on `compare_protocols`, the service tools alerting the team (no automatic email, no 2 day promise), "Works without an API key" on the 16 demo tools, and the parameters the API accepts but does not apply yet (`focus`, `scenarios`, `length`, `get_exchange_flows` `window`, `get_funding_rates` `exchanges`, `build_custom_indicator` `target`). No parameter was removed.
- The `bca` CLI matches the API: `news search` reads `results` (it showed "No results" for every query), `entity` and `explainer` read the nested record, `price` takes CoinGecko ids (it sent tickers to `get_price` and crashed), `indicator` calls the API's routes with `entity_slug`, and `agent` posts to the skill routes (`--code-file` for `translate-contract`, `--webhook` for `monitor-keyword`) and reads `result`. A bad argument prints a `BCA_BAD_REQUEST` line instead of a traceback.
- README: a section on `meta.status` (complete, partial, stale, unseeded and their diagnostics) and on `attribution.citations[0]` as the primary source; corpus and entity counts from the API (3,800+ articles, 150+ entities); errors are described for every failed tool call.
- `get_mica_status` describes a country outside the EU and EEA as unseeded only while BCA has no reviewed row for it (the API returns the row when there is one). `get_agent_job` names its tier (Pro) and that a job is visible only to the key that started it.

## [0.6.2] — 2026-10-19

### Added — live crypto jobs (lockstep with @blockchainacademics/mcp 0.6.2)

`list_jobs` now returns real data: 1,300+ open roles at 50+ crypto companies, collected every 6 hours from the companies' own job boards, with apply links to the company's own page. Both job tools are available on the demo tier. 103 → 104 tools.

- `list_jobs`: filters now match the API (keyword, role category, remote, location, employment type, company); descriptions are opt-in to keep responses small.
- `get_job`: one role in full, with apply link and BCA job page URL.

## [0.6.1] — 2026-10-19

### Added — grants (lockstep with @blockchainacademics/mcp 0.6.1)

The live grants directory behind blockchainacademics.com/grants: 200+ crypto, web3, AI and public-funding programs, each checked against the funder's page weekly. Expired rounds are never returned. Available on the demo tier. 101 → 103 tools.

- `search_grants`: filter by keyword, ecosystem (web3, ai, web2_cloud, gov, edu), country, minimum award, application complexity and deadline. Soonest deadline first.
- `get_grant`: one program in full, with apply link and last verified date.

## [0.6.0] — 2026-10-09

### Added — crypto Twitter intelligence (lockstep with @blockchainacademics/mcp 0.6.0)

BCA's read of what crypto Twitter is saying, as analysis in our own words with X post URLs as citations (never reposted post text). Pro tier. 98 → 101 tools.

- `get_ct_pulse`: last-24h takeaway, top stories, narratives, sourced numbers, notable posts. No topic = latest scheduled market snapshot.
- `get_x_signals`: breaking stories surfaced on X before news outlets, by lane (security, news, keyword), with confidence and on-chain evidence flags.
- `get_kol_consensus`: where credible CT voices stand on the most-covered tokens.

### Changed

- `get_social_pulse` is now live (was `integration_pending`).
- `get_article` works without an API key (rate-limited per IP).

## [0.5.3] — 2026-09-28

### Security

- **Prompt-injection fence hardening.** Upstream text (news bodies, whitepapers,
  contract source, entity dossiers) is wrapped in `<untrusted_content>` fences so
  the host LLM treats it as data. That defence is only sound if the text can't
  contain the fence's own closing token — an attacker embedding a literal
  `</untrusted_content>` could otherwise close the fence early and inject
  instructions. New `_untrusted.neutralize_fence_tokens()` rewrites any literal
  fence tag (open/close, case/space/attribute tolerant) to an inert `&lt;…&gt;`
  form before wrapping, at every fence site. Mirrors the TS sibling.

## [0.5.2] — 2026-09-22

### Fixed

- **Critical packaging bug: the published package crashed on import.** `client.py`
  imports `bca_mcp._demo_key` at module load, but `_demo_key.py` is generated and
  gitignored — hatchling excludes gitignored files, so **0.5.0 and 0.5.1 shipped
  without it** and every `pip install bca-mcp` / `uvx bca-mcp` failed with
  `ModuleNotFoundError: No module named 'bca_mcp._demo_key'`. (npm's
  `@blockchainacademics/mcp` was unaffected.)

### Changed

- **Pinned `mcp>=1.0.0,<2.0.0`.** `mcp` 2.x removed the low-level
  `Server.list_tools()` / `call_tool()` decorator API that `server.py` uses, so a
  fresh install pulling `mcp` 2.x made the stdio server fail to start
  (`AttributeError: 'Server' object has no attribute 'list_tools'`). This was
  masked in 0.5.0/0.5.1 by the import crash. Migrating to the `mcp` 2.x API is a
  tracked follow-up.
- `pyproject.toml`: `[tool.hatch.build] artifacts = ["src/bca_mcp/_demo_key.py"]`
  force-includes the generated demo-key module in the wheel + sdist.
- `client.py`: the `_demo_key` import is now wrapped in `try/except ImportError`
  with the public demo-key literal as a fallback, so import can never crash again
  even if the generator wasn't run.
- Added a GitHub Actions CI gate (`.github/workflows/ci.yml`) that builds the wheel,
  installs it in a **clean venv**, and asserts `import bca_mcp` + the `bca-mcp`/`bca`
  entry points work — the exact check that would have caught this before publish.
- `USER_AGENT` → `bca-mcp/0.5.2`.

### Action

- Yank 0.5.0 and 0.5.1 from PyPI after 0.5.2 is confirmed installable.

## [0.5.1] — 2026-06-04

### Lockstep

Version bump only, to match `@blockchainacademics/mcp@0.5.1` on npm.
The TS sibling's 0.5.1 fixed an npx-symlink entry-point bug; Python
does not have an equivalent bug (`__name__ == "__main__"` resolves
correctly through PyPI console_scripts entry points), so this release
is pure version alignment.

`USER_AGENT` bumped to `bca-mcp/0.5.1` to match.

## [0.5.0] — 2026-06-04

### Added — public demo tier (zero-config first run)

Sibling of `@blockchainacademics/mcp@0.5.0`. Byte-identical demo banner,
identical fallback chain order, identical envelope/error additions.

When `BCA_API_KEY` is unset, `BcaClient` falls back to a baked-in public
demo key. The backend recognises it, applies a 10-tool allowlist, and
rate-limits at 100/day global + 20/day per-IP. `uvx bca-mcp` is now a
true zero-config demo instead of `build_server()` raising `RuntimeError`
on import.

- `EnvelopeMeta` TypedDict gains optional `tier` + `upgrade_url`
  (passthrough on canonical and legacy-flat branches).
- `BcaErrorCode` Literal extends with `BCA_TIER_LOCKED`. 401/403 handler
  peeks at upstream body and surfaces the signup URL verbatim.
- New `@property using_demo_key` drives a one-time stderr banner from
  `run_stdio()` after `build_server()`.
- `_assert_api_key_present()` removed. `build_server(check_env=...)`
  retained as a deprecated no-op for one release (test signature
  compat). Removed in 0.6.0.
- Build infrastructure: `scripts/demo-key.txt` (committed) +
  `scripts/gen_demo_key.py` write `src/bca_mcp/_demo_key.py` (gitignored)
  before `python -m build`.

### Fixed

- `USER_AGENT` was hardcoded to `bca-mcp/0.3.1` since v0.3.1 (latent
  bug that under-attributed all subsequent versions on the backend
  rate-limit logs). Now `bca-mcp/0.5.0`.

## [0.4.2] — 2026-06-02

### Lockstep

- Version bump only, to match `@blockchainacademics/mcp@0.4.2` on npm.
  The TS sibling's `server.json` now declares both npm + PyPI packages
  in a single MCP Registry entry; PyPI `bca-mcp` is referenced at
  `0.4.2`.

## [0.4.1] — 2026-06-02

### Fixed

- **Python 3.10 import crash.** 0.4.0 failed at import time on Python
  3.10 with `TypeError: cannot inherit from both a TypedDict type and a
  non-TypedDict base class` — `class ResponseEnvelope(TypedDict, Generic[T])`
  is only valid on Python 3.11+. Bumped `requires-python` to `>=3.11`
  so `pip install` / `uvx` resolve the correct interpreter from the
  start. No source change required; 0.4.0 stays on PyPI for the audit
  trail.

### Lockstep

- `@blockchainacademics/mcp@0.4.1` on npm carries the same version bump
  (no functional delta on the TS side).

## [0.4.0] — 2026-06-02

Distribution release. Lockstep with `@blockchainacademics/mcp@0.4.0` on npm.

### Security — MCP-TS-2 parity (closes redirect-hardening gap with TS sibling)

- **`follow_redirects=False` on `httpx.AsyncClient`.** Mirrors
  `~/bca-mcp-ts/src/client.ts` commit `895bfee` (2026-04-22). Without this
  flag, a compromised or mis-configured upstream that responds with a 3xx
  and an attacker-controlled `Location` header would cause `httpx` to
  re-issue the request — `X-API-Key` and all — to the redirect target.
- **Explicit 3xx rejection in `BcaClient._call()`.** Any 300–399 status now
  raises `BcaUpstreamError`. The error message includes the status code
  but masks the `Location` header so the attacker URL never leaks into
  logs or LLM context.
- **3 new regression tests** in `test_client_security.py`:
  - `test_rejects_302_redirect`
  - `test_rejects_301_permanent_redirect`
  - `test_api_key_never_sent_to_redirect_target` (defense-in-depth — confirms
    only ONE outbound request fires, to BCA, not the attacker)
- The `BCA_API_BASE` allowlist from 0.3.1 already bounds the initial host;
  this closes the redirect-based escape from that bound. Test suite:
  **113 / 113 passing.**

### Verified

- Envelope canonicality + hybrid citations (the TS sibling 0.4.0 changes
  land on the API surface, not the Python MCP layer — Python passes
  through the canonical envelope unchanged).
- 110 → 113 passing tests.

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
