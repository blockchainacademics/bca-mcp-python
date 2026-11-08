"""LangChain integration through `langchain.mcp` (LangChain 1.4 and later).

`MCPAdapter` starts the bca-mcp stdio server and turns its tools into
LangChain tools that a LangChain or LangGraph agent can call. It replaces the
archived langchain-mcp-adapters package.

Install:

    pip install bca-mcp "langchain[mcp]>=1.4.0"

Run (BCA_API_KEY is optional: without it 17 tools work in demo mode):

    BCA_API_KEY=... python examples/langchain_agent.py

Hand the loaded tools to `langchain.agents.create_agent` with the chat model
of your choice.

Docs: https://docs.langchain.com/oss/python/migrate/langchain-mcp-adapters
"""

from __future__ import annotations

import asyncio
import os
import sys


async def _demo(query: str) -> None:
    try:
        from langchain.mcp import MCPAdapter
    except ImportError:
        print(
            "langchain.mcp is not installed. Run:\n"
            '  pip install "langchain[mcp]>=1.4.0"\n',
            file=sys.stderr,
        )
        raise

    config = {
        "mcpServers": {
            "bca": {
                "command": sys.executable,
                "args": ["-m", "bca_mcp"],
                "env": {**os.environ, "BCA_API_KEY": os.environ.get("BCA_API_KEY", "")},
            }
        }
    }

    async with MCPAdapter(config) as adapter:
        # MCP stdio tools -> LangChain tools, ready for create_agent.
        tools = await adapter.list_tools()
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
