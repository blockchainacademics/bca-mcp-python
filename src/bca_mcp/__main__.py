"""Entry point — `python -m bca_mcp` or `bca-mcp` runs the stdio server."""

from __future__ import annotations

import asyncio
import sys

from bca_mcp.server import run_stdio


def main() -> None:
    try:
        asyncio.run(run_stdio())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as err:  # noqa: BLE001
        # Fatal startup → stderr so the host sees it without corrupting stdio.
        sys.stderr.write(f"[bca-mcp] fatal: {err!r}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
