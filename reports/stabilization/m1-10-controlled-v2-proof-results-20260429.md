# M1.10 — Controlled Production-like v2 Proof Results (2026-04-29)

## Status

**Precondition 3 closed: DONE.**

The controlled production-like v2 proof ran end-to-end through
`data_platform.daily_refresh --mock` against a local-PG-backed Iceberg
SqlCatalog, with separate writer and reader processes pinning to the same
manifest snapshots. Every gate that the M1.10 fixture proof could not
exercise (real `dbt run`, real PG-backed Iceberg catalog, cross-process
snapshot pinning, and end-to-end ingest → staging → intermediate → marts →
canonical → reader smoke) has now passed.

## Companion Evidence Artifacts (gitignored runtime output)

These JSON artifacts live under `assembly/tmp-runtime/m1-controlled-v2-proof/`
which is matched by the `.gitignore` pattern `tmp-*/`. They are forensic
runtime output — this markdown captures the parts that need to be
preserved alongside the source tree.

| Artifact | Path |
|---|---|
| Daily-refresh JSON report | `assembly/tmp-runtime/m1-controlled-v2-proof/daily-refresh-20260429.json` |
| Reader smoke JSON report | `assembly/tmp-runtime/m1-controlled-v2-proof/reader-smoke-20260429.json` |
| Iceberg warehouse | `assembly/tmp-runtime/m1-controlled-v2-proof/iceberg/` |
| DuckDB staging + dbt target | `assembly/tmp-runtime/m1-controlled-v2-proof/duckdb/` |
| Raw zone artifacts | `assembly/tmp-runtime/m1-controlled-v2-proof/raw/` |

## Daily-Refresh Step Summary

`daily-refresh-20260429.json` — `ok: true`, `partition_date: 2026-04-29`.

| Step | Status | Duration |
|---|---|---|
| `adapter` | ok | 0.04s |
| `dbt_run` | ok | 12.41s |
| `dbt_test` | ok | 7.25s |
| `canonical` | ok | 10.26s |
| `raw_health` | ok | 0.01s |

### Adapter (`mock=True`)

- `asset_specs_count: 93`
- `artifact_count: 28` (raw zone parquet/JSON files written via fixture
  adapter — no Tushare network call, no production fetch)

### dbt_run

```
command: scripts/dbt.sh run --profiles-dir <tmp>/duckdb/daily_refresh_dbt_profiles \
  --target-path <tmp>/duckdb/daily_refresh_dbt_target/run_20260429 \
  --select staging intermediate marts marts_v2 marts_lineage
returncode: 0
result: Done. PASS=62 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=62
```

All 62 dbt models (staging + intermediate + 8 legacy marts + 9 marts_v2 +
9 marts_lineage = 26 marts plus 36 staging/intermediate) materialized
without error. Deprecation warnings about
`MissingArgumentsPropertyInGenericTestDeprecation` are dbt-core noise,
not test failures.

### dbt_test

```
command: scripts/dbt.sh test --profiles-dir <tmp>/duckdb/daily_refresh_dbt_profiles \
  --target-path <tmp>/duckdb/daily_refresh_dbt_target/test_20260429 \
  --select staging intermediate marts marts_v2 marts_lineage
returncode: 0
result: Done. PASS=477 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=477
```

All 477 dbt data tests passed across legacy + v2 + lineage selectors.

### canonical

27 write results, 0 skipped:

| Namespace | Tables Written | Mart Identifiers |
|---|---|---|
| `canonical.*` (legacy) | 9 | dim_security, dim_index, fact_price_bar, fact_financial_indicator, fact_event, fact_market_daily_feature, fact_index_price_bar, fact_forecast_event, stock_basic |
| `canonical_v2.*` | 9 | dim_security, stock_basic, dim_index, fact_price_bar, fact_financial_indicator, fact_market_daily_feature, fact_index_price_bar, fact_forecast_event, fact_event |
| `canonical_lineage.*` | 9 | lineage_* (matching v2 by canonical name) |

Sample row counts (full list in JSON): `canonical_v2.fact_event` writes
**8 rows** (one per source interface in the safe subset: anns, suspend_d,
dividend, share_float, stk_holdernumber, disclosure_date, namechange,
block_trade); `canonical_v2.fact_price_bar` writes 3 rows; the other 7 v2
marts write 1 row each. Lineage rows match v2 row counts pair-by-pair.

### raw_health

`ok` — `checked_artifacts` confirms 28 raw artifacts on disk, no missing
or corrupt files.

## Reader Smoke Summary

`reader-smoke-20260429.json` — separate Python process, `DP_CANONICAL_USE_V2=1`.

All 10 v2 dataset_ids resolved through `read_canonical_dataset()` to the
manifest-pinned snapshot ids matching the writer's published
`WriteResult.snapshot_id`:

| dataset_id | table_identifier | snapshot_id (writer == reader) | row_count |
|---|---|---|---|
| security_master | canonical_v2.dim_security | 6182450702461391134 | 1 |
| security_profile | canonical_v2.dim_security | 6182450702461391134 | 1 |
| price_bar | canonical_v2.fact_price_bar | 6372163478129560328 | 3 |
| adjustment_factor | canonical_v2.fact_price_bar | 6372163478129560328 | 3 |
| market_daily_feature | canonical_v2.fact_market_daily_feature | 6023947161963413751 | 1 |
| index_master | canonical_v2.dim_index | 2459450982081566056 | 1 |
| index_price_bar | canonical_v2.fact_index_price_bar | 1050919947241454606 | 1 |
| event_timeline | canonical_v2.fact_event | 7963438051924622533 | 8 |
| financial_indicator | canonical_v2.fact_financial_indicator | 4843896257386181535 | 1 |
| financial_forecast_event | canonical_v2.fact_forecast_event | 3017459585203585239 | 1 |

`stock_basic_helper`: `get_canonical_stock_basic(active_only=True)` returned
1 row from `canonical_v2.stock_basic` (manifest snapshot id
2267729095191945811 in the writer log).

## Cross-Process Snapshot Pinning

The same snapshot ids appear in both the writer's `daily-refresh` JSON and
the reader's `reader-smoke` JSON — for example:

- `canonical_v2.dim_security` → 6182450702461391134 (both)
- `canonical_v2.fact_event` → 7963438051924622533 (both)
- `canonical_v2.fact_price_bar` → 6372163478129560328 (both)

This proves the reader did not silently fall back to head; it consulted
the `_mart_snapshot_set.json` manifest written by the writer process and
resolved each dataset to the writer's published snapshot via `iceberg_scan(...,
snapshot_from_id = N)`.

## Code / Test Changes Required for the Controlled Proof to Run

The fixture proof did not require any production-code change. The
controlled compose-PG run exposed three real consistency gaps that had to
be closed before `dbt run`/`dbt test` would pass and before `daily_refresh`
would write all 27 marts. All three changes are minimal, additive, and
land alongside this evidence.

### `data-platform/src/data_platform/daily_refresh.py`

- Added `load_canonical_v2_marts` import.
- Added `marts_v2` and `marts_lineage` to `DEFAULT_DBT_SELECTORS`.
- Added 3 date field names to `DATE_FIELD_NAMES` (`div_listdate`,
  `first_ann_date`, `imp_ann_date`) and ~26 decimal-numeric fields to
  `STRING_NUMERIC_FIELD_NAMES` (forecast event nets, p_change ranges,
  market_daily_feature buy/sell/net flow columns, stk_limit up/down
  limits) so the `--mock` adapter generates DuckDB-castable values that
  match the dbt staging schema.
- Wired `load_canonical_v2_marts(catalog, duckdb_path)` into
  `_run_canonical_step` after the legacy `load_canonical_marts`/
  `load_canonical_stock_basic` calls. The legacy write path is
  **unchanged** — v2 + lineage are written **additively** alongside
  legacy. This is Phase A wiring, not Phase B retirement.
- Added `"canonical_v2.canonical_marts"` to the `skipped_writes` list when
  the canonical step is skipped, mirroring the legacy entry.
- `_mock_value` returns `"SSE"` for the `exchange` field so trade_cal
  fixture rows produce a valid value that the staging cast accepts.

### `data-platform/tests/integration/test_daily_refresh.py`

- Imported `CANONICAL_V2_MART_LOAD_SPECS` and `CANONICAL_LINEAGE_MART_LOAD_SPECS`.
- Existing repeatable-mock test now expects 27 write_results
  (`1 + len(CANONICAL_MART_LOAD_SPECS) + len(CANONICAL_V2_MART_LOAD_SPECS) + len(CANONICAL_LINEAGE_MART_LOAD_SPECS)`).
- Existing real-PG test extended the same way.
- Added 3 new tests:
  - `test_daily_refresh_full_dbt_selectors_include_v2_and_lineage` — the
    selector tuple includes `marts_v2` and `marts_lineage` when all assets
    are selected.
  - `test_daily_refresh_partial_dbt_selectors_keep_legacy_staging_path` —
    partial selection still picks the right `stg_*` selectors.
  - `test_mock_adapter_values_cover_dbt_cast_fields` — fixture rows for
    `forecast`, `stk_limit`, `moneyflow`, and `trade_cal` carry valid
    decimal/exchange/is_open values.
- `_install_fast_success_stubs` mocks `load_canonical_v2_marts` to
  produce one row per v2/lineage spec so the unit test does not need a
  real dbt run.

### `data-platform/src/data_platform/dbt/models/marts/_schema.yml`

- Extended legacy `mart_fact_event.event_type` accepted_values to include
  `name_change` and `block_trade`. Both legacy and v2 marts consume the
  same `int_event_timeline.sql`; after M1.6 (namechange) and M1.8
  (block_trade) promotions, `int_event_timeline` produces these event
  types. Without this update, `dbt test` fails on the legacy mart's
  accepted_values constraint while the v2 mart passes — which is the
  exact dbt_test failure the controlled run had to repair before
  reaching `Done. PASS=477` above.

## Pytest Sweeps After Code/Test Changes

```sh
# Preflight (writer + reader + integration)
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
  -p no:cacheprovider \
  tests/serving/test_canonical_writer.py \
  tests/serving/test_reader.py \
  tests/integration/test_daily_refresh.py
# → 58 passed, 1 skipped, 15 warnings in 3.84s
#   (was 57 baseline; +1 from new test_daily_refresh tests)

# M1 standard
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
  -p no:cacheprovider \
  tests/dbt/test_intermediate_models.py tests/dbt/test_marts_models.py \
  tests/dbt/test_dbt_skeleton.py tests/dbt/test_dbt_test_coverage.py \
  tests/dbt/test_marts_provider_neutrality.py tests/provider_catalog
# → 58 passed, 2 skipped, 8 xfailed in 1.61s

# V2 default-on lane
DP_CANONICAL_USE_V2=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
  -p no:cacheprovider \
  tests/serving tests/cycle/test_current_cycle_inputs.py \
  tests/cycle/test_current_cycle_inputs_lineage_absent.py tests/test_assets.py
# → 177 passed, 5 skipped, 17 xfailed in 3.17s
```

xfail counts stable: 8 (M1 standard), 17 (V2 lane). No regressions vs M1.9
or vs the M1.10 fixture-only baseline.

## What This Closes vs What Remains

### Closed by this proof

- **Precondition 3** — controlled production-like v2 proof: `dbt run`
  over `marts_v2` + `marts_lineage`, `load_canonical_v2_marts`, and
  read-side smoke through `read_canonical_dataset` under
  `DP_CANONICAL_USE_V2=1` — **DONE**.
- The `READY_FOR_LITE_COMPOSE_PLANNING` boundary in
  `m1-10-controlled-v2-proof-preflight-20260429.md` is now obsolete; the
  preflight is amended in this round to record the actual run path
  (host-driven `daily_refresh --mock` against a local PG service rather
  than `compose exec dagster-daemon`, which is still probe-only).

### Still open (unchanged)

- **Preconditions 6, 7, 8** — Phase B retirement steps (extend
  `FORBIDDEN_*_FIELDS`, strip `_M1D_LEGACY_RETIREMENT_XFAIL` markers,
  delete `CANONICAL_MART_LOAD_SPECS` / `CANONICAL_MART_TABLE_SPECS` /
  legacy dbt marts). Sequenced per
  [`m1-10-legacy-retirement-phase-b-inventory-20260429.md`](m1-10-legacy-retirement-phase-b-inventory-20260429.md).
  NOT executed in this round.
- **Precondition 9** — 8 `event_timeline` candidate sources
  (`pledge_*`, `repurchase`, `stk_holdertrade`, `limit_list_*`,
  `hm_detail`, `stk_surv`) remain `BLOCKED_NO_LOCAL_SCHEMA`.
- **P5** remains BLOCKED.

## Hard-Rule Declarations

- `project_ult_v5_0_1.md` UNCHANGED.
- `ult_milestone.md` UNCHANGED.
- No production fetch (mock adapter only; `artifact_count: 28` from
  fixture data, `mock: true` recorded in JSON).
- No P5 shadow-run.
- No M2 / M3 / M4 work.
- No API-6 / sidecar / frontend write API / Kafka / Flink / Temporal /
  news / Polymarket touched.
- Tushare remains a `provider="tushare"` source adapter only.
- Legacy `canonical.*` specs / load specs / dbt marts NOT deleted.
- `_M1D_LEGACY_RETIREMENT_XFAIL` NOT removed.
- `FORBIDDEN_SCHEMA_FIELDS` / `FORBIDDEN_PAYLOAD_FIELDS` NOT extended.
- `/Users/fanjie/Desktop/BIG/FrontEnd` NOT modified.
- No commits, no push, no amend, no reset.

## Cross-References

- Preflight (now superseded): [`m1-10-controlled-v2-proof-preflight-20260429.md`](m1-10-controlled-v2-proof-preflight-20260429.md)
- Phase B inventory: [`m1-10-legacy-retirement-phase-b-inventory-20260429.md`](m1-10-legacy-retirement-phase-b-inventory-20260429.md)
- Progress: [`m1-legacy-retirement-preconditions-progress-20260428.md`](m1-legacy-retirement-preconditions-progress-20260428.md)
- Readiness: [`m1-legacy-canonical-retirement-readiness-20260428.md`](m1-legacy-canonical-retirement-readiness-20260428.md)
- Fixture closed-loop test: `data-platform/tests/serving/test_canonical_writer.py::test_load_canonical_v2_marts_closed_loop_under_v2_flag_reads_pinned_snapshots`
