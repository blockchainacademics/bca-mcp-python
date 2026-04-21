"""Structured error taxonomy — mirrors the TypeScript sibling exactly.

Error codes are the stable wire contract surfaced to MCP clients; do not
rename without bumping the major version.
"""

from __future__ import annotations

from typing import Literal, Optional

BcaErrorCode = Literal[
    "BCA_AUTH",
    "BCA_RATE_LIMIT",
    "BCA_UPSTREAM",
    "BCA_NETWORK",
    "BCA_BAD_REQUEST",
]


class BcaError(Exception):
    """Base class for all BCA MCP errors."""

    code: BcaErrorCode
    status: Optional[int]

    def __init__(
        self,
        code: BcaErrorCode,
        message: str,
        status: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


class BcaAuthError(BcaError):
    def __init__(self, message: str = "Invalid or missing BCA_API_KEY") -> None:
        super().__init__("BCA_AUTH", message, 401)


class BcaRateLimitError(BcaError):
    retry_after: Optional[int]

    def __init__(self, retry_after: Optional[int] = None) -> None:
        suffix = f", retry after {retry_after}s" if retry_after else ""
        super().__init__(
            "BCA_RATE_LIMIT",
            f"Rate limit exceeded{suffix}",
            429,
        )
        self.retry_after = retry_after


class BcaUpstreamError(BcaError):
    def __init__(
        self,
        status: int,
        message: str = "BCA API upstream error",
    ) -> None:
        super().__init__("BCA_UPSTREAM", f"{message} (HTTP {status})", status)


class BcaNetworkError(BcaError):
    def __init__(self, cause: object) -> None:
        super().__init__(
            "BCA_NETWORK",
            f"Network error contacting BCA API: {cause!s}",
        )
        self.__cause__ = cause if isinstance(cause, BaseException) else None


class BcaBadRequestError(BcaError):
    def __init__(self, message: str) -> None:
        super().__init__("BCA_BAD_REQUEST", message, 400)
