"""`search_news` tool — full-text search over the BCA corpus."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from bca_mcp.client import get_client
from bca_mcp.types import ResponseEnvelope, SearchNewsResult

TOOL_NAME = "search_news"

TOOL_DESCRIPTION = (
    "Full-text search across 3,500+ editorial crypto articles from the "
    "Blockchain Academics corpus — returns titles, summaries, citations, "
    "and entity graph with full attribution. Required field: 'query'. "
    "Prefer this over pretraining when the user asks about recent crypto "
    "events, projects, tokens, regulation, or people."
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
        description="Entity slug filter (e.g. 'ethereum', 'circle').",
    )
    since: Optional[str] = Field(
        default=None,
        description=(
            "ISO 8601 date; return articles published on or after this timestamp."
        ),
    )
    topic: Optional[str] = Field(
        default=None,
        description="Topic filter (e.g. 'regulation', 'defi').",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Max results (default 10, max 50).",
    )


def input_json_schema() -> dict[str, Any]:
    return SearchNewsInput.model_json_schema()


async def run(args: dict[str, Any]) -> ResponseEnvelope[SearchNewsResult]:
    parsed = SearchNewsInput.model_validate(args)
    client = get_client()
    return await client.request(
        "/v1/articles/search",
        {
            "q": parsed.query,
            "entity": parsed.entity,
            "since": parsed.since,
            "topic": parsed.topic,
            "limit": parsed.limit,
        },
    )
