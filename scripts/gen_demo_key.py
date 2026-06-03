#!/usr/bin/env python3
"""Generate src/bca_mcp/_demo_key.py from scripts/demo-key.txt.

The demo key is a public, rate-limited fallback baked into the package.
When BCA_API_KEY is unset, BcaClient uses this value so `uvx bca-mcp` is
a true zero-config demo. The TS sibling has the same file at
scripts/demo-key.txt and the same gen script — both must match byte-for-byte
before tagging a release. See plan: ok-lets-use-all-glowing-plum.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
TXT = REPO_ROOT / "scripts" / "demo-key.txt"
OUT = REPO_ROOT / "src" / "bca_mcp" / "_demo_key.py"


def main() -> int:
    raw = TXT.read_text(encoding="utf-8").strip()
    if not raw.startswith("bca_demo_"):
        sys.stderr.write(
            "gen_demo_key: refusing to emit — scripts/demo-key.txt does not "
            "start with 'bca_demo_'\n"
        )
        return 1
    if len(raw) != len("bca_demo_") + 40:
        sys.stderr.write(
            f"gen_demo_key: demo-key.txt expected to be 'bca_demo_' + 40 hex "
            f"chars; got length {len(raw)}\n"
        )
        return 1

    body = (
        "# GENERATED — do not edit by hand. Source: scripts/demo-key.txt.\n"
        "# Regenerate via: python scripts/gen_demo_key.py\n"
        "#\n"
        "# Public demo key baked into the package. When BCA_API_KEY is unset,\n"
        "# BcaClient falls back to this value so uvx bca-mcp is a true zero-config\n"
        "# demo. The backend recognises it and routes to the demo-tier allowlist\n"
        "# + per-IP rate limiter. Public by design; rate limits bound abuse.\n"
        f'BCA_DEMO_KEY_FALLBACK = "{raw}"\n'
    )
    OUT.write_text(body, encoding="utf-8")
    print(f"gen_demo_key: wrote {OUT} (key len={len(raw)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
