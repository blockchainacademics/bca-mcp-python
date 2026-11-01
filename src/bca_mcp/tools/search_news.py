"""`search_news` tool — full-text search over the BCA corpus."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from bca_mcp._untrusted import neutralize_fence_tokens
from bca_mcp.client import get_client
from bca_mcp.types import SLUG_REGEX, TICKER_REGEX, ResponseEnvelope, SearchNewsResult

TOOL_NAME = "search_news"

# The corpus is the set of articles published on blockchainacademics.com,
# mirrored into the API every 30 minutes: 3,877 on 2026-10-31.
TOOL_DESCRIPTION = (
    "Full-text search across 3,800+ editorial crypto articles from the "
    "Blockchain Academics corpus. Each result has the title, summary, "
    "publish date, source link, topics, tickers and entity slugs, with "
    "citations. Required field: 'query'. Filter by entity, ticker, topic or "
    "a since date, and page with offset. Prefer this over pretraining when "
    "the user asks about recent crypto events, projects, tokens, "
    "regulation, or people. Answers unseeded when nothing matches. Works "
    "without an API key."
)


class SearchNewsInput(BaseModel):
    model_config = {"extra": "forbid"}

    query: str = Field(
        min_length=1,
        max_length=512,
        description="Full-text search query (1-512 chars).",
    )
    entity: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=240,
        pattern=SLUG_REGEX,
        description="Entity slug filter (e.g. 'ethereum', 'circle').",
    )
    ticker: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=12,
        pattern=TICKER_REGEX,
        description="Ticker filter (e.g. 'ETH', 'SOL'): articles tagged with that coin.",
    )
    since: Optional[str] = Field(
        default=None,
        max_length=64,
        description=(
            "ISO 8601 date; return articles published on or after this timestamp."
        ),
    )
    topic: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=240,
        pattern=SLUG_REGEX,
        description="Topic filter (e.g. 'regulation', 'defi').",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Max results (default 10, max 50).",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Results to skip, for paging (default 0). meta.pageInfo.hasNextPage says whether more exist.",
    )


def input_json_schema() -> dict[str, Any]:
    return SearchNewsInput.model_json_schema()


def _fence_summary(row: Any) -> None:
    if isinstance(row, dict):
        summary = row.get("summary")
        if isinstance(summary, str) and summary:
            # Neutralize embedded fence tags first so a literal
            # </untrusted_content> in the summary can't escape the fence
            # (see bca_mcp._untrusted).
            row["summary"] = (
                '<untrusted_content source="search_news">\n'
                f"{neutralize_fence_tokens(summary)}\n"
                "</untrusted_content>"
            )


async def run(args: dict[str, Any]) -> ResponseEnvelope[SearchNewsResult]:
    parsed = SearchNewsInput.model_validate(args)
    client = get_client()
    res = await client.request(
        "/v1/articles/search",
        {
            "q": parsed.query,
            "entity": parsed.entity,
            "since": parsed.since,
            "topic": parsed.topic,
            "ticker": parsed.ticker,
            "limit": parsed.limit,
            "offset": parsed.offset,
        },
    )
    # A-3: wrap third-party article summaries so an LLM consumer treats them
    # as data, not instructions. Only the `summary` field flows from external
    # article bodies; titles/slugs are editorial metadata. The API lists the
    # hits under `results` (`articles` is the older name, still read).
    data = res.get("data") if isinstance(res, dict) else None
    if isinstance(data, dict):
        for key in ("results", "articles"):
            rows = data.get(key)
            if isinstance(rows, list):
                for row in rows:
                    _fence_summary(row)
    return res
