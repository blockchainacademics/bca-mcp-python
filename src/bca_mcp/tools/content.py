"""Content & corpus tools (category 1).

Wraps read-only `/v1/articles`, `/v1/topics`, `/v1/entities` endpoints.
Mirrors `src/tools/content.ts` (``search_news``, ``get_entity`` and
``get_explainer`` live in their own modules).

Tool surface exported here:
  * ``get_article``           full body + citations for a single article slug
  * ``list_entity_mentions``  mention timeline for one entity
  * ``list_topics``           topic taxonomy for filter discovery
  * ``get_as_of_snapshot``    corpus search as of a past date

Each tool is a self-contained module-level triple of
``<NAME>``, ``<DESCRIPTION>``, ``<input_schema>()``, and ``run_<name>()``
so ``server.py`` can wire them up uniformly.
"""

from __future__ import annotations

from typing import Any, Optional
from urllib.parse import quote

from pydantic import BaseModel, Field

from bca_mcp._untrusted import neutralize_fence_tokens
from bca_mcp.client import get_client
from bca_mcp.types import SLUG_REGEX, ResponseEnvelope


def _wrap_untrusted(source: str, value: Any) -> Any:
    """Fence a free-text field that originated from a third-party article so
    downstream LLM consumers treat it as data, not instructions. Mirrors
    `wrapUntrusted()` in `src/tools/content.ts`.

    Any fence tag embedded in ``value`` is neutralized first so a literal
    ``</untrusted_content>`` in the upstream text cannot close the fence early.
    """
    if not isinstance(value, str) or not value:
        return value
    return (
        f'<untrusted_content source="{source}">\n'
        f"{neutralize_fence_tokens(value)}\n"
        "</untrusted_content>"
    )


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
    res = await get_client().request(
        f"/v1/articles/{quote(parsed.slug, safe='')}",
    )
    # A-3: wrap third-party article body/excerpt fields before the LLM
    # consumes them. Mirrors TS sibling (`content.ts:34-43`).
    data = res.get("data") if isinstance(res, dict) else None
    if isinstance(data, dict):
        for key in ("body", "excerpt", "body_markdown", "summary"):
            v = data.get(key)
            if isinstance(v, str):
                data[key] = _wrap_untrusted("get_article", v)
    return res


# --- list_entity_mentions --------------------------------------------------

LIST_ENTITY_MENTIONS_TOOL_NAME = "list_entity_mentions"

LIST_ENTITY_MENTIONS_TOOL_DESCRIPTION = (
    "Timeline of editorial mentions for an entity: sentiment score, "
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
        default=50,
        ge=1,
        le=200,
        description="Max mentions (default 50, max 200).",
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
    res = await get_client().request(
        f"/v1/entities/{quote(parsed.slug, safe='')}/mentions",
        {"limit": parsed.limit, "since": parsed.since},
    )
    # A-3: mention rows may surface third-party excerpts. Mirror TS sibling
    # (`content.ts:64-78`).
    data = res.get("data") if isinstance(res, dict) else None
    mentions: Any
    if isinstance(data, dict):
        mentions = data.get("mentions", data)
    else:
        mentions = data
    if isinstance(mentions, list):
        for m in mentions:
            if isinstance(m, dict):
                for key in ("excerpt", "snippet", "body"):
                    v = m.get(key)
                    if isinstance(v, str):
                        m[key] = _wrap_untrusted("list_entity_mentions", v)
    return res


# --- list_topics -----------------------------------------------------------

LIST_TOPICS_TOOL_NAME = "list_topics"

# The ten topics of the API's taxonomy (topic_taxonomy, seeded by
# scripts/seed_canonical_slugs.py in the API repo). Same list as the TS sibling.
LIST_TOPICS_TOOL_DESCRIPTION = (
    "Browse the BCA topic taxonomy: regulation, defi, nft, layer-2, bitcoin, "
    "ethereum, solana, stablecoins, rwa and ai-agents. No required fields. "
    "Use to discover valid filter values for search_news."
)


class ListTopicsInput(BaseModel):
    model_config = {"extra": "forbid"}


def list_topics_input_schema() -> dict[str, Any]:
    return ListTopicsInput.model_json_schema()


async def run_list_topics(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    ListTopicsInput.model_validate(args)
    return await get_client().request("/v1/topics")


# --- get_as_of_snapshot ----------------------------------------------------
# Port of `getAsOfSnapshot` in the TS sibling's src/tools/content.ts: the
# article search, pinned to the corpus as it stood at `as_of`.

GET_AS_OF_SNAPSHOT_TOOL_NAME = "get_as_of_snapshot"

GET_AS_OF_SNAPSHOT_TOOL_DESCRIPTION = (
    "Time-travel query: return the corpus state as it existed at a specific "
    "historical date. Enterprise tier. Useful for backtesting and audit "
    "trails."
)


class GetAsOfSnapshotInput(BaseModel):
    model_config = {"extra": "forbid"}

    as_of: str = Field(
        max_length=64,
        description=(
            "ISO 8601 timestamp: corpus state at this date (Enterprise tier)."
        ),
    )
    query: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=512,
        description="Optional search query.",
    )
    entity: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=240,
        pattern=SLUG_REGEX,
        description="Optional entity slug filter.",
    )
    limit: int = Field(default=20, ge=1, le=50)


def get_as_of_snapshot_input_schema() -> dict[str, Any]:
    return GetAsOfSnapshotInput.model_json_schema()


async def run_get_as_of_snapshot(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetAsOfSnapshotInput.model_validate(args)
    return await get_client().request(
        "/v1/articles/search",
        {
            "as_of": parsed.as_of,
            "q": parsed.query,
            "entity": parsed.entity,
            "limit": parsed.limit,
        },
    )
