"""Rich rendering helpers — tables, panels, markdown for CLI output."""

from __future__ import annotations

import json
from typing import Any, Iterable

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

console = Console()


def as_json(payload: Any) -> None:
    """Dump response verbatim (including envelope)."""
    console.print_json(json.dumps(payload, default=str))


def unwrap(envelope: dict[str, Any]) -> Any:
    """Return envelope['data'] for rendering, falling back to envelope itself."""
    if isinstance(envelope, dict) and "data" in envelope:
        return envelope["data"]
    return envelope


def cite_footer(envelope: dict[str, Any]) -> None:
    """Render provenance footer from the canonical envelope.

    Reads from `attribution.citations[0]` (v0.3.0 canonical shape) and
    falls back to the legacy flat `cite_url`/`as_of` keys for
    forward/backward compatibility during the rollout window.
    """
    cite: Any = None
    as_of: Any = None

    if isinstance(envelope, dict):
        attribution = envelope.get("attribution")
        if isinstance(attribution, dict):
            citations = attribution.get("citations")
            if isinstance(citations, list) and citations:
                first = citations[0]
                if isinstance(first, dict):
                    cite = first.get("cite_url")
                    as_of = first.get("as_of")
        # Legacy fallbacks (pre-v0.3.0 flat shape).
        if cite is None:
            cite = envelope.get("cite_url")
        if as_of is None:
            as_of = envelope.get("as_of")

    if cite or as_of:
        bits: list[str] = []
        if cite:
            bits.append(f"[link={cite}]{cite}[/link]")
        if as_of:
            bits.append(f"as_of={as_of}")
        console.print(f"[dim]{' · '.join(bits)}[/dim]")


def news_table(rows: Iterable[dict[str, Any]]) -> None:
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Published")
    table.add_column("Title")
    table.add_column("Source")
    table.add_column("Cite")
    for row in rows:
        table.add_row(
            str(row.get("published_at") or "—")[:10],
            str(row.get("title") or "—"),
            str(row.get("source") or row.get("source_slug") or "—"),
            str(row.get("cite_url") or row.get("url") or "—"),
        )
    console.print(table)


def price_table(rows: Iterable[dict[str, Any]]) -> None:
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Ticker")
    table.add_column("Price (USD)", justify="right")
    table.add_column("24h %", justify="right")
    table.add_column("Market cap", justify="right")
    for row in rows:
        ch = row.get("change_24h_percent") or row.get("change_24h")
        ch_str = f"{ch:+.2f}%" if isinstance(ch, (int, float)) else "—"
        color = "green" if isinstance(ch, (int, float)) and ch >= 0 else "red"
        mc = row.get("market_cap_usd") or row.get("market_cap")
        table.add_row(
            str(row.get("ticker") or row.get("symbol") or "—").upper(),
            f"${row.get('price_usd') or row.get('price') or '—'}",
            f"[{color}]{ch_str}[/{color}]",
            f"${mc:,.0f}" if isinstance(mc, (int, float)) else "—",
        )
    console.print(table)


def entity_panel(data: dict[str, Any]) -> None:
    title = data.get("name") or data.get("slug") or "entity"
    kind = data.get("kind") or "—"
    body_lines: list[str] = [f"[bold]kind:[/bold] {kind}"]
    for key in ("ticker", "chain", "website", "twitter", "github"):
        val = data.get(key)
        if val:
            body_lines.append(f"[bold]{key}:[/bold] {val}")
    if data.get("summary"):
        body_lines.append("")
        body_lines.append(str(data["summary"]))
    console.print(
        Panel.fit(
            "\n".join(body_lines),
            title=f"[bold cyan]{title}[/bold cyan]",
            border_style="cyan",
        )
    )


def indicator_panel(name: str, entity: str, data: dict[str, Any]) -> None:
    value = data.get("value") if isinstance(data, dict) else data
    window = data.get("window") if isinstance(data, dict) else "—"
    console.print(
        Panel.fit(
            f"[bold]value:[/bold] {value}\n"
            f"[bold]window:[/bold] {window}",
            title=f"[bold magenta]{name}[/bold magenta] · {entity}",
            border_style="magenta",
        )
    )


def explainer_render(data: dict[str, Any]) -> None:
    title = data.get("title") or data.get("slug") or "Explainer"
    console.print(f"[bold cyan]{title}[/bold cyan]\n")
    body = data.get("body") or data.get("content") or data.get("summary") or ""
    console.print(Markdown(str(body)))


def markdown_render(text: str) -> None:
    console.print(Markdown(text))
