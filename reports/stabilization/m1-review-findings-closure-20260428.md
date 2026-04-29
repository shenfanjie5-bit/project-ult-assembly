# M1 Review Findings Closure

Date: 2026-04-28

Scope: closure for the six review findings raised against the M0/M1 Claude Code implementation. This is still M1 work only. It does not start M2/M3/M4/P5, does not enable production fetch, and does not modify `project_ult_v5_0_1.md`.

## Closure Summary

| Finding | Status | Evidence |
| --- | --- | --- |
| F1 v2 tables never ensured | Fixed | `data-platform/src/data_platform/ddl/iceberg_tables.py` now includes `CANONICAL_V2_TABLE_SPECS` and `CANONICAL_LINEAGE_TABLE_SPECS` in `DEFAULT_TABLE_SPECS`; `tests/ddl/test_iceberg_tables.py` covers default ensure. |
| F2 daily refresh never publishes v2 | Fixed | `data-platform/src/data_platform/daily_refresh.py` includes `marts_v2` and `marts_lineage` selectors for full refresh and calls `load_canonical_v2_marts()` after the legacy mart publish. |
| F3 asset graph excludes v2/lineage | Fixed | `data-platform/src/data_platform/assets.py` includes v2/lineage DuckDB relations and a `canonical_v2.canonical_marts` publish asset. |
| F4 co-pin manifest not atomic | Mitigated | `data-platform/src/data_platform/serving/canonical_writer.py` validates v2/lineage key pairing before overwrite and performs best-effort rollback to prior snapshots on overwrite/manifest failure. If a table had no prior snapshot, PyIceberg has no safe rollback-to-no-snapshot API; this remains a documented storage limitation. |
| F5 formal leak path open | Fixed for legacy compat route | `frontend-api/src/frontend_api/routes/cycle.py` sanitizes legacy compat payloads recursively before returning them. Focused tests cover nested raw/source/provider fields. |
| F6 dim_security lineage misattributes source | Fixed | `data-platform/src/data_platform/dbt/models/marts_lineage/mart_lineage_dim_security.sql` now uses composite `source_interface_id='stock_basic+stock_company+namechange'` and the schema description/test document the multi-source attribution. |

## Verification

Commands run:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
.venv/bin/python -m pytest tests/ddl/test_iceberg_tables.py tests/integration/test_daily_refresh.py tests/test_assets.py tests/serving/test_canonical_writer.py -q
.venv/bin/python -m pytest tests/serving/test_catalog.py -q
.venv/bin/python -m ruff check src/data_platform/assets.py src/data_platform/daily_refresh.py src/data_platform/ddl/iceberg_tables.py src/data_platform/serving/canonical_writer.py tests/ddl/test_iceberg_tables.py tests/integration/test_daily_refresh.py tests/test_assets.py tests/serving/test_canonical_writer.py tests/dbt/test_marts_provider_neutrality.py scripts/init_iceberg_catalog.py tests/serving/test_catalog.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -p no:cacheprovider -q tests/dbt/test_marts_provider_neutrality.py -k 'dim_security_lineage_mart_discloses_composite_source_interface or lineage_mart_sql_carries_lineage_columns'
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -p no:cacheprovider --tb=no tests/ddl tests/serving tests/dbt tests/provider_catalog tests/cycle/test_current_cycle_inputs.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -p no:cacheprovider -q tests/ddl/test_iceberg_tables.py tests/serving/test_canonical_writer.py tests/serving/test_schema_evolution.py tests/serving/test_catalog.py tests/serving/test_formal.py tests/serving/test_formal_manifest_consistency.py tests/serving/test_canonical_datasets.py tests/serving/test_reader.py tests/dbt/test_dbt_skeleton.py tests/dbt/test_dbt_test_coverage.py tests/dbt/test_dbt_wrapper.py tests/dbt/test_intermediate_models.py tests/dbt/test_marts_models.py tests/dbt/test_tushare_local_fixtures.py tests/dbt/test_tushare_staging_models.py tests/provider_catalog tests/cycle/test_current_cycle_inputs.py tests/cycle/test_current_cycle_inputs_lineage_absent.py tests/integration/test_daily_refresh.py tests/test_assets.py

cd /Users/fanjie/Desktop/Cowork/project-ult/frontend-api
.venv/bin/pytest tests/test_cycle_routes.py tests/test_no_source_leak.py -q
.venv/bin/python -m py_compile src/frontend_api/routes/cycle.py tests/test_cycle_routes.py
```

Results:

- Finding-focused data-platform tests: `51 passed, 1 skipped`.
- `tests/serving/test_catalog.py`: `18 passed`.
- Focused lineage SQL regression tests: `2 passed`.
- Frontend legacy/no-source tests: `10 passed`.
- Ruff on Python files: passed.
- Non-parity data-platform sweep: passed.
- Full broader M1 sweep including expected parity scoreboard: `44 failed, 164 passed, 12 skipped`. All 44 failures are the intentionally retained legacy provider-neutrality scoreboard in:
  - `tests/ddl/test_canonical_provider_neutrality.py`
  - `tests/serving/test_canonical_writer_provider_neutrality.py`
  - `tests/dbt/test_marts_provider_neutrality.py`

`dbt parse` was attempted with the assembly Python 3.12 dbt executable but was blocked by missing local `data_platform` dbt profile. It was not used as pass evidence.

## Gate Status

- M1 review findings F1-F3 and F5-F6: fixed.
- F4: mitigated with pre-write validation and best-effort rollback; first-publish no-prior-snapshot atomic rollback remains a storage limitation.
- G1 Provider-neutral canonical: still partial/blocked because legacy `canonical.*` physical schemas and writer specs remain active for the seven unmigrated marts plus `stock_basic`.
- P5: still blocked.
