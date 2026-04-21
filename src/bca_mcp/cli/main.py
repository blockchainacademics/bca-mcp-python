"""`bca` CLI — human-facing counterpart to the MCP server.

Each subcommand reuses `bca_mcp.client.BcaClient` + existing tool wrappers,
so the CLI stays in lockstep with MCP tool behavior and envelope parsing.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

import typer

from bca_mcp.cli.config import (
    CONFIG_FILE,
    apply_env_defaults,
    mask_key,
    read_config,
    write_config,
)
from bca_mcp.cli.render import (
    as_json,
    cite_footer,
    console,
    entity_panel,
    explainer_render,
    indicator_panel,
    markdown_render,
    news_table,
    price_table,
    unwrap,
)
from bca_mcp.cli.runner import err_console, handle_errors, run_async

app = typer.Typer(
    name="bca",
    help="Blockchain Academics CLI — crypto intelligence for terminals + scripts.",
    no_args_is_help=True,
    add_completion=False,
)
config_app = typer.Typer(help="Config management.")
news_app = typer.Typer(help="News search + retrieval.")
market_app = typer.Typer(help="Market data (prices, overview).")
app.add_typer(config_app, name="config")
app.add_typer(news_app, name="news")
app.add_typer(market_app, name="market")


# ---------- core commands ----------


@app.command()
def login(
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        "-k",
        help="API key; if omitted, prompted interactively.",
    ),
    api_base: Optional[str] = typer.Option(
        None,
        "--api-base",
        help="Override API base URL (default https://api.blockchainacademics.com).",
    ),
) -> None:
    """Store your BCA API key in ~/.bca/config.toml (chmod 600)."""
    import os

    cfg = read_config()
    if api_key is None:
        api_key = typer.prompt("BCA API key", hide_input=True)
    if not api_key.strip():
        err_console.print("[red]Empty key; aborting.[/red]")
        raise typer.Exit(code=1)
    cfg["api_key"] = api_key.strip()
    if api_base:
        cleaned = api_base.strip().rstrip("/")
        # HIGH: refuse to persist a non-HTTPS base URL unless the operator
        # has explicitly opted in via BCA_ALLOW_INSECURE_BASE=1. Mirrors the
        # same gate inside BcaClient so CLI config and runtime agree.
        if (
            not cleaned.startswith("https://")
            and os.environ.get("BCA_ALLOW_INSECURE_BASE") != "1"
        ):
            err_console.print(
                f"[red]Refusing to save non-HTTPS api_base='{cleaned}'.[/red] "
                "Set BCA_ALLOW_INSECURE_BASE=1 to override for local dev."
            )
            raise typer.Exit(code=1)
        cfg["api_base"] = cleaned
    write_config(cfg)
    console.print(f"[green]Saved[/green] to [bold]{CONFIG_FILE}[/bold]")


@config_app.command("show")
def config_show() -> None:
    """Show config location and masked key."""
    cfg = read_config()
    console.print(f"[bold]Config file:[/bold] {CONFIG_FILE}")
    console.print(f"[bold]API key:[/bold]    {mask_key(cfg.get('api_key'))}")
    console.print(
        f"[bold]API base:[/bold]   "
        f"{cfg.get('api_base') or 'https://api.blockchainacademics.com (default)'}"
    )


@app.command()
@handle_errors
@run_async
async def version() -> None:
    """Show CLI version + live API version."""
    from bca_mcp import __version__

    console.print(f"[bold]bca-mcp[/bold] {__version__}")
    apply_env_defaults()
    from bca_mcp.client import BcaClient

    client = BcaClient()
    try:
        res = await client.request("/v1/status")
        data = unwrap(res)
        if isinstance(data, dict):
            api_ver = data.get("version") or data.get("commit") or "live"
            console.print(f"[bold]api:[/bold]     {api_ver}")
    except Exception as exc:  # noqa: BLE001
        console.print(f"[yellow]API unreachable:[/yellow] {exc}")


# ---------- news ----------


@news_app.command("search")
@handle_errors
@run_async
async def news_search(
    query: str = typer.Argument(..., help="Search query (1-512 chars)."),
    limit: int = typer.Option(10, "--limit", "-n", min=1, max=50),
    entity: Optional[str] = typer.Option(None, "--entity"),
    topic: Optional[str] = typer.Option(None, "--topic"),
    since: Optional[str] = typer.Option(None, "--since", help="ISO 8601."),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Full-text search across the BCA corpus."""
    apply_env_defaults()
    from bca_mcp.tools import search_news

    args = {"query": query, "limit": limit}
    if entity:
        args["entity"] = entity
    if topic:
        args["topic"] = topic
    if since:
        args["since"] = since
    res = await search_news.run(args)
    if json_out:
        as_json(res)
        return
    data = unwrap(res)
    articles = (
        data.get("articles") if isinstance(data, dict) else data
    ) or (data if isinstance(data, list) else [])
    if not articles:
        console.print("[yellow]No results.[/yellow]")
        return
    news_table(articles)
    cite_footer(res)


# ---------- entity ----------


@app.command()
@handle_errors
@run_async
async def entity(
    slug: str = typer.Argument(..., help="Entity slug (e.g. 'ethereum')."),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Entity dossier: chain, project, person, or ticker."""
    apply_env_defaults()
    from bca_mcp.tools import get_entity

    res = await get_entity.run({"slug": slug})
    if json_out:
        as_json(res)
        return
    data = unwrap(res)
    if isinstance(data, dict):
        entity_panel(data)
    else:
        console.print(str(data))
    cite_footer(res)


# ---------- market ----------


@app.command("price")
@handle_errors
@run_async
async def price(
    tickers: str = typer.Argument(..., help="Comma-separated tickers, e.g. BTC,ETH,SOL"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Spot price + 24h change for one or more tickers."""
    apply_env_defaults()
    from bca_mcp.tools import market

    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if not ticker_list:
        err_console.print("[red]No tickers provided.[/red]")
        raise typer.Exit(code=1)
    rows: list[dict[str, Any]] = []
    last_envelope: dict[str, Any] = {}
    for t in ticker_list:
        try:
            res = await market.run_get_price({"ticker": t})
        except AttributeError:
            # Fallback if tool module shape differs.
            from bca_mcp.client import get_client

            res = await get_client().request("/v1/prices", {"ticker": t})
        last_envelope = res if isinstance(res, dict) else {}
        data = unwrap(res)
        if isinstance(data, dict):
            data.setdefault("ticker", t)
            rows.append(data)
        elif isinstance(data, list):
            rows.extend(d for d in data if isinstance(d, dict))
    if json_out:
        as_json(rows)
        return
    if not rows:
        console.print("[yellow]No price data.[/yellow]")
        return
    price_table(rows)
    cite_footer(last_envelope)


@market_app.command("overview")
@handle_errors
@run_async
async def market_overview(
    limit: int = typer.Option(10, "--limit", "-n", min=1, max=50),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Top-N market overview by market cap."""
    apply_env_defaults()
    from bca_mcp.client import get_client

    res = await get_client().request("/v1/market/overview", {"limit": limit})
    if json_out:
        as_json(res)
        return
    data = unwrap(res)
    rows = (
        data.get("tokens") if isinstance(data, dict) else data
    ) or (data if isinstance(data, list) else [])
    if not rows:
        console.print("[yellow]No data.[/yellow]")
        return
    price_table(rows)
    cite_footer(res)


# ---------- explainer ----------


@app.command()
@handle_errors
@run_async
async def explainer(
    slug: str = typer.Argument(..., help="Academy lesson slug."),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Render an academy lesson as markdown."""
    apply_env_defaults()
    from bca_mcp.tools import get_explainer

    res = await get_explainer.run({"slug": slug})
    if json_out:
        as_json(res)
        return
    data = unwrap(res)
    if isinstance(data, dict):
        explainer_render(data)
    else:
        console.print(str(data))
    cite_footer(res)


# ---------- indicators ----------


@app.command()
@handle_errors
@run_async
async def indicator(
    name: str = typer.Argument(..., help="Indicator slug, e.g. coverage-index."),
    entity: str = typer.Argument(..., help="Entity slug."),
    window: str = typer.Option("30d", "--window", "-w", help="7d | 30d | 90d"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Read a proprietary indicator value."""
    apply_env_defaults()
    from bca_mcp.client import get_client

    res = await get_client().request(
        f"/v1/indicators/{name}",
        {"entity": entity, "window": window},
    )
    if json_out:
        as_json(res)
        return
    data = unwrap(res)
    if isinstance(data, dict):
        indicator_panel(name, entity, data)
    else:
        console.print(str(data))
    cite_footer(res)


# ---------- agent ----------


@app.command()
@handle_errors
@run_async
async def agent(
    skill: str = typer.Argument(
        ...,
        help="Skill slug: due-diligence, tokenomics-model, summarize-whitepaper, "
        "translate-contract, monitor-keyword.",
    ),
    entity: Optional[str] = typer.Option(None, "--entity"),
    url: Optional[str] = typer.Option(None, "--url"),
    source: Optional[str] = typer.Option(None, "--source"),
    target: Optional[str] = typer.Option(None, "--target"),
    keyword: Optional[str] = typer.Option(None, "--keyword"),
    timeout_s: int = typer.Option(120, "--timeout", help="Polling timeout seconds."),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Kick off an async agent-backed skill job and poll until done."""
    apply_env_defaults()
    from bca_mcp.client import get_client

    client = get_client()
    payload: dict[str, Any] = {}
    for k, v in (
        ("entity", entity),
        ("url", url),
        ("source_language", source),
        ("target_language", target),
        ("keyword", keyword),
    ):
        if v is not None:
            payload[k] = v

    res = await client.post(f"/v1/agent-jobs/{skill}/run", payload)
    data = unwrap(res)
    job_id = (data or {}).get("job_id") if isinstance(data, dict) else None
    if not job_id:
        err_console.print(
            "[red]No job_id returned.[/red] Raw response:"
        )
        as_json(res)
        raise typer.Exit(code=1)

    console.print(f"[cyan]Job[/cyan] {job_id} [dim]submitted — polling…[/dim]")
    start = time.monotonic()
    with console.status("[dim]Running skill…[/dim]", spinner="dots"):
        while time.monotonic() - start < timeout_s:
            poll = await client.request(f"/v1/agent-jobs/{job_id}")
            poll_data = unwrap(poll) or {}
            status = poll_data.get("status") if isinstance(poll_data, dict) else None
            if status in ("completed", "success", "done"):
                if json_out:
                    as_json(poll)
                    return
                output = poll_data.get("output") if isinstance(poll_data, dict) else None
                if isinstance(output, dict):
                    # Try common shapes: {markdown, summary, body}
                    body = (
                        output.get("markdown")
                        or output.get("summary")
                        or output.get("body")
                    )
                    if body:
                        markdown_render(str(body))
                    else:
                        as_json(output)
                elif isinstance(output, str):
                    markdown_render(output)
                else:
                    as_json(poll)
                cite_footer(poll)
                return
            if status in ("failed", "error"):
                err_console.print(
                    f"[red]Job {job_id} failed:[/red] "
                    f"{poll_data.get('error') if isinstance(poll_data, dict) else status}"
                )
                raise typer.Exit(code=1)
            await asyncio.sleep(2)
    err_console.print(f"[yellow]Timeout after {timeout_s}s.[/yellow] Job {job_id} still running.")
    raise typer.Exit(code=124)


if __name__ == "__main__":  # pragma: no cover
    app()
