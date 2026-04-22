"""Async HTTP client for the Blockchain Academics API.

Mirrors `src/client.ts`: reads `BCA_API_KEY` / `BCA_API_BASE` (with
`BCA_API_BASE_URL` accepted as legacy fallback), 20s timeout, X-API-Key
header, canonical-envelope-aware response parsing.

Canonical envelope (v0.3.0, locked 2026-04-22):

    { "data": ..., "attribution": {"citations": [...]}, "meta": {...} }

A temporary shim below upgrades legacy flat-shaped responses
(`{data, cite_url, as_of, source_hash, status}`) into the canonical
shape while logging a one-time warning — this covers any upstream
deploys that haven't rolled to the new envelope yet. Remove the shim
once the rollout is confirmed complete.
"""

from __future__ import annotations

import json as _json
import logging
import os
import sys
import uuid
from typing import Any, Mapping, Optional

import httpx

from bca_mcp.errors import (
    BcaAuthError,
    BcaBadRequestError,
    BcaNetworkError,
    BcaRateLimitError,
    BcaUpstreamError,
)
from bca_mcp.types import (
    Attribution,
    Citation,
    ResponseEnvelope,
    default_page_info,
    resolve_envelope_status,
)

DEFAULT_BASE = "https://api.blockchainacademics.com"
USER_AGENT = "bca-mcp/0.3.1 (+https://github.com/blockchainacademics/bca-mcp-python)"

# H-1: strict allowlist of base URLs. Env vars and constructor args are both
# validated against this list at startup. An attacker who controls
# BCA_API_BASE (malicious shell profile, hostile MCP client config,
# compromised CI secret) would otherwise redirect every outbound request —
# including the user's X-API-Key — to an attacker-controlled host.
# Mirrors the TS sibling's allowlist in `src/client.ts` so both servers
# accept the exact same set of bases.
_ALLOWED_EXACT_BASES = (
    "https://api.blockchainacademics.com",
    "https://staging-api.blockchainacademics.com",
)
_ALLOWED_LOCAL_HOSTS = ("localhost", "127.0.0.1")


def _is_allowed_base(url: str) -> bool:
    """Return True iff ``url`` is in the allowlist.

    The allowlist covers:
      * ``https://api.blockchainacademics.com`` (prod, default)
      * ``https://staging-api.blockchainacademics.com`` (staging)
      * ``http://localhost[:port]`` and ``http://127.0.0.1[:port]`` (dev)

    Comparisons are made after ``rstrip("/")`` — any trailing slash has
    already been stripped by the caller.
    """
    if url in _ALLOWED_EXACT_BASES:
        return True
    # Dev: http://localhost or http://127.0.0.1 with any (or no) port.
    # Parse minimally to avoid pulling in urllib just for this check.
    for scheme, host in (("http://", "localhost"), ("http://", "127.0.0.1")):
        prefix = scheme + host
        if url == prefix:
            return True
        if url.startswith(prefix + ":"):
            # Must be prefix:<port> and nothing else (no path, no userinfo).
            rest = url[len(prefix) + 1 :]
            if rest.isdigit() and 1 <= int(rest) <= 65535:
                return True
    return False


def _format_allowlist_error(url: str) -> str:
    return (
        f"Refusing to use BCA_API_BASE='{url}'. "
        "Value must be one of: "
        "https://api.blockchainacademics.com, "
        "https://staging-api.blockchainacademics.com, "
        "http://localhost[:port], http://127.0.0.1[:port]."
    )

_logger = logging.getLogger("bca_mcp.client")

# One-shot guard so the flat→canonical shim only logs once per process.
_legacy_envelope_warned = False


def _warn_legacy_envelope_once() -> None:
    global _legacy_envelope_warned
    if not _legacy_envelope_warned:
        _legacy_envelope_warned = True
        _logger.warning(
            "bca-mcp client: received legacy flat envelope "
            "(top-level cite_url/as_of/source_hash). Upgrading to canonical "
            "shape. Upstream should emit attribution.citations[] + meta.* "
            "directly — this shim is temporary."
        )


def _canonicalize_envelope(payload: Any) -> ResponseEnvelope[Any]:
    """Accept either a canonical or legacy-flat upstream body and return
    a canonical `ResponseEnvelope`.

    Canonical detection: the presence of BOTH `attribution` (dict with
    `citations` array) AND `meta` (dict) keys means the body is already
    in the new shape and passes through unchanged.

    Legacy detection: a `dict` with a top-level `data` key and one or
    more of `cite_url` / `as_of` / `source_hash` / `status` is upgraded
    in place. `status` values outside the canonical enum (e.g. legacy
    "integration_pending", "upstream_error", "error") are rewritten to
    the nearest canonical equivalent — "integration_pending" → "unseeded",
    everything else unknown → "partial" so no data is dropped on the floor.

    Non-dict / non-enveloped JSON is wrapped under `data` with an empty
    attribution and meta defaults.
    """

    if isinstance(payload, dict):
        has_canonical_attribution = (
            isinstance(payload.get("attribution"), dict)
            and isinstance(payload["attribution"].get("citations"), list)
        )
        has_canonical_meta = isinstance(payload.get("meta"), dict)

        # Already canonical → passthrough.
        if has_canonical_attribution and has_canonical_meta:
            return payload  # type: ignore[return-value]

        # Legacy flat envelope → upgrade.
        has_flat_attribution = any(
            k in payload for k in ("cite_url", "as_of", "source_hash")
        )
        has_flat_status = "status" in payload and not has_canonical_meta
        if "data" in payload and (has_flat_attribution or has_flat_status):
            _warn_legacy_envelope_once()

            citation: Citation = {
                "cite_url": payload.get("cite_url"),
                "as_of": payload.get("as_of"),
                "source_hash": payload.get("source_hash"),
            }
            has_any_citation_field = any(
                citation.get(k) is not None
                for k in ("cite_url", "as_of", "source_hash")
            )
            attribution: Attribution = {
                "citations": [citation] if has_any_citation_field else [],
            }

            raw_status = payload.get("status")
            if raw_status in ("complete", "unseeded", "partial", "stale"):
                status = raw_status
            elif raw_status is None:
                status = resolve_envelope_status(payload.get("data"))
            elif raw_status == "integration_pending":
                status = "unseeded"
            else:
                # Legacy upstream_error / error / anything else — don't
                # drop the payload; mark it partial and stash the raw
                # status in diagnostic for observability.
                status = "partial"

            diagnostic: dict[str, Any] = {}
            if raw_status is not None and raw_status != status:
                diagnostic["legacy_status"] = raw_status
            # Carry any legacy `meta` dict through under `diagnostic.legacy_meta`
            # so we don't silently drop fields tool authors may have set.
            legacy_meta = payload.get("meta")
            if isinstance(legacy_meta, dict) and legacy_meta:
                diagnostic["legacy_meta"] = legacy_meta

            meta: dict[str, Any] = {
                "status": status,
                "request_id": f"req_{uuid.uuid4().hex[:16]}",
                "pageInfo": default_page_info(),
            }
            if diagnostic:
                meta["diagnostic"] = diagnostic

            return {
                "data": payload.get("data"),
                "attribution": attribution,
                "meta": meta,  # type: ignore[typeddict-item]
            }

        # Dict with `data` but no provenance hints at all → wrap in
        # canonical defaults.
        if "data" in payload:
            return {
                "data": payload["data"],
                "attribution": {"citations": []},
                "meta": {  # type: ignore[typeddict-item]
                    "status": resolve_envelope_status(payload["data"]),
                    "request_id": f"req_{uuid.uuid4().hex[:16]}",
                    "pageInfo": default_page_info(),
                },
            }

    # Non-enveloped JSON (list, scalar, or dict without `data`) → wrap.
    return {
        "data": payload,
        "attribution": {"citations": []},
        "meta": {  # type: ignore[typeddict-item]
            "status": resolve_envelope_status(payload),
            "request_id": f"req_{uuid.uuid4().hex[:16]}",
            "pageInfo": default_page_info(),
        },
    }

# HIGH: cap response body size to prevent a malicious or compromised upstream
# from exhausting host memory. 10 MiB is well above any legitimate envelope
# this API returns (largest real responses — agent-job outputs — are ~200 KB).
# Mirrors `MAX_BODY_BYTES` in `src/client.ts`.
MAX_BODY_BYTES = 10 * 1024 * 1024

# Module-level guard so we only warn once per process when a non-default
# BCA_API_BASE is in use. Exposed via `reset_nondefault_warning()` so tests
# can reset state between cases.
_nondefault_base_warned = False


def reset_nondefault_warning() -> None:
    """Reset the one-time non-default BCA_API_BASE warning flag.

    Tests that exercise the warning path call this between cases so the
    first client built in each test sees `_nondefault_base_warned=False`.
    Mirrors `__resetNonDefaultBaseWarning()` in the TS sibling.
    """
    global _nondefault_base_warned
    _nondefault_base_warned = False


def reset_legacy_envelope_warning() -> None:
    """Reset the one-time legacy-envelope upgrade warning flag.

    Used by tests that exercise the flat→canonical shim.
    """
    global _legacy_envelope_warned
    _legacy_envelope_warned = False


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
        resolved = raw_base.rstrip("/")

        # H-1 (v0.3.1): strict allowlist. The v0.3.0 HTTPS-only gate was
        # insufficient — a compromised env could still point the client at
        # `https://attacker.controlled.example` and exfiltrate the user's
        # X-API-Key on the first outbound request. The allowlist pins the
        # base URL to the canonical prod/staging hosts or explicit local-dev
        # loopback. Any other value — HTTPS or not — is rejected at
        # construction. Mirrors the TS sibling's allowlist so both servers
        # fence identically.
        if not _is_allowed_base(resolved):
            raise ValueError(_format_allowlist_error(resolved))

        self._base_url = resolved
        self._is_nondefault_base = resolved != DEFAULT_BASE
        self._api_key = api_key or os.environ.get("BCA_API_KEY")
        self._timeout = httpx.Timeout(timeout_s, connect=3.0)
        self._transport = transport  # test injection

    def _warn_nondefault_base_once(self) -> None:
        global _nondefault_base_warned
        if self._is_nondefault_base and not _nondefault_base_warned:
            _nondefault_base_warned = True
            print(
                f"warning: using non-default BCA_API_BASE='{self._base_url}'",
                file=sys.stderr,
            )

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

        # HIGH: emit a one-time warning whenever the operator is pointing this
        # client at something other than the canonical production API. This
        # runs on first call (not ctor) so tests that build-then-discard a
        # client against a mock transport don't spam stderr.
        self._warn_nondefault_base_once()

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

        # MEDIUM: cap body size. A compromised upstream could otherwise stream
        # an unbounded response and exhaust host memory. httpx has already
        # materialised `res.content`; we size-check it here and fail fast
        # with a clear BcaUpstreamError (rather than silently truncating).
        raw = res.content  # bytes
        if len(raw) > MAX_BODY_BYTES:
            raise BcaUpstreamError(
                res.status_code,
                f"response exceeded {MAX_BODY_BYTES} byte cap "
                f"({len(raw)} bytes received)",
            )

        try:
            payload = res.json()
        except (ValueError, _json.JSONDecodeError) as err:
            raise BcaUpstreamError(
                res.status_code,
                f"Invalid JSON from BCA API: {err!s}",
            ) from err

        # Canonical-envelope-aware: passthrough if already canonical,
        # upgrade legacy flat shape (with one-time warning), else wrap
        # as a best-effort canonical envelope.
        return _canonicalize_envelope(payload)


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
