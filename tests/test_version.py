"""One version everywhere: pyproject, __version__, the User-Agent, and the TS
sibling the parity fixture was dumped from (the two packages ship in lockstep).
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from bca_mcp import __version__
from bca_mcp.client import USER_AGENT

ROOT = Path(__file__).resolve().parent.parent


def test_versions_agree() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text("utf-8"))["project"]
    assert project["version"] == __version__
    assert USER_AGENT.startswith(f"bca-mcp/{__version__} ")
    fixture = ROOT / "tests" / "fixtures" / f"ts_tools_{__version__.replace('.', '_')}.json"
    source = json.loads(fixture.read_text("utf-8"))["source"]
    assert f"@blockchainacademics/mcp {__version__} " in source


def test_python_classifiers_respect_requires_python() -> None:
    # PyPI shows these; none may name a Python older than requires-python.
    project = tomllib.loads((ROOT / "pyproject.toml").read_text("utf-8"))["project"]
    floor = tuple(int(p) for p in project["requires-python"].removeprefix(">=").split("."))
    listed = [
        tuple(int(p) for p in c.rsplit(" :: ", 1)[1].split("."))
        for c in project["classifiers"]
        if c.startswith("Programming Language :: Python :: 3.")
    ]
    assert listed and all(v >= floor for v in listed), listed


def test_changelog_has_a_section_for_this_version() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text("utf-8")
    assert f"## [{__version__}]" in changelog
