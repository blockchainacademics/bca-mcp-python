"""Typed shapes returned by the BCA API.

These intentionally mirror `src/types.ts` in the TypeScript sibling. We use
`TypedDict` (not pydantic) because the client deliberately passes upstream
JSON through without re-validating — the upstream contract is the source of
truth and we don't want to reject forward-compatible fields.

Canonical response envelope (locked 2026-04-22, v0.3.0):

    {
      "data": { ... },
      "attribution": {
        "citations": [
          { "cite_url": "...", "as_of": "...", "source_hash": "sha256:..." }
        ]
      },
      "meta": {
        "status": "complete" | "unseeded" | "partial" | "stale",
        "request_id": "req_...",
        "pageInfo": { "hasNextPage": bool, "hasPreviousPage": bool,
                      "startCursor": str|None, "endCursor": str|None },
        "diagnostic": { ... }   // optional
      }
    }

Rules:
  * `attribution.citations[]` is array-only — no singular shorthand.
  * `meta.status` enum: complete | unseeded | partial | stale. NO "error".
  * `meta.request_id` is always a string.
  * Rate-limit info lives in HTTP headers, not the body.
"""

from __future__ import annotations

from typing import Any, Dict, Generic, List, Literal, Optional, TypedDict, TypeVar

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
# ISO 3166 alpha-2 country code, any case: what the API's regulatory routes
# take (EL and UK are accepted there as GR and GB).
ISO2_COUNTRY_REGEX = r"^[A-Za-z]{2}$"

# Rolling-window enum shared across sentiment + indicator tools. Mirrors
# the zod `z.enum(["1d","7d","30d","90d"])` declaration used in
# `src/tools/sentiment.ts` + `src/tools/indicators.ts`.
Window = Literal["1d", "7d", "30d", "90d"]

# Windows of the tweet-derived routes (/v1/trending, /v1/social-signals):
# the API answers 400 for anything else.
SocialWindow = Literal["1h", "6h", "24h", "7d"]


# --- canonical envelope shapes --------------------------------------------

# Envelope status enum. NOTE: "error" is NOT a valid status — upstream
# errors surface through the transport layer (HTTP status, BcaError raises)
# and never as a successful-looking body.
Status = Literal["complete", "unseeded", "partial", "stale"]

# Back-compat alias — older tool modules imported `EnvelopeStatus`. Keep
# the alias so the import surface stays stable, but point at the new
# canonical enum.
EnvelopeStatus = Status


class Citation(TypedDict, total=False):
    """Single provenance record. All fields optional individually but at
    least one citation should be emitted when the backend has provenance
    data available."""

    cite_url: Optional[str]
    as_of: Optional[str]  # ISO 8601
    source_hash: Optional[str]  # typically "sha256:<hex>"


class PageInfo(TypedDict):
    """Relay-style cursor pagination descriptor. Always present on the
    wire — non-paginated payloads emit the zero-pagination default
    (no-next, no-prev, null cursors)."""

    hasNextPage: bool
    hasPreviousPage: bool
    startCursor: Optional[str]
    endCursor: Optional[str]


class EnvelopeMeta(TypedDict, total=False):
    """Canonical meta block. `status`, `request_id`, and `pageInfo` are
    always present; `diagnostic` is an optional free-form bag the backend
    uses for observability (trace IDs, timing, upstream codes).

    `tier` and `upgrade_url` were added 2026-06-02 with the public demo-tier
    launch. Backend-emitted on every authenticated response. Demo callers
    always get `upgrade_url`; free callers get it above ~80% of daily cap.
    """

    status: Status
    request_id: str
    pageInfo: PageInfo
    diagnostic: Dict[str, Any]  # optional
    tier: str  # demo | free | starter | pro | team | enterprise
    upgrade_url: str  # present on demo + near-cap free


class Attribution(TypedDict):
    """Provenance block — always array-shaped. Use `citations: []` when
    there is no provenance rather than omitting the key."""

    citations: List[Citation]


class ResponseEnvelope(TypedDict, Generic[T], total=False):
    """Canonical JSON:API-inspired envelope. All three top-level keys
    (`data`, `attribution`, `meta`) are present on every response the
    REST API and MCP server now emit (locked 2026-04-22)."""

    data: T
    attribution: Attribution
    meta: EnvelopeMeta


def default_page_info() -> PageInfo:
    """Canonical zero-pagination default for non-paginated payloads."""

    return {
        "hasNextPage": False,
        "hasPreviousPage": False,
        "startCursor": None,
        "endCursor": None,
    }


def resolve_envelope_status(
    data: Any, explicit: Optional[Status] = None
) -> Status:
    """Mirror of TS `resolveEnvelopeStatus`.

    Tool authors may set `status` explicitly; otherwise we auto-detect
    "unseeded" from empty payloads, falling back to "complete". The
    server's call_tool wrapper uses this to guarantee every wire
    response carries a status field.
    """
    if explicit:
        return explicit
    if data is None:
        return "unseeded"
    if isinstance(data, list) and len(data) == 0:
        return "unseeded"
    if isinstance(data, dict):
        if len(data) == 0:
            return "unseeded"
        for key in ("articles", "entities", "items", "results", "rows", "events"):
            v = data.get(key)
            if isinstance(v, list) and len(v) == 0:
                return "unseeded"
    return "complete"


class Article(TypedDict, total=False):
    """One article row of /v1/articles/search (``data.results[]``)."""

    slug: str
    title: str
    summary: Optional[str]
    author: Optional[str]
    source_name: Optional[str]
    source_url: Optional[str]
    canonical_url: Optional[str]
    published_at: Optional[str]
    topics: List[str]
    tickers: List[str]
    entities: List[str]
    sentiment_bucket: Optional[str]
    sentiment_score: Optional[float]


class ArticleRef(TypedDict, total=False):
    slug: str
    title: str
    published_at: str
    url: str


class EntitySentiment(TypedDict, total=False):
    score: float
    sample_size: int


class Entity(TypedDict, total=False):
    """One dossier as /v1/entities/{slug} serves it (under ``data.result``)."""

    slug: str
    kind: str  # "chain" | "project" | "person" | "ticker"
    display_name: str
    ticker: Optional[str]
    chain: Optional[str]
    website: Optional[str]
    twitter: Optional[str]
    summary: Optional[str]
    mention_count: Optional[int]
    first_seen_at: Optional[str]
    last_mentioned_at: Optional[str]
    derived_fields: List[str]
    resolved_from_alias: str  # only when the slug was an alias


class Explainer(TypedDict, total=False):
    """A course or a lesson from /v1/academy (under ``data.result``)."""

    slug: str
    course_slug: str
    title: str
    summary: str
    body_md: str  # lessons only
    level: str  # "beginner" | "intermediate" | "advanced" | ...
    topics: List[str]
    site_url: str
    result_type: str  # "lesson" when the slug named a lesson


class SearchNewsResult(TypedDict, total=False):
    query: Optional[str]
    count: int
    total: int
    limit: int
    offset: int
    results: List[Article]
