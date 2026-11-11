"""Security regression tests for the BCA HTTP client.

Covers the defensive guards that must stay intact to match the TS sibling:

  1. (v0.3.1) BCA_API_BASE is pinned to an allowlist — prod, staging, or
     loopback dev only. Any other value — HTTP or HTTPS — is rejected at
     construction with ``ValueError``. Closes H-1 (SSRF + X-API-Key exfil
     via env var override).
  2. Non-default bases emit a one-time stderr warning; `reset_nondefault_warning()`
     lets tests reset that latch between cases.
  3. Response bodies larger than 10 MiB raise BcaUpstreamError instead of
     materialising into host memory.
"""

from __future__ import annotations

import httpx
import pytest

from bca_mcp.client import (
    DEFAULT_BASE,
    MAX_BODY_BYTES,
    MAX_ERROR_BODY_BYTES,
    BcaClient,
    reset_nondefault_warning,
    set_client,
)
from bca_mcp.errors import BcaBadRequestError, BcaNetworkError, BcaUpstreamError


# --- allowlist gate (H-1) -------------------------------------------------


def test_rejects_http_base_url_from_argument() -> None:
    # http://attacker.local is neither loopback nor an allowed host.
    with pytest.raises(ValueError, match="Refusing to use BCA_API_BASE"):
        BcaClient(base_url="http://attacker.local", api_key="k")


def test_rejects_http_base_url_from_env(monkeypatch) -> None:
    monkeypatch.setenv("BCA_API_BASE", "http://attacker.local")
    with pytest.raises(ValueError, match="Refusing to use BCA_API_BASE"):
        BcaClient(api_key="k")


def test_legacy_env_var_also_allowlisted(monkeypatch) -> None:
    monkeypatch.delenv("BCA_API_BASE", raising=False)
    monkeypatch.setenv("BCA_API_BASE_URL", "http://legacy.local")
    with pytest.raises(ValueError, match="Refusing to use BCA_API_BASE"):
        BcaClient(api_key="k")


def test_rejects_unrelated_https_base(monkeypatch) -> None:
    # H-1 regression: even an HTTPS attacker-controlled host must be
    # rejected — the prior HTTPS-only gate would have let this through.
    monkeypatch.setenv("BCA_API_BASE", "https://evil.example.com")
    with pytest.raises(ValueError, match="Refusing to use BCA_API_BASE"):
        BcaClient(api_key="k")


def test_allowlist_accepts_staging(monkeypatch) -> None:
    monkeypatch.setenv(
        "BCA_API_BASE", "https://staging-api.blockchainacademics.com"
    )
    c = BcaClient(api_key="k")
    assert c._base_url == "https://staging-api.blockchainacademics.com"


def test_allowlist_accepts_localhost_with_port() -> None:
    c = BcaClient(base_url="http://localhost:8080", api_key="k")
    assert c._base_url == "http://localhost:8080"


def test_allowlist_accepts_127_0_0_1_with_port() -> None:
    c = BcaClient(base_url="http://127.0.0.1:3000", api_key="k")
    assert c._base_url == "http://127.0.0.1:3000"


def test_allowlist_accepts_localhost_without_port() -> None:
    c = BcaClient(base_url="http://localhost", api_key="k")
    assert c._base_url == "http://localhost"


def test_allowlist_rejects_loopback_with_suspicious_suffix() -> None:
    # An attacker might try `http://localhost.attacker.com` banking on a
    # naive prefix match. Must reject.
    with pytest.raises(ValueError, match="Refusing to use BCA_API_BASE"):
        BcaClient(base_url="http://localhost.attacker.com", api_key="k")


def test_default_https_base_is_accepted() -> None:
    c = BcaClient(api_key="k")
    assert c._base_url == DEFAULT_BASE


# --- one-time warning -----------------------------------------------------


@pytest.mark.asyncio
async def test_nondefault_base_warns_once(httpx_mock, capsys) -> None:
    reset_nondefault_warning()
    httpx_mock.add_response(
        url="https://staging-api.blockchainacademics.com/v1/topics",
        json={"data": []},
        status_code=200,
    )
    httpx_mock.add_response(
        url="https://staging-api.blockchainacademics.com/v1/topics",
        json={"data": []},
        status_code=200,
    )
    c = BcaClient(
        base_url="https://staging-api.blockchainacademics.com",
        api_key="k",
    )
    await c.request("/v1/topics")
    await c.request("/v1/topics")
    err = capsys.readouterr().err
    # Warning must appear exactly once across the two calls.
    assert err.count("non-default BCA_API_BASE") == 1
    assert "staging-api.blockchainacademics.com" in err


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


class _Chunks(httpx.AsyncByteStream):
    """A response body sent in ``count`` chunks of ``size`` bytes, counting
    how many the client pulled; ``fail_after`` drops the connection there."""

    def __init__(self, size: int, count: int, fail_after: int | None = None) -> None:
        self.size, self.count, self.fail_after = size, count, fail_after
        self.sent = 0

    async def __aiter__(self):
        for _ in range(self.count):
            if self.sent == self.fail_after:
                raise httpx.ReadError("connection reset")
            self.sent += 1
            yield b"x" * self.size


def _streaming_client(status: int, body: _Chunks) -> BcaClient:
    return BcaClient(
        api_key="k",
        transport=httpx.MockTransport(lambda request: httpx.Response(status, stream=body)),
    )


@pytest.mark.asyncio
async def test_oversize_body_stops_reading_at_the_cap() -> None:
    """The read stops once the body passes MAX_BODY_BYTES: 11 chunks of
    1 MiB are pulled out of the 32 the server would send."""
    body = _Chunks(1024 * 1024, 32)
    with pytest.raises(BcaUpstreamError) as exc:
        await _streaming_client(200, body).request("/v1/topics")
    assert str(exc.value) == f"response exceeded {MAX_BODY_BYTES} byte cap (HTTP 200)"
    assert body.sent == MAX_BODY_BYTES // (1024 * 1024) + 1


@pytest.mark.asyncio
async def test_oversize_error_body_stops_at_its_cap_and_gives_no_detail() -> None:
    body = _Chunks(8 * 1024, 100)
    with pytest.raises(BcaBadRequestError) as exc:
        await _streaming_client(404, body).request("/v1/topics")
    assert str(exc.value) == "BCA API rejected request: HTTP 404"
    assert exc.value.detail is None
    assert body.sent == MAX_ERROR_BODY_BYTES // (8 * 1024) + 1


@pytest.mark.asyncio
async def test_a_body_cut_off_mid_stream_is_a_network_error() -> None:
    body = _Chunks(1024, 10, fail_after=3)
    with pytest.raises(BcaNetworkError, match="ReadError: connection reset"):
        await _streaming_client(200, body).request("/v1/topics")


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


# --- MCP-TS-2 parity: redirect hardening (v0.4.0) ------------------------


@pytest.mark.asyncio
async def test_rejects_302_redirect(httpx_mock) -> None:
    """Upstream 302 must raise BcaUpstreamError — never follow.

    Without `follow_redirects=False`, httpx would re-issue the request to
    the attacker-controlled `Location`, leaking `X-API-Key` to the
    redirect target. We mirror the TS sibling's commit `895bfee`:
    explicit 3xx rejection.
    """
    httpx_mock.add_response(
        url="https://api.blockchainacademics.com/v1/topics",
        status_code=302,
        headers={"Location": "https://attacker.example/exfil"},
    )
    c = BcaClient(api_key="k")
    with pytest.raises(BcaUpstreamError) as exc_info:
        await c.request("/v1/topics")
    # 302 must surface, AND the attacker URL must NOT leak into the error
    # message (only the status code + "redirect refused" tag).
    assert "302" in str(exc_info.value)
    assert "attacker.example" not in str(exc_info.value)
    assert "redirect refused" in str(exc_info.value)


@pytest.mark.asyncio
async def test_rejects_301_permanent_redirect(httpx_mock) -> None:
    httpx_mock.add_response(
        url="https://api.blockchainacademics.com/v1/topics",
        status_code=301,
        headers={"Location": "https://attacker.example/perm"},
    )
    c = BcaClient(api_key="k")
    with pytest.raises(BcaUpstreamError, match="301"):
        await c.request("/v1/topics")


@pytest.mark.asyncio
async def test_api_key_never_sent_to_redirect_target(httpx_mock) -> None:
    """Defense-in-depth: if a 3xx slipped past the rejection, httpx would
    re-issue to Location — but `follow_redirects=False` is set on the
    AsyncClient itself, so no second request fires. Verify by adding a
    response for the Location URL and confirming the mock never sees it.
    """
    httpx_mock.add_response(
        url="https://api.blockchainacademics.com/v1/topics",
        status_code=303,
        headers={"Location": "https://attacker.example/sink"},
    )
    # No httpx_mock.add_response for the attacker URL — if a redirect
    # WERE followed, httpx would error with "no mock for that URL", which
    # would also fail the test. Either way, the BcaUpstreamError is what
    # we expect.
    c = BcaClient(api_key="leaky-key-do-not-exfil")
    with pytest.raises(BcaUpstreamError):
        await c.request("/v1/topics")
    # Confirm only ONE request was actually sent — to BCA, not the
    # attacker.
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    assert "api.blockchainacademics.com" in str(requests[0].url)


# --- API key hygiene ------------------------------------------------------


def test_api_key_surrounding_whitespace_is_stripped(monkeypatch) -> None:
    # A pasted key often brings a trailing newline. The TS sibling's fetch
    # strips it from the header value, so this package does too.
    monkeypatch.setenv("BCA_API_KEY", "  bca_live_test_key\n")
    client = BcaClient()
    assert client._api_key == "bca_live_test_key"
    assert client.using_demo_key is False
    assert BcaClient(api_key="bca_live_test_key \r\n")._api_key == "bca_live_test_key"


def test_blank_api_key_falls_back_to_the_demo_key(monkeypatch) -> None:
    monkeypatch.setenv("BCA_API_KEY", " \n")
    assert BcaClient().using_demo_key is True


@pytest.mark.asyncio
async def test_stripped_key_is_the_header_sent(httpx_mock) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE}/v1/topics",
        match_headers={"X-API-Key": "bca_live_test_key"},
        json={"data": {}},
    )
    await BcaClient(api_key="bca_live_test_key\n").request("/v1/topics")


@pytest.mark.asyncio
async def test_invalid_api_key_is_never_echoed_in_a_tool_error() -> None:
    # h11 refuses a header value with a control character and repeats the
    # value in its error text, which 0.6.2 passed on as BCA_NETWORK: the
    # user's key ended up in front of the host model. A throwaway loopback
    # listener lets the request get that far without leaving the machine.
    import asyncio
    import json

    from bca_mcp.server import call_tool

    async def handle(_reader, writer) -> None:
        writer.close()

    listener = await asyncio.start_server(handle, "127.0.0.1", 0)
    port = listener.sockets[0].getsockname()[1]
    secret = "bca_live_SECRETVALUE0123"
    try:
        set_client(BcaClient(base_url=f"http://127.0.0.1:{port}", api_key=f"{secret}\r\nX-Injected: 1"))
        result = await call_tool("list_topics", {})
    finally:
        listener.close()
        await listener.wait_closed()
    text = result.content[0].text
    assert result.isError is True
    assert json.loads(text)["error"]["code"] == "BCA_AUTH"
    assert "SECRETVALUE" not in text
    assert "X-Injected" not in text
