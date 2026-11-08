"""`get_entity` tool — canonical entity dossier by slug xor ticker."""

from __future__ import annotations

from typing import Any, Optional
from urllib.parse import quote

from pydantic import BaseModel, Field, model_validator

from bca_mcp._untrusted import neutralize_fence_tokens
from bca_mcp.client import get_client
from bca_mcp.types import SLUG_REGEX, TICKER_REGEX, Entity, ResponseEnvelope

TOOL_NAME = "get_entity"

# The ticker form stays on /v1/entities?ticker=. The slug route resolves a
# slug and then entity_aliases (app/api/v1/entities.py _resolve_entity), and
# the alias table holds no tickers, so 'ETH' there finds only the bare ticker
# dossier and an unlisted symbol is a 404. The list route matches the ticker
# column, ticker dossiers and linked currencies, but it is not on the demo
# allowlist, so the ticker form needs an API key. Same as the TS sibling.
TOOL_DESCRIPTION = (
    "Fetch a BCA entity dossier (chain, project, person or ticker): name, "
    "kind, ticker, chain, website and X handle, summary when there is one, "
    "mention count and first and last mention dates. Takes exactly one of slug "
    "or ticker. Aliases in slug form resolve to the canonical entity ('cz' to "
    "changpeng-zhao, 'maker' to makerdao) and the answer names the alias in "
    "resolved_from_alias. The ticker form returns every entity that matches "
    "the ticker (the ticker dossier and the chain or project it maps to) and "
    "needs an API key; the slug form works without one. Many dossiers are "
    "still thin: meta.status partial, with meta.diagnostic.missing naming what "
    "is absent (summary, mentions). Applies to 'what is X' and 'who is X' "
    "questions, including names found by search_news."
)


class GetEntityInput(BaseModel):
    model_config = {"extra": "forbid"}

    slug: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=240,
        pattern=SLUG_REGEX,
        description=(
            "Entity slug or a known alias in slug form (e.g. 'vitalik-buterin', "
            "'ethereum', 'cz')."
        ),
    )
    ticker: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=12,
        pattern=TICKER_REGEX,
        description=(
            "Ticker symbol (e.g. 'ETH', 'SOL'), case-insensitive. Needs an API "
            "key: the demo key covers the slug form only."
        ),
    )

    @model_validator(mode="after")
    def _exactly_one(self) -> "GetEntityInput":
        has_slug = bool(self.slug)
        has_ticker = bool(self.ticker)
        if has_slug == has_ticker:
            raise ValueError("Provide exactly one of 'slug' or 'ticker'.")
        return self


def input_json_schema() -> dict[str, Any]:
    return GetEntityInput.model_json_schema()


def _fence_summary(holder: Any) -> None:
    """A-3: a dossier summary may carry third-party text ingested into the
    dossier, so it is fenced as untrusted content (as in the TS sibling)."""
    if isinstance(holder, dict):
        summary = holder.get("summary")
        if isinstance(summary, str) and summary:
            holder["summary"] = (
                '<untrusted_content source="get_entity">\n'
                f"{neutralize_fence_tokens(summary)}\n"
                "</untrusted_content>"
            )


async def run(args: dict[str, Any]) -> ResponseEnvelope[Entity]:
    parsed = GetEntityInput.model_validate(args)
    client = get_client()
    if parsed.slug:
        res = await client.request(f"/v1/entities/{quote(parsed.slug, safe='')}")
    else:
        # ticker branch — uppercase as in TS
        assert parsed.ticker is not None
        res = await client.request("/v1/entities", {"ticker": parsed.ticker.upper()})
    data = res.get("data") if isinstance(res, dict) else None
    if isinstance(data, dict):
        # The slug route nests the dossier under `result`; the ticker route
        # lists the matches under `results`; the flat shape is the older one.
        _fence_summary(data.get("result"))
        rows = data.get("results")
        if isinstance(rows, list):
            for row in rows:
                _fence_summary(row)
        _fence_summary(data)
    return res
