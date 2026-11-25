"""Prompt-injection fence hardening.

The MCP server wraps untrusted upstream text (news article bodies,
whitepapers, contract source, event descriptions, entity dossiers) inside
``<untrusted_content …>…</untrusted_content>`` fences so the host LLM treats
it as data, not instructions. That defence is only sound if the upstream text
cannot itself contain the fence's *closing* token: an attacker who embeds a
literal ``</untrusted_content>`` in — say — an article body would otherwise
close the fence early, and everything after it would be read by the host model
as trusted instructions (classic fence-escape / prompt injection).

``neutralize_fence_tokens`` rewrites any literal fence tag — opening OR
closing — found inside upstream text into an inert, still-human-readable form
(``&lt;/untrusted_content&gt;``) so the fence can never be broken (or forged)
from within. It is deliberately tolerant of:

  * case            — ``</UNTRUSTED_CONTENT>`` is caught
  * internal spaces — ``< / untrusted_content >`` is caught
  * attributes      — ``<untrusted_content source="x">`` is caught

Call it on the raw upstream value *before* wrapping that value in a real
fence. Our own fence delimiters are added afterwards and are therefore never
touched.

Kept behaviourally identical to the TS sibling (``src/untrusted.ts``): both
neutralize to the same ``&lt;…&gt;`` bytes so the two servers emit identical
output for the same payload.

0.7.0 (AGENTS-08 fixes 1, 2 and 7): before the whole-data fence neutralizes
tags, every string of the payload, the keys of its objects included, is
cleaned with ``clean_fence_value``:
NFKC, so fullwidth brackets become plain ones, then the hidden characters
out, so a zero width space or a soft hyphen cannot split a tag name. A
look-alike tag then becomes a plain tag, which ``neutralize_fence_tokens``
catches. Tab, line feed and carriage return stay, so article bodies and
contract code keep their lines. The fence itself carries an id made new for
each answer (``new_fence_id``), which a tag planted upstream cannot know.
"""

from __future__ import annotations

import re
import secrets
import unicodedata
from typing import Any

# Matches an opening OR closing untrusted_content tag. ``/?`` covers the
# closing slash; the leading/trailing ``\s*`` and the ``\s*`` around the slash
# tolerate obfuscation whitespace; ``[^>]*`` swallows any attributes on the
# opening form up to the terminating ``>``.
# `(?:/\s*)?` in place of `/?\s*`: the same matches, in linear time (two runs of
# spaces next to each other made the old form backtrack with the square of
# their length). The TypeScript package holds the same pattern.
_FENCE_TAG_RE = re.compile(r"<\s*(?:/\s*)?untrusted_content\b[^>]*>", re.IGNORECASE)


def _escape_tag(match: "re.Match[str]") -> str:
    # Escape only the angle brackets: the token stays legible to a human
    # reading the transcript/logs, but can no longer be parsed as a real
    # fence delimiter by the host model.
    return match.group(0).replace("<", "&lt;").replace(">", "&gt;")


def neutralize_fence_tokens(text: str) -> str:
    """Defang every embedded ``<untrusted_content …>`` / ``</untrusted_content>``
    token in ``text`` so upstream content cannot break out of (or forge) a
    fence. Non-strings and empty strings pass through unchanged.
    """
    if not isinstance(text, str) or not text:
        return text
    return _FENCE_TAG_RE.sub(_escape_tag, text)


# The hidden characters of the Stats design's cleaners (design-final.md
# appendix C), less tab, line feed and carriage return. The same set as
# FENCE_HIDDEN_RE in the TS sibling's src/untrusted.ts.
_FENCE_HIDDEN_RE = re.compile(
    "[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f\u00ad\u061c\u115f\u1160"
    "\u17b4\u17b5\u180b-\u180f\u200b-\u200f\u2028-\u202e\u2060-\u206f\u3164"
    "\ufe00-\ufe0f\ufeff\uffa0\ufff0-\ufffb\U000e0000-\U000e007f]"
)


def clean_fence_text(text: str) -> str:
    """One text cleaned before the whole-data fence neutralizes tags: NFKC,
    then the hidden characters out."""
    return _FENCE_HIDDEN_RE.sub("", unicodedata.normalize("NFKC", text))


def clean_fence_value(value: Any) -> Any:
    """A copy of a payload with every string in it cleaned, the keys of its
    objects included: a key is part of the fenced text too. Every other value
    stays as it is. Two keys that clean to the same text keep the place of
    the earlier one and the value of the later one, as in the TS sibling."""
    if isinstance(value, str):
        return clean_fence_text(value)
    if isinstance(value, list):
        return [clean_fence_value(v) for v in value]
    if isinstance(value, dict):
        return {
            (clean_fence_text(k) if isinstance(k, str) else k): clean_fence_value(v)
            for k, v in value.items()
        }
    return value


def new_fence_id() -> str:
    """The id of one whole-data fence: 16 hex characters from the system's
    random source, made new for each answer."""
    return secrets.token_hex(8)


def wrap_untrusted(source: str, text: str) -> str:
    """Fence one upstream string: neutralize embedded fence tags, then wrap it
    in ``<untrusted_content source="...">`` so the host model reads it as data.

    Same bytes as the per-field fences the tool modules apply to article
    bodies and job output. Non-strings and empty strings pass through.
    """
    if not isinstance(text, str) or not text:
        return text
    return (
        f'<untrusted_content source="{source}">\n'
        f"{neutralize_fence_tokens(text)}\n"
        "</untrusted_content>"
    )
