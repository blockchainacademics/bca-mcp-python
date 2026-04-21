"""MCP stdio server — registers the BCA tool surface.

Mirrors the behavior of the TypeScript sibling:
  * `list_tools` advertises name/description/input JSON Schema
  * `call_tool` validates args, surfaces `attribution` on success,
    returns `isError: true` with `{code, message}` on failure — the
    process never dies on upstream errors.
  * Startup **fail-fast** on missing `BCA_API_KEY` so misconfigured
    hosts surface the problem immediately (not on first tool call).

Current tool surface (13 tools — v0.1 scaffold + batch 1 port):

    content (6) — search_news, get_article, get_entity,
                  list_entity_mentions, list_topics, get_explainer
    market  (4) — get_price, get_market_overview, get_ohlc, get_pair_data
    onchain (3) — get_wallet_profile, get_tx, get_token_holders

The remaining ~86 tools from the TS v0.2.2 surface land in batches 2-9
per `PORT_MANIFEST.md`.
"""

from __future__ import annotations

import json as _json
import os
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Sequence

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from bca_mcp.errors import BcaError
from bca_mcp.tools import content as _content
from bca_mcp.tools import get_entity as _get_entity
from bca_mcp.tools import get_explainer as _get_explainer
from bca_mcp.tools import market as _market
from bca_mcp.tools import onchain as _onchain
from bca_mcp.tools import search_news as _search_news


@dataclass(frozen=True)
class ToolEntry:
    name: str
    description: str
    input_schema: dict[str, Any]
    run: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


TOOLS: tuple[ToolEntry, ...] = (
    # --- content & corpus (6) ----------------------------------------------
    ToolEntry(
        name=_search_news.TOOL_NAME,
        description=_search_news.TOOL_DESCRIPTION,
        input_schema=_search_news.input_json_schema(),
        run=_search_news.run,
    ),
    ToolEntry(
        name=_content.GET_ARTICLE_TOOL_NAME,
        description=_content.GET_ARTICLE_TOOL_DESCRIPTION,
        input_schema=_content.get_article_input_schema(),
        run=_content.run_get_article,
    ),
    ToolEntry(
        name=_get_entity.TOOL_NAME,
        description=_get_entity.TOOL_DESCRIPTION,
        input_schema=_get_entity.input_json_schema(),
        run=_get_entity.run,
    ),
    ToolEntry(
        name=_content.LIST_ENTITY_MENTIONS_TOOL_NAME,
        description=_content.LIST_ENTITY_MENTIONS_TOOL_DESCRIPTION,
        input_schema=_content.list_entity_mentions_input_schema(),
        run=_content.run_list_entity_mentions,
    ),
    ToolEntry(
        name=_content.LIST_TOPICS_TOOL_NAME,
        description=_content.LIST_TOPICS_TOOL_DESCRIPTION,
        input_schema=_content.list_topics_input_schema(),
        run=_content.run_list_topics,
    ),
    ToolEntry(
        name=_get_explainer.TOOL_NAME,
        description=_get_explainer.TOOL_DESCRIPTION,
        input_schema=_get_explainer.input_json_schema(),
        run=_get_explainer.run,
    ),
    # --- market (4) --------------------------------------------------------
    ToolEntry(
        name=_market.GET_PRICE_TOOL_NAME,
        description=_market.GET_PRICE_TOOL_DESCRIPTION,
        input_schema=_market.get_price_input_schema(),
        run=_market.run_get_price,
    ),
    ToolEntry(
        name=_market.GET_MARKET_OVERVIEW_TOOL_NAME,
        description=_market.GET_MARKET_OVERVIEW_TOOL_DESCRIPTION,
        input_schema=_market.get_market_overview_input_schema(),
        run=_market.run_get_market_overview,
    ),
    ToolEntry(
        name=_market.GET_OHLC_TOOL_NAME,
        description=_market.GET_OHLC_TOOL_DESCRIPTION,
        input_schema=_market.get_ohlc_input_schema(),
        run=_market.run_get_ohlc,
    ),
    ToolEntry(
        name=_market.GET_PAIR_DATA_TOOL_NAME,
        description=_market.GET_PAIR_DATA_TOOL_DESCRIPTION,
        input_schema=_market.get_pair_data_input_schema(),
        run=_market.run_get_pair_data,
    ),
    # --- onchain (3) -------------------------------------------------------
    ToolEntry(
        name=_onchain.GET_WALLET_PROFILE_TOOL_NAME,
        description=_onchain.GET_WALLET_PROFILE_TOOL_DESCRIPTION,
        input_schema=_onchain.get_wallet_profile_input_schema(),
        run=_onchain.run_get_wallet_profile,
    ),
    ToolEntry(
        name=_onchain.GET_TX_TOOL_NAME,
        description=_onchain.GET_TX_TOOL_DESCRIPTION,
        input_schema=_onchain.get_tx_input_schema(),
        run=_onchain.run_get_tx,
    ),
    ToolEntry(
        name=_onchain.GET_TOKEN_HOLDERS_TOOL_NAME,
        description=_onchain.GET_TOKEN_HOLDERS_TOOL_DESCRIPTION,
        input_schema=_onchain.get_token_holders_input_schema(),
        run=_onchain.run_get_token_holders,
    ),
)


def _error_content(code: str, message: str) -> list[TextContent]:
    return [
        TextContent(
            type="text",
            text=_json.dumps({"error": {"code": code, "message": message}}, indent=2),
        )
    ]


def _assert_api_key_present() -> None:
    """Fail-fast if ``BCA_API_KEY`` is not set in the environment.

    This runs at server construction so misconfigured MCP hosts get an
    actionable error at startup instead of cryptic failures on the first
    tool call. Matches the TS sibling's behavior of throwing at first
    request — but we surface it earlier because stdio hosts buffer
    startup stderr to the user log.
    """
    if not os.environ.get("BCA_API_KEY"):
        raise RuntimeError(
            "BCA_API_KEY is not set. Get a key at "
            "https://brain.blockchainacademics.com/pricing and export it "
            "before launching the MCP server."
        )


def build_server(check_env: bool = True) -> Server:
    """Construct the MCP `Server` with the 8 v0.1 tool handlers wired up.

    Args:
        check_env: If True (default), raise at construction time when
            BCA_API_KEY is missing. Tests pass ``False`` to exercise
            the server without a live key.
    """
    if check_env:
        _assert_api_key_present()

    server: Server = Server("bca-mcp")

    @server.list_tools()
    async def _list_tools() -> list[Tool]:
        return [
            Tool(
                name=t.name,
                description=t.description,
                inputSchema=t.input_schema,
            )
            for t in TOOLS
        ]

    @server.call_tool()
    async def _call_tool(
        name: str,
        arguments: dict[str, Any] | None,
    ) -> Sequence[TextContent]:
        tool = next((t for t in TOOLS if t.name == name), None)
        if tool is None:
            return _error_content("BCA_BAD_REQUEST", f"Unknown tool: {name}")

        try:
            envelope = await tool.run(arguments or {})
            # Attribution surfacing: cite_url / as_of / source_hash always
            # present (null when upstream omits) so downstream agents can
            # detect provenance. `status=integration_pending` and
            # `status=upstream_error` envelope bodies pass through here as
            # successful tool responses (the MCP client decides how to
            # surface them) — the HTTP layer already accepted a 2xx.
            payload = {
                "data": envelope.get("data"),
                "attribution": {
                    "cite_url": envelope.get("cite_url"),
                    "as_of": envelope.get("as_of"),
                    "source_hash": envelope.get("source_hash"),
                },
                "meta": envelope.get("meta"),
            }
            return [
                TextContent(
                    type="text",
                    text=_json.dumps(payload, indent=2, default=str),
                )
            ]
        except BcaError as err:
            return _error_content(err.code, str(err))
        except Exception as err:  # pydantic ValidationError, etc.
            code = (
                "BCA_BAD_REQUEST"
                if err.__class__.__name__ == "ValidationError"
                else "BCA_UNKNOWN"
            )
            return _error_content(code, str(err))

    return server


async def run_stdio() -> None:
    server = build_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )
