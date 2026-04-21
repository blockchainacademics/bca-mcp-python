"""Security regression tests for the BCA HTTP client.

Covers three defensive guards that must stay intact to match the TS sibling:

  1. BCA_API_BASE must be HTTPS unless BCA_ALLOW_INSECURE_BASE=1 — a hostile
     env var otherwise steals the X-API-Key on first request.
  2. Non-default bases emit a one-time stderr warning; `reset_nondefault_warning()`
     lets tests reset that latch between cases.
  3. Response bodies larger than 10 MiB raise BcaUpstreamError instead of
     materialising into host memory.
"""

from __future__ import annotations

import pytest

from bca_mcp.client import (
    DEFAULT_BASE,
    MAX_BODY_BYTES,
    BcaClient,
    reset_nondefault_warning,
    set_client,
)
from bca_mcp.errors import BcaBadRequestError, BcaUpstreamError


# --- scheme gate ----------------------------------------------------------


def test_rejects_http_base_url_from_argument() -> None:
    with pytest.raises(BcaBadRequestError, match="non-HTTPS"):
        BcaClient(base_url="http://attacker.local", api_key="k")


def test_rejects_http_base_url_from_env(monkeypatch) -> None:
    monkeypatch.setenv("BCA_API_BASE", "http://attacker.local")
    monkeypatch.delenv("BCA_ALLOW_INSECURE_BASE", raising=False)
    with pytest.raises(BcaBadRequestError, match="non-HTTPS"):
        BcaClient(api_key="k")


def test_legacy_env_var_also_scheme_checked(monkeypatch) -> None:
    monkeypatch.delenv("BCA_API_BASE", raising=False)
    monkeypatch.setenv("BCA_API_BASE_URL", "http://legacy.local")
    monkeypatch.delenv("BCA_ALLOW_INSECURE_BASE", raising=False)
    with pytest.raises(BcaBadRequestError, match="non-HTTPS"):
        BcaClient(api_key="k")


def test_allow_insecure_base_env_opens_gate(monkeypatch) -> None:
    monkeypatch.setenv("BCA_ALLOW_INSECURE_BASE", "1")
    # Must not raise.
    c = BcaClient(base_url="http://localhost:8080", api_key="k")
    assert c._base_url == "http://localhost:8080"


def test_default_https_base_is_accepted() -> None:
    c = BcaClient(api_key="k")
    assert c._base_url == DEFAULT_BASE


# --- one-time warning -----------------------------------------------------


@pytest.mark.asyncio
async def test_nondefault_base_warns_once(httpx_mock, capsys) -> None:
    reset_nondefault_warning()
    httpx_mock.add_response(
        url="https://staging.blockchainacademics.com/v1/topics",
        json={"data": []},
        status_code=200,
    )
    httpx_mock.add_response(
        url="https://staging.blockchainacademics.com/v1/topics",
        json={"data": []},
        status_code=200,
    )
    c = BcaClient(
        base_url="https://staging.blockchainacademics.com",
        api_key="k",
    )
    await c.request("/v1/topics")
    await c.request("/v1/topics")
    err = capsys.readouterr().err
    # Warning must appear exactly once across the two calls.
    assert err.count("non-default BCA_API_BASE") == 1
    assert "staging.blockchainacademics.com" in err


@pytest.mark.asyncio
async def test_default_base_does_not_warn(httpx_mock, capsys) -> None:
    reset_nondefault_warning()
    httpx_mock.add_response(
        url="https://api.blockchainacademics.com/v1/topics",
        json={"data": []},
        status_code=200,
    )
    c = BcaClient(api_key="k")
    await c.request("/v1/topics")
    err = capsys.readouterr().err
    assert "non-default BCA_API_BASE" not in err


# --- body size cap --------------------------------------------------------


@pytest.mark.asyncio
async def test_oversize_response_body_raises_upstream(httpx_mock) -> None:
    """A body exceeding MAX_BODY_BYTES must fail fast, not materialise."""
    # One byte over the cap — pytest-httpx streams this as raw bytes so
    # the client sees the real content length.
    oversize = b"x" * (MAX_BODY_BYTES + 1)
    httpx_mock.add_response(
        url="https://api.blockchainacademics.com/v1/topics",
        content=oversize,
        status_code=200,
        headers={"content-type": "application/json"},
    )
    c = BcaClient(api_key="k")
    set_client(c)
    with pytest.raises(BcaUpstreamError, match="byte cap"):
        await c.request("/v1/topics")


@pytest.mark.asyncio
async def test_undersize_response_body_passes(httpx_mock) -> None:
    """A body well under the cap must round-trip normally."""
    httpx_mock.add_response(
        url="https://api.blockchainacademics.com/v1/topics",
        json={"data": {"topics": ["defi", "regulation"]}},
        status_code=200,
    )
    c = BcaClient(api_key="k")
    out = await c.request("/v1/topics")
    assert out.get("data", {}).get("topics") == ["defi", "regulation"]
