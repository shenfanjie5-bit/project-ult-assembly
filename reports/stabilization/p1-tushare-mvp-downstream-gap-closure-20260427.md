# P1 Tushare MVP Downstream Gap Closure - 2026-04-27

## Scope

This evidence covers the P1 data-platform hardening batch for the six known
MVP downstream gaps among already connected Tushare APIs. It does not add new
Tushare APIs, does not add API-6, and does not introduce news, Polymarket,
sidecar, command/run/freeze, or release-freeze surfaces.

## Closed Downstream Gaps

| Tushare dataset | New intermediate path | New mart path | Canonical path |
| --- | --- | --- | --- |
| `daily_basic` | `int_market_daily_features` | `mart_fact_market_daily_feature` | `canonical.fact_market_daily_feature` |
| `stk_limit` | `int_market_daily_features` | `mart_fact_market_daily_feature` | `canonical.fact_market_daily_feature` |
| `moneyflow` | `int_market_daily_features` | `mart_fact_market_daily_feature` | `canonical.fact_market_daily_feature` |
| `index_daily` | `int_index_price_bars` | `mart_fact_index_price_bar` | `canonical.fact_index_price_bar` |
| `trade_cal` | `int_index_price_bars` | `mart_fact_index_price_bar` | `canonical.fact_index_price_bar` |
| `forecast` | `int_forecast_events` | `mart_fact_forecast_event` | `canonical.fact_forecast_event` |

## Code Evidence

- dbt intermediate models:
  - `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/dbt/models/intermediate/int_market_daily_features.sql`
  - `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/dbt/models/intermediate/int_index_price_bars.sql`
  - `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/dbt/models/intermediate/int_forecast_events.sql`
- dbt mart models:
  - `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/dbt/models/marts/mart_fact_market_daily_feature.sql`
  - `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/dbt/models/marts/mart_fact_index_price_bar.sql`
  - `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/dbt/models/marts/mart_fact_forecast_event.sql`
- Canonical mart load specs:
  - `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/ddl/iceberg_tables.py`
  - `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/serving/canonical_writer.py`
- The `index_daily` + `trade_cal` path is exchange-aware: index suffixes
  `.SH`, `.SZ`, and `.BJ` map to `SSE`, `SZSE`, and `BSE` before calendar
  enrichment, preventing a Shenzhen index from inheriting an SSE calendar row.
- Asset/cycle wiring follows `CANONICAL_MART_LOAD_SPECS`, so the new mart
  relations are included in the single `canonical_marts` write group instead
  of being exposed as separate public canonical writes.

## Validation

User-requested P1 verification command:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest -q \
  tests/adapters/test_tushare*.py \
  tests/dbt/test_tushare_staging_models.py \
  tests/dbt/test_intermediate_models.py \
  tests/dbt/test_marts_models.py \
  tests/dbt/test_dbt_test_coverage.py \
  tests/serving/test_canonical_writer.py
```

Result: passed.

Additional impacted tests:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest -q \
  tests/dbt/test_dbt_skeleton.py \
  tests/ddl/test_iceberg_tables.py \
  tests/test_assets.py \
  tests/serving/test_reader.py \
  tests/integration/test_daily_refresh.py
```

Result: `43 passed, 1 skipped`.

## Negative Scope

- The old verified compatibility matrix rows were not touched.
- This is not a P5 shadow-run claim.
- This is not a production daily-cycle proof; it only closes the known P1
  downstream data-platform gaps needed before that proof.
- The remaining 12 APIs required to reach the blueprint's 40 API target are
  handled in the separate target-list decision evidence.
