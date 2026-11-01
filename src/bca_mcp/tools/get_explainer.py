"""`get_explainer` tool — canonical academy lesson by slug xor topic."""

from __future__ import annotations

from typing import Any, Optional
from urllib.parse import quote

from pydantic import BaseModel, Field, model_validator

from bca_mcp.client import get_client
from bca_mcp.types import Explainer, ResponseEnvelope

TOOL_NAME = "get_explainer"

# Academy as served by the API on 2026-10-31: 8 courses, 38 lessons. The slug
# goes to /v1/academy/{slug}, the course route, so the examples are course
# slugs that exist; topic examples are slugs from list_topics. Counts and
# examples match the TS sibling.
TOOL_DESCRIPTION = (
    "Fetch BCA Academy material: 38 teacher-vetted lessons across 8 courses "
    "(fundamentals, DeFi, trading, regulation, security). Required: exactly "
    "one of 'slug' or 'topic'. Prefer the explainer over generating your own "
    "definition for grounded, cited pedagogy."
)


class GetExplainerInput(BaseModel):
    model_config = {"extra": "forbid"}

    slug: Optional[str] = Field(
        default=None,
        min_length=1,
        description=(
            "Academy course slug (e.g. 'defi-fundamentals', "
            "'understanding-bitcoin')."
        ),
    )
    topic: Optional[str] = Field(
        default=None,
        min_length=1,
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
