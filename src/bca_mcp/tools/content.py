"""Content & corpus tools (category 1).

Wraps read-only `/v1/articles`, `/v1/topics`, `/v1/entities` endpoints.
Mirrors the subset of `src/tools/content.ts` that ships in the v0.1
Python scaffold — further corpus tools (`get_as_of_snapshot`, etc.)
land in v0.2.

Tool surface exported here:
  * ``get_article``           — full body + citations for a single article slug
  * ``list_entity_mentions``  — mention timeline for one entity
  * ``list_topics``           — topic taxonomy for filter discovery

Each tool is a self-contained module-level triple of
``<NAME>``, ``<DESCRIPTION>``, ``<input_schema>()``, and ``run_<name>()``
so ``server.py`` can wire them up uniformly.
"""

from __future__ import annotations

from typing import Any, Optional
from urllib.parse import quote

from pydantic import BaseModel, Field

from bca_mcp.client import get_client
from bca_mcp.types import ResponseEnvelope


# --- get_article -----------------------------------------------------------

GET_ARTICLE_TOOL_NAME = "get_article"

GET_ARTICLE_TOOL_DESCRIPTION = (
    "Fetch a single editorial crypto article by slug: full body, "
    "citations, entity graph, and attribution metadata. Required field: "
    "'slug'. Use after search_news when you need the full text of a "
    "specific result."
)


class GetArticleInput(BaseModel):
    model_config = {"extra": "forbid"}

    slug: str = Field(
        min_length=1,
        max_length=240,
        description="Article slug (e.g. 'circle-ipo-pricing-2026-04').",
    )


def get_article_input_schema() -> dict[str, Any]:
    return GetArticleInput.model_json_schema()


async def run_get_article(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetArticleInput.model_validate(args)
    return await get_client().request(
        f"/v1/articles/{quote(parsed.slug, safe='')}",
    )


# --- list_entity_mentions --------------------------------------------------

LIST_ENTITY_MENTIONS_TOOL_NAME = "list_entity_mentions"

LIST_ENTITY_MENTIONS_TOOL_DESCRIPTION = (
    "Timeline of editorial mentions for an entity — sentiment score, "
    "sentiment bucket, and article linkback per mention. Required field: "
    "'slug' (entity slug). Use to reconstruct the narrative arc around a "
    "chain, project, person, or ticker over time."
)


class ListEntityMentionsInput(BaseModel):
    model_config = {"extra": "forbid"}

    slug: str = Field(
        min_length=1,
        max_length=240,
        description="Entity slug (chain, project, person, ticker).",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=200,
        description="Max mentions (default 20, max 200).",
    )
    since: Optional[str] = Field(
        default=None,
        description="ISO 8601 lower bound for published_at.",
    )


def list_entity_mentions_input_schema() -> dict[str, Any]:
    return ListEntityMentionsInput.model_json_schema()


async def run_list_entity_mentions(
    args: dict[str, Any],
) -> ResponseEnvelope[Any]:
    parsed = ListEntityMentionsInput.model_validate(args)
    return await get_client().request(
        f"/v1/entities/{quote(parsed.slug, safe='')}/mentions",
        {"limit": parsed.limit, "since": parsed.since},
    )


# --- list_topics -----------------------------------------------------------

LIST_TOPICS_TOOL_NAME = "list_topics"

LIST_TOPICS_TOOL_DESCRIPTION = (
    "Browse the BCA topic taxonomy (regulation, defi, infra, memecoins, "
    "security, etc.). No required fields. Use to discover valid filter "
    "values for search_news."
)


class ListTopicsInput(BaseModel):
    model_config = {"extra": "forbid"}


def list_topics_input_schema() -> dict[str, Any]:
    return ListTopicsInput.model_json_schema()


async def run_list_topics(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    ListTopicsInput.model_validate(args)
    return await get_client().request("/v1/topics")
