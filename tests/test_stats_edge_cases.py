"""The shared table of edge cases of the Stats output rules (review finding 4).

tests/fixtures/stats_edge_cases.json holds edge inputs and the outputs the
rules give, written by hand from the rules, not by running either package.
Each field has one rule in both packages, the stricter one, so the
TypeScript package can run the same file: strip_markers, clean_citations,
clean_meta, the outside keys and holds_address here are stripMarkers,
cleanCitations, cleanStatsMeta, outsideKeys and holdsAddress there.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from bca_mcp._outside import clean_citations, clean_meta, listed_keys_ok, outside_keys, strip_markers
from bca_mcp.tools.stats import holds_address

TABLE = json.loads((Path(__file__).parent / "fixtures" / "stats_edge_cases.json").read_text("utf-8"))


def _run(rule: str, value: Any) -> Any:
    if rule == "strip":
        return strip_markers(value)
    if rule == "citations":
        return clean_citations({"citations": value})["citations"]
    if rule == "meta":
        return clean_meta(value, TABLE["call_id"])
    if rule == "keys":
        return sorted(outside_keys({"outside_text_keys": value})) if listed_keys_ok(value) else "refused"
    if rule == "address":
        return holds_address(value)
    raise AssertionError(f"unknown rule {rule}")


def test_the_table_covers_each_rule() -> None:
    rules = [case["rule"] for case in TABLE["cases"]]
    assert set(rules) == {"strip", "citations", "meta", "keys", "address"}
    assert len(rules) >= 40


@pytest.mark.parametrize("case", TABLE["cases"], ids=[f'{c["rule"]}: {c["name"]}' for c in TABLE["cases"]])
def test_each_edge_case_gives_its_output(case) -> None:
    assert _run(case["rule"], case["input"]) == case["output"]
