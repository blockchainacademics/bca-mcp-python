"""User-facing copy: demo banner, README, tool descriptions (F36, F51,
shared decisions 1 and 5)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from bca_mcp._demo_banner import DEMO_BANNER
from bca_mcp.server import TOOLS

ROOT = Path(__file__).resolve().parent.parent
EM_DASH = "—"

# The API's demo allowlist (blockchainacademics-api app/api/v1/_demo_allowlist.py;
# 2026-11-02: the 16 of 2026-10-31 plus get_article).
DEMO_TOOLS = (
    "get_price", "get_trending", "get_fear_greed", "get_market_overview",
    "search_news", "get_article", "get_sentiment", "get_entity",
    "get_explainer", "get_recent_stories", "get_topic", "search_grants",
    "get_grant", "list_jobs", "get_job", "search_academy",
    "get_as_of_snapshot",
)

# The API's topic taxonomy (topic_taxonomy, scripts/seed_canonical_slugs.py).
TAXONOMY = {
    "regulation", "defi", "nft", "layer-2", "bitcoin", "ethereum", "solana",
    "stablecoins", "rwa", "ai-agents",
}


def _tool(name: str):
    return next(t for t in TOOLS if t.name == name)


def test_demo_banner_exact_bytes() -> None:
    assert DEMO_BANNER == (
        "[bca-mcp] Running in DEMO mode: 17 tools work without a key, under a shared daily cap.\n"
        "[bca-mcp] A free key opens 52 tools and paid plans open the rest: https://blockchainacademics.com/crypto-api/signup?ref=mcp-first-run\n"
        "[bca-mcp] Set: export BCA_API_KEY=bca_...   (or add to your client config)\n"
    )
    assert DEMO_BANNER.isascii()


def test_demo_tools_exist() -> None:
    names = {t.name for t in TOOLS}
    assert len(DEMO_TOOLS) == 17 and set(DEMO_TOOLS) <= names
    assert f"{len(DEMO_TOOLS)} tools work without a key" in DEMO_BANNER


def test_every_demo_tool_description_says_it_works_without_a_key() -> None:
    for name in DEMO_TOOLS:
        # get_entity: only the slug form ("the slug form works without one").
        assert re.search(r"(works|open) without (an API key|one)", _tool(name).description, re.I), name
    assert "Works without an API key." in _tool("get_article").description


def test_no_copy_still_counts_16_demo_tools() -> None:
    stale = re.compile(r"\b16 tools\b|\b16 of (which|them)\b|\(16 without|\b89 of the 105\b|\bother 89\b")
    for path in (
        "README.md",
        "docs/langchain_submission.md",
        "examples/eliza_plugin.md",
        "examples/langchain_agent.py",
    ):
        assert not stale.search((ROOT / path).read_text("utf-8")), path
    readme = (ROOT / "README.md").read_text("utf-8")
    assert "| `get_article` | content | `GET /v1/articles/{slug}` | Free | yes |" in readme


def test_free_key_reach_matches_the_tool_descriptions() -> None:
    # A tool on a paid plan names its tier in its description; the others are
    # the free tier (52 of the 105 on 2026-11-01).
    paid = [t for t in TOOLS if re.search(r"\b(Starter|Pro|Team) tier\b", t.description)]
    free = len(TOOLS) - len(paid)
    assert free == 52
    assert f"A free key opens {free} tools and paid plans open the rest" in DEMO_BANNER
    readme = (ROOT / "README.md").read_text("utf-8")
    assert f"A free key opens {free} tools." in readme
    stale = re.compile(
        r"for all (105|tools)|unlock all 105|all 105 tools are open|full 105-tool surface"
        r"|opens the rest up to|until a free key is set",
        re.IGNORECASE,
    )
    for where, text in (
        ("banner", DEMO_BANNER),
        ("README.md", readme),
        ("docs/langchain_submission.md", (ROOT / "docs/langchain_submission.md").read_text("utf-8")),
    ):
        assert not stale.search(text), f"{where} says a free key opens every tool"


def test_readme_lists_the_17_demo_tools_and_current_counts() -> None:
    readme = (ROOT / "README.md").read_text("utf-8")
    section = readme.split("## Zero-config first run", 1)[1].split("\n## ", 1)[0]
    listed = re.findall(r"`([a-z_]+)`", section)
    assert [t for t in listed if t in {x.name for x in TOOLS}] == list(DEMO_TOOLS)
    assert "17 tools" in section
    assert "upgrade message" in section
    for stale in ("10 marquee", "first 8 tools", "8 tools", "1,000 calls", "99-tool",
                  "91 of the 105", "89 of the 105", "16 tools", "43 academy", "102 tools"):
        assert stale not in readme, stale
    assert "88 of the 105" in readme
    assert "38 academy lessons" in readme


def test_no_em_dashes_in_user_facing_text() -> None:
    assert EM_DASH not in DEMO_BANNER
    for path in ("README.md", "examples/eliza_plugin.md"):
        assert EM_DASH not in (ROOT / path).read_text("utf-8"), path
    for t in TOOLS:
        assert EM_DASH not in t.description, t.name
        assert EM_DASH not in json.dumps(t.input_schema, ensure_ascii=False), t.name


def _schema_descriptions(node) -> list[str]:
    out: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "description" and isinstance(value, str):
                out.append(value)
            else:
                out.extend(_schema_descriptions(value))
    elif isinstance(node, list):
        for item in node:
            out.extend(_schema_descriptions(item))
    return out


def test_descriptions_never_tell_the_model_how_to_behave_or_sell() -> None:
    # Directory review criteria: "Describe what the tool does, and don't tell
    # Claude how to behave"; descriptions must not "promote products and
    # services" (directory-submissions.md 4.6, row A3). Same check as the TS
    # sibling's test/api_alignment.test.ts.
    banned = [
        re.compile(r"\bUse (this|after|to|for|when)\b", re.I),
        re.compile(r"\bPrefer\b", re.I),
        re.compile(r"pretraining|from memory|your own definition|instead of relying", re.I),
        re.compile(r"\bpoll get_agent_job\b", re.I),
        re.compile(r"\blink (with|to) site_url\b", re.I),
        re.compile(r"teacher-vetted|pedagog", re.I),
        re.compile(r"before news outlets", re.I),
        re.compile(r"accumulation edge|pair trades|reversal", re.I),
        re.compile(r"Free to submit|paid to be featured|featured listing|Stripe", re.I),
        # Sending the model to another tool ("use get_job for one role").
        re.compile(r"\b(use|call|poll|try) [a-z]+_[a-z_]+\b", re.I),
        # Orders about the arguments: a description says what the tool takes.
        re.compile(r"(^|[.;:]\s+)(Provide|Pick|Choose)\b"),
    ]
    for t in TOOLS:
        for text in [t.description, *_schema_descriptions(t.input_schema)]:
            for pattern in banned:
                assert not pattern.search(text), f"{t.name}: {pattern.pattern} in {text!r}"
    # The tier stays named on every paid tool (52 free-tier tools, see above).
    assert "Pro tier" in _tool("get_token_holders").description
    assert "Team tier" in _tool("translate_contract").description
    assert "the free tier is enough" in _tool("submit_listing").description


def test_readme_carries_the_directory_notes() -> None:
    readme = (ROOT / "README.md").read_text("utf-8")
    # The official MCP Registry verifies PyPI ownership through this line.
    assert "<!-- mcp-name: io.github.blockchainacademics/mcp -->" in readme
    assert re.search(r"^## Not financial advice$", readme, re.M)
    assert re.search(r"^## Privacy$", readme, re.M)
    assert "about 150 entity dossiers" in readme
    assert not re.search(r"150\+ entit|canonical crypto MCP|ground-truth", readme, re.I)
    # langchain-mcp-adapters is archived; LangChain ships MCP as langchain.mcp.
    # The prose may name the old package, but no code imports it or links it.
    for path in ("README.md", "examples/langchain_agent.py"):
        text = (ROOT / path).read_text("utf-8")
        assert "langchain_mcp_adapters" not in text, path
        assert "github.com/langchain-ai/langchain-mcp-adapters" not in text, path
        assert "from langchain.mcp import MCPAdapter" in text, path
    # The elizaos-plugins/plugin-mcp repo answers 404; the npm page is the reference.
    eliza = (ROOT / "examples/eliza_plugin.md").read_text("utf-8")
    assert "github.com/elizaos-plugins/plugin-mcp" not in eliza
    assert "npmjs.com/package/@elizaos/plugin-mcp" in eliza


def test_list_topics_names_only_taxonomy_topics() -> None:
    desc = _tool("list_topics").description
    named = set(desc.split(":", 1)[1].split(". ", 1)[0].replace(" and ", ", ").replace(" ", "").split(","))
    assert named == TAXONOMY
    for outside in ("infra", "memecoins", "security"):
        assert outside not in desc


def test_get_explainer_counts_and_examples() -> None:
    tool = _tool("get_explainer")
    assert "38 lessons across 8 courses" in tool.description
    assert "43" not in tool.description and "9 courses" not in tool.description
    props = tool.input_schema["properties"]
    # Course slugs served by /v1/academy/{slug} (8 courses on 2026-10-31).
    assert "'defi-fundamentals'" in props["slug"]["description"]
    assert "'understanding-bitcoin'" in props["slug"]["description"]
    assert "what-is-a-blockchain" not in json.dumps(tool.input_schema)
    # Topic examples come from the taxonomy.
    topic_examples = set(re.findall(r"'([a-z0-9-]+)'", props["topic"]["description"]))
    assert topic_examples and topic_examples <= TAXONOMY
    assert "liquidity-pools" not in props["topic"]["description"]


def test_cli_error_text_escapes_markup_and_shows_detail() -> None:
    from bca_mcp.cli.runner import _error_text
    from bca_mcp.errors import BcaBadRequestError

    text = _error_text(BcaBadRequestError("BCA API rejected request: HTTP 404", detail="[bold]x[/bold]"))
    assert text == "BCA API rejected request: HTTP 404: \\[bold]x\\[/bold]"
