"""Typed shapes returned by the BCA API.

These intentionally mirror `src/types.ts` in the TypeScript sibling. We use
`TypedDict` (not pydantic) because the client deliberately passes upstream
JSON through without re-validating — the upstream contract is the source of
truth and we don't want to reject forward-compatible fields.
"""

from __future__ import annotations

from typing import Any, Generic, List, Literal, Optional, TypedDict, TypeVar

T = TypeVar("T")


# --- shared input primitives (factorable across tools) --------------------
#
# These mirror the zod primitives used repeatedly across TS tools so the
# Python ports can reuse them without re-defining regex/enum surface per
# module. Keep in sync with `src/schema.ts` + per-tool enums in
# `src/tools/*.ts`.

# Chain literals — onchain tool surface.
#   * `OnchainChain` covers EVM + Solana (used by wallet / tx).
#   * `EvmChain` is the EVM-only subset (used by token_holders).
OnchainChain = Literal[
    "ethereum", "solana", "arbitrum", "base", "optimism", "polygon", "bsc"
]
EvmChain = Literal[
    "ethereum", "arbitrum", "base", "optimism", "polygon", "bsc"
]

# Regex strings — shared between pydantic validators and any manual checks.
# These match the TS zod regexes verbatim (see `src/tools/onchain.ts`,
# `src/tools/market.ts`, `src/schema.ts`).
SLUG_REGEX = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
EVM_ADDRESS_REGEX = r"^0x[a-fA-F0-9]{40}$"
EVM_TX_HASH_REGEX = r"^0x[a-fA-F0-9]{64}$"
# Alphanumeric — used for EVM-or-Solana addresses/hashes where the tool
# accepts either family and backend re-validates per chain.
ALNUM_REGEX = r"^[A-Za-z0-9]+$"
# Ticker — 1..12 alphanumerics (mirror `src/schema.ts::tickerSchema`).
TICKER_REGEX = r"^[A-Za-z0-9]{1,12}$"

# Rolling-window enum shared across sentiment + indicator tools. Mirrors
# the zod `z.enum(["1d","7d","30d","90d"])` declaration used in
# `src/tools/sentiment.ts` + `src/tools/indicators.ts`.
Window = Literal["1d", "7d", "30d", "90d"]


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
