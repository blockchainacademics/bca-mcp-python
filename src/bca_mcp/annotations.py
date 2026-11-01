"""MCP tool annotations for every tool, kept in one place.

Every tool advertises ``title`` and ``openWorldHint: true`` (each one calls
the BCA API, an external system). The eight tools in ``WRITE_TOOLS`` create
a record or start a job on the BCA side, so they carry
``readOnlyHint: false``, ``destructiveHint: false`` (nothing is deleted or
overwritten) and ``idempotentHint: false`` (calling twice creates two
records). Every other tool only reads, so it carries ``readOnlyHint: true``.

The map matches the TypeScript sibling (``@blockchainacademics/mcp``)
exactly. Add a new write tool here when it ships.
"""

from __future__ import annotations

from typing import Any

WRITE_TOOLS: frozenset[str] = frozenset(
    {
        "submit_listing",
        "book_kol_campaign",
        "request_custom_research",
        "monitor_keyword",
        "generate_due_diligence",
        "generate_tokenomics_model",
        "summarize_whitepaper",
        "translate_contract",
    }
)


def tool_title(name: str) -> str:
    """Tool name with underscores as spaces, first letter capitalized.

    ``get_price`` -> ``Get price``.
    """
    text = name.replace("_", " ")
    return text[:1].upper() + text[1:]


def tool_annotations(name: str) -> dict[str, Any]:
    """The MCP ``annotations`` object for tool ``name``."""
    if name in WRITE_TOOLS:
        return {
            "title": tool_title(name),
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    return {
        "title": tool_title(name),
        "readOnlyHint": True,
        "openWorldHint": True,
    }
