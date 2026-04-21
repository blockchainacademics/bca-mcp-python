"""Async → sync bridge + uniform error handling for Typer commands."""

from __future__ import annotations

import asyncio
import functools
from typing import Any, Awaitable, Callable

import typer
from rich.console import Console

from bca_mcp.errors import BcaAuthError, BcaError

err_console = Console(stderr=True)


def run_async(
    coro_fn: Callable[..., Awaitable[Any]],
) -> Callable[..., Any]:
    """Wrap an async function so Typer can call it synchronously."""

    @functools.wraps(coro_fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return asyncio.run(coro_fn(*args, **kwargs))

    return wrapper


def handle_errors(
    fn: Callable[..., Any],
) -> Callable[..., Any]:
    """Catch BcaError → print red + exit 1. Missing key → actionable hint."""

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except BcaAuthError as exc:
            err_console.print(
                f"[yellow]Auth error:[/yellow] {exc}\n"
                "[dim]Run `bca login` to store your key, "
                "or export BCA_API_KEY.[/dim]"
            )
            raise typer.Exit(code=1)
        except BcaError as exc:
            err_console.print(f"[red]Error ({exc.code}):[/red] {exc}")
            raise typer.Exit(code=1)
        except KeyboardInterrupt:
            err_console.print("[dim]Interrupted.[/dim]")
            raise typer.Exit(code=130)

    return wrapper
