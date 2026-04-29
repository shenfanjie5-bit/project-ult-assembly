# M1.10 — Legacy Canonical Retirement Phase B Readiness Inventory (2026-04-29)

## Scope

Read-only inventory of every legacy `canonical.*` site that must be retired
or extended in the post-M1.5 Phase B execution round. M1.10 does **not**
delete or modify any legacy code or tests in this round. The goal is a
traceable map: every Phase B step lists exact file paths, line ranges, and
the test gate that proves the deletion is safe.

## Phase B Gating Order

Steps **must** be executed in the order below. Each step has a single test
gate. The order is dictated by code-load semantics: `assets.py` references
the loaders by string at module-load time; deleting the loaders before
re-routing assets would break import. Likewise the `FORBIDDEN_*` extension
must follow legacy-spec deletion or fail-closed will trip on legacy
`source_run_id` columns still embedded in `CANONICAL_MART_TABLE_SPECS`.

---

## Reference-Site Inventory (Phase B targets)

### Group A — Legacy writer entry points

| Symbol | Site (path:line) | Phase B step | Test gate |
|---|---|---|---|
| `load_canonical_marts(catalog, duckdb_path)` | `data-platform/src/data_platform/serving/canonical_writer.py:890` | step 2 (delete) | `tests/serving/test_canonical_writer_provider_neutrality.py::test_canonical_mart_load_spec_does_not_require_raw_lineage` flips xfail → pass |
| `load_canonical_stock_basic(catalog, duckdb_path, *, allow_empty=False)` | `data-platform/src/data_platform/serving/canonical_writer.py:874` | step 2 (delete) | (covered by ingestion + cycle inputs tests; see below) |
| `load_canonical_table(...)` legacy publish guard | `data-platform/src/data_platform/serving/canonical_writer.py:815` | step 2 (delete or shrink to v2 only) | `tests/serving/test_canonical_writer.py::test_load_canonical_table_rejects_public_single_mart_publish` (semantic update) |
| Legacy `__all__` exports | `data-platform/src/data_platform/serving/canonical_writer.py:1508-1509` (load_canonical_marts, load_canonical_stock_basic) | step 2 (remove from `__all__`) | tree shake / test_assets coverage |

### Group B — Legacy loader callers

| Symbol | Site (path:line) | Phase B step | Test gate |
|---|---|---|---|
| `daily_refresh.py` import + invocation | `data-platform/src/data_platform/daily_refresh.py:36-37` (imports), `:522` (load_canonical_stock_basic call), `:532` (load_canonical_marts call) | step 1 (route to v2) | `tests/integration/test_daily_refresh.py::test_mock_daily_refresh_is_repeatable_and_writes_report` keeps passing once legacy stubs removed |
| Asset-graph callable string references | `data-platform/src/data_platform/assets.py:35` (`":load_canonical_stock_basic"`), `:37` (`CANONICAL_MARTS_CALLABLE = ":load_canonical_marts"`) | step 1 (remove) | `tests/test_assets.py::test_build_assets_links_raw_staging_marts_and_canonical_specs` (update assertion to v2) |
| Asset-graph references — additional sites | `data-platform/src/data_platform/assets.py:19, 322, 383, 393, 396, 400` (per M1.10 plan) | step 1 (remove) | same as above |
| Internal callers in writer module | `data-platform/src/data_platform/serving/canonical_writer.py:1297, 1303` (called from internal CLI helper / fallback) | step 2 (delete branch with loaders) | `tests/serving/test_canonical_writer.py` 39 existing tests guard regression |

### Group C — Legacy specs

| Symbol | Site (path:line) | Phase B step | Test gate |
|---|---|---|---|
| `CANONICAL_MART_LOAD_SPECS` | `data-platform/src/data_platform/serving/canonical_writer.py:141, 807, 905, 1493` | step 2 (delete) | `tests/serving/test_canonical_writer_provider_neutrality.py::test_canonical_mart_load_spec_does_not_require_provider_shaped_identifier` flips xfail → pass |
| `CANONICAL_STOCK_BASIC_SPEC` | `data-platform/src/data_platform/ddl/iceberg_tables.py:71` (export), `:1050` (table-list) | step 3 (delete) | `tests/ddl/test_canonical_provider_neutrality.py::test_canonical_business_spec_does_not_carry_raw_lineage` (parametrize covers stock_basic) flips xfail → pass |
| `CANONICAL_MART_TABLE_SPECS` | `data-platform/src/data_platform/ddl/iceberg_tables.py:365, 869` | step 3 (delete) | same as above + `test_canonical_business_spec_does_not_carry_provider_shaped_identifier` flips |

### Group D — Forbidden-fields extension

| Symbol | Current value | Site (path:line) | Phase B step | Test gate |
|---|---|---|---|---|
| `FORBIDDEN_PAYLOAD_FIELDS` | `frozenset({"submitted_at", "ingest_seq"})` | `data-platform/src/data_platform/serving/canonical_writer.py:35` (declaration), `:76, :1360` (use sites) | step 4 (extend with `source_run_id`, `raw_loaded_at`) | `tests/serving/test_canonical_writer_provider_neutrality.py::test_FORBIDDEN_PAYLOAD_FIELDS_extends_to_canonical_lineage` flips xfail → pass |
| `FORBIDDEN_SCHEMA_FIELDS` | `frozenset({"submitted_at", "ingest_seq"})` | `data-platform/src/data_platform/ddl/iceberg_tables.py:23` (declaration), `:55` (use site) | step 4 (extend with `source_run_id`, `raw_loaded_at`) | `tests/ddl/test_canonical_provider_neutrality.py:109::test_FORBIDDEN_SCHEMA_FIELDS_includes_canonical_lineage_block` flips xfail → pass |

After step 4 lands, the canonical_lineage namespace must keep these fields
(it's the lineage table's job to carry them); confirm the FORBIDDEN sets
apply only to canonical business specs (the existing canonical_lineage
specs have their own validation per M1-D design).

### Group E — Legacy XFAIL markers (`_M1D_LEGACY_RETIREMENT_XFAIL`)

The marker name string is a Python identifier defined at the top of each
file and applied as a decorator. Each marker is gated by
`os.environ.get("DP_ENFORCE_M1D_PROVIDER_NEUTRALITY") != "1"` so the suite
can be flipped early under that env var to dry-run the post-Phase-B state.

| File | Definition | Use sites | Phase B step | Strict-pass gate |
|---|---|---|---|---|
| `data-platform/tests/serving/test_canonical_writer_provider_neutrality.py` | `:22-29` | `:48`, `:71`, `:90` (3 use sites) | step 5 (remove decorator + definition) | After steps 2 + 4 land, run `DP_ENFORCE_M1D_PROVIDER_NEUTRALITY=1 pytest tests/serving/test_canonical_writer_provider_neutrality.py` — must pass before stripping markers |
| `data-platform/tests/dbt/test_marts_provider_neutrality.py` | `:25-32` | `:78` (1 parametrized use) | step 5 (remove decorator + definition) | After step 6 (delete legacy mart SQL) lands, parametrized matrix becomes empty → use site is vacuous → marker can be removed |
| `data-platform/tests/ddl/test_canonical_provider_neutrality.py` | `:31-38` | `:74`, `:93`, `:109` (3 use sites) | step 5 (remove decorator + definition) | After steps 3 + 4 land, all 3 tests pass strict |

Total marker usage: **7 decorator sites** across **3 files**, plus **3 marker
definitions** to remove. Phase B step 5 is structurally final once steps 1–4
are merged.

### Group F — Legacy dbt mart SQL files

`data-platform/src/data_platform/dbt/models/marts/` (8 SQL + `_schema.yml`):

| File | v2 replacement |
|---|---|
| `mart_dim_security.sql` | `marts_v2/mart_dim_security_v2.sql` |
| `mart_dim_index.sql` | `marts_v2/mart_dim_index_v2.sql` |
| `mart_fact_price_bar.sql` | `marts_v2/mart_fact_price_bar_v2.sql` |
| `mart_fact_financial_indicator.sql` | `marts_v2/mart_fact_financial_indicator_v2.sql` |
| `mart_fact_market_daily_feature.sql` | `marts_v2/mart_fact_market_daily_feature_v2.sql` |
| `mart_fact_index_price_bar.sql` | `marts_v2/mart_fact_index_price_bar_v2.sql` |
| `mart_fact_forecast_event.sql` | `marts_v2/mart_fact_forecast_event_v2.sql` |
| `mart_fact_event.sql` | `marts_v2/mart_fact_event_v2.sql` |
| `_schema.yml` | `marts_v2/_schema.yml` (already in place) |

Note: `marts/mart_stock_basic.sql` does **not** exist; legacy stock_basic is
written by `load_canonical_stock_basic` directly (no dbt model). v2 adds
`marts_v2/mart_stock_basic_v2.sql` so v2 has 9 files vs legacy's 8.

Phase B step 6 deletes the 8 legacy SQLs + `marts/_schema.yml`. Test gates:

- `tests/dbt/test_marts_provider_neutrality.py::test_canonical_mart_sql_does_not_select_lineage_columns` (parametrized 8×) — vacuously passes once `marts/` dir empty.
- `tests/dbt/test_dbt_skeleton.py` — update `EXPECTED_LEGACY_MARTS` (or equivalent) to expect zero legacy mart SQLs.

### Group G — Tests asserting legacy `canonical.*`

| File | Site (selected high-confidence references) | Phase B disposition |
|---|---|---|
| `data-platform/tests/serving/test_canonical_writer.py` | `:53, :69, :84, :113, :128, :148, :180, :213, :451, :470, :485` (12+ tests using `load_canonical_stock_basic` / `load_canonical_marts` / `CANONICAL_STOCK_BASIC_IDENTIFIER`) | step 5 / step 8 (rewrite to assert only v2 path) |
| `data-platform/tests/serving/test_reader.py` | `:518, :555` (legacy loader invocations); `:832-858` (`test_read_canonical_rejects_unpublished_mart_head` for legacy namespace) | step 5 / step 8 (mirror to v2 namespace; existing v2 tests already cover) |
| `data-platform/tests/test_assets.py` | `:171, :179` (asserts legacy callable identifiers) | step 1 update (re-target to v2 callable) |
| `data-platform/tests/integration/test_daily_refresh.py` | references legacy load via mock pipeline (verified during M1.5) | step 1 update (drop legacy loader stubs once daily_refresh.py is v2-only) |

This is not exhaustive — Phase B step 5 must run a `grep -rn "load_canonical_marts\|load_canonical_stock_basic\|CANONICAL_MART_LOAD_SPECS\|CANONICAL_MART_TABLE_SPECS\|CANONICAL_STOCK_BASIC_SPEC\|canonical\\.\\(dim_\\|fact_\\|stock_basic\\)"` sweep before merging.

---

## Phased Deletion / Cutover Plan

| Step | Action | Files | Test gate |
|---|---|---|---|
| 1 | Route writer to v2 only — remove legacy loader calls from `daily_refresh.py` (`:36-37, :522, :532`); remove legacy callable refs from `assets.py` (`:19, :35, :37, :322, :383, :393, :396, :400`) | `daily_refresh.py`, `assets.py` | `tests/integration/test_daily_refresh.py` + `tests/test_assets.py` (update v2 expectations) |
| 2 | Delete legacy loaders + load specs — `load_canonical_marts`, `load_canonical_stock_basic`, `CANONICAL_MART_LOAD_SPECS`; remove from `__all__` | `serving/canonical_writer.py:141, 807, 874, 890, 905, 1297, 1303, 1493, 1508-1509` | `test_canonical_writer_provider_neutrality.py::test_canonical_mart_load_spec_does_not_require_raw_lineage` and `…does_not_require_provider_shaped_identifier` flip xfail → pass |
| 3 | Delete legacy table specs — `CANONICAL_MART_TABLE_SPECS`, `CANONICAL_STOCK_BASIC_SPEC` | `ddl/iceberg_tables.py:71, 365, 869, 1050` | `test_canonical_provider_neutrality.py:74, :93` flip xfail → pass |
| 4 | Extend forbidden-fields sets — add `source_run_id`, `raw_loaded_at` to both `FORBIDDEN_SCHEMA_FIELDS` (ddl/iceberg_tables.py:23) and `FORBIDDEN_PAYLOAD_FIELDS` (serving/canonical_writer.py:35) | as listed | `test_FORBIDDEN_PAYLOAD_FIELDS_extends_to_canonical_lineage` (test_canonical_writer_provider_neutrality.py:90) and `test_FORBIDDEN_SCHEMA_FIELDS_includes_canonical_lineage_block` (test_canonical_provider_neutrality.py:109) flip xfail → pass |
| 5 | Remove `_M1D_LEGACY_RETIREMENT_XFAIL` decorator + 3 definitions; rewrite tests asserting legacy `canonical.*` | 7 decorator sites + 3 definitions across `test_canonical_writer_provider_neutrality.py`, `test_marts_provider_neutrality.py`, `test_canonical_provider_neutrality.py`; legacy-asserting tests in `test_canonical_writer.py`, `test_reader.py`, `test_assets.py`, `test_daily_refresh.py` | `DP_ENFORCE_M1D_PROVIDER_NEUTRALITY=1 pytest <files>` must pass strict before markers are stripped |
| 6 | Delete legacy dbt marts under `data-platform/src/data_platform/dbt/models/marts/` (8 SQL + `_schema.yml`) | listed in Group F | `test_canonical_mart_sql_does_not_select_lineage_columns` (parametrized 8×) becomes vacuous; `test_dbt_skeleton.py` expectation update |
| 7 | Archive (do not active-write) legacy `canonical.*` Iceberg tables in catalog — drop the writer path but leave existing tables in PG/Iceberg catalog so historical cycles remain queryable | `serving/catalog.py` (canonical_v2 namespace registration only); migration playbook in assembly | manual; no automated test gate (catalog state is operational) |

---

## Why Phase B is NOT executed in M1.10

- Hard rules forbid deletion of legacy `canonical.*`, removal of
  `_M1D_LEGACY_RETIREMENT_XFAIL`, and extension of `FORBIDDEN_*_FIELDS`
  in this round.
- Controlled production-like v2 proof has now executed successfully after
  approval (precondition 3 = DONE). Phase B was still not executed in M1.10;
  this inventory remains the map for the next atomic retirement round.
- 8 event_timeline candidates (`pledge_*`, `repurchase`, `stk_holdertrade`,
  `limit_list_*`, `hm_detail`, `stk_surv`) remain
  `BLOCKED_NO_LOCAL_SCHEMA`. Phase B does not block on them — but legacy
  `canonical.fact_event` covers the same 8 source interfaces today via
  the int_event_timeline UNION. Removing the legacy table before the
  candidate sources are promoted would not lose data (canonical_v2 is a
  superset for the 8 already-promoted interfaces) but losing an active
  fallback now is risky.
- Preconditions 6, 7, 8 (which depend on Phase B) all stay BLOCKED until
  the retirement round lands.

---

## What Must Happen Before Phase B Step 1 Can Land

1. Controlled v2 proof has passed. The executed command is recorded in
   `m1-10-controlled-v2-proof-preflight-20260429.md` (boundary
   `CONTROLLED_COMPOSE_PROOF_PASSED`); it started only the existing
   `lite-local` PostgreSQL service and ran host-side data-platform/dbt
   under Python 3.12. This is M1 controlled proof only, not M2
   `daily_cycle_job` proof or P5 readiness.
2. Phase B steps 1–5 must land as one atomic round (any of them out
   of order leaves the codebase un-buildable). Step 6 + 7 can land
   separately.
3. `tests/test_assets.py` expectation update must be planned together
   with `assets.py` callable removal (single PR).

## Cross-References

- Preflight evidence: [`m1-10-controlled-v2-proof-preflight-20260429.md`](m1-10-controlled-v2-proof-preflight-20260429.md)
- Controlled-proof results: [`m1-10-controlled-v2-proof-results-20260429.md`](m1-10-controlled-v2-proof-results-20260429.md)
- Progress evidence: [`m1-legacy-retirement-preconditions-progress-20260428.md`](m1-legacy-retirement-preconditions-progress-20260428.md)
- Readiness evidence: [`m1-legacy-canonical-retirement-readiness-20260428.md`](m1-legacy-canonical-retirement-readiness-20260428.md)
- Closed-loop test: `data-platform/tests/serving/test_canonical_writer.py::test_load_canonical_v2_marts_closed_loop_under_v2_flag_reads_pinned_snapshots`
