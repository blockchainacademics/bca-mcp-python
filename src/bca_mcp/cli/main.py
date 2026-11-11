"""`bca` CLI — human-facing counterpart to the MCP server.

Each subcommand reuses `bca_mcp.client.BcaClient` + existing tool wrappers,
so the CLI stays in lockstep with MCP tool behavior and envelope parsing.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote

import typer
from rich.markup import escape

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
    price_rows,
    price_table,
    result_of,
    status_note,
    unwrap,
)
from bca_mcp.cli.runner import err_console, handle_errors, run_async

app = typer.Typer(
    name="bca",
    help="Blockchain Academics CLI: crypto intelligence for terminals + scripts.",
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
    from bca_mcp.client import _format_allowlist_error, _is_allowed_base

    cfg = read_config()
    if api_key is None:
        api_key = typer.prompt("BCA API key", hide_input=True)
    if not api_key.strip():
        err_console.print("[red]Empty key; aborting.[/red]")
        raise typer.Exit(code=1)
    cfg["api_key"] = api_key.strip()
    if api_base:
        cleaned = api_base.strip().rstrip("/")
        # Refuse to persist a base URL BcaClient would refuse: the same
        # allowlist, so a saved value never breaks every later command.
        if not _is_allowed_base(cleaned):
            err_console.print(f"[red]{escape(_format_allowlist_error(cleaned))}[/red]")
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

    args: dict[str, Any] = {"query": query, "limit": limit}
    # Slug filters are lower case kebab; accept any case here.
    if entity:
        args["entity"] = entity.strip().lower()
    if topic:
        args["topic"] = topic.strip().lower()
    if since:
        args["since"] = since
    res = await search_news.run(args)
    if json_out:
        as_json(res)
        return
    data = unwrap(res)
    articles: Any = []
    if isinstance(data, dict):
        # `results` since 2026; `articles` was the earlier name.
        articles = data.get("results") or data.get("articles") or []
    elif isinstance(data, list):
        articles = data
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

    # Slugs are lower case kebab ('ethereum', 'cz'); accept any case here.
    res = await get_entity.run({"slug": slug.strip().lower()})
    if json_out:
        as_json(res)
        return
    data = result_of(unwrap(res))
    if isinstance(data, dict):
        entity_panel(data)
    else:
        console.print(str(data))
    status_note(res)
    cite_footer(res)


# ---------- market ----------


@app.command("price")
@handle_errors
@run_async
async def price(
    ids: str = typer.Argument(
        ...,
        help="Comma-separated CoinGecko ids (not tickers), e.g. bitcoin,ethereum,solana",
    ),
    vs: str = typer.Option("usd", "--vs", help="Quote currency."),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Spot price, 24h change and market cap for one or more coins."""
    apply_env_defaults()
    from bca_mcp.tools import market

    id_list = [t.strip().lower() for t in ids.split(",") if t.strip()]
    if not id_list:
        err_console.print("[red]No CoinGecko ids provided.[/red]")
        raise typer.Exit(code=1)
    res = await market.run_get_price({"ids": ",".join(id_list), "vs": vs.strip().lower()})
    if json_out:
        as_json(res)
        return
    rows = price_rows(unwrap(res), vs.lower())
    if not rows:
        console.print("[yellow]No price data.[/yellow]")
        return
    price_table(rows)
    cite_footer(res)


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
    slug: str = typer.Argument(
        ..., help="Academy course or lesson slug (e.g. defi-fundamentals)."
    ),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Render an academy course or lesson as markdown."""
    apply_env_defaults()
    from bca_mcp.tools import get_explainer

    res = await get_explainer.run({"slug": slug.strip().lower()})
    if json_out:
        as_json(res)
        return
    data = result_of(unwrap(res))
    if isinstance(data, dict):
        explainer_render(data)
    else:
        console.print(str(data))
    status_note(res)
    cite_footer(res)


# ---------- indicators ----------

# CLI indicator names (both the MCP tool's words and the API's path work)
# -> (tool module runner name, takes a window).
_INDICATORS: dict[str, tuple[str, bool]] = {
    "coverage-index": ("run_get_coverage_index", True),
    "coverage": ("run_get_coverage_index", True),
    "narrative-strength": ("run_get_narrative_strength", True),
    "narrative": ("run_get_narrative_strength", True),
    "sentiment-velocity": ("run_get_sentiment_velocity", True),
    "editorial-premium": ("run_get_editorial_premium", True),
    "kol-influence": ("run_get_kol_influence", True),
    "risk-score": ("run_get_risk_score", False),
    "risk": ("run_get_risk_score", False),
}


@app.command()
@handle_errors
@run_async
async def indicator(
    name: str = typer.Argument(
        ...,
        help="coverage-index, narrative-strength, sentiment-velocity, "
        "editorial-premium, kol-influence or risk-score.",
    ),
    entity: str = typer.Argument(..., help="Entity slug."),
    window: str = typer.Option(
        "30d", "--window", "-w", help="7d | 30d | 90d (not used by risk-score)."
    ),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Read a proprietary indicator value."""
    apply_env_defaults()
    from bca_mcp.tools import indicators

    spec = _INDICATORS.get(name.strip().lower())
    if spec is None:
        err_console.print(
            f"[red]Unknown indicator {escape(name)!r}.[/red] Use one of: "
            + ", ".join(k for k in _INDICATORS if "-" in k)
        )
        raise typer.Exit(code=1)
    runner_name, takes_window = spec
    args: dict[str, Any] = {"entity_slug": entity.strip().lower()}
    if takes_window:
        args["window"] = window
    res = await getattr(indicators, runner_name)(args)
    if json_out:
        as_json(res)
        return
    data = unwrap(res)
    if isinstance(data, dict):
        indicator_panel(name, entity, data)
    else:
        console.print(str(data))
    status_note(res)
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
    entity: Optional[str] = typer.Option(
        None, "--entity", help="Entity slug (due-diligence, tokenomics-model)."
    ),
    url: Optional[str] = typer.Option(None, "--url", help="Whitepaper URL (summarize-whitepaper)."),
    code_file: Optional[Path] = typer.Option(
        None, "--code-file", help="Contract source file (translate-contract)."
    ),
    source: Optional[str] = typer.Option(
        None, "--source", help="Source language (translate-contract): solidity, vyper, move, rust-anchor."
    ),
    target: Optional[str] = typer.Option(None, "--target", help="Target language (translate-contract)."),
    keyword: Optional[str] = typer.Option(None, "--keyword", help="Keyword (monitor-keyword)."),
    webhook: Optional[str] = typer.Option(
        None, "--webhook", help="https webhook URL (monitor-keyword)."
    ),
    timeout_s: int = typer.Option(120, "--timeout", help="Polling timeout seconds."),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Kick off an async agent-backed skill job and poll until done."""
    apply_env_defaults()
    from bca_mcp.client import get_client
    from bca_mcp.tools import agent_jobs

    skill_key = skill.strip().lower().replace("_", "-")
    args: dict[str, Any] = {}
    if skill_key == "due-diligence":
        runner = agent_jobs.run_generate_due_diligence
        args["entity_slug"] = entity
    elif skill_key == "tokenomics-model":
        runner = agent_jobs.run_generate_tokenomics_model
        args["entity_slug"] = entity
    elif skill_key == "summarize-whitepaper":
        runner = agent_jobs.run_summarize_whitepaper
        args["url"] = url
    elif skill_key == "translate-contract":
        runner = agent_jobs.run_translate_contract
        if code_file is None:
            err_console.print("[red]translate-contract needs --code-file.[/red]")
            raise typer.Exit(code=1)
        try:
            args["code"] = code_file.read_text(encoding="utf-8")
        except OSError as exc:
            err_console.print(f"[red]Cannot read {escape(str(code_file))}:[/red] {escape(str(exc))}")
            raise typer.Exit(code=1)
        args["source_language"] = source
        args["target_language"] = target
    elif skill_key == "monitor-keyword":
        runner = agent_jobs.run_monitor_keyword
        args["keyword"] = keyword
        args["webhook_url"] = webhook
    else:
        err_console.print(
            f"[red]Unknown skill {escape(skill)!r}.[/red] Use due-diligence, "
            "tokenomics-model, summarize-whitepaper, translate-contract or monitor-keyword."
        )
        raise typer.Exit(code=1)

    # Missing options stay out, so the tool model names the required ones.
    res = await runner({k: v for k, v in args.items() if v is not None})
    data = unwrap(res)
    job_id = (data or {}).get("job_id") if isinstance(data, dict) else None
    if not job_id:
        err_console.print(
            "[red]No job_id returned.[/red] Raw response:"
        )
        as_json(res)
        raise typer.Exit(code=1)

    console.print(f"[cyan]Job[/cyan] {job_id} [dim]submitted, polling...[/dim]")
    status_note(res)
    client = get_client()
    start = time.monotonic()
    with console.status("[dim]Running skill...[/dim]", spinner="dots"):
        while time.monotonic() - start < timeout_s:
            poll = await client.request(f"/v1/agent-jobs/{quote(str(job_id), safe='')}")
            poll_data = unwrap(poll) or {}
            status = poll_data.get("status") if isinstance(poll_data, dict) else None
            if status in ("done", "completed", "success"):
                if json_out:
                    as_json(poll)
                    return
                # The API returns the skill output under `result`.
                output = None
                if isinstance(poll_data, dict):
                    output = poll_data.get("result") or poll_data.get("output")
                if isinstance(output, dict):
                    body = (
                        output.get("markdown")
                        or output.get("summary")
                        or output.get("body")
                        or output.get("target_code")
                    )
                    if isinstance(body, str) and body:
                        markdown_render(body)
                    else:
                        as_json(output)
                elif isinstance(output, str):
                    markdown_render(output)
                else:
                    as_json(poll)
                status_note(poll)
                cite_footer(poll)
                return
            if status in ("failed", "error"):
                err_console.print(
                    f"[red]Job {job_id} failed:[/red] "
                    f"{escape(str(poll_data.get('error') if isinstance(poll_data, dict) else status))}"
                )
                raise typer.Exit(code=1)
            await asyncio.sleep(2)
    err_console.print(f"[yellow]Timeout after {timeout_s}s.[/yellow] Job {job_id} still running.")
    raise typer.Exit(code=124)


if __name__ == "__main__":  # pragma: no cover
    app()
