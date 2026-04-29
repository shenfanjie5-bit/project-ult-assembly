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
| 6 | `FORBIDDEN_SCHEMA_FIELDS` / `FORBIDDEN_PAYLOAD_FIELDS` extension to lineage fields (`source_run_id`, `raw_loaded_at`) | **DONE (M1.12)** — both sets extended; `_forbidden_payload_fields_for(identifier)` and `_forbidden_schema_fields_for(namespace)` helpers strip the lineage block from the forbidden set when the spec lives in `canonical_lineage`. 3 new tests added in `tests/serving/test_canonical_writer.py` verify positive/negative path; `test_FORBIDDEN_PAYLOAD_FIELDS_extends_to_canonical_lineage` and `test_FORBIDDEN_SCHEMA_FIELDS_includes_canonical_lineage_block` flipped from xfail → strict pass. | [m1-12-phase-b-retirement-proof-20260429.md](assembly/reports/stabilization/m1-12-phase-b-retirement-proof-20260429.md) | n/a (precondition closed) |
| 7 | `_M1D_LEGACY_RETIREMENT_XFAIL` decorator removed | **DONE (M1.12) for 6 of 7 sites; 1 site deferred to M1.14** — `tests/serving/test_canonical_writer_provider_neutrality.py` (3 sites + def) and `tests/ddl/test_canonical_provider_neutrality.py` (3 sites + def) are stripped; tests now strict-pass. The remaining site at `tests/dbt/test_marts_provider_neutrality.py:78` parametrizes over `_legacy_mart_sql_files()` which still finds 8 SQL files on disk (M1.10 inventory step 6 retains them until M1.14). M1.14 deletes those SQLs and lets the test go strict-pass. | [m1-12-phase-b-retirement-proof-20260429.md](assembly/reports/stabilization/m1-12-phase-b-retirement-proof-20260429.md) | M1.14 owner (delete `dbt/models/marts/mart_*.sql` + strip last marker) |
| 8 | Legacy `CANONICAL_MART_LOAD_SPECS`, `CANONICAL_MART_TABLE_SPECS`, `CANONICAL_STOCK_BASIC_SPEC`, `load_canonical_marts()`, `load_canonical_stock_basic()` deletion | **DONE (M1.12)** — all 5 symbols deleted from `canonical_writer.py` + `iceberg_tables.py`. Daily refresh + assets graph routed to `load_canonical_v2_marts` only. `load_canonical_table` retained but reduced (now non-mart canonical entity-table writes only, used by `serving.schema_evolution`). 14 legacy tests deleted; 12 v2 tests + 4 schema_evolution tests refactored. **Legacy `dbt/models/marts/mart_*.sql` files NOT deleted** (deferred to M1.14 per M1.10 inventory). **Legacy `canonical.*` Iceberg tables NOT archived in catalog** (deferred to M1.14). | [m1-12-phase-b-retirement-proof-20260429.md](assembly/reports/stabilization/m1-12-phase-b-retirement-proof-20260429.md) | M1.14 owner (delete legacy mart SQLs + archive Iceberg tables) |
| 9 | `namechange`, `block_trade`, 8 candidate event_timeline sources promotion (so `accepted_values` taxonomy on `mart_fact_event_v2` extends and the safe-subset closure converts to full M1 closure) | **PARTIAL — 2/10 promoted; 8 candidates schema-checked-in and uniqueness-verified, READY_FOR_TAXONOMY_SIGNOFF (M1.11)** — `namechange` PROMOTED in M1.6 (event_type='name_change'); `block_trade` PROMOTED in M1.8 (event_type='block_trade'). **M1.11 supersedes the M1.9 BLOCKED_NO_LOCAL_SCHEMA verdict for all 8 remaining candidates**: the local Tushare archive at `/Volumes/dockcase2tb/database_all/股票数据/` carries authoritative CSV-header schemas + millions of historical rows, which let us (a) lift authoritative column lists, (b) verify intra-day uniqueness empirically (5 sources `PK_CONFIRMED`, 3 sources `PK_CONFIRMED_AFTER_STAGING_DEDUP` — byte-identical Tushare re-emissions resolved by the existing `stg_latest_raw` macro), and (c) propose canonical `event_type` taxonomy + `summary` template + identity_fields per source. Owner sign-off table sits in the M1.11 evidence file; M1.13 implements adapter + fixture + staging + UNION + parity-test for 8 sources after sign-off. | [event-timeline-m1-6-source-promotion-audit-20260429.md](assembly/reports/stabilization/event-timeline-m1-6-source-promotion-audit-20260429.md), [event-timeline-m1-6-promotion-proof-20260429.md](assembly/reports/stabilization/event-timeline-m1-6-promotion-proof-20260429.md), [event-timeline-m1-7-source-closure-audit-20260429.md](assembly/reports/stabilization/event-timeline-m1-7-source-closure-audit-20260429.md), [event-timeline-m1-7-promotion-proof-20260429.md](assembly/reports/stabilization/event-timeline-m1-7-promotion-proof-20260429.md), [event-timeline-m1-8-block-trade-promotion-proof-20260429.md](assembly/reports/stabilization/event-timeline-m1-8-block-trade-promotion-proof-20260429.md), [event-timeline-m1-9-candidate-contract-audit-20260429.md](assembly/reports/stabilization/event-timeline-m1-9-candidate-contract-audit-20260429.md) (M1.9 BLOCKED verdict superseded), [event-timeline-m1-9-candidate-promotion-proof-20260429.md](assembly/reports/stabilization/event-timeline-m1-9-candidate-promotion-proof-20260429.md), [event-timeline-m1-11-candidate-schema-checkin-20260429.md](assembly/reports/stabilization/event-timeline-m1-11-candidate-schema-checkin-20260429.md) (M1.11 schema + uniqueness evidence) | M1.13 implementation owner: read M1.11 sign-off table verbatim → 8 staging models + 1 `int_event_timeline.sql` UNION-arms patch + 2 `_schema.yml` accepted_values extensions + 1 adapter `_TushareFetchSpec` patch + 1 `registry.py` identity-tuple patch + 8 parity tests + `tushare_available_interfaces.csv` flip |

## Status summary

- **DONE:** preconditions 1, 2, 3, 4, 5, 6, 7, 8 (8 of 9 — M1.12 closed 6/7/8).
- **PARTIAL (2 of 10 sources promoted: namechange in M1.6, block_trade in M1.8; 8 candidates schema-checked-in + uniqueness-verified in M1.11, READY_FOR_TAXONOMY_SIGNOFF; M1.13 implementation in parallel worktree):** precondition 9.

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

## M1.12 delta (2026-04-29)

Round M1.12 executed the **Phase B atomic retirement** (steps 1–5 from
the M1.10 inventory). It branched from `m1-baseline-2026-04-29` in a
dedicated worktree (`/Users/fanjie/Desktop/Cowork/project-ult-m1-12/`)
running in parallel with M1.13.

- **Step 1** (route writer to v2 only): `daily_refresh._run_canonical_step`
  + `assets.py` callable graph reduced to `load_canonical_v2_marts`. Legacy
  loaders no longer invoked.
- **Step 2** (delete legacy load specs + loaders): `CANONICAL_MART_LOAD_SPECS`,
  `load_canonical_marts`, `load_canonical_stock_basic`, `CANONICAL_STOCK_BASIC_IDENTIFIER`
  deleted from `serving/canonical_writer.py`; 14 legacy tests deleted from
  `tests/serving/test_canonical_writer.py` + `test_reader.py`.
  `load_canonical_table` retained but scope-reduced to non-mart canonical
  writes (consumed by `serving.schema_evolution`).
- **Step 3** (delete legacy table specs): `CANONICAL_STOCK_BASIC_SPEC`,
  `CANONICAL_MART_TABLE_SPECS` deleted from `ddl/iceberg_tables.py`.
  `DEFAULT_TABLE_SPECS` 28 → 20.
- **Step 4** (extend FORBIDDEN_*_FIELDS with lineage namespace bypass):
  both sets extended with `source_run_id` + `raw_loaded_at`; new
  `_forbidden_payload_fields_for(identifier)` and
  `_forbidden_schema_fields_for(namespace)` helpers strip the lineage
  block when the spec lives in `canonical_lineage`. 3 new tests verify
  positive/negative bypass behavior.
- **Step 5** (strip `_M1D_LEGACY_RETIREMENT_XFAIL` markers): 6 of 7
  decorator usages + 2 of 3 marker definitions removed across
  `tests/serving/test_canonical_writer_provider_neutrality.py` and
  `tests/ddl/test_canonical_provider_neutrality.py`. Tests refactored
  to parametrize over `CANONICAL_V2_MART_LOAD_SPECS` /
  `CANONICAL_V2_TABLE_SPECS` (legacy symbols gone). The 1 remaining
  marker site at `tests/dbt/test_marts_provider_neutrality.py:78` is
  deferred to M1.14 because the legacy `dbt/models/marts/mart_*.sql`
  files are still on disk per the M1.10 inventory step 6 deferral.

Side fix during Step 5: `tests/serving/test_schema_evolution.py` was
referencing `canonical.stock_basic` and `canonical.fact_price_bar`
(deleted in Step 3); rewritten to use the still-declared
`canonical.canonical_entity` and `canonical.entity_alias`.

Test sweeps after M1.12:
- preflight: **47 passed, 1 skipped** (M1.11 was 58/1; -12 deleted legacy + 3 added lineage bypass = -9 net).
- M1 standard: **58 passed, 2 skipped, 8 xfailed** (xfail count unchanged; deferred to M1.14).
- V2 lane: **185 passed, 5 skipped, 0 xfailed** (M1.11 was 177/5/17; xfail count dropped 17→0 — every retirement xfail is now strict-pass).
- DP_ENFORCE_M1D_PROVIDER_NEUTRALITY=1 strict sweep: 72 passed / 8 failed (the 8 failures are the deferred legacy SQL parametrize set).

Hard rules: no production fetch; no P5; no M2/M3/M4; no API-6/sidecar/news/Polymarket; Tushare-only adapter; legacy `mart_*.sql` files not deleted; legacy Iceberg tables not archived; `/Users/fanjie/Desktop/BIG/FrontEnd/**` unchanged. No commits, no push.

Full evidence at [`m1-12-phase-b-retirement-proof-20260429.md`](assembly/reports/stabilization/m1-12-phase-b-retirement-proof-20260429.md).

## P5 status

**P5 remains BLOCKED.** None of the M1.5–M1.12 work changes that. P5 still requires:
- M2.6 production daily-cycle proof (gated on M2 entry, which is OUT OF SCOPE for M1).
- Legacy retirement Phase B (preconditions 6, 7, 8) — **DONE in M1.12** (the legacy `mart_*.sql` files deleted and the last xfail marker stripped will land in optional M1.14 cleanup; that's not gating P5).
- Closure of the 8 remaining `event_timeline` candidate sources (precondition 9) — independent track running in parallel as M1.13. After M1.13 lands, M1 = 9/9 DONE; P5 is gated on M2.6 only.

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
