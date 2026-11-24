"""No file of the package holds a hidden or direction character itself.

A zero width space, a soft hyphen or a right-to-left override written into a
source file cannot be seen in an editor or a review, and GitHub marks such a
file with its hidden Unicode warning. The code and the tests write these
characters as escapes (\\u200b), so what a file holds is what a reader sees.

The cleaners' sets stay the ones of design-final.md appendix C.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bca_mcp._untrusted import _FENCE_HIDDEN_RE
from bca_mcp.tools import stats

ROOT = Path(__file__).resolve().parent.parent
SCANNED = ("src", "tests", "scripts", ".github", "docs", "examples")
TOP_FILES = ("README.md", "CHANGELOG.md", "pyproject.toml", "requirements.lock.txt")
SUFFIXES = {".py", ".md", ".yml", ".yaml", ".toml", ".txt", ".json", ".ts"}

# Appendix C: control characters, U+007F to U+009F, the soft hyphen, U+061C,
# the Hangul fillers, U+17B4 and U+17B5, the Mongolian selectors, the zero
# width and direction marks, the separators and overrides, the word joiners
# and invisible operators, the variation selectors, the byte order mark and
# U+FFF0 to U+FFFB.
APPENDIX_C = (
    set(range(0x00, 0x20)) | set(range(0x7F, 0xA0))
    | {0xAD, 0x61C, 0x115F, 0x1160, 0x17B4, 0x17B5, 0x3164, 0xFEFF, 0xFFA0}
    | set(range(0x180B, 0x1810)) | set(range(0x200B, 0x2010)) | set(range(0x2028, 0x202F))
    | set(range(0x2060, 0x2070)) | set(range(0xFE00, 0xFE10)) | set(range(0xFFF0, 0xFFFC))
)


def _files() -> list[Path]:
    found = [ROOT / name for name in TOP_FILES if (ROOT / name).is_file()]
    for folder in SCANNED:
        found += sorted(p for p in (ROOT / folder).rglob("*") if p.is_file() and p.suffix in SUFFIXES)
    return found


def test_no_file_holds_a_hidden_or_direction_character() -> None:
    files = _files()
    assert any(p.name == "stats.py" for p in files)
    hits = []
    for path in files:
        text = path.read_text("utf-8")
        for number, line in enumerate(text.split("\n"), 1):
            for ch in _FENCE_HIDDEN_RE.findall(line):
                hits.append(f"{path.relative_to(ROOT)}:{number}: U+{ord(ch):04X}")
    assert hits == [], hits[:20]


@pytest.mark.parametrize(
    "pattern,kept",
    [(stats._HIDDEN, set()), (_FENCE_HIDDEN_RE, {0x09, 0x0A, 0x0D})],
    ids=["stats", "fence"],
)
def test_the_cleaners_take_out_the_characters_of_appendix_c(pattern, kept) -> None:
    taken = {cp for cp in range(0x10000) if pattern.fullmatch(chr(cp))}
    assert taken == APPENDIX_C - kept
    assert not any(pattern.fullmatch(chr(cp)) for cp in (0x10000, 0x1F600, 0xE0001, 0x10FFFF))
