"""CLI smoke tests — exercise Typer commands via CliRunner, no live API calls.

Uses `pytest-httpx` to stub the BCA REST endpoints the CLI hits.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bca_mcp.cli import config as cli_config
from bca_mcp.cli.main import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch, tmp_path):
    """Retarget CONFIG_DIR/CONFIG_FILE at a tmp dir + set API key env."""
    cfg_dir = tmp_path / ".bca"
    monkeypatch.setattr(cli_config, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(cli_config, "CONFIG_FILE", cfg_dir / "config.toml")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("BCA_API_KEY", "bca_test_key")
    # H-1: BCA_API_BASE is allowlisted, so tests must use an allowed host.
    # Staging is the canonical non-default allowed value.
    monkeypatch.setenv(
        "BCA_API_BASE", "https://staging-api.blockchainacademics.com"
    )
    # Other test files leave a shared client behind (set_client); drop it so
    # the commands build theirs from the env above.
    import bca_mcp.client as bca_client

    monkeypatch.setattr(bca_client, "_shared", None)
    yield


def test_help_lists_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("login", "config", "news", "market", "entity", "price", "explainer", "indicator", "agent", "version"):
        assert cmd in result.stdout


def test_config_show_without_file(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("BCA_API_KEY", raising=False)
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "Config file" in result.stdout


def test_login_writes_config():
    result = runner.invoke(app, ["login", "--api-key", "bca_live_abcdef1234567890"])
    assert result.exit_code == 0
    cfg = cli_config.CONFIG_FILE
    assert cfg.exists()
    contents = cfg.read_text()
    assert "bca_live_abcdef1234567890" in contents
    if os.name == "posix":
        assert oct(cfg.stat().st_mode)[-3:] == "600"


def test_login_rejects_empty_key():
    result = runner.invoke(app, ["login", "--api-key", "   "])
    assert result.exit_code == 1


def test_login_saves_a_local_api_base_the_client_allows():
    result = runner.invoke(
        app, ["login", "--api-key", "bca_k", "--api-base", "http://localhost:8000/"]
    )
    assert result.exit_code == 0, result.output
    assert cli_config.read_config()["api_base"] == "http://localhost:8000"


def test_login_refuses_an_api_base_the_client_refuses():
    result = runner.invoke(
        app, ["login", "--api-key", "bca_k", "--api-base", "https://proxy.example.com"]
    )
    assert result.exit_code == 1
    assert "Refusing to use BCA_API_BASE='https://proxy.example.com'" in " ".join(
        result.output.split()
    )
    assert not cli_config.CONFIG_FILE.exists()


def test_a_stored_bad_api_base_gives_one_error_line_not_a_traceback(monkeypatch):
    # Saved before the login check existed, or edited by hand.
    cli_config.write_config({"api_key": "bca_k", "api_base": "https://proxy.example.com"})
    monkeypatch.delenv("BCA_API_BASE")
    for args in (["news", "search", "bitcoin"], ["version"]):
        result = runner.invoke(app, args)
        assert result.exit_code == 1, result.output
        assert isinstance(result.exception, SystemExit)
        assert "Traceback" not in result.output
        assert "Error: Refusing to use BCA_API_BASE='https://proxy.example.com'" in " ".join(
            result.output.split()
        )


def test_news_search_pretty(httpx_mock):
    httpx_mock.add_response(
        json={
            "data": {
                "articles": [
                    {
                        "title": "Bitcoin ETF approved",
                        "published_at": "2026-04-20T10:00:00Z",
                        "source": "BCA Newsroom",
                        "cite_url": "https://blockchainacademics.com/articles/btc-etf",
                    }
                ]
            },
            "cite_url": "https://blockchainacademics.com/articles/btc-etf",
            "as_of": "2026-04-21T00:00:00Z",
        },
    )
    result = runner.invoke(app, ["news", "search", "bitcoin", "--limit", "5"])
    assert result.exit_code == 0
    assert "Bitcoin ETF approved" in result.stdout


def test_news_search_json(httpx_mock):
    httpx_mock.add_response(
        json={"data": {"articles": []}, "cite_url": None, "as_of": None},
    )
    result = runner.invoke(app, ["news", "search", "eth", "--json"])
    assert result.exit_code == 0
    assert "articles" in result.stdout


def test_version_command(httpx_mock):
    from bca_mcp import __version__
    httpx_mock.add_response(
        json={"data": {"version": "prod-abc123"}, "cite_url": None, "as_of": None},
    )
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


# --- commands against the API's response shapes (pass 2) -------------------

STAGING = "https://staging-api.blockchainacademics.com"


def _envelope(data, status="complete", diagnostic=None):
    meta = {"status": status, "request_id": "r", "pageInfo": {}}
    if diagnostic:
        meta["diagnostic"] = diagnostic
    return {"data": data, "attribution": {"citations": []}, "meta": meta}


def test_news_search_reads_results(httpx_mock):
    httpx_mock.add_response(
        url=f"{STAGING}/v1/articles/search?q=bitcoin&limit=10&offset=0",
        json=_envelope({
            "count": 1,
            "results": [{
                "title": "Spot ETF flows turn positive",
                "published_at": "2026-10-30T10:00:00Z",
                "source_name": "Blockchain Academics",
                "canonical_url": "https://blockchainacademics.com/news/etf-flows",
            }],
        }),
    )
    result = runner.invoke(app, ["news", "search", "bitcoin"])
    assert result.exit_code == 0, result.output
    # The table wraps long cells; check the words, not the whole title.
    for word in ("Spot", "ETF", "positive", "Blockchain"):
        assert word in result.stdout, word
    assert "No results" not in result.stdout


def test_entity_reads_the_nested_dossier_and_shows_partial(httpx_mock):
    httpx_mock.add_response(
        url=f"{STAGING}/v1/entities/ethereum",
        json=_envelope(
            {"result": {"slug": "ethereum", "display_name": "Ethereum", "kind": "chain",
                        "ticker": "ETH", "summary": "Smart contract chain"}},
            status="partial",
            diagnostic={"reason": "entity_not_enriched", "missing": ["mentions"]},
        ),
    )
    result = runner.invoke(app, ["entity", "ethereum"])
    assert result.exit_code == 0, result.output
    assert "Ethereum" in result.stdout and "ETH" in result.stdout
    assert "Smart contract chain" in result.stdout
    assert "untrusted_content" not in result.stdout
    assert "partial" in result.stdout


def test_price_takes_coingecko_ids(httpx_mock):
    httpx_mock.add_response(
        url=f"{STAGING}/v1/market/price?ids=bitcoin%2Cethereum&vs=usd",
        json=_envelope({
            "bitcoin": {"usd": 70000, "usd_24h_change": 1.5, "usd_market_cap": 1.4e12},
            "ethereum": {"usd": 2500, "usd_24h_change": -0.5, "usd_market_cap": 3.0e11},
        }),
    )
    result = runner.invoke(app, ["price", "bitcoin,ethereum"])
    assert result.exit_code == 0, result.output
    assert "BITCOIN" in result.stdout and "70000" in result.stdout
    assert "+1.50%" in result.stdout


def test_market_overview_reads_coingecko_rows(httpx_mock):
    httpx_mock.add_response(
        url=f"{STAGING}/v1/market/overview?limit=10",
        json=_envelope([
            {"symbol": "btc", "current_price": 70000, "price_change_percentage_24h": 2.0,
             "market_cap": 1.4e12},
        ]),
    )
    result = runner.invoke(app, ["market", "overview"])
    assert result.exit_code == 0, result.output
    assert "BTC" in result.stdout and "70000" in result.stdout and "+2.00%" in result.stdout


def test_explainer_renders_a_lesson_body(httpx_mock):
    httpx_mock.add_response(
        url=f"{STAGING}/v1/academy/decentralized-exchanges",
        json=_envelope({"result": {"title": "Decentralized Exchanges", "result_type": "lesson",
                                   "body_md": "A DEX matches trades on chain."}}),
    )
    result = runner.invoke(app, ["explainer", "decentralized-exchanges"])
    assert result.exit_code == 0, result.output
    assert "A DEX matches trades on chain." in result.stdout


def test_indicator_calls_the_api_route_with_entity_slug(httpx_mock):
    httpx_mock.add_response(
        url=f"{STAGING}/v1/indicators/coverage?entity_slug=bitcoin&window=30d",
        json=_envelope({"indicator": "coverage_index", "window": "30d", "value": 0.4}),
    )
    result = runner.invoke(app, ["indicator", "coverage-index", "bitcoin", "-w", "30d"])
    assert result.exit_code == 0, result.output
    assert "0.4" in result.stdout


def test_indicator_risk_score_sends_no_window(httpx_mock):
    httpx_mock.add_response(
        url=f"{STAGING}/v1/indicators/risk?entity_slug=bitcoin",
        json=_envelope({"indicator": "risk_score", "value": 0.2}),
    )
    result = runner.invoke(app, ["indicator", "risk-score", "bitcoin"])
    assert result.exit_code == 0, result.output


def test_indicator_rejects_unknown_names_and_windows(httpx_mock):
    result = runner.invoke(app, ["indicator", "hype-index", "bitcoin"])
    assert result.exit_code == 1
    result = runner.invoke(app, ["indicator", "sentiment-velocity", "bitcoin", "-w", "90d"])
    assert result.exit_code == 1
    assert "BCA_BAD_REQUEST" in result.output and "window" in result.output


def test_agent_posts_to_the_skill_route_and_reads_result(httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url=f"{STAGING}/v1/agent-jobs/due-diligence",
        json=_envelope({"job_id": "11111111-2222-3333-4444-555555555555", "status": "queued"}),
        status_code=202,
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{STAGING}/v1/agent-jobs/11111111-2222-3333-4444-555555555555",
        json=_envelope({"status": "done", "kind": "due_diligence",
                        "result": {"markdown": "Due diligence report body"}}),
    )
    result = runner.invoke(app, ["agent", "due-diligence", "--entity", "ethereum"])
    assert result.exit_code == 0, result.output
    assert "Due diligence report body" in result.stdout
    import json as _json

    post = httpx_mock.get_requests(method="POST")[0]
    assert _json.loads(post.content) == {"entity_slug": "ethereum", "depth": "standard", "focus": []}


def test_agent_translate_contract_sends_the_code(httpx_mock, tmp_path):
    src = tmp_path / "Token.sol"
    src.write_text("contract Token { uint x; }", encoding="utf-8")
    httpx_mock.add_response(
        method="POST",
        url=f"{STAGING}/v1/agent-jobs/translate-contract",
        json=_envelope({"job_id": "j-1"}),
        status_code=202,
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{STAGING}/v1/agent-jobs/j-1",
        json=_envelope({"status": "done", "kind": "translate_contract",
                        "result": {"target_code": "module token {}"}}),
    )
    result = runner.invoke(app, [
        "agent", "translate-contract", "--code-file", str(src),
        "--source", "solidity", "--target", "move",
    ])
    assert result.exit_code == 0, result.output
    import json as _json

    body = _json.loads(httpx_mock.get_requests(method="POST")[0].content)
    assert body == {
        "code": "contract Token { uint x; }",
        "source_language": "solidity",
        "target_language": "move",
    }


def test_agent_reports_missing_options_without_a_request(httpx_mock):
    result = runner.invoke(app, ["agent", "due-diligence"])
    assert result.exit_code == 1
    assert "entity_slug" in result.output
    result = runner.invoke(app, ["agent", "translate-contract"])
    assert result.exit_code == 1
    assert "--code-file" in result.output
