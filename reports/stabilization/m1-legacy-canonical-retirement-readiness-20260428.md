# M1 Legacy Canonical Retirement Readiness Plan

**Round:** M1-G3
**Date:** 2026-04-28
**Status:** Inventory + plan only. NO legacy code deleted in this round.

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
| event_timeline | canonical.fact_event | canonical_v2.fact_event | **CUTOVER-ELIGIBLE-PARTIAL** (8 promoted sources after M1.8; 8 candidate interfaces remain BLOCKED_NO_LOCAL_SCHEMA per the M1.9 contract audit — column lists not in repo, owner check-in needed) |
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

Extending to `frozenset({"submitted_at", "ingest_seq", "source_run_id", "raw_loaded_at"})` would IMMEDIATELY fail every legacy `CANONICAL_MART_TABLE_SPECS` entry (they all carry `source_run_id` and `raw_loaded_at` — these are the lineage columns the legacy specs require). Cannot extend until legacy specs are removed.

Test that captures this: [test_canonical_provider_neutrality.py:110-122](data-platform/tests/ddl/test_canonical_provider_neutrality.py:110) — `test_FORBIDDEN_SCHEMA_FIELDS_includes_canonical_lineage_block` — currently `xfail` under `_M1D_LEGACY_RETIREMENT_XFAIL`.

### `FORBIDDEN_PAYLOAD_FIELDS`

[canonical_writer.py:35](data-platform/src/data_platform/serving/canonical_writer.py:35): `frozenset({"submitted_at", "ingest_seq"})`.

Extending to add `source_run_id`, `raw_loaded_at` would IMMEDIATELY fail every legacy `CanonicalLoadSpec.required_columns` (they require lineage columns by design). Cannot extend until legacy load specs are removed.

Test that captures this: [test_canonical_writer_provider_neutrality.py:91-102](data-platform/tests/serving/test_canonical_writer_provider_neutrality.py:91) — `test_FORBIDDEN_PAYLOAD_FIELDS_extends_to_canonical_lineage` — currently `xfail` under `_M1D_LEGACY_RETIREMENT_XFAIL`.

## Section 5 — When can `_M1D_LEGACY_RETIREMENT_XFAIL` be removed?

Pre-conditions, in dependency order:

1. **All in-repo direct callers of `read_canonical(<bare_name>)` audited.** Confirm zero direct calls in src code outside test fixtures. (Candidates to inspect: orchestrator, main-core, frontend-api, subsystem-*.) — **NOT YET VERIFIED.**
2. **`DP_CANONICAL_USE_V2=1` exercised once in a controlled production-like test** (Lite compose PostgreSQL service + host-side Python 3.12 `daily_refresh --mock` + `load_canonical_v2_marts` + read-side smoke through `read_canonical_dataset`) so all readers run on v2 end-to-end. **This is a precondition for M2.6 readiness review, NOT gated by M2.6 itself.** Section 6 below confirms the dependency direction (M2.6 depends on M1, not vice versa). — **DONE in M1.10 follow-up.**
3. **`load_canonical_marts()` / `load_canonical_stock_basic()` either deleted or re-pointed to canonical_v2 specs.** This is the actual write-side cutover. — **NOT YET STARTED.**
4. **`CANONICAL_MART_LOAD_SPECS`, `CANONICAL_MART_TABLE_SPECS`, `CANONICAL_STOCK_BASIC_SPEC` deleted from src.** This unblocks `FORBIDDEN_SCHEMA_FIELDS` and `FORBIDDEN_PAYLOAD_FIELDS` extensions.
5. **`FORBIDDEN_SCHEMA_FIELDS` and `FORBIDDEN_PAYLOAD_FIELDS` extended to include `{"source_run_id", "raw_loaded_at"}`.**
6. **Legacy `mart_*.sql` files in `dbt/models/marts/` deleted or marked as compatibility shims.** (8 files.) Verifies that no canonical `mart_*` SQL still selects lineage at the SELECT shape.
7. **Decorator `_M1D_LEGACY_RETIREMENT_XFAIL` removed** from:
   - [test_canonical_provider_neutrality.py](data-platform/tests/ddl/test_canonical_provider_neutrality.py) (3 tests)
   - [test_canonical_writer_provider_neutrality.py](data-platform/tests/serving/test_canonical_writer_provider_neutrality.py) (3 tests)
   - [test_marts_provider_neutrality.py](data-platform/tests/dbt/test_marts_provider_neutrality.py) (1 test)
8. **Remaining 8 candidate event_timeline sources promoted or explicitly scoped out in a future adapter-build round** (so `accepted_values` taxonomy on `mart_fact_event_v2` either extends to full event_timeline coverage or records the narrowed scope).
9. **Remaining event_timeline branches resolved or explicitly scoped out**: M1.6 promoted `namechange`; M1.8 promoted `block_trade` (with the int_event_timeline uniqueness contract widened to include `summary`); M1.9 contract audit refined the 8 candidate interfaces' verdict to `BLOCKED_NO_LOCAL_SCHEMA` (the upstream blocker is owner column-list check-in, not staging implementation effort).

The retirement is **NOT blocked on M2.6**: M2.6 production daily-cycle proof depends on canonical_v2 write/read readiness, not the other way around. M1-G3 retirement readiness can land before M2.6 if steps 1-7 above are taken in sequence — and step 2 in particular (the controlled v2-default-on proof) is what M2.6's readiness review will look for, NOT something to wait for M2.6 to deliver.

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

### Recommended sequencing (handoff to M1.5 owner; M2.6 reads the result)

1. **Phase A (M1.5)** — verification + controlled v2 proof:
   - Audit every subrepo for direct `read_canonical("<bare_name>")` calls.
   - Default `DP_CANONICAL_USE_V2=1` in CI/test.
   - Run E2E test suite under v2-default-on.
   - Run a controlled Lite-compose v2 cycle (dbt run + load_canonical_v2_marts + read-side smoke) — this is the production-like proof M2.6 review will reference; it is delivered by M1.5, NOT by M2.6.
2. **Phase B (post-M1.5, before legacy retirement)** — retirement:
   - Delete legacy load specs from canonical_writer.py.
   - Delete legacy table specs from iceberg_tables.py.
   - Extend `FORBIDDEN_SCHEMA_FIELDS` and `FORBIDDEN_PAYLOAD_FIELDS`.
   - Delete legacy `dbt/models/marts/mart_*.sql` files.
   - Remove `_M1D_LEGACY_RETIREMENT_XFAIL` decorator.
   - Update test fixtures.
3. **Phase C (M2.6)** — production daily-cycle proof reads the now-canonical-v2-only state.

### Rollback plan

If Phase C breaks production:
- Restore the deleted legacy specs from git history.
- Restore `FORBIDDEN_SCHEMA_FIELDS` to the `{submitted_at, ingest_seq}` set.
- Re-add the xfail decorator.
- Set `DP_CANONICAL_USE_V2` to unset (default legacy).

## Section 8 — Status declarations

- This is a **READINESS** evidence file. No legacy code deleted.
- M1-G2 advanced (NOT closed) M1 by adding canonical_v2.fact_event for the safe subset.
- Full M1 closure remains pending until the 8 remaining PROMOTION_CANDIDATE_MAPPINGS sources are adapter-built/promoted or explicitly scoped out AND the retirement sequencing in Section 5 lands.
- P5 remains BLOCKED.
- `project_ult_v5_0_1.md` and `ult_milestone.md` UNCHANGED.

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
  Phase B step executed in M1.10. The inventory is a map, not a green
  light — Phase B can now start, but it remains unexecuted.
- M1.10 status declarations:
  - `project_ult_v5_0_1.md` and `ult_milestone.md` UNCHANGED.
  - No production fetch. No P5 shadow-run. No M2/M3/M4 work.
  - No API-6 / sidecar / frontend write API / Kafka / Flink / Temporal /
    news / Polymarket touched.
  - Tushare remains a `provider="tushare"` source adapter only.
  - Legacy `canonical.*` specs / load specs / dbt marts NOT deleted.
  - `_M1D_LEGACY_RETIREMENT_XFAIL` NOT removed.
  - `FORBIDDEN_SCHEMA_FIELDS` / `FORBIDDEN_PAYLOAD_FIELDS` NOT extended.
  - `/Users/fanjie/Desktop/BIG/FrontEnd` NOT modified.
  - No commits, no push, no amend, no reset.
