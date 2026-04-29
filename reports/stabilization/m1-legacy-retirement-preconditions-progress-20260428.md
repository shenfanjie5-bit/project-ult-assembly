# M1 Legacy Retirement Preconditions — M1.5 Progress

**Round:** M1.5-5
**Date:** 2026-04-28
**Status:** Progress audit only. NO legacy code deleted. NO xfail removed. NO `FORBIDDEN_*_FIELDS` extended. Supersedes the §5 status table in [m1-legacy-canonical-retirement-readiness-20260428.md](assembly/reports/stabilization/m1-legacy-canonical-retirement-readiness-20260428.md) with the M1.5 deltas.

## Purpose

Track the 9 preconditions to legacy `canonical.*` retirement after M1.5. Each row records current status, the evidence file that supports the status, and the next-owner action.

## Preconditions table

| # | Precondition | Status | Evidence | Next owner |
|---|---|---|---|---|
| 1 | Cross-repo direct reader audit complete (zero `read_canonical("<bare>")` callers in production paths; zero hardcoded legacy `canonical.<mart>` literals; zero hardcoded `ts_code`/`index_code` aliases on canonical-read paths) | **DONE (M1.5-1)** | [m1-reader-cutover-audit-20260428.md](assembly/reports/stabilization/m1-reader-cutover-audit-20260428.md) — zero `BLOCKED_*` hits across all 14 audited subrepos + read-only `BIG/FrontEnd` audit; entity-registry is now `OK_SELECTED_MAPPING` via v2-aware `get_canonical_stock_basic` compatibility in [reader.py:173-204](data-platform/src/data_platform/serving/reader.py:173), proven by [test_reader.py:169-358](data-platform/tests/serving/test_reader.py:169) | n/a (precondition closed) |
| 2 | `DP_CANONICAL_USE_V2=1` test lane passing | **DONE (M1.5-3, CI-protected in M1.6-R)** | [canonical-v2-default-on-test-proof-20260428.md](assembly/reports/stabilization/canonical-v2-default-on-test-proof-20260428.md) — v2 lane now runs as GitHub Actions job `canonical-v2-default-on`; latest proof reports 198 tests, 0 failures, 176 passed, 5 skipped, 17 xfailed | n/a (precondition closed) |
| 3 | Controlled production-like v2 proof: `dbt run` over `marts_v2` + `marts_lineage`, `load_canonical_v2_marts`, read smoke under `DP_CANONICAL_USE_V2=1` | **DONE (M1.10 follow-up)** — M1.10-3 added [`test_load_canonical_v2_marts_closed_loop_under_v2_flag_reads_pinned_snapshots`](data-platform/tests/serving/test_canonical_writer.py), then the controlled compose-Postgres proof was explicitly approved and executed. The approved run used only the existing `lite-local` PostgreSQL service plus a host-side Python 3.12 / uv throwaway venv, ran `data_platform.daily_refresh --mock`, completed `adapter`, `dbt_run`, `dbt_test`, `canonical`, and `raw_health` successfully, wrote 27 canonical results with 0 skipped writes, and persisted reader-smoke evidence for all 10 v2 dataset mappings plus `get_canonical_stock_basic()`. This is still not an M2 daily-cycle proof and not P5 readiness. | [m1-10-controlled-v2-proof-preflight-20260429.md](assembly/reports/stabilization/m1-10-controlled-v2-proof-preflight-20260429.md) (`CONTROLLED_COMPOSE_PROOF_PASSED`), `assembly/tmp-runtime/m1-controlled-v2-proof/daily-refresh-20260429.json`, `assembly/tmp-runtime/m1-controlled-v2-proof/reader-smoke-20260429.json`, closed-loop test in `tests/serving/test_canonical_writer.py` | n/a (precondition closed; Phase B retirement can start) |
| 4 | All 9 v2 + 9 lineage specs present (`canonical_v2.*` + `canonical_lineage.lineage_*`) | **DONE (M1-G2)** | [iceberg_tables.py:641-651, 801-811](data-platform/src/data_platform/ddl/iceberg_tables.py:641); [canonical_writer.py:692-712](data-platform/src/data_platform/serving/canonical_writer.py:692). Verified by [test_iceberg_tables.py:271-307](data-platform/tests/ddl/test_iceberg_tables.py:271) idempotent table list (28 tables sorted). | n/a (precondition closed) |
| 5 | All 9 v2/lineage asset graph deps present (Dagster asset graph + dbt selectors) | **DONE (M1-G2 + M1.5-4 verified)** | [test_assets.py:26-72](data-platform/tests/test_assets.py:26) `EXPECTED_CANONICAL_V2_IDENTIFIERS` (9 v2 + 9 lineage); [daily_refresh.py:49](data-platform/src/data_platform/daily_refresh.py:49) `DEFAULT_DBT_SELECTORS = ("staging", "intermediate", "marts", "marts_v2", "marts_lineage")`; [test_daily_refresh.py:100-110](data-platform/tests/integration/test_daily_refresh.py:100) asserts write_results includes all three group lengths; [test_daily_refresh.py:517](data-platform/tests/integration/test_daily_refresh.py:517) mocks `load_canonical_v2_marts` | n/a (precondition closed) |
| 6 | `FORBIDDEN_SCHEMA_FIELDS` / `FORBIDDEN_PAYLOAD_FIELDS` extension to lineage fields (`source_run_id`, `raw_loaded_at`) | **BLOCKED until legacy specs deleted** — intentionally NOT extended in M1.5 per hard rules | retirement-readiness §4. Extension would IMMEDIATELY fail every legacy `CANONICAL_MART_LOAD_SPECS` entry which still requires lineage columns. | retirement Phase B (after step 7 below) |
| 7 | `_M1D_LEGACY_RETIREMENT_XFAIL` decorator removed from 7 tests across 3 files | **NOT STARTED (intentional)** — xfail decorator remains in M1.5 per hard rules | [test_canonical_provider_neutrality.py](data-platform/tests/ddl/test_canonical_provider_neutrality.py) (3 tests), [test_canonical_writer_provider_neutrality.py](data-platform/tests/serving/test_canonical_writer_provider_neutrality.py) (3 tests), [test_marts_provider_neutrality.py](data-platform/tests/dbt/test_marts_provider_neutrality.py) (1 test). The override sweep (`DP_ENFORCE_M1D_PROVIDER_NEUTRALITY=1`) still produces the expected 44 failed parametrize-cases. | retirement Phase B (after step 8 below) |
| 8 | Legacy `CANONICAL_MART_LOAD_SPECS`, `CANONICAL_MART_TABLE_SPECS`, legacy `dbt/models/marts/mart_*.sql`, legacy `load_canonical_marts()` / `load_canonical_stock_basic()` call sites deletion | **NOT STARTED (intentional)** — legacy retained in M1.5 per hard rules | retirement-readiness §1, §7 Phase B | retirement Phase B owner |
| 9 | `namechange`, `block_trade`, 8 candidate event_timeline sources promotion (so `accepted_values` taxonomy on `mart_fact_event_v2` extends and the safe-subset closure converts to full M1 closure) | **DONE (M1.13)** — all 10 sources PROMOTED. `namechange` (M1.6, event_type='name_change'), `block_trade` (M1.8, event_type='block_trade'), and the 8 M1.11 candidates (M1.13: pledge_stat→pledge_summary, pledge_detail→pledge_event, repurchase→share_repurchase, stk_holdertrade→shareholder_trade, stk_surv→institutional_survey, limit_list_ths→price_limit_status, limit_list_d→price_limit_event, hm_detail→hot_money_trade). `mart_fact_event_v2.event_type` accepted_values taxonomy is now 16 entries; `mart_lineage_fact_event.source_interface_id` accepted_values is 16 entries; `int_event_timeline.sql` carries 16 UNION arms; `TUSHARE_ASSETS` count went from 28 → 36; provider_catalog `PROVIDER_MAPPINGS` event_timeline rows went from 8 → 16 with `PROMOTION_CANDIDATE_MAPPINGS` event_timeline rows going from 8 → 0. 8 new parity tests in `test_marts_models.py` mirror the block_trade exemplar and all pass; full repo sweep is 604 passed / 74 skipped / 44 xfailed (matches M1.11 baseline + 8 new passing tests). | [event-timeline-m1-6-source-promotion-audit-20260429.md](assembly/reports/stabilization/event-timeline-m1-6-source-promotion-audit-20260429.md), [event-timeline-m1-6-promotion-proof-20260429.md](assembly/reports/stabilization/event-timeline-m1-6-promotion-proof-20260429.md), [event-timeline-m1-7-source-closure-audit-20260429.md](assembly/reports/stabilization/event-timeline-m1-7-source-closure-audit-20260429.md), [event-timeline-m1-7-promotion-proof-20260429.md](assembly/reports/stabilization/event-timeline-m1-7-promotion-proof-20260429.md), [event-timeline-m1-8-block-trade-promotion-proof-20260429.md](assembly/reports/stabilization/event-timeline-m1-8-block-trade-promotion-proof-20260429.md), [event-timeline-m1-9-candidate-contract-audit-20260429.md](assembly/reports/stabilization/event-timeline-m1-9-candidate-contract-audit-20260429.md) (M1.9 BLOCKED verdict superseded), [event-timeline-m1-9-candidate-promotion-proof-20260429.md](assembly/reports/stabilization/event-timeline-m1-9-candidate-promotion-proof-20260429.md), [event-timeline-m1-11-candidate-schema-checkin-20260429.md](assembly/reports/stabilization/event-timeline-m1-11-candidate-schema-checkin-20260429.md) (M1.11 schema + uniqueness evidence), [event-timeline-m1-13-candidate-promotion-proof-20260429.md](assembly/reports/stabilization/event-timeline-m1-13-candidate-promotion-proof-20260429.md) (M1.13 promotion proof) | n/a (precondition closed) |

## Status summary

- **DONE:** preconditions 1, 2, 3, 4, 5, 9 (6 of 9). M1.13 closes precondition 9 (10 of 10 event_timeline sources PROMOTED, taxonomy 8 → 16 values).
- **BLOCKED until earlier preconditions close:** precondition 6.
- **NOT STARTED (intentional, sequencing):** preconditions 7, 8.

## M1.10 delta (2026-04-29)

Round M1.10 advanced precondition 3 to `DONE`: local fixture closed-loop proof
passed, then the controlled compose-Postgres proof was explicitly approved and
executed successfully.

- Added closed-loop fixture test
  `data-platform/tests/serving/test_canonical_writer.py::test_load_canonical_v2_marts_closed_loop_under_v2_flag_reads_pinned_snapshots`.
  Test runs writer over all 9 v2 + 9 lineage marts, then under
  `DP_CANONICAL_USE_V2=1` reads back via `read_canonical_dataset()` for all
  10 v2 dataset_ids + `get_canonical_stock_basic()` for stock_basic — every
  read confirms manifest-pinned snapshot equality with the writer
  `WriteResult.snapshot_id`. Fail-closed verified by deleting manifest and
  re-running.
- Wrote preflight feasibility evidence
  [`m1-10-controlled-v2-proof-preflight-20260429.md`](assembly/reports/stabilization/m1-10-controlled-v2-proof-preflight-20260429.md)
  with the `CONTROLLED_COMPOSE_PROOF_PASSED` boundary. The approved command
  started only the existing `lite-local` PostgreSQL service, installed
  data-platform into a throwaway Python 3.12 venv outside the repo, ran
  `python -m data_platform.daily_refresh --date 20260429 --mock`, then ran a
  separate `DP_CANONICAL_USE_V2=1` read smoke across all v2 dataset mappings.
  It is M1 controlled proof only — not M2 `daily_cycle_job` proof and not P5
  readiness.
- Wrote controlled-proof results write-up
  [`m1-10-controlled-v2-proof-results-20260429.md`](assembly/reports/stabilization/m1-10-controlled-v2-proof-results-20260429.md)
  capturing the dbt PASS=62/PASS=477 totals, the 27-write canonical step
  with 0 skips, and the matching writer→reader snapshot ids that prove
  cross-process manifest pinning.
- Wrote Phase B retirement readiness inventory
  [`m1-10-legacy-retirement-phase-b-inventory-20260429.md`](assembly/reports/stabilization/m1-10-legacy-retirement-phase-b-inventory-20260429.md)
  cataloging every legacy site that Phase B steps 1–7 must touch, with
  test gates per step. NO Phase B step executed in M1.10.
- Production code touched in M1.10 (additive Phase A wiring, NOT Phase B
  retirement):
  - `data-platform/src/data_platform/daily_refresh.py` — wired
    `load_canonical_v2_marts` into `_run_canonical_step`; added
    `marts_v2`/`marts_lineage` to `DEFAULT_DBT_SELECTORS`; added 3 date
    fields and ~26 decimal-numeric fields to the mock-fixture cast
    allow-lists; `_mock_value` now returns `"SSE"` for `exchange`. Legacy
    write path is unchanged — v2 + lineage are written **alongside**
    legacy.
  - `data-platform/tests/integration/test_daily_refresh.py` — extended
    write-result count assertion from `1 + len(CANONICAL_MART_LOAD_SPECS)`
    to also include v2 + lineage; added 3 new tests covering selectors
    + mock cast fields; mocked `load_canonical_v2_marts` in the fast
    success stub.
  - `data-platform/src/data_platform/dbt/models/marts/_schema.yml` —
    extended legacy `mart_fact_event.event_type` accepted_values to
    include `name_change` and `block_trade` (legacy and v2 marts share
    the same `int_event_timeline` source after M1.6 + M1.8).

## M1.11 delta (2026-04-29)

Round M1.11 advanced precondition 9 from `BLOCKED_NO_LOCAL_SCHEMA` (M1.9
verdict for the 8 candidates) to **`READY_FOR_TAXONOMY_SIGNOFF`** for all 8
sources. The unblock came from a newly-available local Tushare archive at
`/Volumes/dockcase2tb/database_all/股票数据/` which carries authoritative
CSV-header schemas + millions of historical rows for every previously-blocked
candidate.

- Wrote
  [`event-timeline-m1-11-candidate-schema-checkin-20260429.md`](assembly/reports/stabilization/event-timeline-m1-11-candidate-schema-checkin-20260429.md)
  containing per-source: authoritative column list (lifted directly from
  the Tushare-emitted CSV header in the archive), volume + date span,
  identity-fields proposal, empirical PK verification verdict, and a
  recommended canonical taxonomy (`event_type`, `event_date`,
  `event_subtype`, `summary` template).
- Empirical uniqueness verifier (read-only Python + DuckDB in-memory)
  scanned the full archive: 5 sources `PK_CONFIRMED` outright; 3 sources
  `PK_CONFIRMED_AFTER_STAGING_DEDUP` (byte-identical Tushare re-emissions
  collapse via the existing `stg_latest_raw` macro). All 8 verdicts
  reproducible by re-running
  `assembly/tmp-runtime/m1-11-precondition-9/run_uniqueness.py` (gitignored
  runtime helper).
- Production code touched in M1.11: NONE. No edits to
  `provider_catalog/registry.py`, `adapters/tushare/adapter.py`,
  `dbt/models/staging/`, `dbt/models/intermediate/int_event_timeline.sql`,
  `dbt/models/marts*/`. Implementation is M1.13's job after taxonomy
  sign-off.
- Hard rules: read-only access to `/Volumes/dockcase2tb`. No Tushare HTTP.
  No commits / push. M1.10 baseline test counts unchanged.

Preconditions 6, 7, 8 unchanged after M1.11 (still BLOCKED / NOT STARTED).

## M1.13 delta (2026-04-29)

Round M1.13 closes precondition 9 by promoting the 8 candidate
event_timeline sources whose schemas + identity tuples were verified in
M1.11. The mechanical closure followed the M1.6 / M1.8 exemplars —
adapter spec + staging model + UNION arm + accepted_values + parity test
for each source.

- Wrote
  [`event-timeline-m1-13-candidate-promotion-proof-20260429.md`](assembly/reports/stabilization/event-timeline-m1-13-candidate-promotion-proof-20260429.md)
  capturing per-source taxonomy mapping, files added/modified, parity
  test pass results, and the before/after coverage summary.
- Production code touched in M1.13 (12 files modified, 8 staging SQL
  files added):
  - `data-platform/src/data_platform/adapters/tushare/assets.py` —
    8 new schemas + 8 new asset specs; `TUSHARE_ASSETS` count
    28 → 36; `EVENT_METADATA_FIELDS` 7 → 15.
  - `data-platform/src/data_platform/adapters/tushare/__init__.py` —
    re-exports for the 8 new asset symbols.
  - `data-platform/src/data_platform/adapters/tushare/adapter.py` —
    8 new `_TushareClient` Protocol methods + 8 new entries in each
    of `EVENT_IDENTITY_FIELDS`, `EVENT_DATE_FIELDS`,
    `_METHOD_BY_DATASET`, `_PARTITION_DATE_FIELD_BY_DATASET`,
    `_PARTITION_REQUEST_PARAMS_BY_DATASET`,
    `_DATE_PARAM_NAMES_BY_DATASET`. `STOCK_TS_CODE_DATASETS` extends
    automatically through `EVENT_DATASETS = frozenset(EVENT_METADATA_FIELDS)`.
  - `data-platform/src/data_platform/provider_catalog/registry.py` —
    8 entries moved from `PROMOTION_CANDIDATE_MAPPINGS` (status
    `candidate`) to `PROVIDER_MAPPINGS` (status `promoted`) with the
    M1.11-verified wide identity tuples. Extended
    `_PARTITION_KEY_BY_RAW_DATASET` with the 8 new entries.
  - `data-platform/src/data_platform/daily_refresh.py` — extended
    `DATE_FIELD_NAMES` with `release_date` + `surv_date`; extended
    `STRING_NUMERIC_FIELD_NAMES` with the new sources' numeric
    columns so `--mock` rows pass the staging cast.
  - `data-platform/src/data_platform/dbt/models/staging/stg_*.sql` —
    8 new staging SQL files (pledge_stat, pledge_detail, repurchase,
    stk_holdertrade, stk_surv, limit_list_ths, limit_list_d,
    hm_detail) using the `stg_latest_raw` macro pattern.
  - `data-platform/src/data_platform/dbt/models/staging/_schema.yml` —
    8 new staging-model declarations with `unique_combination_of_columns`
    + per-column `not_null` + `parsable_yyyymmdd_or_date` tests.
  - `data-platform/src/data_platform/dbt/models/staging/_sources.yml` —
    8 new raw source declarations.
  - `data-platform/src/data_platform/dbt/models/intermediate/int_event_timeline.sql` —
    8 new UNION arms with literal `event_type` + `source_interface_id`
    + `concat()`-based `summary` from M1.11 sign-off table.
  - `data-platform/src/data_platform/dbt/models/intermediate/_schema.yml` —
    `event_type` and `source_interface_id` accepted_values 8 → 16
    each; updated description with M1.13 closure pointer.
  - `data-platform/src/data_platform/dbt/models/marts_v2/_schema.yml` —
    `mart_fact_event_v2.event_type` accepted_values 8 → 16; updated
    header comment + model description.
  - `data-platform/src/data_platform/dbt/models/marts_lineage/_schema.yml` —
    `mart_lineage_fact_event.source_interface_id` accepted_values
    8 → 16; updated header comment + model description.
  - `data-platform/src/data_platform/dbt/models/marts/_schema.yml` —
    legacy `mart_fact_event.event_type` accepted_values 8 → 16
    (legacy and v2 share the same `int_event_timeline` source).
- Test code touched in M1.13:
  - `data-platform/tests/adapters/test_tushare_events.py` — `EVENT_ASSETS`,
    `METHOD_BY_DATASET`, `FETCH_PARAMS_BY_DATASET`, `FakeTushareEventClient`
    extended for 8 new sources; `_event_row` date-field set extended
    with `exp_date`, `release_date`, `start_date`, `surv_date`;
    `_raw_partition_call_params` extended with new partition-date
    cases.
  - `data-platform/tests/dbt/test_intermediate_models.py` — `event_types`
    assertion 8 → 16 entries (alphabetic).
  - `data-platform/tests/dbt/test_marts_models.py` — bumped
    `event_summary` count `(8, 8)` → `(16, 16)`; added 8 new parity
    tests + 1 shared helper `_assert_event_v2_and_lineage_pair_preserved`
    that mirrors the block_trade exemplar (v2/lineage canonical-PK
    parity, lineage-column membership, event_type/source_interface_id
    presence).
  - `data-platform/tests/dbt/test_tushare_staging_models.py` —
    `DATE_FIELD_NAMES` + 7 new `<DATASET>_NUMERIC_FIELD_NAMES`
    constants + extended `_sample_value` so the 8 new datasets get
    parsable date strings + decimal-style numeric strings in
    fixtures.
  - `data-platform/tests/provider_catalog/test_provider_catalog.py` —
    `len(production_entries) == len(TUSHARE_ASSETS) == 28` → `36`.
- Production code NOT touched in M1.13:
  - `mart_fact_event_v2.sql` — `event_key` md5 derivation unchanged.
  - `mart_lineage_fact_event.sql` — same.
  - `tushare_available_interfaces.csv` — UNCHANGED. The validator at
    `registry.py:84` enforces `access_status == "available"` for
    every row in this inventory CSV. The actual "promotion" the
    M1.11 evidence file described as a `tushare_available_interfaces.csv` flip
    is encoded in `provider_catalog/registry.py` (PROVIDER_MAPPINGS
    membership) — `TUSHARE_INTERFACE_REGISTRY[<source_id>].promotion_status`
    is `"promoted"` for each of the 8 sources after M1.13.
  - Iceberg DDL, canonical writer specs, dataset routing, serving
    runtime — unchanged.
  - Legacy `canonical.*` specs — NOT deleted (Phase B owns it).
  - `_M1D_LEGACY_RETIREMENT_XFAIL` — NOT removed.
  - `FORBIDDEN_SCHEMA_FIELDS` / `FORBIDDEN_PAYLOAD_FIELDS` — NOT extended.
- Test sweep results after M1.13:
  - Provider catalog: 11 passed.
  - Adapter / raw: 171 passed.
  - dbt (skeleton + coverage + intermediate + marts + provider
    neutrality + staging): 64 passed, 3 skipped, 8 xfailed.
  - Integration daily refresh + canonical writer + reader: 58
    passed, 1 skipped.
  - V2 lane (`DP_CANONICAL_USE_V2=1`): 177 passed, 5 skipped, 17 xfailed.
  - 8 new parity tests via `-k pledge_stat or ...`: 8 passed.
  - Full repo sweep: 604 passed, 74 skipped, 44 xfailed.
- Hard rules: no Tushare HTTP. Local archive at
  `/Volumes/dockcase2tb/database_all/股票数据/` consulted read-only
  for column-list verification only (no rows copied into repo). No
  commits / push / amend / reset. `_M1D_LEGACY_RETIREMENT_XFAIL`,
  `FORBIDDEN_SCHEMA_FIELDS`, `FORBIDDEN_PAYLOAD_FIELDS` untouched.
  Legacy `canonical.*` specs untouched.

Preconditions 6, 7, 8 unchanged after M1.13 (still BLOCKED / NOT STARTED).

## P5 status

**P5 remains BLOCKED.** Precondition 9 closed in M1.13 (10/10 event_timeline
sources promoted, taxonomy 8 → 16 values), but P5 still requires:
- M2.6 production daily-cycle proof (gated on M2 entry, which is OUT OF SCOPE for M1.5+).
- Legacy retirement Phase B (preconditions 6, 7, 8) — can now start because the controlled production-like v2 proof passed and precondition 9 is closed, but it is not yet executed.

## Hard-rule declarations

- File started as M1.5 progress audit (no production code changed in that
  round). M1.10 added additive Phase A wiring — see *M1.10 delta* above
  for the exact diffs. No legacy `canonical.*` specs / load specs / dbt
  marts deleted; no `_M1D_LEGACY_RETIREMENT_XFAIL` removed; no
  `FORBIDDEN_SCHEMA_FIELDS` / `FORBIDDEN_PAYLOAD_FIELDS` extended.
- `project_ult_v5_0_1.md` and `ult_milestone.md` UNCHANGED.
- Production fetch / P5 shadow-run NOT started. Compose PostgreSQL was
  started only for the approved M1 controlled proof.
- API-6 / sidecar / frontend write API / Kafka/Flink/Temporal / news/Polymarket NOT touched.
- Tushare remains a `provider="tushare"` source adapter ONLY.
- `/Users/fanjie/Desktop/BIG/FrontEnd` NOT modified (read-only audit).
- Pre-existing dirty files NOT reverted.
- No `git init`. No commits. No push.
