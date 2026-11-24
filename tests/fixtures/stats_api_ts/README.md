# Recorded Stats answers

Stand-ins until the API's dump (`scripts/dump_stats_answers.py`, task A1 of the Stats design) is copied in. `test/stats_outside.test.ts` runs every file here.

- `answers/<call>.json`: one tool call. It holds the tool, its arguments, the request the package must send (path and query) and the API's envelope. The six wallet lookups read one shard, kept once under `shards/`.
- `expected_outputs/<call>.json`: what the tool hands the model, with the marker id `0123456789abcdef` and the call id `fedcba9876543210`.
- `SHA256SUMS`: the hash of every file above.

Nothing here is real. Every address is `0x` plus the leading 40 hex characters of SHA-256 of `bca-fixture-<n>`, every vault name starts with `Fixture` (one name that cleans to nothing excepted), and every figure is made up. The exchange rows carry the 8 listed names with every fact being checked, as on 2026-11-24, and two made-up exchanges (`test-exchange-a`, `test-exchange-b`) carry signed facts.

How they were made: a made-up nightly feed folder was run through the design's reference script (`stats_reference.py`, SHA-256 `7d5b932f7492a33c3fd85848a5005270a87ec236bdb9363ab26517ba34d62693`) for the API side. The expected outputs use the reference's own `wrap` and `lookup_in_package`, and the package's rules for citations and meta, written again in Python. So they do not come from this package's code.

When the API's dump arrives, it replaces `answers/`, `expected_outputs/`, `shards/` and `SHA256SUMS`. The Python package keeps the same files under `tests/fixtures/stats_api/`.
