"""LangChain integration via `langchain-mcp-adapters` (the official bridge).

This is the recommended way to expose BCA MCP tools to a LangChain /
LangGraph agent. The adapter converts the stdio tool surface into native
`StructuredTool` objects the agent can call like any LangChain tool.

Install:

    pip install bca-mcp langchain langchain-mcp-adapters langchain-openai

Run:

    BCA_API_KEY=... OPENAI_API_KEY=... python examples/langchain_agent.py

Docs: https://github.com/langchain-ai/langchain-mcp-adapters
"""

from __future__ import annotations

import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def _demo(query: str) -> None:
    try:
        from langchain_mcp_adapters.tools import load_mcp_tools  # type: ignore
    except ImportError:
        print(
            "langchain-mcp-adapters not installed — run:\n"
            "  pip install langchain-mcp-adapters\n",
            file=sys.stderr,
        )
        raise

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "bca_mcp"],
        env={**os.environ, "BCA_API_KEY": os.environ.get("BCA_API_KEY", "")},
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # One-line bridge: MCP stdio tools -> LangChain StructuredTool list
            tools = await load_mcp_tools(session)
            print(f"Loaded {len(tools)} BCA tools into LangChain:")
            for t in tools:
                print(f"  - {t.name}")

            # Find `search_news` and round-trip a single call.
            search_news = next(t for t in tools if t.name == "search_news")
            result = await search_news.ainvoke({"query": query, "limit": 3})
            print("\n--- search_news result ---")
            print(result)


def main() -> None:
    query = sys.argv[1] if len(sys.argv) > 1 else "ethereum roadmap"
    asyncio.run(_demo(query))


if __name__ == "__main__":
    main()
