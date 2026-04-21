"""Async HTTP client for the Blockchain Academics API.

Mirrors `src/client.ts`: reads `BCA_API_KEY` / `BCA_API_BASE` (with
`BCA_API_BASE_URL` accepted as legacy fallback), 20s timeout, X-API-Key
header, envelope-aware response parsing.
"""

from __future__ import annotations

import json as _json
import os
from typing import Any, Mapping, Optional

import httpx

from bca_mcp.errors import (
    BcaAuthError,
    BcaBadRequestError,
    BcaNetworkError,
    BcaRateLimitError,
    BcaUpstreamError,
)
from bca_mcp.types import ResponseEnvelope

DEFAULT_BASE = "https://api.blockchainacademics.com"
USER_AGENT = "bca-mcp/0.2.0 (+https://github.com/blockchainacademics/bca-mcp-python)"


class BcaClient:
    """Thin async wrapper around `httpx.AsyncClient` for the BCA REST API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_s: float = 20.0,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        raw_base = (
            base_url
            or os.environ.get("BCA_API_BASE")
            or os.environ.get("BCA_API_BASE_URL")
            or DEFAULT_BASE
        )
        self._base_url = raw_base.rstrip("/")
        self._api_key = api_key or os.environ.get("BCA_API_KEY")
        self._timeout = httpx.Timeout(timeout_s, connect=3.0)
        self._transport = transport  # test injection

    def _build_client(self) -> httpx.AsyncClient:
        kwargs: dict[str, Any] = {
            "timeout": self._timeout,
            "headers": {
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
        }
        if self._transport is not None:
            kwargs["transport"] = self._transport
        return httpx.AsyncClient(**kwargs)

    async def request(
        self,
        path: str,
        params: Optional[Mapping[str, Any]] = None,
    ) -> ResponseEnvelope[Any]:
        """GET request. Alias for `call("GET", ...)`."""
        return await self._call("GET", path, params=params)

    async def post(
        self,
        path: str,
        body: Optional[Mapping[str, Any]] = None,
    ) -> ResponseEnvelope[Any]:
        """POST request with JSON body. Mirrors TS `client.post()`."""
        return await self._call("POST", path, body=body)

    async def _call(
        self,
        method: str,
        path: str,
        params: Optional[Mapping[str, Any]] = None,
        body: Optional[Mapping[str, Any]] = None,
    ) -> ResponseEnvelope[Any]:
        if not self._api_key:
            raise BcaAuthError("BCA_API_KEY env var is not set")

        url = self._base_url + (path if path.startswith("/") else "/" + path)

        # Drop empty values (None, ""), coerce to str — matches TS behavior.
        clean_params: dict[str, str] = {}
        if params:
            for k, v in params.items():
                if v is None or v == "":
                    continue
                clean_params[k] = str(v)

        headers: dict[str, str] = {"X-API-Key": self._api_key}
        if method == "POST":
            headers["Content-Type"] = "application/json"

        try:
            async with self._build_client() as http:
                if method == "POST":
                    res = await http.post(
                        url,
                        json=dict(body) if body else None,
                        headers=headers,
                    )
                else:
                    res = await http.get(url, params=clean_params, headers=headers)
        except httpx.HTTPError as err:
            raise BcaNetworkError(err) from err

        if res.status_code in (401, 403):
            raise BcaAuthError()
        if res.status_code == 429:
            ra = res.headers.get("retry-after")
            retry_after: Optional[int] = None
            if ra is not None:
                try:
                    retry_after = int(ra)
                except ValueError:
                    retry_after = None
            raise BcaRateLimitError(retry_after)
        if res.status_code >= 500:
            raise BcaUpstreamError(res.status_code)
        if 400 <= res.status_code < 500:
            # 4xx (other than 401/403/429) = bad request from caller.
            raise BcaBadRequestError(
                f"BCA API rejected request: HTTP {res.status_code}"
            )
        if not (200 <= res.status_code < 300):
            raise BcaUpstreamError(
                res.status_code,
                f"BCA API responded {res.status_code}",
            )

        try:
            payload = res.json()
        except (ValueError, _json.JSONDecodeError) as err:
            raise BcaUpstreamError(
                res.status_code,
                f"Invalid JSON from BCA API: {err!s}",
            ) from err

        # Envelope-aware: pass through if already shaped, else wrap.
        if isinstance(payload, dict) and "data" in payload:
            return payload  # type: ignore[return-value]
        return {"data": payload}


# Shared singleton for tool modules — overridable for tests.
_shared: Optional[BcaClient] = None


def get_client() -> BcaClient:
    global _shared
    if _shared is None:
        _shared = BcaClient()
    return _shared


def set_client(client: BcaClient) -> None:
    global _shared
    _shared = client
