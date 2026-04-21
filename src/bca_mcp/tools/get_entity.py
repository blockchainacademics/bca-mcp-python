"""`get_entity` tool — canonical entity dossier by slug xor ticker."""

from __future__ import annotations

from typing import Any, Optional
from urllib.parse import quote

from pydantic import BaseModel, Field, model_validator

from bca_mcp.client import get_client
from bca_mcp.types import Entity, ResponseEnvelope

TOOL_NAME = "get_entity"

TOOL_DESCRIPTION = (
    "Fetch a canonical BCA entity dossier (chain, project, person, "
    "organization, or ticker) with cross-referenced articles, aliases, "
    "and sentiment. Required: exactly one of 'slug' or 'ticker'. Aliases "
    "('CZ' -> changpeng-zhao, 'Maker' -> makerdao) resolve automatically."
)


class GetEntityInput(BaseModel):
    model_config = {"extra": "forbid"}

    slug: Optional[str] = Field(
        default=None,
        min_length=1,
        description=(
            "Canonical entity slug (e.g. 'vitalik-buterin', 'ethereum', 'circle')."
        ),
    )
    ticker: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Ticker symbol (e.g. 'ETH', 'SOL'). Case-insensitive.",
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


async def run(args: dict[str, Any]) -> ResponseEnvelope[Entity]:
    parsed = GetEntityInput.model_validate(args)
    client = get_client()
    if parsed.slug:
        return await client.request(f"/v1/entities/{quote(parsed.slug, safe='')}")
    # ticker branch — uppercase as in TS
    assert parsed.ticker is not None
    return await client.request(
        "/v1/entities",
        {"ticker": parsed.ticker.upper()},
    )
