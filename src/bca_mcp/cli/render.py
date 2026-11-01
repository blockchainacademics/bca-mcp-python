"""Rich rendering helpers — tables, panels, markdown for CLI output."""

from __future__ import annotations

import json
from typing import Any, Iterable

from rich.console import Console
from rich.markdown import Markdown
from rich.markup import escape
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


_FENCE_HEAD = '<untrusted_content source="'
_FENCE_TAIL = "\n</untrusted_content>"


def plain(text: Any) -> str:
    """A field the MCP tools fenced as untrusted content, without the fence
    (the CLI prints for a person, not for a model)."""
    value = str(text)
    if value.startswith(_FENCE_HEAD) and value.endswith(_FENCE_TAIL):
        head_end = value.find(">\n")
        if head_end != -1:
            return value[head_end + 2 : -len(_FENCE_TAIL)]
    return value


def result_of(data: Any) -> Any:
    """The record a single-item route nests under ``result`` (entities,
    articles, academy), or ``data`` itself for flat payloads."""
    if isinstance(data, dict) and isinstance(data.get("result"), dict):
        return data["result"]
    return data


def status_note(envelope: Any) -> None:
    """Say so when the answer is not complete (unseeded, partial, stale)."""
    meta = envelope.get("meta") if isinstance(envelope, dict) else None
    if not isinstance(meta, dict):
        return
    status = meta.get("status")
    if not status or status == "complete":
        return
    diagnostic = meta.get("diagnostic")
    reason = diagnostic.get("reason") if isinstance(diagnostic, dict) else None
    text = f"status: {status}" + (f" ({reason})" if reason else "")
    console.print(f"[yellow]{escape(text)}[/yellow]")


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
        source = row.get("source_name") or row.get("source") or row.get("source_slug")
        link = (
            row.get("canonical_url")
            or row.get("source_url")
            or row.get("cite_url")
            or row.get("url")
        )
        table.add_row(
            str(row.get("published_at") or "-")[:10],
            escape(str(row.get("title") or "-")),
            escape(str(source or "-")),
            escape(str(link or "-")),
        )
    console.print(table)


def price_rows(data: Any, vs: str = "usd") -> list[dict[str, Any]]:
    """Rows for price_table from get_price's CoinGecko shape,
    ``{coin_id: {usd, usd_24h_change, usd_market_cap}}``."""
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    rows: list[dict[str, Any]] = []
    if isinstance(data, dict):
        for coin_id, quote in data.items():
            if not isinstance(quote, dict):
                continue
            rows.append({
                "ticker": coin_id,
                "price": quote.get(vs),
                "change_24h": quote.get(f"{vs}_24h_change"),
                "market_cap": quote.get(f"{vs}_market_cap"),
            })
    return rows


def price_table(rows: Iterable[dict[str, Any]]) -> None:
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Ticker")
    table.add_column("Price (USD)", justify="right")
    table.add_column("24h %", justify="right")
    table.add_column("Market cap", justify="right")
    for row in rows:
        ch = (
            row.get("change_24h_percent")
            or row.get("change_24h")
            or row.get("price_change_percentage_24h")
        )
        ch_str = f"{ch:+.2f}%" if isinstance(ch, (int, float)) else "-"
        color = "green" if isinstance(ch, (int, float)) and ch >= 0 else "red"
        mc = row.get("market_cap_usd") or row.get("market_cap")
        price_value = row.get("price_usd") or row.get("price") or row.get("current_price")
        table.add_row(
            escape(str(row.get("ticker") or row.get("symbol") or "-").upper()),
            f"${price_value if price_value is not None else '-'}",
            f"[{color}]{ch_str}[/{color}]",
            f"${mc:,.0f}" if isinstance(mc, (int, float)) else "-",
        )
    console.print(table)


def entity_panel(data: dict[str, Any]) -> None:
    title = data.get("display_name") or data.get("name") or data.get("slug") or "entity"
    kind = data.get("kind") or "-"
    body_lines: list[str] = [f"[bold]kind:[/bold] {escape(str(kind))}"]
    for key in ("ticker", "chain", "website", "twitter", "github", "mention_count"):
        val = data.get(key)
        if val:
            body_lines.append(f"[bold]{key}:[/bold] {escape(str(val))}")
    if data.get("summary"):
        body_lines.append("")
        body_lines.append(escape(plain(data["summary"])))
    console.print(
        Panel.fit(
            "\n".join(body_lines),
            title=f"[bold cyan]{escape(str(title))}[/bold cyan]",
            border_style="cyan",
        )
    )


def indicator_panel(name: str, entity: str, data: dict[str, Any]) -> None:
    value = data.get("value") if isinstance(data, dict) else data
    window = data.get("window") if isinstance(data, dict) else "-"
    console.print(
        Panel.fit(
            f"[bold]value:[/bold] {value}\n"
            f"[bold]window:[/bold] {window}",
            title=f"[bold magenta]{name}[/bold magenta] · {entity}",
            border_style="magenta",
        )
    )


def explainer_render(data: dict[str, Any]) -> None:
    """A lesson (body_md) or a course (summary and its lesson index)."""
    title = data.get("title") or data.get("slug") or "Explainer"
    console.print(f"[bold cyan]{escape(str(title))}[/bold cyan]\n")
    body = (
        data.get("body_md")
        or data.get("body")
        or data.get("content")
        or data.get("summary")
        or ""
    )
    console.print(Markdown(str(body)))
    lessons = data.get("lessons")
    if isinstance(lessons, list) and lessons:
        console.print("")
        for lesson in lessons:
            if isinstance(lesson, dict):
                name = lesson.get("title") or lesson.get("slug") or "-"
                console.print(f"  {lesson.get('ordinal', '-')}. {escape(str(name))}")


def markdown_render(text: str) -> None:
    console.print(Markdown(text))
