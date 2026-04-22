"""Blockchain Academics MCP server (Python).

Sibling of `@blockchainacademics/mcp` — same tool surface, same REST API,
same attribution contract.
"""

from bca_mcp.client import BcaClient, get_client, set_client
from bca_mcp.errors import (
    BcaAuthError,
    BcaBadRequestError,
    BcaError,
    BcaNetworkError,
    BcaRateLimitError,
    BcaUpstreamError,
)

__version__ = "0.3.1"

__all__ = [
    "__version__",
    "BcaClient",
    "get_client",
    "set_client",
    "BcaError",
    "BcaAuthError",
    "BcaBadRequestError",
    "BcaNetworkError",
    "BcaRateLimitError",
    "BcaUpstreamError",
]
