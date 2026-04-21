"""Generic MCP research-agent demo (Python sibling of `research-agent.ts`).

Spawns `python -m bca_mcp` as a stdio subprocess, calls `search_news`, then
fans out to `get_entity` on the top article's first entity. Illustrates
the canonical tool-chaining loop.

Run (after installing the package):

    BCA_API_KEY=... python examples/generic_agent.py "stablecoin regulation"
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _extract_text(content: Any) -> str | None:
    """Pull the text payload out of the first TextContent block."""
    if not content:
        return None
    first = content[0] if isinstance(content, list) else content
    text = getattr(first, "text", None)
    if text is None and isinstance(first, dict):
        text = first.get("text")
    return text


async def main() -> None:
    query = sys.argv[1] if len(sys.argv) > 1 else "ethereum roadmap"

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "bca_mcp"],
        env={**os.environ, "BCA_API_KEY": os.environ.get("BCA_API_KEY", "")},
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            search = await session.call_tool(
                "search_news",
                {"query": query, "limit": 5},
            )
            print("--- search_news ---")
            print(search.content)

            text = _extract_text(search.content)
            if not text:
                return

            parsed = json.loads(text)
            articles = (parsed.get("data") or {}).get("articles") or []
            first_entity = None
            if articles:
                entities = articles[0].get("entities") or []
                if entities:
                    first_entity = entities[0]

            if first_entity:
                ent = await session.call_tool(
                    "get_entity",
                    {"slug": first_entity},
                )
                print(f"--- get_entity {first_entity} ---")
                print(ent.content)


if __name__ == "__main__":
    asyncio.run(main())
