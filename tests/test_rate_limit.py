"""429 answers: a call the per-second limit turned away is sent again, every
other limit is returned at once. Same rule as the TS sibling
(test/rate_limit.test.ts). All HTTP goes through a fake transport and the
waits are recorded instead of slept; nothing here reaches the network.
"""

from __future__ import annotations

from typing import Callable

import httpx
import pytest

import bca_mcp.client as client_mod
from bca_mcp.client import BcaClient
from bca_mcp.errors import BcaRateLimitError

SIGNUP = "https://blockchainacademics.com/crypto-api/signup?ref=mcp-demo-rate"
CODE = {"x-bca-error-code": "BCA_RATE_LIMIT"}

# The API's 429 answers, as it sends them: (detail, headers).
Limit = tuple[str, dict[str, str]]
DEMO_PER_SECOND: Limit = (
    f"Demo tier is at its per-second cap. Free account is 2,000/month: {SIGNUP}",
    {"retry-after": "1", **CODE},
)
KEYED_PER_SECOND: Limit = ("Rate limit exceeded: 2 requests/second for free tier", {})
KEYED_DAILY: Limit = ("Daily limit exceeded: 87 requests/day for free tier", {})
DEMO_PER_IP: Limit = (
    f"Demo per-IP limit reached (20/day). Free account is 2,000/month: {SIGNUP}",
    {"retry-after": "3600", **CODE},
)
JOB_QUEUE: Limit = (
    "You already have 3 jobs queued or running. Wait for one to finish before starting another.",
    {"retry-after": "60", **CODE},
)
# Sent after the call was counted, with the seconds left in the vendor's window.
VENDOR: Limit = ("Upstream vendor rate limit, retry after 1s", {"retry-after": "1"})


def limited(limit: Limit) -> Callable[[], httpx.Response]:
    detail, headers = limit
    return lambda: httpx.Response(429, json={"detail": detail}, headers=headers)


def ok() -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "data": {"ok": True},
            "attribution": {"citations": []},
            "meta": {"status": "complete", "request_id": "req_t", "pageInfo": {}},
        },
    )


class Scripted:
    """A client whose transport gives each answer in turn (the last one
    repeats), with the number of requests sent."""

    def __init__(self, *answers: Callable[[], httpx.Response]) -> None:
        self.calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            self.calls += 1
            return answers[min(self.calls, len(answers)) - 1]()

        self.client = BcaClient(api_key="k", transport=httpx.MockTransport(handler))


@pytest.fixture
def waits(monkeypatch) -> list[float]:
    """The waits the client asked for, recorded instead of slept, with a
    fixed jitter (random 0.5 gives 200 ms)."""
    recorded: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        recorded.append(seconds)

    monkeypatch.setattr(client_mod, "_sleep", fake_sleep)
    monkeypatch.setattr(client_mod.random, "random", lambda: 0.5)
    return recorded


# --- a 429 from the per-second limit ----------------------------------------


@pytest.mark.asyncio
async def test_is_sent_again_after_retry_after_plus_jitter(waits) -> None:
    sent = Scripted(limited(DEMO_PER_SECOND), ok)
    out = await sent.client.request("/v1/market/price")
    assert out["data"] == {"ok": True}
    assert sent.calls == 2
    assert waits == [pytest.approx(1.2)]


@pytest.mark.asyncio
async def test_waits_1s_without_retry_after_when_the_detail_names_the_limit(waits) -> None:
    sent = Scripted(limited(KEYED_PER_SECOND), ok)
    out = await sent.client.request("/v1/market/price")
    assert out["data"] == {"ok": True}
    assert sent.calls == 2
    assert waits == [pytest.approx(1.2)]


@pytest.mark.asyncio
@pytest.mark.parametrize(("rand", "wait"), [(0.0, 1.1), (0.999, 1.2998)])
async def test_adds_100_to_300_ms_of_jitter(waits, monkeypatch, rand, wait) -> None:
    monkeypatch.setattr(client_mod.random, "random", lambda: rand)
    sent = Scripted(limited(DEMO_PER_SECOND), ok)
    await sent.client.request("/v1/market/price")
    assert sent.calls == 2
    assert waits == [pytest.approx(wait)]


@pytest.mark.asyncio
async def test_gives_up_after_two_retries(waits) -> None:
    sent = Scripted(limited(DEMO_PER_SECOND))
    with pytest.raises(BcaRateLimitError) as exc:
        await sent.client.request("/v1/market/price")
    assert exc.value.code == "BCA_RATE_LIMIT"
    assert exc.value.retry_after == 1
    assert sent.calls == 3
    assert waits == [pytest.approx(1.2), pytest.approx(1.2)]


@pytest.mark.asyncio
async def test_never_repeats_a_post(waits) -> None:
    sent = Scripted(limited(DEMO_PER_SECOND), ok)
    with pytest.raises(BcaRateLimitError):
        await sent.client.post("/v1/agent-jobs", {"kind": "due_diligence"})
    assert sent.calls == 1
    assert waits == []


# --- every other 429 is returned at once ------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("limit", "retry_after"),
    [
        pytest.param(KEYED_DAILY, None, id="a keyed daily cap"),
        pytest.param(DEMO_PER_IP, 3600, id="the no-key daily cap per IP"),
        pytest.param(JOB_QUEUE, 60, id="the job queue cap"),
        pytest.param(VENDOR, 1, id="a vendor limit with a short Retry-After and no error code"),
        pytest.param(
            (DEMO_PER_SECOND[0], {"retry-after": "3", **CODE}), 3,
            id="a Retry-After over 2 seconds",
        ),
        pytest.param(
            (DEMO_PER_SECOND[0], {"retry-after": "Wed, 11 Nov 2026 07:28:00 GMT", **CODE}),
            None,
            id="a Retry-After that is an HTTP date",
        ),
    ],
)
async def test_every_other_429_is_returned_at_once(waits, limit, retry_after) -> None:
    sent = Scripted(limited(limit), ok)
    with pytest.raises(BcaRateLimitError) as exc:
        await sent.client.request("/v1/market/price")
    assert exc.value.retry_after == retry_after
    assert sent.calls == 1
    assert waits == []
