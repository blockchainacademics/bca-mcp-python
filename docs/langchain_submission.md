# LangChain Community PR Submission Package: `bca-mcp`

**Status:** Draft (task #73, Phase 5 Registry blitz)
**Owner:** Blockchain Academics
**Target package:** [`bca-mcp`](https://pypi.org/project/bca-mcp/) 0.6.3
**Drafted:** 2026-04-21, counts and facts updated 2026-11-01

> **Before filing:** verify the two assumptions marked `VERIFY` below against the live LangChain CONTRIBUTING.md and the `langchain-mcp-adapters` README. Web research was blocked during drafting.

---

## 1. Target PR Details

### 1a. Fork & path recommendation

**Recommendation: do NOT add a hand-rolled tool wrapper under `libs/community/langchain_community/tools/bca_mcp/`.**

LangChain's current guidance (as of late 2025 / 2026) is:

- **MCP servers should be consumed through [`langchain-mcp-adapters`](https://github.com/langchain-ai/langchain-mcp-adapters)**, which converts an MCP server's tool list into `StructuredTool` objects at runtime. This avoids per-server glue code in `langchain-community` and keeps the MCP wire format as the single source of truth.
- **Third-party-maintained integrations that are NOT pure MCP** increasingly live in standalone `langchain-{partner}` packages under `libs/partners/`, not in `libs/community`. `libs/community` is in soft-freeze for new adapters. `VERIFY` against the current CONTRIBUTING.md before filing.

**Therefore, the PR we file is NOT a code PR against `langchain-ai/langchain`.** We should instead file **two smaller, higher-acceptance PRs**:

| # | Repo | Path | What it adds |
|---|---|---|---|
| **PR A** | [`langchain-ai/langchain`](https://github.com/langchain-ai/langchain) | `docs/docs/integrations/providers/blockchain_academics.mdx` + `docs/docs/integrations/tools/bca_mcp.ipynb` | Provider page + notebook tutorial under the "Tools" integration section, demonstrating BCA via `langchain-mcp-adapters`. **No code in `langchain_community`.** |
| **PR B** | [`langchain-ai/langchain-mcp-adapters`](https://github.com/langchain-ai/langchain-mcp-adapters) | `README.md` (Examples section) | One-paragraph entry + link to our notebook, same as existing community MCP server entries. |

This is the lowest-friction path: no new Python code in LangChain's tree, no long review cycle on a redundant adapter, and we land in the exact docs pages crypto-curious LangChain users search. `VERIFY` current docs directory layout: it was `docs/docs/integrations/` in 2024 and 2025; confirm before opening PR A.

If a reviewer pushes back and insists on a tool wrapper in `libs/community`, the fallback path is `libs/community/langchain_community/tools/bca/` (short dir name, matching the `arxiv` and `serpapi` conventions) with `tool.py`, `__init__.py`, and a `tests/integration_tests/tools/test_bca.py`. Do NOT nest under `bca_mcp/`: LangChain's tools dir is flat.

### 1b. Suggested PR title (under 70 chars)

**Primary (PR A, docs):**
> `docs: add Blockchain Academics (bca-mcp) integration page + notebook`
> *(64 chars)*

**Alternative phrasings to A/B with maintainers:**
- `docs: add bca-mcp crypto MCP server tutorial` (46 chars)
- `integration: Blockchain Academics MCP (crypto corpus + market)` (63 chars)

**Secondary (PR B, adapters README):**
> `docs: list bca-mcp under example MCP servers` (45 chars)

### 1c. PR body template (PR A, LangChain docs)

```markdown
## What

Adds a new third-party integration entry for [`bca-mcp`](https://pypi.org/project/bca-mcp/),
a Python MCP server that exposes the Blockchain Academics crypto corpus (3,800+ editorial
articles, 150+ entity dossiers, 38 academy lessons in 8 courses, live market data) as
105 MCP tools, 16 of which work without an API key.

Changes:
- **New provider page:** `docs/docs/integrations/providers/blockchain_academics.mdx`
- **New notebook:** `docs/docs/integrations/tools/bca_mcp.ipynb`: install, client setup,
  three tool calls, and a LangGraph agent that answers a real crypto research question
  using three BCA tools.
- **No code changes** in `langchain_community` or any `libs/*` package. BCA is consumed
  via the existing [`langchain-mcp-adapters`](https://github.com/langchain-ai/langchain-mcp-adapters)
  pattern.

## Why

- Crypto is a high-hallucination domain for LLMs; grounding agents in a cited editorial
  corpus is the typical mitigation. No existing LangChain integration covers crypto editorial
  + entity dossiers with a structured `attribution` envelope (`citations[]` with cite_url,
  as_of, source_hash) and an honest `meta.status` on every answer.
- `bca-mcp` has a TypeScript sibling (`@blockchainacademics/mcp`) with the same 105 tools,
  already listed in the MCP community registry; this PR closes the Python-side docs gap.
- 16 tools work without a key (demo mode), a free API key opens 52 (every tool the notebook
  calls among them) and paid plans open the rest, so reviewers and new users can run the
  notebook end-to-end with no billing friction.

## Docs / Links

- Package: https://pypi.org/project/bca-mcp/
- Source: https://github.com/blockchainacademics/bca-mcp-python
- API docs: https://blockchainacademics.com/crypto-api/docs
- Free API key: https://blockchainacademics.com/crypto-api/signup
- TS sibling (already in MCP registry): https://www.npmjs.com/package/@blockchainacademics/mcp

## Test plan

- [ ] `pip install bca-mcp` succeeds on a clean 3.11 / 3.12 venv
- [ ] Notebook executes top-to-bottom with a free-tier `BCA_API_KEY`
- [ ] `search_news`, `get_entity`, `get_explainer` each return a response with a
      populated `attribution.citations[0].cite_url`
- [ ] LangGraph agent cell completes in <60s and cites at least one source URL in
      its final answer
- [ ] Provider MDX page renders locally with `yarn start` in `docs/`
- [ ] No links 404 (`make lint-docs` or equivalent)

## Checklist

- [ ] Conforms to the docs style guide (headings, code block language tags, relative links)
- [ ] Notebook has cleared outputs before commit (LangChain convention)
- [ ] Notebook cells are idempotent: a re-run does not error
- [ ] No secrets in the notebook; API key pulled from `os.environ["BCA_API_KEY"]`
- [ ] Added entry to `docs/docs/integrations/tools/index.mdx` (if the repo still maintains
      the index manually, `VERIFY`)
```

---

## 2. Example Jupyter Notebook Outline

**Path:** `docs/docs/integrations/tools/bca_mcp.ipynb`
**Title:** `Blockchain Academics (bca-mcp): crypto corpus + market data via MCP`
**Target runtime:** 60s or less end-to-end on a free-tier API key

### Cell-by-cell outline (11 cells)

| # | Type | Purpose |
|---|---|---|
| 1 | Markdown | **Header + one-paragraph overview.** What BCA is, what the 105 tools cover (16 without a key), the attribution contract, link to the signup page for a free key. |
| 2 | Markdown | **Setup.** Note: needs Python 3.11 or later, a free `BCA_API_KEY`, and `langchain-mcp-adapters`. |
| 3 | Code | **Install.** `%pip install --quiet bca-mcp langchain-mcp-adapters langgraph` plus the chat model package of the reader's choice. |
| 4 | Code | **Imports + env.** `import asyncio, os, sys; from mcp import ClientSession, StdioServerParameters; from mcp.client.stdio import stdio_client; from langchain_mcp_adapters.tools import load_mcp_tools`. Sets `os.environ["BCA_API_KEY"]` via `getpass` if not already set. |
| 5 | Code | **Instantiate MCP client.** Build `StdioServerParameters(command=sys.executable, args=["-m", "bca_mcp"], env={...})`. Open `stdio_client` + `ClientSession` as async context managers. Call `session.initialize()`. `tools = await load_mcp_tools(session)`. Print `[t.name for t in tools]`, which confirms the 105 tools loaded. |
| 6 | Markdown | **Tool 1: `search_news`.** Explain the tool and its envelope shape. |
| 7 | Code | **Call `search_news`.** `result = await tools_by_name["search_news"].ainvoke({"query": "stablecoin regulation", "limit": 3})`; print a results table (title, link, published date). |
| 8 | Code | **Call `list_entity_mentions`** for bitcoin with a 30 day `since` window (free tier). `get_coverage_index` is in the tool list too, but it needs a Pro key; mention it as the upgrade path. |
| 9 | Code | **Envelope inspection.** Pretty-print the `attribution` and `meta` blocks of one response. Highlight `citations[0]` (the primary source: cite_url, as_of, source_hash) and `meta.status` (complete, partial, stale or unseeded, with `meta.diagnostic`). Explain the attribution contract: _if your agent shows BCA content to a user, link `citations[0].cite_url`._ |
| 10 | Markdown | **LangGraph agent example.** Motivation: "how has coverage of Bitcoin vs Ethereum moved over the last 30 days" is a multi-tool question: it needs entity dossiers, mention timelines and news search to answer defensibly. |
| 11 | Code | **LangGraph agent.** Build a `create_react_agent` with the reader's chat model and three tools: `get_entity`, `list_entity_mentions`, `search_news`. Invoke with `{"messages": [("user", "How has coverage of Bitcoin vs Ethereum moved over the last 30 days? Cite sources.")]}`. Print the final message. Assert the answer includes at least one cited URL. |

**Pre-publish scrub:**
- Clear all cell outputs before committing (LangChain docs convention)
- Confirm the notebook runs on a 3.11 env with only the packages in cell 3
- Replace any `bca_live_*` live API key with a `getpass` prompt

---

## 3. Pre-submit Checklist

### PyPI / package health

- [ ] **Rotate PyPI publish token**: revoke the v0.1.0 upload token, mint a scoped-to-`bca-mcp` token, store in 1Password under `PyPI / bca-mcp` (or publish through the trusted publishing workflow)
- [ ] `pip install bca-mcp` installs clean on fresh venvs: 3.11, 3.12 (macOS arm64, Linux x86_64)
- [ ] `pipx install bca-mcp && bca --help` works (console script entry points register)
- [ ] `python -m bca_mcp` starts without `BCA_API_KEY` set in demo mode: a one-time stderr banner, and 16 tools answer
- [ ] `dist/` contains both wheel + sdist; both pass `twine check`

### README coverage

- [ ] At least 3 worked examples: Claude Desktop config, LangChain via `langchain-mcp-adapters`, Eliza plugin (already present)
- [ ] Attribution contract section is prominent: reviewers WILL ask (already present, with `citations[0]` as the primary source)
- [ ] `meta.status` (complete, partial, stale, unseeded) is documented (already present)
- [ ] Error code table present (already present)
- [ ] Tool catalog table present with endpoints + tiers (already present)

### Repo hygiene

- [x] `mcp>=1.21.1,<2.0.0` in pyproject.toml (0.6.3), so no SDK release that drops the session can be installed
- [ ] `CHANGELOG.md` has a 0.6.3 entry (105 tools, parity with the TS package)
- [ ] GitHub repo has a top-level `examples/langchain_agent.py` that matches the notebook logic (README references it; confirm it runs)
- [ ] CI green on main (pytest, `twine check`, build)
- [ ] LICENSE is MIT and the file is present at repo root
- [ ] `SECURITY.md` with disclosure email + 90-day window (LangChain reviewers occasionally flag a missing SECURITY.md)

### Docs PR prep

- [ ] Fork `langchain-ai/langchain` under the BCA GitHub org, not a personal account
- [ ] Branch naming: `docs/bca-mcp-integration`
- [ ] Notebook outputs cleared (`jupyter nbconvert --clear-output --inplace bca_mcp.ipynb`)
- [ ] Provider MDX page passes `yarn start` local render with no broken links
- [ ] Screenshot of the LangGraph agent output attached to PR body (optional, but helps reviewers)

### Legal / attribution

- [ ] Confirm BCA's brand usage is OK for use in LangChain docs screenshots (internal sign-off)
- [ ] The citation contract is explicit in the notebook narrative: reviewers should see the attribution requirement in cell 9

---

## 4. Anticipated Review Questions + Prep Answers

### Q1. "Why another MCP adapter? Why not just add BCA to `langchain-mcp-adapters` examples?"

**Answer:** We're not shipping an adapter. This PR is **pure docs**: a provider page and a notebook that consume BCA via the existing `langchain-mcp-adapters` library. No new Python code in `langchain-community` or any `libs/*` package. If the reviewer prefers, we can move the notebook into `langchain-mcp-adapters/examples/` instead; we're drafting PR B for exactly that. The provider MDX page still belongs in `langchain-ai/langchain` because that's where LangChain users discover integrations via the integrations index.

### Q2. "Does this duplicate `langchain-mcp-adapters`?"

**Answer:** No. `langchain-mcp-adapters` is the runtime glue that turns any MCP server's tool list into `StructuredTool` objects. `bca-mcp` is an MCP **server**, the thing on the other end of that wire. The notebook shows users how to plug our server into the existing adapter; we don't fork, wrap, or shadow any adapter code. It is the same relationship as between `langchain-mcp-adapters` and `@modelcontextprotocol/server-filesystem` or `@modelcontextprotocol/server-github`.

### Q3. "Is rate-limiting handled? What happens at scale?"

**Answer:** Yes, at three layers:
1. **Server-side:** the BCA API enforces per-key rate limits (free tier: 2,000 calls/month; paid tiers scale). 429s return `Retry-After` headers.
2. **MCP server layer:** `bca-mcp` surfaces 429s as MCP responses with `isError: true` and error code `BCA_RATE_LIMIT`, preserving `Retry-After` in the message body. The server never crashes the stdio process on a 429.
3. **Envelope layer:** every successful response carries an `as_of` timestamp in its citations and a `meta.status` (stale answers say how old they are), so downstream callers can cache aggressively and detect staleness.

### Q4. "Does the Python package cover the same tools as the TypeScript one?"

**Answer:** Yes. Both packages expose the same 105 tools with the same names, input schemas and annotations, and both talk to the same REST API with the same attribution contract. 16 of them work without a key, a free key opens 52, and paid plans open the rest; without a key, the other 89 answer with a clean upgrade message. Reviewers can test end-to-end on a free-tier key.

### Q5. "How do you handle auth? API key in env var is fine for Claude Desktop but what about shared infra?"

**Answer:** The `BCA_API_KEY` env var is the only supported auth mode in 0.6.3, the standard MCP pattern. Without it the server runs in demo mode on a shared, rate-limited public key. The CLI additionally supports `~/.bca/config.toml` with `chmod 600`. For shared / multi-tenant infra, the recommended pattern is per-user MCP server instances with per-user env vars (same as every other MCP server). No shared-secret brokering yet; a future version may add OIDC once the MCP spec stabilizes auth.

### Q6. "What's the licensing on the corpus? Can LangChain users freely call this in production?"

**Answer:** The MCP client code is MIT. The corpus content is served under BCA's terms (free tier for non-commercial + light commercial, paid tiers for heavy use). The **attribution contract** (citations on every response) is the core trade: agents get ground-truth citations, BCA gets distribution. This is explicit in the README and in the notebook narrative (cell 9).

### Q7. "Does this work with both stdio and SSE/streamable-HTTP transports?"

**Answer:** 0.6.3 ships stdio only. Streamable HTTP is on the roadmap. The notebook uses stdio because (a) it's the most widely supported transport across MCP clients today and (b) it matches the Claude Desktop configuration most of our users start with.

### Q8. "Tests?"

**Answer:** `pytest -q` runs 470+ tests in the repo (`tests/`): schemas, errors, the attribution envelope, untrusted content fences, the stdio transport and the CLI. Every HTTP call in them is mocked, so CI never touches the live API. For LangChain-side CI, the notebook is the integration test: it runs end-to-end against the public free-tier API.

---

## Notes for the person filing the PR

1. **File PR B first** (the one-liner in `langchain-mcp-adapters/README.md`): lower risk, builds the relationship with that maintainer, lands in a day.
2. **Let PR B merge before filing PR A.** The provider page can then link to the adapter's example section, which makes PR A a more obvious accept.
3. **Don't bundle Phase 5 Registry work into either PR.** Keep the MCP registry submission separate; LangChain reviewers don't care about MCP registry status and bundling slows review.
4. **If PR A stalls more than 2 weeks**, ping `#contributing` in the LangChain Discord with a one-line summary. Don't open a second PR.
5. **VERIFY markers above**: before filing, re-check `CONTRIBUTING.md` and the current integrations docs directory layout. `get_coverage_index` is in the tool list but needs a Pro key, so the notebook uses `list_entity_mentions` for the free-tier path.

---

**Package owner:** Blockchain Academics
**Contact:** dev@blockchainacademics.com
**Task:** #73, Phase 5 Registry blitz
