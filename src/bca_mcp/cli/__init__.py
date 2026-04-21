"""`bca` command-line interface — bundled with the bca-mcp package.

Human-facing counterpart to the MCP server. Talks to the same REST API
(`api.blockchainacademics.com`) via the same `BcaClient`. Distribution:
`pipx install bca-mcp` OR `pip install bca-mcp` exposes the `bca` binary
alongside the `bca-mcp` MCP server entry point.
"""

from bca_mcp.cli.main import app

__all__ = ["app"]
