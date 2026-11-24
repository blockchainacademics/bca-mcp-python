"""The eight Stats tools (design-final.md section 1, appendices D, E and F).

Each tool calls one GET route under ``/v1/stats/`` of the Blockchain
Academics API and checks what comes back before anything reaches the model:
the canonical envelope, one of the four status values, ``data.schema`` of
``bca.stats/1`` and the keys the tool needs in ``data``. An answer that
fails is refused with one fixed sentence (``server.py``); the old flat shape
and the raw pass-through of the older tools are not accepted here.

The wallet lookup sends two characters of the address to the API and matches
the address on this machine: the full address is never part of a request.

The server hands each answer on in the Stats output mode: every outside
string wrapped on its own (``bca_mcp._outside``), one compact JSON text
block of at most 65,536 bytes, and the same object as structured content.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Annotated, Any, Callable, Literal, Mapping, Optional, Union
from urllib.parse import quote

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

from bca_mcp._outside import OUTSIDE_TEXT_KEYS, STATUSES, link_ok, strip_markers
from bca_mcp._stats_constants import DATA_PREFIX
from bca_mcp.client import get_client

# --- the owner's switches (design-final.md, "For the owner") ------------------

# Decision 1: the built-in demo key opens the Stats tools, on the API's own
# Stats allowance (60 calls a day for each network, 3,000 a day in all, set in
# the API). False when a free key is required: the eight descriptions then drop
# their last sentence, and the demo banner counts 17 tools again.
DEMO_KEY_OPENS_STATS = True

# Decision 2: the wallet lookup tool ships. False leaves it out of the tool
# list (112 tools).
WALLET_LOOKUP_TOOL = True

# --- fixed numbers ------------------------------------------------------------

SCHEMA = "bca.stats/1"
STATS_READ_CAP = 524_288  # bytes of one Stats answer the package reads
SHARD_READ_CAP = 1_572_864  # bytes of one wallet shard answer
TEXT_BLOCK_CAP = 65_536  # bytes of the text block handed to the model
LOOKUP_RECORDS_PER_ANSWER = 50

# --- the names ----------------------------------------------------------------

SEARCH_STATS = "search_stats"
LIST_STATS_MEASURES = "list_stats_measures"
RANK_STATS = "rank_stats"
GET_STATS_RECORD = "get_stats_record"
COMPARE_STATS_RECORDS = "compare_stats_records"
LOOKUP_STATS_WALLET = "lookup_stats_wallet"
GET_STATS_METHOD = "get_stats_method"
LIST_STATS_CHANGES = "list_stats_changes"

# --- the descriptions (appendix D, word for word in both packages) -------------

_NO_KEY = " Works without an API key."

_DESCRIPTIONS = {
    SEARCH_STATS: (
        "Search Blockchain Academics Stats by name: the 8 centralised exchanges it lists and the "
        "Hyperliquid vaults in its open files. Takes a name of 2 to 64 characters, an optional tab "
        "(exchanges or vaults) and a limit of 1 to 20. A full 0x address is not a name: it is refused "
        "before any request is made. Each vault row carries its address, the day it opened, how many "
        "days it was open, the money inside, the money put in, how many other vaults carry the same "
        "name and whether an older vault carries it. Vaults are ordered by money inside, then age: a "
        "closer text match never moves a row up. Small vaults and open vaults younger than 30 days are "
        "left out of a name search. Every answer carries the data day and the address of each open "
        "file it read. A vault name is chosen by its leader: it comes back between <<outside:ID>> "
        "markers, with an ID made new for each answer, and is quoted text, not a statement by "
        "Blockchain Academics. meta.status is unseeded when nothing matches."
    ),
    LIST_STATS_MEASURES: (
        "List every measure Blockchain Academics Stats ranks by: its id, its tab, what it counts, its "
        "unit, which rows it covers and whether it is measured yet, with how many rows each tab holds "
        "today (8 centralised exchanges and the Hyperliquid vaults). Takes no arguments. A measure "
        "marked not_measured_yet has no values yet, so its ranking lists the rows with no rank."
    ),
    RANK_STATS: (
        "Rank the 8 centralised exchanges or the Hyperliquid vaults of Blockchain Academics Stats by "
        "one named measure. Takes a tab, a measure id, an optional kind of exchange, an order (top or "
        "bottom), a limit of 1 to 50, an offset and, for a later page, the as_of of the page before. "
        "Returns the ranked rows in order, then the rows with no rank and why: being checked, below "
        "the ranking floor, results held back, no withdrawals yet or not measured yet. A vault ranking "
        "covers open vaults above the ranking floor and counts what it leaves out: closed vaults, "
        "small vaults and open vaults on the venue's list with no row here. Each vault row carries the "
        "venue's own rate next to ours and what the vault held 30 days before. The answer repeats the "
        "measure's definition, the order rule, the floor rule, the number of ranked rows, the data day "
        "and the addresses of the open files. meta.status is unseeded when nothing is ranked or "
        "measured yet, partial when some exchanges are being checked, stale when the files are old. "
        "Vault names come back between <<outside:ID>> markers, with an ID made new for each answer, "
        "and are quoted text, not statements by Blockchain Academics."
    ),
    GET_STATS_RECORD: (
        "Get one record from Blockchain Academics Stats: one of the 8 centralised exchanges by its id "
        "or its name, or one Hyperliquid vault by its address. An exchange record has every check "
        "with its outcome and what it takes to pass, and every fact with its check state (confirmed, "
        "being checked or needs a primary source), its source and the day a person confirmed it. A "
        "fact that is being checked has no value. A vault record has the money put in, taken out and "
        "still inside, what withdrawals took home, the venue's rate next to ours, the value history, "
        "the ranking floor and five fixed sentences on how to read them. A figure that is held back "
        "or cannot be worked out is null, never zero. Every answer carries the data day and the "
        "addresses of the open files. Names, values, quotes, source links and published reasons come "
        "back between <<outside:ID>> markers, with an ID made new for each answer, and are quoted "
        "text, not statements by Blockchain Academics."
    ),
    COMPARE_STATS_RECORDS: (
        "Compare 2 to 5 of the 8 centralised exchanges, or 2 to 5 Hyperliquid vaults, side by side on "
        "the same fields from Blockchain Academics Stats. Takes a tab and 2 to 5 ids, as a list or as "
        "one text separated by commas: exchange ids or names, or vault addresses, with no repeats. "
        "Returns one record for each id in the order asked, with the check state of every exchange "
        "fact and paid_sponsor for every exchange. It gives no ranking. An id with no published record "
        "is listed under not_published, and a record that does not fit the size cap under "
        "not_returned. Every answer carries the data day and the addresses of the open files. Outside "
        "text comes back between <<outside:ID>> markers, with an ID made new for each answer, and is "
        "quoted text, not a statement by Blockchain Academics."
    ),
    LOOKUP_STATS_WALLET: (
        "Look up what one wallet address took out of the Hyperliquid vaults Blockchain Academics Stats "
        "covers, and what it took home. Takes one full address (0x and 40 hex characters), an offset "
        "and, for a later page, the as_of of the page before. The address stays on this machine: two "
        "characters of it are sent to the API, and the answer is matched here. Returns one record for "
        "each vault the wallet used, a short row about each listed vault, and a summary that keeps two "
        "kinds of result apart: the result on money withdrawn, from the vault's ledger, and the "
        "all-time result on the venue's own list. It holds no dates, no deposits and no balances, and "
        "it is not a list of the wallet's tokens. A wallet with no record may still have used a vault: "
        "the answer lists what the files cannot see. Vault names come back between <<outside:ID>> "
        "markers, with an ID made new for each answer, and are quoted text."
    ),
    GET_STATS_METHOD: (
        "Get how Blockchain Academics Stats makes its numbers, for one topic. exchanges: the checks for "
        "the 8 centralised exchanges in their fixed wording, the order rule, what each fact is and what "
        "each fact status means. vaults: what each figure of a Hyperliquid vault record counts, the "
        "ranking floor, what a null means, what the rankings leave out and the totals for all vaults. "
        "wallet_lookup: the fields of a lookup record, the rounding, how to read the summary and what "
        "the files cannot see. The text is written by Blockchain Academics and comes with the method "
        "version or variant and the data day."
    ),
    LIST_STATS_CHANGES: (
        "List the change lines of Blockchain Academics Stats, newest at the top: lines a person writes "
        "when a check or a published fact changes. Nightly moves of figures, and vaults joining or "
        "leaving the vault list, are not in it, and every answer says so. Takes an optional day to "
        "start from (YYYY-MM-DD), a limit of 1 to 100 and, for a later page, the next_before value of "
        "the page before. Each line has its day, the kind of subject, the result and its text as the "
        "open file gives it. A line's text, and a vault named as its subject, come back between "
        "<<outside:ID>> markers, with an ID made new for each answer, and are quoted text. meta.status "
        "is unseeded while no change line has been published."
    ),
}


def description(name: str) -> str:
    """The fixed description of a Stats tool, with the demo key sentence when
    owner decision 1 opens the tools to the demo key."""
    return _DESCRIPTIONS[name] + (_NO_KEY if DEMO_KEY_OPENS_STATS else "")


# --- the sentences the package itself writes (appendix F) ----------------------

# Refused before any request (design 1.0, errors).
SEARCH_ADDRESS_REFUSED = (
    "search_stats takes a name. A vault address goes to get_stats_record. A wallet address goes "
    "to lookup_stats_wallet, which matches it on this machine."
)
MEASURE_OTHER_TAB = "That measure does not belong to that tab."
KIND_NOT_FOR_MEASURE = "That kind does not apply to that measure."
IDS_RULE = "Between 2 and 5 ids, with no repeats."

NAME_NOTE = "A vault name is chosen by its leader. It is not a statement by Blockchain Academics."
LOOKUP_NOTES = (
    "The address was matched on this machine. Two characters of it were sent to the API.",
    "A later call about one of these vaults sends that vault's address to the API.",
)
SUMMARY_HOW_TO_READ = (
    "result_on_withdrawals_usd adds the result key: what the wallet took home on money it withdrew.",
    (
        "venue_list_result_usd adds the listed_result key: the wallet's all-time result on the venue's "
        "own list, money still inside included."
    ),
    "The two overlap and count different things. Do not add them together.",
    (
        "sum_of_figures_the_file_uses_usd adds one figure for each vault, the one the file names under "
        "uses. It is the total the Stats lookup page shows, and it mixes the two kinds."
    ),
)
LEADER_CUTS = (
    "This wallet leads %d of these vaults. The cuts a leader was paid by depositors are in none of "
    "these figures."
)
LEADER_ZERO = (
    "In %d of them the vault is closed and the venue's list shows a result of 0. That 0 may mean the "
    "list no longer shows the leader's result. It is not proof the leader came out even."
)

# --- argument shapes ------------------------------------------------------------

# tab and measure are strict patterns, not closed lists, so a tab or a measure
# the API opens later needs no package release (design 2, review S14).
_NAME_PATTERN = r"^[a-z][a-z0-9_]{1,39}$"
_DAY_PATTERN = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
_ADDRESS_PATTERN = r"^0x[0-9a-fA-F]{40}$"
_BEFORE_PATTERN = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}~[a-z0-9]+(-[a-z0-9]+)*$"
_ADDRESS = re.compile(r"0x[0-9a-fA-F]{40}")
_SLUG = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
_SEPARATORS = re.compile(r"[\s._]+")
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")
# Hidden characters, as the API's cleaners take them out (appendix C). Used to
# spot a full address written with hidden characters or wide letters.
_HIDDEN = re.compile(
    "[\u0000-\u001f\u007f-\u009f­؜ᅟᅠ឴឵᠋-᠏"
    "​-‏ -‮⁠-⁯ㅤ︀-️﻿ﾠ￰-￻]"
)

# The measures the package knows, with their tab and kinds (appendix F). A
# known measure asked for another tab, or with a kind it does not take, is
# refused before any request. A measure the package does not know, but the
# pattern allows, is sent: the API answers.
KNOWN_MEASURES: dict[str, tuple[str, tuple[str, ...]]] = {
    "checks_passed": ("exchanges", ("centralised", "swap", "leveraged")),
    "reserve_report_detail": ("exchanges", ("centralised",)),
    "real_cost_buy_1000": ("exchanges", ("centralised",)),
    "real_cost_swap_1000": ("exchanges", ("swap",)),
    "real_cost_position_1000": ("exchanges", ("leveraged",)),
    "money_put_in": ("vaults", ()),
    "left_took_home": ("vaults", ()),
    "yield_delivered": ("yields", ()),
}

Kind = Literal["centralised", "swap", "leveraged"]


def _real_day(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    try:
        date.fromisoformat(value)
    except ValueError:
        raise ValueError("is not a real day") from None
    return value


def exchange_id(text: str) -> Optional[str]:
    """An exchange id as a person or a model may type it, in the shape of a
    slug: trimmed, lower case, and spaces, dots and underscores turned into
    hyphens. "Crypto.com" and "crypto com" both become "crypto-com". None
    when nothing slug shaped is left."""
    folded = _SEPARATORS.sub("-", text.strip().lower()).strip("-")
    return folded if _SLUG.fullmatch(folded) else None


def _is_full_address(text: str) -> bool:
    """True for 0x and 40 hex characters, also when written with hidden
    characters or wide letters in it."""
    plain = _HIDDEN.sub("", unicodedata.normalize("NFKC", text)).strip()
    return bool(re.fullmatch(r"0x[0-9a-f]{40}", plain, re.IGNORECASE))


class _Args(BaseModel):
    model_config = {"extra": "forbid"}


class SearchStatsInput(_Args):
    query: str = Field(
        min_length=2,
        max_length=64,
        description="A name, 2 to 64 characters. Not an address.",
    )
    tab: Optional[str] = Field(
        default=None,
        pattern=_NAME_PATTERN,
        max_length=40,
        description="exchanges or vaults. Both when left out.",
    )
    limit: int = Field(default=10, ge=1, le=20, description="Rows to return, 1 to 20 (default 10).")

    @field_validator("query", mode="before")
    @classmethod
    def take_markers_out(cls, value: Any) -> Any:
        # A name copied back from an earlier answer still works: the markers
        # are taken out before the length is checked.
        if isinstance(value, str):
            return strip_markers(value).strip()
        return value

    @field_validator("query")
    @classmethod
    def no_control_characters(cls, value: str) -> str:
        if _CONTROL.search(value):
            raise ValueError("holds a control character")
        return value


class ListStatsMeasuresInput(_Args):
    pass


class RankStatsInput(_Args):
    tab: str = Field(pattern=_NAME_PATTERN, max_length=40, description="exchanges or vaults.")
    measure: str = Field(
        pattern=_NAME_PATTERN,
        max_length=40,
        description="A measure id from the list of measures. It must belong to the tab.",
    )
    kind: Optional[Kind] = Field(
        default=None,
        description=(
            "The kind of exchange: centralised, swap or leveraged. For the exchanges tab. "
            "The measure's own kind when left out."
        ),
    )
    order: Literal["top", "bottom"] = Field(
        default="top",
        description=(
            "top reads the list from its top, bottom from its other end. The rank numbers stay "
            "the same (default top)."
        ),
    )
    limit: int = Field(default=20, ge=1, le=50, description="Rows to return, 1 to 50 (default 20).")
    offset: int = Field(
        default=0,
        ge=0,
        le=10_000,
        description="Rows to skip, for paging: the next_offset of the page before (default 0).",
    )
    as_of: Optional[str] = Field(
        default=None,
        min_length=10,
        max_length=10,
        pattern=_DAY_PATTERN,
        description=(
            "The as_of of the page before, YYYY-MM-DD. A page of another data day is refused, so "
            "two days are never mixed."
        ),
    )

    @field_validator("as_of")
    @classmethod
    def check_as_of(cls, value: Optional[str]) -> Optional[str]:
        return _real_day(value)

    @model_validator(mode="after")
    def measure_fits_the_tab(self) -> "RankStatsInput":
        known = KNOWN_MEASURES.get(self.measure)
        if known is not None and known[0] != self.tab:
            raise ValueError(MEASURE_OTHER_TAB)
        if self.kind is not None:
            if known is not None and self.kind not in known[1]:
                raise ValueError(KIND_NOT_FOR_MEASURE)
            if known is None and self.tab != "exchanges":
                raise ValueError(KIND_NOT_FOR_MEASURE)
        return self


class GetStatsRecordInput(_Args):
    tab: str = Field(pattern=_NAME_PATTERN, max_length=40, description="exchanges or vaults.")
    id: str = Field(
        min_length=1,
        max_length=64,
        description=(
            "An exchange id or name (for example kraken or Crypto.com), or a vault address "
            "(0x and 40 hex characters)."
        ),
    )

    @model_validator(mode="after")
    def fold_the_id(self) -> "GetStatsRecordInput":
        self.id = _record_id(self.tab, self.id)
        return self


def _record_id(tab: str, text: str) -> str:
    """One id in the form the API is sent: a vault address in lower case, or
    an exchange id folded to a slug."""
    if tab == "vaults":
        trimmed = text.strip()
        if not _ADDRESS.fullmatch(trimmed):
            raise ValueError("a vault id is 0x and 40 hex characters")
        return trimmed.lower()
    slug = exchange_id(text)
    if slug is None or len(slug) > 64:
        raise ValueError("an exchange id is a slug or a name, such as kraken or Crypto.com")
    return slug


_IdText = Annotated[str, StringConstraints(min_length=1, max_length=64)]


class CompareStatsRecordsInput(_Args):
    tab: str = Field(pattern=_NAME_PATTERN, max_length=40, description="exchanges or vaults.")
    ids: Union[
        Annotated[list[_IdText], Field(min_length=2, max_length=5)],
        Annotated[str, StringConstraints(min_length=3, max_length=400)],
    ] = Field(
        description=(
            "2 to 5 ids with no repeats, as a list or as one text separated by commas "
            "(for example kraken,coinbase)."
        ),
    )

    @model_validator(mode="after")
    def fold_the_ids(self) -> "CompareStatsRecordsInput":
        if isinstance(self.ids, str):
            if _CONTROL.search(self.ids):
                raise ValueError("ids holds a control character")
            parts = self.ids.split(",")
        else:
            parts = list(self.ids)
        if not 2 <= len(parts) <= 5:
            raise ValueError(IDS_RULE)
        folded: list[str] = []
        for part in parts:
            if self.tab != "vaults" and _ADDRESS.fullmatch(part.strip()):
                # A vault address in the exchanges tab: ids from two tabs.
                raise ValueError(IDS_RULE)
            folded.append(_record_id(self.tab, part))
        if len(set(folded)) != len(folded):
            raise ValueError(IDS_RULE)
        self.ids = folded
        return self


class LookupStatsWalletInput(_Args):
    address: str = Field(
        min_length=42,
        max_length=42,
        pattern=_ADDRESS_PATTERN,
        description="One full wallet address: 0x and 40 hex characters.",
    )
    offset: int = Field(
        default=0,
        ge=0,
        le=5_000,
        description=(
            "Records to skip when the wallet has more than 50: the next_offset of the page before "
            "(default 0)."
        ),
    )
    as_of: Optional[str] = Field(
        default=None,
        min_length=10,
        max_length=10,
        pattern=_DAY_PATTERN,
        description=(
            "The as_of of the page before, YYYY-MM-DD. A page of another data day is refused, so "
            "two days are never mixed."
        ),
    )

    @field_validator("address", mode="before")
    @classmethod
    def trim(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value

    @field_validator("as_of")
    @classmethod
    def check_as_of(cls, value: Optional[str]) -> Optional[str]:
        return _real_day(value)


class GetStatsMethodInput(_Args):
    topic: Literal["exchanges", "vaults", "wallet_lookup"] = Field(
        description="exchanges, vaults or wallet_lookup.",
    )


class ListStatsChangesInput(_Args):
    since: Optional[str] = Field(
        default=None,
        min_length=10,
        max_length=10,
        pattern=_DAY_PATTERN,
        description=(
            "A day, YYYY-MM-DD: lines on or after it. A day outside the allowed range is moved to "
            "the nearest allowed day, and the answer says so."
        ),
    )
    limit: int = Field(default=20, ge=1, le=100, description="Lines to return, 1 to 100 (default 20).")
    before: Optional[str] = Field(
        default=None,
        max_length=80,
        pattern=_BEFORE_PATTERN,
        description="The next_before value of the page before, for the next page.",
    )

    @field_validator("since")
    @classmethod
    def check_since(cls, value: Optional[str]) -> Optional[str]:
        return _real_day(value)


# --- errors of a Stats call ------------------------------------------------------


class StatsRefusal(Exception):
    """A call the package refuses before any request, with a fixed sentence."""


class StatsShapeError(Exception):
    """An API answer that is not the canonical envelope or lacks a key its tool
    needs. The text never reaches the model; ``server.py`` answers with one
    fixed sentence and the call id."""


# --- the check of an answer ------------------------------------------------------


def _whole(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _number_or_null(value: Any) -> bool:
    return value is None or (isinstance(value, (int, float)) and not isinstance(value, bool))


def _text(value: Any) -> bool:
    return isinstance(value, str)


def _day(value: Any) -> bool:
    if not isinstance(value, str) or not re.fullmatch(_DAY_PATTERN, value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


_KINDS: dict[str, Callable[[Any], bool]] = {
    "whole": _whole,
    "text": _text,
    "list": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
    "bool": lambda v: isinstance(v, bool),
    "whole_or_null": lambda v: v is None or _whole(v),
    "text_or_null": lambda v: v is None or _text(v),
    "present": lambda v: True,
    "prefix": lambda v: isinstance(v, str) and bool(re.fullmatch(r"[0-9a-f]{2}", v)),
    "sha256": lambda v: isinstance(v, str) and bool(re.fullmatch(r"[0-9a-f]{64}", v)),
}

# The keys each tool needs in data, with their kinds (design 1.0).
REQUIRED: dict[str, dict[str, str]] = {
    SEARCH_STATS: {
        "count": "whole", "matches_total": "whole", "limit": "whole", "results": "list",
        "left_out": "object", "searched": "object", "order": "text",
    },
    LIST_STATS_MEASURES: {"count": "whole", "measures": "list", "tabs": "list"},
    RANK_STATS: {
        "tab": "text", "measure": "object", "order": "text", "order_rule": "text",
        "sample_size": "whole", "counts": "object", "count": "whole", "total": "whole",
        "limit": "whole", "offset": "whole", "results": "list", "what_is_missing": "list",
        "next_offset": "whole_or_null", "trimmed": "bool",
    },
    GET_STATS_RECORD: {"tab": "text", "record": "object"},
    COMPARE_STATS_RECORDS: {
        "tab": "text", "ids_asked": "present", "count": "whole", "records": "list",
        "not_published": "list", "not_returned": "list",
    },
    LOOKUP_STATS_WALLET: {
        "prefix": "prefix", "page": "text", "page_sha256": "sha256", "counts": "object",
        "lookup_notes": "object", "vaults": "object", "wallets": "object",
    },
    GET_STATS_METHOD: {"topic": "text", "text": "object"},
    LIST_STATS_CHANGES: {
        "count": "whole", "total": "whole", "limit": "whole", "results": "list",
        "covers": "text", "not_covered": "list", "next_before": "text_or_null",
    },
}

_LOOKUP_NOTE_KEYS = ("fields", "status_meanings", "uses_meanings", "why_sentences", "rounding", "cannot_see")
_DIGITS = re.compile(r"[0-9]+")


def _walk_is_plain(node: Any, depth: int = 0) -> bool:
    """No key made of digits alone (JavaScript would move it, and the two
    packages must parse the same answer) and no number that is not finite."""
    if depth > 64:
        return False
    if isinstance(node, dict):
        for key, value in node.items():
            if not isinstance(key, str) or _DIGITS.fullmatch(key):
                return False
            if not _walk_is_plain(value, depth + 1):
                return False
        return True
    if isinstance(node, list):
        return all(_walk_is_plain(v, depth + 1) for v in node)
    if isinstance(node, float):
        return node == node and node not in (float("inf"), float("-inf"))
    return True


def _check_data(tool: str, data: Mapping[str, Any]) -> None:
    if data.get("schema") != SCHEMA:
        raise StatsShapeError("schema")
    if "status" in data:
        raise StatsShapeError("data.status")
    if not _day(data.get("as_of")):
        raise StatsShapeError("as_of")
    sources = data.get("sources")
    if not isinstance(sources, list) or not all(
        isinstance(s, dict) and link_ok(s.get("file"), (DATA_PREFIX,)) for s in sources
    ):
        raise StatsShapeError("sources")
    listed = data.get("outside_text_keys")
    if (
        not isinstance(listed, list)
        or not all(isinstance(k, str) for k in listed)
        or not set(OUTSIDE_TEXT_KEYS) <= set(listed)
    ):
        raise StatsShapeError("outside_text_keys")
    rows_dropped = data.get("rows_dropped")
    if not _whole(rows_dropped) or rows_dropped < 0:
        raise StatsShapeError("rows_dropped")
    notes = data.get("notes")
    if not isinstance(notes, list) or not all(isinstance(n, str) for n in notes):
        raise StatsShapeError("notes")
    for key, kind in REQUIRED[tool].items():
        if key not in data or not _KINDS[kind](data[key]):
            raise StatsShapeError(key)
    if tool == LOOKUP_STATS_WALLET:
        notes_block = data["lookup_notes"]
        if not all(k in notes_block for k in _LOOKUP_NOTE_KEYS):
            raise StatsShapeError("lookup_notes")
        if not (
            isinstance(notes_block["status_meanings"], dict)
            and isinstance(notes_block["uses_meanings"], dict)
            and isinstance(notes_block["cannot_see"], list)
        ):
            raise StatsShapeError("lookup_notes")
    if not _walk_is_plain(data):
        raise StatsShapeError("keys or numbers")


def check_answer(tool: str, payload: Any) -> dict[str, Any]:
    """The envelope of a Stats answer, refused unless it has the Stats shape.

    It must be the canonical envelope, ``meta.status`` one of the four values,
    and ``data`` must hold the keys its tool needs. ``data`` may be null when
    the status is unseeded or partial: the API then has nothing to give, and
    the answer is passed on as it is. A missing status is never read as
    complete.
    """
    if not isinstance(payload, dict) or "data" not in payload:
        raise StatsShapeError("envelope")
    attribution = payload.get("attribution")
    meta = payload.get("meta")
    if not (
        isinstance(attribution, dict)
        and isinstance(attribution.get("citations"), list)
        and isinstance(meta, dict)
    ):
        raise StatsShapeError("envelope")
    if meta.get("status") not in STATUSES:
        raise StatsShapeError("meta.status")
    data = payload["data"]
    if data is None:
        if meta["status"] not in ("unseeded", "partial"):
            raise StatsShapeError("data")
    elif isinstance(data, dict):
        _check_data(tool, data)
    else:
        raise StatsShapeError("data")
    return {"data": data, "attribution": attribution, "meta": meta}


# --- calling the API ---------------------------------------------------------------


async def _get(
    tool: str,
    path: str,
    params: Optional[Mapping[str, Any]],
    call_id: str,
    cap: int = STATS_READ_CAP,
) -> dict[str, Any]:
    payload = await get_client().request(
        path, params, max_body_bytes=cap, request_id=call_id, canonicalize=False
    )
    return check_answer(tool, payload)


def _segment(text: str) -> str:
    return quote(text, safe="")


async def run_search_stats(args: dict[str, Any], call_id: str) -> dict[str, Any]:
    parsed = SearchStatsInput.model_validate(args)
    if _is_full_address(parsed.query):
        raise StatsRefusal(SEARCH_ADDRESS_REFUSED)
    return await _get(
        SEARCH_STATS,
        "/v1/stats/search",
        {"q": parsed.query, "tab": parsed.tab, "limit": parsed.limit},
        call_id,
    )


async def run_list_stats_measures(args: dict[str, Any], call_id: str) -> dict[str, Any]:
    ListStatsMeasuresInput.model_validate(args)
    return await _get(LIST_STATS_MEASURES, "/v1/stats/measures", None, call_id)


async def run_rank_stats(args: dict[str, Any], call_id: str) -> dict[str, Any]:
    parsed = RankStatsInput.model_validate(args)
    return await _get(
        RANK_STATS,
        "/v1/stats/rank",
        {
            "tab": parsed.tab,
            "measure": parsed.measure,
            "kind": parsed.kind,
            "order": parsed.order,
            "limit": parsed.limit,
            "offset": parsed.offset,
            "as_of": parsed.as_of,
        },
        call_id,
    )


async def run_get_stats_record(args: dict[str, Any], call_id: str) -> dict[str, Any]:
    parsed = GetStatsRecordInput.model_validate(args)
    path = f"/v1/stats/{_segment(parsed.tab)}/{_segment(parsed.id)}"
    return await _get(GET_STATS_RECORD, path, None, call_id)


async def run_compare_stats_records(args: dict[str, Any], call_id: str) -> dict[str, Any]:
    parsed = CompareStatsRecordsInput.model_validate(args)
    ids = parsed.ids if isinstance(parsed.ids, list) else [parsed.ids]
    return await _get(
        COMPARE_STATS_RECORDS,
        "/v1/stats/compare",
        {"tab": parsed.tab, "ids": ",".join(ids)},
        call_id,
    )


async def run_get_stats_method(args: dict[str, Any], call_id: str) -> dict[str, Any]:
    parsed = GetStatsMethodInput.model_validate(args)
    return await _get(GET_STATS_METHOD, "/v1/stats/method", {"topic": parsed.topic}, call_id)


async def run_list_stats_changes(args: dict[str, Any], call_id: str) -> dict[str, Any]:
    parsed = ListStatsChangesInput.model_validate(args)
    return await _get(
        LIST_STATS_CHANGES,
        "/v1/stats/changes",
        {"since": parsed.since, "limit": parsed.limit, "before": parsed.before},
        call_id,
    )


# --- the wallet lookup, matched on this machine -------------------------------------

_RECORD_NUMBERS = ("cost", "received", "result", "cut", "listed_result")
_USES = ("ledger", "list")


def _record_ok(record: Any) -> bool:
    """One lookup record as the API hands it on: the 12 keys of the file and
    vault_listed, each of its kind."""
    return (
        isinstance(record, dict)
        and isinstance(record.get("vault"), str)
        and bool(_ADDRESS.fullmatch(record["vault"]))
        and record.get("vault_state") in ("open", "closed")
        and isinstance(record.get("leader"), bool)
        and isinstance(record.get("status"), str)
        and _whole(record.get("withdrawals"))
        and all(k in record and _number_or_null(record[k]) for k in _RECORD_NUMBERS)
        and isinstance(record.get("uses"), str)
        and isinstance(record.get("why"), str)
        and isinstance(record.get("vault_listed"), bool)
    )


def _joined(record: Mapping[str, Any], vaults: Mapping[str, Any]) -> dict[str, Any]:
    item = dict(record)
    item["figure_the_file_uses"] = record["result"] if record["uses"] == "ledger" else record["listed_result"]
    item["leader_listed_zero_after_close"] = bool(
        record["leader"] and record["vault_state"] == "closed" and record["listed_result"] == 0
    )
    row = vaults.get(record["vault"], vaults.get(record["vault"].lower()))
    item["vault_row"] = dict(row) if isinstance(row, dict) else None
    return item


def _summary(every: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """A reading of the wallet as a whole, over every record and not one page.
    The two kinds of result are kept apart."""
    if not every:
        return None
    by_status: dict[str, int] = {}
    for r in every:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    leads = sum(1 for r in every if r["leader"])
    zeros = sum(1 for r in every if r["leader_listed_zero_after_close"])
    how_to_read = list(SUMMARY_HOW_TO_READ)
    if leads:
        how_to_read.append(LEADER_CUTS % leads)
    if zeros:
        how_to_read.append(LEADER_ZERO % zeros)
    with_result = [r["result"] for r in every if r["result"] is not None]
    on_list = [r["listed_result"] for r in every if r["listed_result"] is not None]
    return {
        "records": len(every),
        "leads": leads,
        "by_status": by_status,
        "records_with_withdrawals": len(with_result),
        "result_on_withdrawals_usd": sum(with_result),
        "records_on_venue_list": len(on_list),
        "venue_list_result_usd": sum(on_list),
        "sum_of_figures_the_file_uses_usd": sum(
            r["figure_the_file_uses"] for r in every if r["figure_the_file_uses"] is not None
        ),
        "how_to_read": how_to_read,
    }


def _wallet_page(data: dict[str, Any], page: list[dict[str, Any]], offset: int, total: int, notes_block: Mapping[str, Any]) -> None:
    data["count"] = len(page)
    more = offset + len(page) < total
    data["next_offset"] = offset + len(page) if more and page else None
    data["records"] = page
    data["status_meanings"] = {
        k: v for k, v in notes_block["status_meanings"].items() if any(r["status"] == k for r in page)
    }


def wallet_answer(shard: Mapping[str, Any], address: str, offset: int = 0) -> dict[str, Any]:
    """The answer for one address, built from the shard answer on this
    machine: that address's records alone, each joined to its vault row, and a
    summary over all of its records. At most 50 records a page."""
    address = address.strip().lower()
    vaults = shard["vaults"]
    notes_block = shard["lookup_notes"]
    wallets = {k.lower(): v for k, v in shard["wallets"].items() if isinstance(k, str)}
    rows = wallets.get(address, [])
    if not isinstance(rows, list) or not all(_record_ok(r) for r in rows):
        raise StatsShapeError("wallets")
    # The package checks uses again and drops a record with any other value.
    every = [_joined(r, vaults) for r in rows if r["uses"] in _USES]
    page = every[offset : offset + LOOKUP_RECORDS_PER_ANSWER]
    data: dict[str, Any] = {
        k: shard.get(k)
        for k in ("schema", "as_of", "uploaded_at", "method_version", "variant", "sources",
                  "outside_text_keys", "rows_dropped")
    }
    notes = list(LOOKUP_NOTES)
    notes += [n for n in shard["notes"] if n not in notes]
    if any((r["vault_row"] or {}).get("name_by_leader") for r in page) and NAME_NOTE not in notes:
        notes.append(NAME_NOTE)
    data["notes"] = notes
    data.update(
        {
            "address": address,
            "found": bool(every),
            "count": 0,
            "total": len(every),
            "limit": LOOKUP_RECORDS_PER_ANSWER,
            "offset": offset,
            "next_offset": None,
            "lookup_page": {"name": shard["page"], "sha256": shard["page_sha256"]},
            "summary": _summary(every),
            "records": [],
            "uses_meanings": notes_block["uses_meanings"],
            "status_meanings": {},
            "cannot_see": notes_block["cannot_see"],
        }
    )
    _wallet_page(data, page, offset, len(every), notes_block)
    return data


def _wallet_page_info(data: Mapping[str, Any]) -> dict[str, Any]:
    # The package builds the page fields of the wallet answer itself.
    return {
        "hasNextPage": data.get("next_offset") is not None,
        "hasPreviousPage": data.get("offset", 0) > 0,
        "startCursor": None,
        "endCursor": None,
    }


async def run_lookup_stats_wallet(args: dict[str, Any], call_id: str) -> dict[str, Any]:
    parsed = LookupStatsWalletInput.model_validate(args)
    address = parsed.address.lower()
    prefix = address[2:4]
    envelope = await _get(
        LOOKUP_STATS_WALLET,
        f"/v1/stats/wallets/shard/{prefix}",
        {"as_of": parsed.as_of},
        call_id,
        cap=SHARD_READ_CAP,
    )
    shard = envelope["data"]
    if shard is None:
        # The API has nothing to give: passed on as it is. No result is guessed.
        return envelope
    if shard["prefix"] != prefix:
        raise StatsShapeError("prefix")
    data = wallet_answer(shard, address, parsed.offset)
    meta = dict(envelope["meta"])
    meta["pageInfo"] = _wallet_page_info(data)
    return {"data": data, "attribution": envelope["attribution"], "meta": meta}


def trim_wallet_answer(envelope: dict[str, Any]) -> bool:
    """The package's last check on a wallet answer: one record goes from the
    end of the page, so the text block can fit under 65,536 bytes. False when
    no record is left to take."""
    data = envelope.get("data")
    if not isinstance(data, dict) or not data.get("records"):
        return False
    data["records"].pop()
    data["count"] = len(data["records"])
    data["next_offset"] = data["offset"] + data["count"] if data["count"] else None
    meta = envelope.get("meta")
    if isinstance(meta, dict):
        meta["pageInfo"] = _wallet_page_info(data)
    return True


# --- the registry ------------------------------------------------------------------


def _schema(model: type[BaseModel]) -> dict[str, Any]:
    return model.model_json_schema()


# (name, description, input schema, runner, trimmer), in the order of the design.
def stats_tool_entries() -> list[tuple[str, str, dict[str, Any], Callable[..., Any], Optional[Callable[[dict[str, Any]], bool]]]]:
    entries: list[tuple[str, str, dict[str, Any], Callable[..., Any], Optional[Callable[[dict[str, Any]], bool]]]] = [
        (SEARCH_STATS, description(SEARCH_STATS), _schema(SearchStatsInput), run_search_stats, None),
        (LIST_STATS_MEASURES, description(LIST_STATS_MEASURES), _schema(ListStatsMeasuresInput),
         run_list_stats_measures, None),
        (RANK_STATS, description(RANK_STATS), _schema(RankStatsInput), run_rank_stats, None),
        (GET_STATS_RECORD, description(GET_STATS_RECORD), _schema(GetStatsRecordInput),
         run_get_stats_record, None),
        (COMPARE_STATS_RECORDS, description(COMPARE_STATS_RECORDS), _schema(CompareStatsRecordsInput),
         run_compare_stats_records, None),
    ]
    if WALLET_LOOKUP_TOOL:
        entries.append(
            (LOOKUP_STATS_WALLET, description(LOOKUP_STATS_WALLET), _schema(LookupStatsWalletInput),
             run_lookup_stats_wallet, trim_wallet_answer)
        )
    entries += [
        (GET_STATS_METHOD, description(GET_STATS_METHOD), _schema(GetStatsMethodInput),
         run_get_stats_method, None),
        (LIST_STATS_CHANGES, description(LIST_STATS_CHANGES), _schema(ListStatsChangesInput),
         run_list_stats_changes, None),
    ]
    return entries
