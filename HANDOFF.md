# bca-mcp-python — Handoff

**Status (2026-04-21):** 0.1.0 built, tested, committed locally. Ready to push to GitHub + publish to PyPI.

## What exists

- `src/bca_mcp/` — 8-tool MVP for LangChain / generic-Python-agent parity with `@blockchainacademics/mcp@0.2.2`
  - Tools: `search_news`, `get_article`, `get_entity`, `list_entity_mentions`, `list_topics`, `get_explainer`, `get_price`, `get_market_overview`
  - Envelope-aware client at `client.py` (parses `{data, cite_url, as_of, source_hash}` and returns the unwrapped payload with attribution fields passed through)
  - stdio transport only (HTTP/SSE is v0.2+)
- `tests/` — 23 tests, all green (`pytest`)
- `dist/bca_mcp-0.1.0{.tar.gz,-py3-none-any.whl}` — built, `twine check` PASSED
- Git: initialized on `main`, first commit landed (no remote yet)

## Publish steps (Wael)

```bash
cd ~/bca-mcp-python

# 1. Create GitHub repo + push
gh repo create blockchainacademics/bca-mcp-python --public --source=. --remote=origin --push

# 2. Create PyPI API token at https://pypi.org/manage/account/token/
#    Scope: project-specific once uploaded; first upload needs account-wide token
#    Save as: ~/.pypirc   OR   export TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-...

# 3. Upload
source .venv/bin/activate
twine upload dist/*

# 4. Tag release
git tag v0.1.0
git push origin v0.1.0
gh release create v0.1.0 --title "0.1.0 — 8-tool MVP" --notes-file CHANGELOG.md
```

## Smoke test post-publish

```bash
pipx run bca-mcp --help       # should print stdio banner
# OR in a LangChain agent:
pip install bca-mcp
```

Config snippet for Claude Desktop (for parity testing vs TS package):

```json
{
  "mcpServers": {
    "bca": {
      "command": "pipx",
      "args": ["run", "bca-mcp"],
      "env": {"BCA_API_KEY": "bca_live_..."}
    }
  }
}
```

## Parity status vs TypeScript package

8/99 tools shipped. The Python package is the **LangChain / Eliza-Python entry point**, not a mirror of the full TS surface. v0.2 will expand once the TS v0.2.0 is listed in the Anthropic directory and we know which tools agents actually call.

## Known gaps (v0.2 targets)

- HTTP/SSE transport for hosted MCP (Virtuals, Bedrock)
- Remaining 91 tools (market data deep cuts, on-chain, indicators, agent-backed jobs)
- Example notebook (`examples/langchain_agent.ipynb`) — scaffold exists, needs a live run + output commit

## Local dev

```bash
cd ~/bca-mcp-python
source .venv/bin/activate   # Python 3.14.4
pytest                      # 23 tests, <1s
python -m bca_mcp           # runs stdio server against localhost:8000 unless BCA_API_BASE set
```
