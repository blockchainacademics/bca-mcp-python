"""Typed shapes returned by the BCA API.

These intentionally mirror `src/types.ts` in the TypeScript sibling. We use
`TypedDict` (not pydantic) because the client deliberately passes upstream
JSON through without re-validating — the upstream contract is the source of
truth and we don't want to reject forward-compatible fields.
"""

from __future__ import annotations

from typing import Any, Generic, List, Optional, TypedDict, TypeVar

T = TypeVar("T")


class ResponseEnvelope(TypedDict, Generic[T], total=False):
    data: T
    cite_url: Optional[str]
    as_of: Optional[str]  # ISO 8601
    source_hash: Optional[str]
    meta: Optional[dict[str, Any]]


class Article(TypedDict, total=False):
    slug: str
    title: str
    summary: str
    published_at: str
    url: str
    entities: List[str]
    topics: List[str]
    author: str
    cite_url: str


class ArticleRef(TypedDict, total=False):
    slug: str
    title: str
    published_at: str
    url: str


class EntitySentiment(TypedDict, total=False):
    score: float
    sample_size: int


class Entity(TypedDict, total=False):
    slug: str
    name: str
    kind: str  # "chain" | "project" | "person" | "ticker" | "organization" | ...
    ticker: str
    aliases: List[str]
    summary: str
    articles: List[ArticleRef]
    sentiment: Optional[EntitySentiment]
    cite_url: str


class Explainer(TypedDict, total=False):
    slug: str
    course: str
    title: str
    summary: str
    body_markdown: str
    level: str  # "beginner" | "intermediate" | "advanced" | ...
    topics: List[str]
    url: str
    cite_url: str


class SearchNewsResult(TypedDict, total=False):
    articles: List[Article]
    total: int
