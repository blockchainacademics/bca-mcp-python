# Recorded Stats answers

`test/stats_outside.test.ts` runs every file here. Two sets sit side by side:

- **From the API's dump** (`scripts/dump_stats_answers.py` at API commit `b1bbcbe`, on the API's made-up fixtures): search_growi, search_crypto_com, search_nothing, measures, rank_real_cost_buy_1000, rank_checks_passed, rank_checks_passed_signed, rank_money_put_in, rank_left_took_home_bottom, record_exchange_kraken, record_exchange_signed, record_vault_top, record_vault_small, record_vault_held_back, compare_exchanges, compare_vaults, method_exchanges, method_vaults, method_wallet_lookup, changes, paused_vaults, and four wallet lookups on the shards `2b` and `ab`. Two dump calls are left out: a measure of the other tab (refused before any request) and an id with no record (an error, covered by the error tests).
- **Stand-ins** made before the dump existed, for cases the dump does not hold: search_hlp, record_exchange_crypto_com, changes_empty, changes_lines, paused, files_unreadable, measures_stale and six wallet lookups on one shard.

- `answers/<call>.json`: one tool call. It holds the tool, its arguments, the request the package must send (path and query) and the API's envelope. A wallet lookup names its shard under `shards/`.
- `expected_outputs/<call>.json`: what the tool hands the model, with the marker id `0123456789abcdef` and the call id `fedcba9876543210`.
- `SHA256SUMS`: the hash of every file above.

Nothing here is real. Every address is made up (`0x` plus SHA-256 of a `bca-fixture` string), every vault name starts with `Fixture` (one name that cleans to nothing excepted), and every figure is made up.

How the expected outputs are made: the design's reference script (`stats_reference.py`, SHA-256 `7d5b932f7492a33c3fd85848a5005270a87ec236bdb9363ab26517ba34d62693`) gives `wrap` and `lookup_in_package`, and the package's rules for citations and meta are written again in Python. So they do not come from this package's code. The Python package keeps the same files under `tests/fixtures/stats_api_ts/`.
