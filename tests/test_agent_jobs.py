"""Tests for batch-5 agent-job tools.

Covers the async POST-based tools plus the get_agent_job poller's
`<untrusted_content>` wrapping on summarize-whitepaper output.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bca_mcp.client import BcaClient, set_client
from bca_mcp.tools.agent_jobs import (
    GenerateDueDiligenceInput,
    MonitorKeywordInput,
    SummarizeWhitepaperInput,
    TranslateContractInput,
    run_generate_due_diligence,
    run_get_agent_job,
    run_summarize_whitepaper,
)


# --- input validation -----------------------------------------------------


def test_generate_due_diligence_defaults() -> None:
    v = GenerateDueDiligenceInput.model_validate({"entity_slug": "ethereum"})
    assert v.depth == "standard"
    assert v.focus is None


def test_generate_due_diligence_rejects_bad_depth() -> None:
    with pytest.raises(ValidationError):
        GenerateDueDiligenceInput.model_validate(
            {"entity_slug": "x", "depth": "bogus"}
        )


def test_summarize_whitepaper_requires_http_url() -> None:
    with pytest.raises(ValidationError):
        SummarizeWhitepaperInput.model_validate({"url": "ftp://x.test/p.pdf"})
    with pytest.raises(ValidationError):
        SummarizeWhitepaperInput.model_validate({"url": "not a url"})
    v = SummarizeWhitepaperInput.model_validate(
        {"url": "https://x.test/p.pdf"}
    )
    assert v.length == "standard"


def test_translate_contract_rejects_unknown_language() -> None:
    with pytest.raises(ValidationError):
        TranslateContractInput.model_validate(
            {
                "source_code": "contract A {}",
                "source_language": "solidity",
                "target_language": "haskell",
            }
        )


def test_monitor_keyword_bounds() -> None:
    with pytest.raises(ValidationError):
        MonitorKeywordInput.model_validate(
            {"keyword": "x", "webhook_url": "https://x.test/hook", "window_hours": 0}
        )
    with pytest.raises(ValidationError):
        MonitorKeywordInput.model_validate(
            {"keyword": "x", "webhook_url": "https://x.test/hook", "window_hours": 500}
        )


# --- POST paths -----------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_due_diligence_posts(httpx_mock) -> None:
    httpx_mock.add_response(
        url="https://api.blockchainacademics.com/v1/agent-jobs/due-diligence",
        method="POST",
        json={"data": {"job_id": "job_abc", "status_url": "/v1/agent-jobs/job_abc"}},
        status_code=202,
    )
    set_client(BcaClient(api_key="k"))
    out = await run_generate_due_diligence(
        {"entity_slug": "ethereum", "depth": "deep"}
    )
    assert out.get("data", {}).get("job_id") == "job_abc"


@pytest.mark.asyncio
async def test_summarize_whitepaper_posts(httpx_mock) -> None:
    httpx_mock.add_response(
        url="https://api.blockchainacademics.com/v1/agent-jobs/summarize-whitepaper",
        method="POST",
        json={"data": {"job_id": "job_wp"}},
        status_code=202,
    )
    set_client(BcaClient(api_key="k"))
    out = await run_summarize_whitepaper(
        {"url": "https://x.test/paper.pdf", "length": "brief"}
    )
    assert out.get("data", {}).get("job_id") == "job_wp"


# --- get_agent_job + untrusted_content fencing ---------------------------


@pytest.mark.asyncio
async def test_get_agent_job_wraps_summarize_whitepaper_summary(httpx_mock) -> None:
    """A-3: third-party whitepaper text must be fenced before the LLM sees it."""
    httpx_mock.add_response(
        url="https://api.blockchainacademics.com/v1/agent-jobs/job_abc",
        json={
            "data": {
                "job_id": "job_abc",
                "kind": "summarize-whitepaper",
                "status": "completed",
                "output": {
                    "summary": "Ethereum is a decentralized platform.",
                    "abstract": "ABS",
                    "body": "BODY",
                    "body_markdown": "MD",
                    "other": "not wrapped",
                },
            }
        },
        status_code=200,
    )
    set_client(BcaClient(api_key="k"))
    out = await run_get_agent_job({"job_id": "job_abc"})
    output = out.get("data", {}).get("output", {})
    for key in ("summary", "abstract", "body", "body_markdown"):
        assert output[key].startswith(
            '<untrusted_content source="summarize_whitepaper">'
        ), f"{key} was not wrapped"
        assert output[key].endswith("</untrusted_content>")
    # Non-untrusted fields pass through unchanged.
    assert output["other"] == "not wrapped"


@pytest.mark.asyncio
async def test_get_agent_job_does_not_wrap_other_kinds(httpx_mock) -> None:
    httpx_mock.add_response(
        url="https://api.blockchainacademics.com/v1/agent-jobs/job_dd",
        json={
            "data": {
                "job_id": "job_dd",
                "kind": "due-diligence",
                "status": "completed",
                "output": {"summary": "In-house DD analysis text."},
            }
        },
        status_code=200,
    )
    set_client(BcaClient(api_key="k"))
    out = await run_get_agent_job({"job_id": "job_dd"})
    # due-diligence output is BCA-authored, not third-party → unwrapped.
    assert out["data"]["output"]["summary"] == "In-house DD analysis text."


def test_get_agent_job_rejects_bad_job_id() -> None:
    from bca_mcp.tools.agent_jobs import GetAgentJobInput

    with pytest.raises(ValidationError):
        GetAgentJobInput.model_validate({"job_id": "has spaces"})
    with pytest.raises(ValidationError):
        GetAgentJobInput.model_validate({"job_id": "bad/slash"})
    GetAgentJobInput.model_validate({"job_id": "job_A-Z-0-9_-"})
