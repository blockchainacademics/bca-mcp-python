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
    "Fetch one BCA article by slug: title, summary, full text (body_md), "
    "author, source, publish date, topics, tickers and entity slugs, with the "
    "article as its citation. This is the full text behind a search_news hit. "
    "An unknown slug is an error (HTTP 404). Works without an API key."
)

# Free-text article fields that carry third-party text. The API nests the
# article under `result` and names the body `body_md`; the flat keys are the
# older shape, still read.
_ARTICLE_TEXT_FIELDS = ("body_md", "body", "excerpt", "body_markdown", "summary")


class GetArticleInput(BaseModel):
    model_config = {"extra": "forbid"}

    slug: str = Field(
        min_length=1,
        max_length=240,
        pattern=SLUG_REGEX,
        description="Article slug from search_news (e.g. 'circle-ipo-pricing-2026-04').",
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
        for holder in (data.get("result"), data):
            if not isinstance(holder, dict):
                continue
            for key in _ARTICLE_TEXT_FIELDS:
                v = holder.get(key)
                if isinstance(v, str):
                    holder[key] = _wrap_untrusted("get_article", v)
    return res


# --- list_entity_mentions --------------------------------------------------

LIST_ENTITY_MENTIONS_TOOL_NAME = "list_entity_mentions"

LIST_ENTITY_MENTIONS_TOOL_DESCRIPTION = (
    "Timeline of BCA article mentions for an entity (slug or alias), newest "
    "first: article slug, title and source URL, publish date, sentiment score "
    "and bucket, mentions in the article and a context snippet. Page with "
    "offset. Shows how coverage of a chain, project, person or ticker changed "
    "over time. Answers unseeded when no public article mentions the entity "
    "yet; an unknown entity is an error (HTTP 404)."
)


class ListEntityMentionsInput(BaseModel):
    model_config = {"extra": "forbid"}

    slug: str = Field(
        min_length=1,
        max_length=240,
        pattern=SLUG_REGEX,
        description="Entity slug or alias (chain, project, person, ticker).",
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Max mentions (default 50, max 100).",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Mentions to skip, for paging (default 0). meta.pageInfo.hasNextPage says whether more exist.",
    )
    since: Optional[str] = Field(
        default=None,
        max_length=64,
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
        {"since": parsed.since, "limit": parsed.limit, "offset": parsed.offset},
    )
    # A-3: mention rows carry a snippet of third-party article text. Mirror
    # TS sibling (`content.ts:64-78`). The API lists the rows under
    # `results` with `context_snippet`; `mentions` and excerpt / snippet /
    # body are the older names, still read.
    data = res.get("data") if isinstance(res, dict) else None
    lists: list[Any] = []
    if isinstance(data, dict):
        lists = [data.get("results"), data.get("mentions")]
    elif isinstance(data, list):
        lists = [data]
    for mentions in lists:
        if not isinstance(mentions, list):
            continue
        for m in mentions:
            if isinstance(m, dict):
                for key in ("context_snippet", "excerpt", "snippet", "body"):
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
    "ethereum, solana, stablecoins, rwa and ai-agents. Each topic comes with "
    "its live article count and child topics, and its slug is a topic filter "
    "value for search_news."
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
    "Time-travel query: the article search as the corpus stood at a past "
    "date (only articles ingested on or before as_of). Free, and open "
    "without an API key. Useful for backtesting and audit trails. Answers "
    "unseeded when nothing matches."
)


class GetAsOfSnapshotInput(BaseModel):
    model_config = {"extra": "forbid"}

    as_of: str = Field(
        max_length=64,
        description="ISO 8601 timestamp: corpus state at this date.",
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
