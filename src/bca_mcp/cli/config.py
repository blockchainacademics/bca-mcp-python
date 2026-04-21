"""CLI config file at `~/.bca/config.toml` — stores API key + base URL.

Env vars (`BCA_API_KEY`, `BCA_API_BASE`) take precedence over stored values.
Config is chmod 600 — plaintext key on disk, user-scoped.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

import tomli_w

CONFIG_DIR = Path.home() / ".bca"
CONFIG_FILE = CONFIG_DIR / "config.toml"


def read_config() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return tomllib.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):
        return {}


def write_config(data: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(mode=0o700, exist_ok=True)
    CONFIG_FILE.write_bytes(tomli_w.dumps(data).encode("utf-8"))
    try:
        CONFIG_FILE.chmod(0o600)
    except OSError:  # pragma: no cover — non-POSIX fallback
        pass


def apply_env_defaults() -> None:
    """Load config into env vars unless env already set.

    Called at the top of every CLI command so `BcaClient()` (which reads
    env) picks up stored values transparently. Env wins — no clobbering.
    """
    cfg = read_config()
    if not os.environ.get("BCA_API_KEY") and cfg.get("api_key"):
        os.environ["BCA_API_KEY"] = str(cfg["api_key"])
    if not os.environ.get("BCA_API_BASE") and cfg.get("api_base"):
        os.environ["BCA_API_BASE"] = str(cfg["api_base"])


def mask_key(key: str | None) -> str:
    if not key:
        return "(not set)"
    if len(key) < 12:
        return "***"
    return f"{key[:8]}…{key[-4:]}"
