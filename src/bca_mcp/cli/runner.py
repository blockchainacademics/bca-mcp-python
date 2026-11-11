"""Async → sync bridge + uniform error handling for Typer commands."""

from __future__ import annotations

import asyncio
import functools
from typing import Any, Awaitable, Callable

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.markup import escape

from bca_mcp.errors import BcaAuthError, BcaError, format_validation_error

err_console = Console(stderr=True)


def _error_text(exc: BcaError) -> str:
    # Messages can carry API text (exc.detail); escape it so square brackets
    # in it are printed, not parsed as rich markup.
    text = str(exc)
    if exc.detail:
        text = f"{text}: {exc.detail}"
    return escape(text)


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
                f"[yellow]Auth error:[/yellow] {_error_text(exc)}\n"
                "[dim]Run `bca login` to store your key, "
                "or export BCA_API_KEY.[/dim]"
            )
            raise typer.Exit(code=1)
        except BcaError as exc:
            err_console.print(f"[red]Error ({exc.code}):[/red] {_error_text(exc)}")
            raise typer.Exit(code=1)
        except ValidationError as exc:
            # The commands validate through the MCP tool models, so a bad
            # argument is reported the way the tools report it.
            name = getattr(fn, "__name__", "command").replace("_", " ")
            err_console.print(
                f"[red]Error (BCA_BAD_REQUEST):[/red] "
                f"{escape(format_validation_error(name, exc))}"
            )
            raise typer.Exit(code=1)
        except ValueError as exc:
            # BcaClient refuses a BCA_API_BASE (env var or stored api_base)
            # outside its allowlist with a ValueError: one line, no traceback.
            err_console.print(f"[red]Error:[/red] {escape(str(exc))}")
            raise typer.Exit(code=1)
        except KeyboardInterrupt:
            err_console.print("[dim]Interrupted.[/dim]")
            raise typer.Exit(code=130)

    return wrapper
