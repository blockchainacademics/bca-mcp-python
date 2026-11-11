"""Structured error taxonomy — mirrors the TypeScript sibling exactly.

Error codes are the stable wire contract surfaced to MCP clients; do not
rename without bumping the major version.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional

if TYPE_CHECKING:
    from pydantic import ValidationError

BcaErrorCode = Literal[
    "BCA_AUTH",
    "BCA_RATE_LIMIT",
    "BCA_UPSTREAM",
    "BCA_NETWORK",
    "BCA_BAD_REQUEST",
    # Added 2026-06-02 with the demo tier. Backend returns 403 + this code
    # when a demo-key caller hits a tool outside the demo allowlist.
    # The upstream message includes the signup URL; client surfaces verbatim.
    # A 402 (a valid key on a plan below the tool's) gets the same code.
    "BCA_TIER_LOCKED",
]


class BcaError(Exception):
    """Base class for all BCA MCP errors.

    ``detail`` carries the API's own explanation of a rejected request
    (FastAPI ``detail``), already rendered and capped at 500 characters. It
    is upstream text, so it stays separate from the message: the MCP server
    fences it as untrusted content before a model reads it.
    """

    code: BcaErrorCode
    status: Optional[int]
    detail: Optional[str]

    def __init__(
        self,
        code: BcaErrorCode,
        message: str,
        status: Optional[int] = None,
        detail: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.detail = detail


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
    def __init__(
        self,
        message: str,
        status: int = 400,
        detail: Optional[str] = None,
    ) -> None:
        super().__init__("BCA_BAD_REQUEST", message, status, detail)


# Validation messages list at most this many problems, each capped, so one
# oversized argument cannot balloon the error the host model reads. Same
# limits as the TS sibling's formatValidationError.
MAX_ISSUES = 10
MAX_ISSUE_CHARS = 200


def _strip_pydantic_prefix(msg: str) -> str:
    # pydantic prefixes errors raised from custom validators with the
    # exception kind; the caller only needs the problem itself.
    for prefix in ("Value error, ", "Assertion failed, "):
        if msg.startswith(prefix):
            return msg[len(prefix):]
    return msg


def format_validation_error(tool_name: str, err: "ValidationError") -> str:
    """Render a pydantic ``ValidationError`` as ``field: problem`` pairs.

    ``Invalid arguments for search_news: query: Field required; limit:
    Input should be less than or equal to 50``. Pairs are joined with
    ``"; "`` and nested locations use dots (``focus.0``). A rule on the
    arguments as a whole (no field, such as get_entity's "exactly one of
    slug or ticker") is listed without a field. Input values are never
    echoed back. Same format as the TS sibling.
    """
    parts: list[str] = []
    for issue in err.errors(include_url=False, include_input=False):
        field = ".".join(str(part) for part in issue.get("loc", ()))
        problem = _strip_pydantic_prefix(str(issue.get("msg") or "invalid value"))
        if len(problem) > MAX_ISSUE_CHARS:
            problem = f"{problem[:MAX_ISSUE_CHARS]}..."
        text = f"{field}: {problem}" if field else problem
        if text not in parts:
            parts.append(text)
    shown = parts[:MAX_ISSUES]
    more = len(parts) - len(shown)
    return f"Invalid arguments for {tool_name}: " + "; ".join(shown) + (
        f"; and {more} more" if more > 0 else ""
    )
