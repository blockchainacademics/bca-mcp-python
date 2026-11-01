"""Parity review of pass 2 (2026-11-01): the Python and TS packages answer the
same inputs the same way and both follow the API on mcp-fix/integration.

These cases were differences between the two packages (the TS sibling now
behaves the same; see its test/parity_review.test.ts) or description fixes
checked against the API routes. Every request goes to a mocked transport.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from bca_mcp.client import BcaClient, set_client
from bca_mcp.server import TOOLS, call_tool

FENCE_PREFIX = '<untrusted_content source="summarize_whitepaper">'


def _tool(name: str):
    return next(t for t in TOOLS if t.name == name)


def _props(name: str) -> dict[str, Any]:
    return _tool(name).input_schema["properties"]


async def _code(name: str, args: dict[str, Any]) -> str | None:
    """The error code of a call that must not reach the network, else None."""
    set_client(BcaClient(api_key="k"))
    result = await call_tool(name, args)
    if not result.isError:
        return None
    return json.loads(result.content[0].text)["error"]["code"]


# --- inputs the API accepts or rejects ---------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("url", ["ftp://example.com/wp.pdf", "javascript:alert(1)"])
async def test_summarize_whitepaper_takes_only_http_urls(httpx_mock, url: str) -> None:
    # The API's SummarizeWhitepaperRequest.url is a pydantic HttpUrl.
    assert httpx_mock is not None
    assert await _code("summarize_whitepaper", {"url": url}) == "BCA_BAD_REQUEST"


def test_url_fields_advertise_the_api_minimum_length() -> None:
    assert _props("summarize_whitepaper")["url"]["minLength"] == 1
    assert _props("monitor_keyword")["webhook_url"]["minLength"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("expiry", ["2026/11/13", "13-NOV-26", "NOV1326", "1DEC26"])
async def test_options_expiry_outside_the_two_api_forms_is_refused(httpx_mock, expiry: str) -> None:
    assert httpx_mock is not None
    assert await _code("get_options_flow", {"symbol": "BTC", "expiry": expiry}) == "BCA_BAD_REQUEST"


@pytest.mark.asyncio
@pytest.mark.parametrize("expiry", ["13NOV26", "01dec26", "2026-11-13"])
async def test_options_expiry_in_an_api_form_is_sent(httpx_mock, expiry: str) -> None:
    httpx_mock.add_response(json={"data": {}})
    assert await _code("get_options_flow", {"symbol": "ETH", "expiry": expiry}) is None
    assert dict(httpx_mock.get_request().url.params)["expiry"] == expiry


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "since", ["2026-10-01", "2026-10-01T00:00:00Z", "2026-10-01T00:00:00+00:00"]
)
async def test_search_news_since_takes_a_bare_date_or_a_timestamp(httpx_mock, since: str) -> None:
    httpx_mock.add_response(json={"data": {"results": []}})
    assert await _code("search_news", {"query": "etf", "since": since}) is None
    assert dict(httpx_mock.get_request().url.params)["since"] == since
    assert _props("search_news")["since"].get("maxLength") == 64
    assert "format" not in _props("search_news")["since"]


# --- get_agent_job fences at every depth ---------------------------------------


@pytest.mark.asyncio
async def test_get_agent_job_fences_nested_summary_members(httpx_mock) -> None:
    from bca_mcp.tools.agent_jobs import run_get_agent_job

    # summarize_whitepaper.py asks for tokenomics as an object of notes.
    httpx_mock.add_response(
        json={
            "data": {
                "kind": "summarize-whitepaper",
                "status": "done",
                "result": {
                    "summary": {
                        "tldr": "A chain.",
                        "tokenomics": {
                            "supply": "21M",
                            "distribution": "mined",
                            "detail": {"note": "deep"},
                            "max": 21000000,
                        },
                        "team": ["Satoshi", {"name": "Hal"}],
                        "risks": ["custody"],
                        "empty": "",
                        "missing": None,
                    }
                },
            }
        }
    )
    set_client(BcaClient(api_key="k"))
    out = await run_get_agent_job({"job_id": "j1"})
    summary = out["data"]["result"]["summary"]
    for value in (
        summary["tldr"],
        summary["tokenomics"]["supply"],
        summary["tokenomics"]["distribution"],
        summary["tokenomics"]["detail"]["note"],
        summary["team"][0],
        summary["team"][1]["name"],
        summary["risks"][0],
    ):
        assert value.startswith(FENCE_PREFIX), value
    assert summary["tokenomics"]["max"] == 21000000
    assert summary["empty"] == ""
    assert summary["missing"] is None


# --- descriptions match what the routes return ---------------------------------


def test_descriptions_match_the_routes() -> None:
    desc = {t.name: t.description for t in TOOLS}
    # regulatory.py get_mica_status returns a reviewed row for any country.
    assert "unseeded unless BCA has a reviewed row for it" in desc["get_mica_status"]
    # agent_jobs.py get_job: require_tier(pro) and the api_key_id filter.
    assert "Pro tier" in desc["get_agent_job"]
    assert "visible only to the key that started them" in desc["get_agent_job"]
    job_id = _props("get_agent_job")["job_id"]["description"]
    assert "monitor_keyword" in job_id and "summarize_whitepaper" in job_id
    # security_intel.py scan_contract returns no owner field.
    assert "owner" not in desc["scan_contract"]
    # fundamentals.py get_audit_reports: partial only when every row is a link.
    assert "partial when only links are on file" in desc["get_audit_reports"]
