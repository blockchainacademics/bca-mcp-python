"""`get_explainer` tool — canonical academy lesson by slug xor topic."""

from __future__ import annotations

from typing import Any, Optional
from urllib.parse import quote

from pydantic import BaseModel, Field, model_validator

from bca_mcp.client import get_client
from bca_mcp.types import SLUG_REGEX, Explainer, ResponseEnvelope

TOOL_NAME = "get_explainer"

# Academy as served by the API on 2026-10-31: 8 courses, 38 lessons. The slug
# goes to /v1/academy/{slug}, which answers a course when one has that slug
# and otherwise the lesson (API slug such as 02-decentralized-exchanges-dexs
# or the website's slug such as decentralized-exchanges) with its body_md.
# Topic examples are slugs from list_topics. Counts and examples match the
# TS sibling.
TOOL_DESCRIPTION = (
    "Fetch BCA Academy material: 38 lessons across 8 courses covering crypto "
    "fundamentals, DeFi, trading, regulation and onchain security. Takes "
    "exactly one of slug or topic. A course slug returns the course and its "
    "lesson index; a lesson slug returns that lesson with its full text "
    "(body_md); an unknown slug returns the closest lesson as partial. A topic "
    "returns the courses tagged with it, or else the top matching lessons with "
    "their text. Applies to requests to explain a crypto concept, such as "
    "'explain liquidity pools' or 'what is DeFi'. Works without an API key."
)


class GetExplainerInput(BaseModel):
    model_config = {"extra": "forbid"}

    slug: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=240,
        pattern=SLUG_REGEX,
        description=(
            "Academy course slug (e.g. 'defi-fundamentals', "
            "'understanding-bitcoin') or lesson slug (e.g. "
            "'decentralized-exchanges')."
        ),
    )
    topic: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=240,
        pattern=SLUG_REGEX,
        description=(
            "Topic keyword that resolves to matching academy material "
            "(e.g. 'defi', 'bitcoin')."
        ),
    )

    @model_validator(mode="after")
    def _exactly_one(self) -> "GetExplainerInput":
        has_slug = bool(self.slug)
        has_topic = bool(self.topic)
        if has_slug == has_topic:
            raise ValueError("Provide exactly one of 'slug' or 'topic'.")
        return self


def input_json_schema() -> dict[str, Any]:
    return GetExplainerInput.model_json_schema()


async def run(args: dict[str, Any]) -> ResponseEnvelope[Explainer]:
    parsed = GetExplainerInput.model_validate(args)
    client = get_client()
    if parsed.slug:
        return await client.request(f"/v1/academy/{quote(parsed.slug, safe='')}")
    assert parsed.topic is not None
    return await client.request("/v1/academy", {"topic": parsed.topic})
