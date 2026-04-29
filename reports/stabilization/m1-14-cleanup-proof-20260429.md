# M1.14 — Phase B Step 6 + 7 Cleanup Proof (2026-04-29)

## Status

**M1.14 status: DONE.** Phase B steps 6 + 7 from the M1.10 inventory complete.
M1 closes to **9/9 preconditions DONE + 0 xfail + 0 deferred** = **完美收官**.

## What this round did

The 8 legacy `dbt/models/marts/mart_*.sql` files and the last
`_M1D_LEGACY_RETIREMENT_XFAIL` marker — both deferred from M1.12 per the M1.10
inventory — are gone. Repository state is clean of legacy retirement debt.

## Files deleted

```
data-platform/src/data_platform/dbt/models/marts/_schema.yml
data-platform/src/data_platform/dbt/models/marts/mart_dim_security.sql
data-platform/src/data_platform/dbt/models/marts/mart_dim_index.sql
data-platform/src/data_platform/dbt/models/marts/mart_fact_price_bar.sql
data-platform/src/data_platform/dbt/models/marts/mart_fact_financial_indicator.sql
data-platform/src/data_platform/dbt/models/marts/mart_fact_market_daily_feature.sql
data-platform/src/data_platform/dbt/models/marts/mart_fact_index_price_bar.sql
data-platform/src/data_platform/dbt/models/marts/mart_fact_forecast_event.sql
data-platform/src/data_platform/dbt/models/marts/mart_fact_event.sql
```

The empty `marts/` directory drops out of git tracking automatically (git
does not track empty directories).

## Files modified

### Production code

- `data-platform/src/data_platform/daily_refresh.py:47`
  - `DEFAULT_DBT_SELECTORS`: `("staging", "intermediate", "marts", "marts_v2", "marts_lineage")`
    → `("staging", "intermediate", "marts_v2", "marts_lineage")`. The `"marts"`
    selector is no longer meaningful (legacy mart SQLs are gone) — leaving it
    in would just match nothing on every dbt run.

### Tests

- `data-platform/tests/dbt/test_marts_provider_neutrality.py` (substantial rewrite):
  - Removed `_M1D_LEGACY_RETIREMENT_XFAIL` definition (the last marker site;
    M1.12 stripped 6/7 sites, this is the 7th).
  - Removed `LEGACY_MARTS_DIR` constant + `_legacy_mart_sql_files()` helper.
  - Removed `test_canonical_mart_sql_does_not_select_lineage_columns`
    (parametrized over `_legacy_mart_sql_files()` — empty post-deletion).
  - Removed `test_legacy_marts_directory_exists_and_is_inventoried` sentinel
    (the directory is gone).
  - Updated module docstring to reflect the post-M1.14 reality.
  - Kept `test_canonical_v2_mart_sql_does_not_select_lineage_columns`,
    `test_canonical_v2_mart_sql_does_not_select_provider_shaped_identifier`,
    `test_lineage_mart_sql_carries_lineage_columns`,
    `test_dim_security_lineage_mart_discloses_composite_source_interface`.

- `data-platform/tests/dbt/test_marts_models.py`:
  - Removed `MARTS_DIR` constant + `MART_MODEL_NAMES` list.
  - Removed `test_marts_sql_and_schema_contracts_are_present` (asserted legacy
    mart `_schema.yml` contracts; that file is gone).
  - Removed `test_marts_models_execute_with_duckdb_raw_fixture` (~110 lines;
    materialized + asserted legacy mart shapes; the `test_event_v2_and_lineage_marts_preserve_*`
    family covers the v2/lineage equivalent end-to-end).
  - Removed `test_price_mart_rejects_malformed_numeric_values` and
    `test_security_mart_rejects_malformed_numeric_values` (operated on
    `_render_mart_model("mart_fact_price_bar")` and
    `_render_mart_model("mart_dim_security")` — both legacy SQLs gone).
  - Updated `test_dbt_run_and_test_marts_with_rawwriter_fixture` selector tuple
    from `("staging", "intermediate", "marts")` to
    `("staging", "intermediate", "marts_v2", "marts_lineage")`.
  - Removed `_create_all_mart_tables` helper (only consumer was the deleted
    `test_marts_models_execute_with_duckdb_raw_fixture`).
  - Removed default `MARTS_DIR` arg from `_render_mart_model` signature
    (callers pass explicit `MARTS_V2_DIR` / `MARTS_LINEAGE_DIR`).
  - Kept all `test_event_v2_and_lineage_marts_preserve_*` tests (10 tests
    covering namechange + block_trade + 8 M1.13 candidate sources).

- `data-platform/tests/dbt/test_dbt_skeleton.py`:
  - Removed `MART_MODEL_NAMES` legacy list and the `marts/.gitkeep` /
    `marts/_schema.yml` / legacy mart SQL entries from the required-paths
    sweep + the SQL-models equality assertion.
  - Updated module comment to reference M1.13 + M1.14 closure state.

- `data-platform/tests/integration/test_daily_refresh.py:140-149`:
  - `test_daily_refresh_full_dbt_selectors_include_v2_and_lineage` selector
    tuple updated to drop `"marts"`.

- `data-platform/scripts/check_repository_artifacts.py:40-41`:
  - `REQUIRED_REPOSITORY_FILES`: replaced
    `src/data_platform/dbt/models/marts/_schema.yml` and
    `src/data_platform/dbt/models/marts/mart_fact_price_bar.sql` with their
    canonical_v2 + canonical_lineage equivalents. The repo guard now requires
    one v2 + one lineage representative SQL.

## Test sweep results

```sh
# Full repo sweep
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -p no:cacheprovider
# → 624 passed, 74 skipped, 0 xfailed, 0 failed
# (M1.13 baseline was 629 passed / 8 xfailed; M1.14 deletes 4 legacy tests +
#  1 sentinel test = -5 total; 8→0 xfail collapse from removing the parametrized
#  legacy test set; net delta -5 passing tests, 0 xfailed)

# Pre-M1.14 state was: 629 passed, 74 skipped, 8 xfailed, 0 failed
# Post-M1.14 state is: 624 passed, 74 skipped, 0 xfailed, 0 failed

# DP_ENFORCE_M1D_PROVIDER_NEUTRALITY=1 strict sweep
DP_ENFORCE_M1D_PROVIDER_NEUTRALITY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv/bin/python -m pytest -p no:cacheprovider \
  tests/serving/test_canonical_writer_provider_neutrality.py \
  tests/dbt/test_marts_provider_neutrality.py \
  tests/ddl/test_canonical_provider_neutrality.py
# → 71 passed, 0 failed
# (M1.13 baseline was 72 passed / 8 failed = the deferred legacy SQL parametrize
#  set; M1.14 removes both the marker + the parametrized tests, so DP_ENFORCE=1
#  is now fully strict-pass)

# Hygiene
git -C data-platform diff --check  # exit 0
```

## xfail count delta

| Sweep | Before M1.14 | After M1.14 | Delta |
|---|---|---|---|
| Full repo | 629/74/8 xfailed | 624/74/0 xfailed | **−8 xfailed**, −5 passing (deleted 4 legacy + 1 sentinel) |
| DP_ENFORCE strict | 72 passed / 8 failed | 71 passed / 0 failed | **−8 deferred failures**, −1 test (the deleted parametrized) |

**xfail count goal met: 8 → 0. M1.14 closure achieved.**

## Preconditions Status (M1 final)

| # | Precondition | Status |
|---|---|---|
| 1 | Cross-repo direct reader audit | DONE (M1.5-1) |
| 2 | DP_CANONICAL_USE_V2=1 test lane | DONE (M1.5-3) |
| 3 | Controlled production-like v2 proof | DONE (M1.10) |
| 4 | 9 v2 + 9 lineage specs present | DONE (M1-G2) |
| 5 | 9 v2/lineage asset graph deps | DONE (M1-G2) |
| 6 | FORBIDDEN_*_FIELDS extension + lineage bypass | DONE (M1.12) |
| 7 | _M1D_LEGACY_RETIREMENT_XFAIL stripped | **DONE (M1.12 + M1.14)** — 6/7 sites in M1.12; final 7th site in M1.14 |
| 8 | Legacy specs / loaders deletion | DONE (M1.12) |
| 9 | 8 candidate event_timeline sources promoted | DONE (M1.13) |

**M1 final state: 9/9 DONE + 0 xfail + 0 deferred.**

## Phase B inventory closure

| Step | Action | Status |
|---|---|---|
| 1 | Route writer to v2 only | DONE (M1.12) |
| 2 | Delete legacy load specs + loaders | DONE (M1.12) |
| 3 | Delete legacy table specs | DONE (M1.12) |
| 4 | Extend FORBIDDEN_*_FIELDS + lineage bypass | DONE (M1.12) |
| 5 | Strip _M1D_LEGACY_RETIREMENT_XFAIL | DONE (M1.12 6 sites + M1.14 1 site) |
| 6 | Delete legacy `dbt/models/marts/mart_*.sql` | **DONE (M1.14)** |
| 7 | Archive legacy `canonical.*` Iceberg tables in catalog | Operational only — no code change. The 9 deleted DDL specs (M1.12 step 3) mean no new writes; existing PG-backed Iceberg tables remain queryable for historical snapshots, no archival action needed. |

## Read-side fallback (NOT in M1.14 scope)

`canonical_datasets.CANONICAL_DATASET_TABLE_MAPPINGS` (10 entries routing
dataset_id → `canonical.*`) and `reader._CANONICAL_MART_TABLES_BY_NAMESPACE[CANONICAL_NAMESPACE]`
remain. Under `DP_CANONICAL_USE_V2=0` (default off), `read_canonical_dataset()`
still resolves to the legacy `canonical.*` namespace. This is by design per
the M1.10 inventory:

> 7. Archive (do not write, do not drop) legacy `canonical.*` Iceberg tables —
>    leave existing tables in catalog with no active writer; do not drop, to
>    preserve historical cycles.

The catalog still holds the 8 legacy `canonical.*` Iceberg tables from
historical writes; reader fallback can still query them (for historical
snapshots). Removing this fallback is a stronger retirement (true 写读双端
retirement) and belongs to a future P5 / M1.5+ milestone, NOT M1.14.

## Hard-rule declarations

- `project_ult_v5_0_1.md` UNCHANGED.
- `ult_milestone.md` UNCHANGED.
- No production fetch.
- No P5 shadow-run.
- No M2 / M3 / M4 work.
- No API-6 / sidecar / frontend write API / Kafka / Flink / Temporal / news / Polymarket touched.
- Tushare remains a `provider="tushare"` source adapter only.
- `frontend-api` NOT touched.
- `/Users/fanjie/Desktop/BIG/FrontEnd/**` NOT modified.
- canonical_v2.* + canonical_lineage.* spec sets unchanged from M1.13 closure
  state (still 9 v2 + 9 lineage = 18 specs in `DEFAULT_TABLE_SPECS`).

## Cross-references

- Phase B inventory (planning): [`m1-10-legacy-retirement-phase-b-inventory-20260429.md`](m1-10-legacy-retirement-phase-b-inventory-20260429.md)
- M1.12 retirement evidence: [`m1-12-phase-b-retirement-proof-20260429.md`](m1-12-phase-b-retirement-proof-20260429.md)
- M1.13 promotion evidence: [`event-timeline-m1-13-candidate-promotion-proof-20260429.md`](event-timeline-m1-13-candidate-promotion-proof-20260429.md)
- M1 progress tracker: [`m1-legacy-retirement-preconditions-progress-20260428.md`](m1-legacy-retirement-preconditions-progress-20260428.md)

## Next steps

- Push `m1-baseline-2026-04-29` to remote.
- Merge baseline → `main` (or open PR).
- M2 entry (M2.6 production daily-cycle proof) is the next blocker for P5;
  out of M1 scope.
