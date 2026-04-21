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
    monkeypatch.setenv("BCA_API_BASE", "https://api.test.local")
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
