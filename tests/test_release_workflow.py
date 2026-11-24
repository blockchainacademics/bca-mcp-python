"""The PyPI release workflow (design-final.md task R2, AGENTS-12).

Every action is pinned by its full commit, so no step runs code that a moved
branch or tag points at. Publishing stays in its own job, in the `pypi`
environment whose required reviewer approves each release, and that job
alone holds the publishing identity.
"""

from __future__ import annotations

import re
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "publish.yml"


def _jobs(text: str) -> dict[str, str]:
    body = text.split("\njobs:\n", 1)[1]
    parts = re.split(r"^  ([a-z][a-z0-9_-]*):\n", body, flags=re.M)
    return dict(zip(parts[1::2], parts[2::2]))


def test_every_action_is_pinned_by_its_commit() -> None:
    text = WORKFLOW.read_text("utf-8")
    uses = re.findall(r"^\s*-?\s*uses:\s*(\S+)(.*)$", text, flags=re.M)
    assert len(uses) == 7
    for action, comment in uses:
        assert re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{40}", action), action
        assert re.fullmatch(r"\s*# v[0-9]+(\.[0-9]+)*", comment), f"{action} names no release in a comment"
    assert any(a.startswith("pypa/gh-action-pypi-publish@") for a, _ in uses)


def test_the_jobs_stay_split_and_the_publish_job_alone_holds_the_identity() -> None:
    jobs = _jobs(WORKFLOW.read_text("utf-8"))
    assert list(jobs) == ["test", "build", "publish"]
    publish = jobs["publish"]
    assert "environment: pypi" in publish
    assert "id-token: write" in publish
    assert "needs: [build, test]" in publish
    for name in ("test", "build"):
        assert "id-token" not in jobs[name], name
    # The publish job downloads the built files and installs or tests nothing.
    for forbidden in ("pip install", "pytest", "python -m build", "checkout@"):
        assert forbidden not in publish, forbidden


def test_every_token_reads_the_repository_and_no_more() -> None:
    # Review finding 8: the test job installs dependencies and runs the
    # repository's code, so its token must be read only.
    text = WORKFLOW.read_text("utf-8")
    top = text.split("\njobs:\n", 1)[0]
    assert re.search(r"^permissions:\n  contents: read\n(?![ ])", top + "\n", flags=re.M), "no read only default"
    jobs = _jobs(text)
    for name in ("test", "build"):
        assert "permissions:" not in jobs[name], f"{name} widens its token"
    assert "    permissions:\n      contents: read\n      id-token: write\n    steps:" in jobs["publish"]


def test_no_checkout_keeps_the_token() -> None:
    text = WORKFLOW.read_text("utf-8")
    checkouts = re.findall(r"^\s*- uses: actions/checkout@.*$", text, flags=re.M)
    kept_out = re.findall(
        r"^\s*- uses: actions/checkout@[0-9a-f]{40} # v[0-9.]+\n\s+with:\n\s+persist-credentials: false$",
        text,
        flags=re.M,
    )
    assert len(checkouts) == 2 and len(kept_out) == len(checkouts)


def test_the_built_wheel_is_checked_for_every_tool() -> None:
    # The release build and CI both assert the count the source tree lists, so
    # a wheel that lost a module fails before anything is uploaded. Owner
    # switch 2 changes the count: this test then names both lines.
    from bca_mcp.server import TOOLS

    ci = WORKFLOW.parent / "ci.yml"
    for path in (WORKFLOW, ci):
        counts = re.findall(r"from bca_mcp\.server import TOOLS; assert len\(TOOLS\) == ([0-9]+)", path.read_text("utf-8"))
        assert counts == [str(len(TOOLS))], f"{path.name}: {counts}"
