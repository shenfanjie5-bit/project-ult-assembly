# M1 Legacy Canonical Retirement Readiness Plan

**Round:** M1-G3
**Date:** 2026-04-28
**Status:** Inventory + plan only. NO legacy code deleted in this round.

**Current supersession (2026-04-30):** The plan below began as M1-G3
inventory. Its open precondition statuses are superseded by
[m1-legacy-retirement-preconditions-progress-20260428.md](assembly/reports/stabilization/m1-legacy-retirement-preconditions-progress-20260428.md):
all 9 preconditions are DONE, M1.13 promoted the 8 event_timeline
candidates, and M1.14 removed the final retirement xfail. M1/G1 is now
closed; P5 remains blocked by post-M1 gates.

## Purpose

Inventory the legacy `canonical.*` namespace surface so M1.5 / M2.6 know exactly what to retire and when. Establish the pre-conditions for removing the `_M1D_LEGACY_RETIREMENT_XFAIL` decorator and extending `FORBIDDEN_SCHEMA_FIELDS` / `FORBIDDEN_PAYLOAD_FIELDS` to lineage fields. The retirement is sequenced behind the canonical_v2 implementation and reader cutover; it does NOT block on M2.6.

## Section 1 — Legacy `canonical.*` source-code reference inventory

### Source-code references (data-platform/src)

`grep -rn '"canonical\.' data-platform/src/data_platform/ | wc -l` returned **41 references** (consistent with the prior C2 audit count of ~40 plus the M1-G2 docstring change).

Top callers by module:

- [registry.py](data-platform/src/data_platform/provider_catalog/registry.py) — 17 refs in `field_mapping` declarations (these are provider-catalog input to BOTH legacy and v2 readers; not retirement targets).
- [canonical_writer.py](data-platform/src/data_platform/serving/canonical_writer.py) — `CANONICAL_MART_LOAD_SPECS` defines 8 legacy load specs at lines 141-363 (after v2 additions). These remain the WRITE path for legacy `canonical.*` tables.
- [iceberg_tables.py](data-platform/src/data_platform/ddl/iceberg_tables.py) — `CANONICAL_NAMESPACE = "canonical"` at line 24; `CANONICAL_MART_TABLE_SPECS` at ~line 365 (after v2 additions). These remain the DDL definitions for legacy tables.
- [assets.py](data-platform/src/data_platform/assets.py) — Dagster asset registration: `CANONICAL_STOCK_BASIC_CALLABLE` at line 35 and `CANONICAL_MARTS_CALLABLE` at line 37 (callable strings pointing at `canonical_writer:load_canonical_marts` / `load_canonical_stock_basic`).
- [daily_refresh.py](data-platform/src/data_platform/daily_refresh.py) — invokes `load_canonical_stock_basic` (line 522) and `load_canonical_marts` (line 532) in the daily refresh path.
- [serving/reader.py](data-platform/src/data_platform/serving/reader.py) — `read_canonical`, `read_canonical_dataset`, `read_canonical_dataset_snapshot` (lines 63, 118, 136) — these resolve through `_selected_dataset_to_table()` so they pick up v2 under the env flag automatically.
- [serving/schema_evolution.py:228](data-platform/src/data_platform/serving/schema_evolution.py:228) — calls `load_canonical_table` (the single-spec writer entry).

### Test-code references (data-platform/tests)

187 occurrences in test code (per C2 audit). The bulk are fixture set-ups that exercise the legacy write path; they are not retirement targets but will need updating when the legacy specs are removed.

## Section 2 — Cutover-eligibility per legacy reader

For every reader that resolves through `_selected_dataset_to_table()` in [canonical_datasets.py](data-platform/src/data_platform/serving/canonical_datasets.py), env flag `DP_CANONICAL_USE_V2=1` flips to v2 transparently. After M1-G2, all 10 legacy mappings have v2 siblings:

| dataset_id | legacy table | v2 table | cutover status |
|---|---|---|---|
| security_master | canonical.dim_security | canonical_v2.dim_security | **CUTOVER-ELIGIBLE** |
| security_profile | canonical.dim_security | canonical_v2.dim_security | **CUTOVER-ELIGIBLE** |
| price_bar | canonical.fact_price_bar | canonical_v2.fact_price_bar | **CUTOVER-ELIGIBLE** |
| adjustment_factor | canonical.fact_price_bar | canonical_v2.fact_price_bar | **CUTOVER-ELIGIBLE** |
| market_daily_feature | canonical.fact_market_daily_feature | canonical_v2.fact_market_daily_feature | **CUTOVER-ELIGIBLE** |
| index_master | canonical.dim_index | canonical_v2.dim_index | **CUTOVER-ELIGIBLE** |
| index_price_bar | canonical.fact_index_price_bar | canonical_v2.fact_index_price_bar | **CUTOVER-ELIGIBLE** |
| event_timeline | canonical.fact_event | canonical_v2.fact_event | **CUTOVER-ELIGIBLE** after M1.13 (16/16 source interfaces promoted; the M1.9 `BLOCKED_NO_LOCAL_SCHEMA` verdict was superseded by M1.11 schema check-in + M1.13 promotion) |
| financial_indicator | canonical.fact_financial_indicator | canonical_v2.fact_financial_indicator | **CUTOVER-ELIGIBLE** |
| financial_forecast_event | canonical.fact_forecast_event | canonical_v2.fact_forecast_event | **CUTOVER-ELIGIBLE** |

All readers that go through `read_canonical_dataset()`, `read_canonical_dataset_snapshot()`, `canonical_table_for_dataset()`, or `canonical_table_identifier_for_dataset()` are CUTOVER-ELIGIBLE because they resolve through the env-flag-aware mapping.

### Direct hardcoded `canonical.<name>` reader callers

- `read_canonical()` itself accepts a bare table name (not a dataset_id). It is called inside `read_canonical_dataset()` after dataset→table resolution, so it inherits the v2 cutover when called via `read_canonical_dataset()`. Any caller that uses `read_canonical("dim_security")` directly with a hardcoded name bypasses the v2 flag.

  - Search target: `rg -n 'read_canonical\("' data-platform/src` — should produce zero hits in src code aside from the alias chain inside reader.py.
  - **CUTOVER-BLOCKED** if any such call sites exist outside the test suite.

- `serving.canonical_writer.load_canonical_marts()` writes ONLY to legacy `canonical.*`. Its v2 counterpart is `load_canonical_v2_marts()`. Both are wired in `daily_refresh.py`. **DUAL-WRITE** today.

- `serving.canonical_writer.load_canonical_stock_basic()` writes ONLY to legacy `canonical.stock_basic`. Its v2 counterpart writes to `canonical_v2.stock_basic`. **DUAL-WRITE** today.

## Section 3 — Compatibility API status

**`read_canonical()`** at [serving/reader.py:63](data-platform/src/data_platform/serving/reader.py:63) is the legacy direct table accessor.
- It takes a bare physical table name (e.g. `"dim_security"`) and returns rows from `canonical.<name>`.
- Callers that go through `read_canonical_dataset()` (line 118) get v2 routing via `_selected_dataset_to_table()`.
- Direct callers of `read_canonical(<bare_name>)` bypass v2 routing.

**No formal "legacy compatibility wrapper" exists.** The legacy code path IS the default (when `DP_CANONICAL_USE_V2` is unset). Removing the legacy code path requires:
1. Confirming all in-repo readers go through `read_canonical_dataset()` (or the helpers in `canonical_datasets.py`), NOT directly through `read_canonical()` with a hardcoded name.
2. Confirming all readers respect `_selected_dataset_to_table()` (which they do, via the helpers).

## Section 4 — `FORBIDDEN_*_FIELDS` extension blockers

### `FORBIDDEN_SCHEMA_FIELDS`

[iceberg_tables.py:23](data-platform/src/data_platform/ddl/iceberg_tables.py:23): `frozenset({"submitted_at", "ingest_seq"})`.

At M1-G3, extending to `frozenset({"submitted_at", "ingest_seq", "source_run_id", "raw_loaded_at"})` would have failed every legacy `CANONICAL_MART_TABLE_SPECS` entry (they all carried `source_run_id` and `raw_loaded_at` — these are the lineage columns the legacy specs required). This is superseded by M1.12, which removed the legacy specs and extended the forbidden-field sets.

Test that captured this at M1-G3: [test_canonical_provider_neutrality.py:110-122](data-platform/tests/ddl/test_canonical_provider_neutrality.py:110) — `test_FORBIDDEN_SCHEMA_FIELDS_includes_canonical_lineage_block` — was `xfail` under `_M1D_LEGACY_RETIREMENT_XFAIL`; later strict-pass after M1.12/M1.14.

### `FORBIDDEN_PAYLOAD_FIELDS`

[canonical_writer.py:35](data-platform/src/data_platform/serving/canonical_writer.py:35): `frozenset({"submitted_at", "ingest_seq"})`.

At M1-G3, extending to add `source_run_id`, `raw_loaded_at` would have failed every legacy `CanonicalLoadSpec.required_columns` (they required lineage columns by design). This is superseded by M1.12, which removed the legacy load specs and extended the payload guard.

Test that captured this at M1-G3: [test_canonical_writer_provider_neutrality.py:91-102](data-platform/tests/serving/test_canonical_writer_provider_neutrality.py:91) — `test_FORBIDDEN_PAYLOAD_FIELDS_extends_to_canonical_lineage` — was `xfail` under `_M1D_LEGACY_RETIREMENT_XFAIL`; later strict-pass after M1.12/M1.14.

## Section 5 — When can `_M1D_LEGACY_RETIREMENT_XFAIL` be removed?

Pre-conditions, in dependency order. The status labels below are current after
M1.14; the original M1-G3 open-plan wording is retained only in the surrounding
inventory context.

1. **All in-repo direct callers of `read_canonical(<bare_name>)` audited.** Confirm zero direct calls in src code outside test fixtures. (Candidates to inspect: orchestrator, main-core, frontend-api, subsystem-*.) — **DONE (M1.5-1).**
2. **`DP_CANONICAL_USE_V2=1` exercised once in a controlled production-like test** (Lite compose PostgreSQL service + host-side Python 3.12 `daily_refresh --mock` + `load_canonical_v2_marts` + read-side smoke through `read_canonical_dataset`) so all readers run on v2 end-to-end. **This is a precondition for M2.6 readiness review, NOT gated by M2.6 itself.** Section 6 below confirms the dependency direction (M2.6 depends on M1, not vice versa). — **DONE in M1.10 follow-up.**
3. **`load_canonical_marts()` / `load_canonical_stock_basic()` either deleted or re-pointed to canonical_v2 specs.** This is the actual write-side cutover. — **DONE (M1.12).**
4. **`CANONICAL_MART_LOAD_SPECS`, `CANONICAL_MART_TABLE_SPECS`, `CANONICAL_STOCK_BASIC_SPEC` deleted from src.** This unblocks `FORBIDDEN_SCHEMA_FIELDS` and `FORBIDDEN_PAYLOAD_FIELDS` extensions. — **DONE (M1.12).**
5. **`FORBIDDEN_SCHEMA_FIELDS` and `FORBIDDEN_PAYLOAD_FIELDS` extended to include `{"source_run_id", "raw_loaded_at"}`.** — **DONE (M1.12).**
6. **Legacy `mart_*.sql` files in `dbt/models/marts/` deleted or marked as compatibility shims.** (8 files.) Verifies that no canonical `mart_*` SQL still selects lineage at the SELECT shape. — **DONE (M1.14 deletion).**
7. **Decorator `_M1D_LEGACY_RETIREMENT_XFAIL` removed** from — **DONE (M1.12 + M1.14, 0 markers remain):**
   - [test_canonical_provider_neutrality.py](data-platform/tests/ddl/test_canonical_provider_neutrality.py) (3 tests)
   - [test_canonical_writer_provider_neutrality.py](data-platform/tests/serving/test_canonical_writer_provider_neutrality.py) (3 tests)
   - [test_marts_provider_neutrality.py](data-platform/tests/dbt/test_marts_provider_neutrality.py) (1 test)
8. **Remaining 8 candidate event_timeline sources promoted or explicitly scoped out in a future adapter-build round** (so `accepted_values` taxonomy on `mart_fact_event_v2` either extends to full event_timeline coverage or records the narrowed scope). — **DONE (M1.13 promotion).**
9. **Remaining event_timeline branches resolved or explicitly scoped out**: M1.6 promoted `namechange`; M1.8 promoted `block_trade` (with the int_event_timeline uniqueness contract widened to include `summary`); M1.9 contract audit refined the 8 candidate interfaces' verdict to `BLOCKED_NO_LOCAL_SCHEMA`; M1.11 supplied schema + uniqueness evidence; M1.13 promoted the 8 candidates. — **DONE.**

The retirement was **NOT blocked on M2.6**: M2.6 production daily-cycle
proof depends on canonical_v2 write/read readiness, not the other way around.
That dependency direction is now resolved for M1: M1.10 supplied step 2,
M1.12/M1.14 completed retirement, and M2.6 remains a separate production
daily-cycle proof gate.

## Section 6 — Dependency direction (M2.6 vs M1)

Reaffirmed per user direction:
- **M2.6 production daily-cycle proof depends on M1 closure** (the canonical write/read path must be on canonical_v2 + lineage).
- **M1 closure does NOT depend on M2.6.**
- Specifically: legacy retirement (steps 3-7 above) can proceed once readers are confirmed cutover-eligible (step 1) and `DP_CANONICAL_USE_V2=1` has been exercised once (step 2). M2.6 is the natural place to exercise step 2 but is not the only place.

## Section 7 — Risks and rollback

### Risks

1. **Silent reader divergence**: a downstream subrepo (orchestrator, main-core, frontend-api) might call `read_canonical("<bare_name>")` directly. If so, the v2 cutover is incomplete and step 1 above is BLOCKED.
2. **Iceberg snapshot continuity**: removing legacy `canonical.*` tables retires their snapshot history. Any analytical query joining historical snapshots loses access. Mitigation: keep the tables in catalog; only remove the writer + DDL spec.
3. **dbt model graph break**: deleting `dbt/models/marts/mart_*.sql` files would break the legacy dbt run. Mitigation: keep the legacy mart files AS-IS until step 4 (load specs deleted), then either delete or convert to compatibility views.
4. **Test fixture cleanup**: 187 test-code references to legacy strings must be reviewed. Many are in shared fixtures.

### Recommended sequencing (historical handoff; current status noted)

1. **Phase A (M1.5/M1.10)** — verification + controlled v2 proof: **DONE**.
   - Audit every subrepo for direct `read_canonical("<bare_name>")` calls.
   - Default `DP_CANONICAL_USE_V2=1` in CI/test.
   - Run E2E test suite under v2-default-on.
   - Run a controlled Lite-compose v2 cycle (dbt run + load_canonical_v2_marts + read-side smoke) — this is the production-like proof M2.6 review will reference; it is delivered by M1.5, NOT by M2.6.
2. **Phase B (M1.12/M1.14)** — retirement: **DONE**.
   - Delete legacy load specs from canonical_writer.py.
   - Delete legacy table specs from iceberg_tables.py.
   - Extend `FORBIDDEN_SCHEMA_FIELDS` and `FORBIDDEN_PAYLOAD_FIELDS`.
   - Delete legacy `dbt/models/marts/mart_*.sql` files.
   - Remove `_M1D_LEGACY_RETIREMENT_XFAIL` decorator.
   - Update test fixtures.
3. **Phase C (M2.6)** — production daily-cycle proof reads the now-canonical-v2-only state: **pending**.

### Rollback plan

If Phase C breaks production:
- Restore the deleted legacy specs from git history.
- Restore `FORBIDDEN_SCHEMA_FIELDS` to the `{submitted_at, ingest_seq}` set.
- Re-add the xfail decorator.
- Set `DP_CANONICAL_USE_V2` to unset (default legacy).

## Section 8 — Status declarations

- This started as a **READINESS** evidence file. No legacy code was deleted in the original M1-G3 round.
- M1-G2 advanced (NOT closed) M1 by adding canonical_v2.fact_event for the safe subset; that statement is historical.
- Current status after M1.14: M1/G1 is closed; all 9 retirement preconditions are DONE, the 8 candidates are promoted, and 0 `_M1D_LEGACY_RETIREMENT_XFAIL` markers remain.
- P5 remains BLOCKED.
- `project_ult_v5_0_1.md` was UNCHANGED in this readiness round.

## Section 9 — M1.10 delta (2026-04-29)

- Phase A step 4 (controlled production-like v2 proof) advanced to
  **DONE — local fixture closed-loop proof passed and controlled
  compose-Postgres proof executed successfully after approval**. M1.10 added
  [`test_load_canonical_v2_marts_closed_loop_under_v2_flag_reads_pinned_snapshots`](data-platform/tests/serving/test_canonical_writer.py)
  — a single test that drives `load_canonical_v2_marts()` once over a
  fixture catalog (all 9 v2 + 9 lineage marts) and then under
  `DP_CANONICAL_USE_V2=1` reads each of the 10 v2 dataset_ids back
  through `read_canonical_dataset()` (plus stock_basic via
  `get_canonical_stock_basic`), confirming each read pins to the
  writer-published snapshot via the combined `_mart_snapshot_set.json`
  manifest. Fail-closed verified by deleting the manifest and re-running.
  See [`m1-10-controlled-v2-proof-preflight-20260429.md`](assembly/reports/stabilization/m1-10-controlled-v2-proof-preflight-20260429.md)
  for the feasibility table and the `CONTROLLED_COMPOSE_PROOF_PASSED`
  boundary classification, and
  [`m1-10-controlled-v2-proof-results-20260429.md`](assembly/reports/stabilization/m1-10-controlled-v2-proof-results-20260429.md)
  for the dbt PASS=62 / PASS=477 totals, 27-write canonical step, and the
  matching writer→reader snapshot ids that prove cross-process manifest
  pinning. The approved command started only the existing
  `lite-local` PostgreSQL service, created a throwaway host-side Python 3.12
  runtime outside the repo, ran `data_platform.daily_refresh --mock`, then
  ran a separate `DP_CANONICAL_USE_V2=1` reader smoke. It is not an M2
  `daily_cycle_job` proof or P5 readiness evidence.
- Phase B (Section 5 + Section 7 step list) gained a structured paper map
  in [`m1-10-legacy-retirement-phase-b-inventory-20260429.md`](assembly/reports/stabilization/m1-10-legacy-retirement-phase-b-inventory-20260429.md).
  The inventory enumerates every reference site (loaders, callers, specs,
  forbidden-field declarations, xfail markers, legacy dbt SQL, legacy
  asserting tests) with file path + line range + per-step test gate. NO
  Phase B step executed in M1.10. The inventory was a map, not a green
  light. Current status is superseded by M1.12/M1.14, where Phase B
  closed.
- Historical M1.10 status declarations:
  - `project_ult_v5_0_1.md` and `ult_milestone.md` UNCHANGED.
  - No production fetch. No P5 shadow-run. No M2/M3/M4 work.
  - No API-6 / sidecar / frontend write API / Kafka / Flink / Temporal /
    news / Polymarket touched.
  - Tushare remains a `provider="tushare"` source adapter only.
  - Legacy `canonical.*` specs / load specs / dbt marts NOT deleted in M1.10; superseded by M1.12/M1.14.
  - `_M1D_LEGACY_RETIREMENT_XFAIL` NOT removed in M1.10; superseded by M1.14.
  - `FORBIDDEN_SCHEMA_FIELDS` / `FORBIDDEN_PAYLOAD_FIELDS` NOT extended in M1.10; superseded by M1.12.
  - `/Users/fanjie/Desktop/BIG/FrontEnd` NOT modified.
  - No commits, no push, no amend, no reset.
