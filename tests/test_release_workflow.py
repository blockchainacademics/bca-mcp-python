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
