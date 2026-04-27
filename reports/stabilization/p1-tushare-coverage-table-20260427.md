# P1 Tushare API / Staging Coverage Table

Date: 2026-04-27

Scope: code-grounded data-platform coverage evidence only. This does not run or add API-6, does not expand ingestion implementation, and does not change data-platform code.

## Source Baseline

- Blueprint target: Project ULT v5.0.1 describes P1 as approximately 40 Tushare APIs, 40 staging models, and 75-90 dbt SQL transformations.
- Current code baseline: `data-platform/src/data_platform/adapters/tushare/assets.py` declares 28 `TUSHARE_ASSETS`.
- Current staging baseline: `data-platform/src/data_platform/dbt/models/staging/` contains 28 `stg_*` models matching the declared Tushare datasets.
- Current downstream baseline: dbt intermediate/mart coverage exists for security master, price bars, index membership/dim, financial latest/fact, event timeline/fact, plus canonical writers for stock_basic and mart outputs.

## Counts

| Metric | Count | Evidence |
| --- | ---: | --- |
| Tushare API/assets declared | 28 | `TUSHARE_ASSETS` |
| Raw ingestion runnable through adapter/RawWriter | 28 | `run_tushare_asset`, adapter tests by family |
| Staging models present | 28 | `models/staging/stg_*.sql`, `_sources.yml`, `_schema.yml` |
| APIs with mart/canonical downstream use | 20 | dbt intermediate/marts + canonical writer specs |
| APIs connected only through raw + staging | 8 | no downstream `ref('stg_*')` in intermediate/marts |
| Blueprint API-count gap | 12 | target 40 minus current 28 |
| MVP-required API-count gap | 12 | blueprint does not name a deferrable subset for the missing 12 |
| MVP-required downstream gaps among connected APIs | 6 | daily_basic, index_daily, trade_cal, stk_limit, moneyflow, forecast |

## Coverage Table

| API / dataset | Status | Raw artifact path / config | Staging model | Mart / formal downstream | Tests / evidence | MVP | Notes / risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| stock_basic | implemented | `tushare/stock_basic/dt=YYYYMMDD/<run_id>.parquet`; `tushare_stock_basic` | `stg_stock_basic.sql` | `int_security_master` -> `mart_dim_security`; `canonical.stock_basic` | `test_tushare.py`, `test_tushare_staging_models.py`, `test_canonical_writer.py` | required | Full P1a path exists. |
| daily | implemented | `tushare/daily/dt=YYYYMMDD/<run_id>.parquet`; `tushare_daily` | `stg_daily.sql` | `int_price_bars_adjusted` -> `mart_fact_price_bar` -> `canonical.fact_price_bar` | `test_tushare_market_data.py`, staging/intermediate/mart tests | required | Blueprint marks daily market data as core. |
| weekly | implemented | `tushare/weekly/dt=YYYYMMDD/<run_id>.parquet`; `tushare_weekly` | `stg_weekly.sql` | `int_price_bars_adjusted` -> `mart_fact_price_bar` -> `canonical.fact_price_bar` | market/staging/intermediate/mart tests | deferrable | Useful historical frequency, not singled out as hard MVP. |
| monthly | implemented | `tushare/monthly/dt=YYYYMMDD/<run_id>.parquet`; `tushare_monthly` | `stg_monthly.sql` | `int_price_bars_adjusted` -> `mart_fact_price_bar` -> `canonical.fact_price_bar` | market/staging/intermediate/mart tests | deferrable | Same downstream as price bars. |
| adj_factor | implemented | `tushare/adj_factor/dt=YYYYMMDD/<run_id>.parquet`; `tushare_adj_factor` | `stg_adj_factor.sql` | joins price bars in `int_price_bars_adjusted` -> price mart/canonical | market/staging/intermediate/mart tests | required | Needed for adjusted price facts. |
| daily_basic | partial | `tushare/daily_basic/dt=YYYYMMDD/<run_id>.parquet`; `tushare_daily_basic` | `stg_daily_basic.sql` | none found | market/staging schema tests | required | Valuation/turnover fields are staged but not in marts/features. |
| index_basic | implemented | `tushare/index_basic/dt=YYYYMMDD/<run_id>.parquet`; `tushare_index_basic` | `stg_index_basic.sql` | `int_index_membership` -> `mart_dim_index` -> `canonical.dim_index` | reference/staging/intermediate/mart tests | required | Index dimension seed. |
| index_daily | partial | `tushare/index_daily/dt=YYYYMMDD/<run_id>.parquet`; `tushare_index_daily` | `stg_index_daily.sql` | none found | reference/staging tests | required | Index time-series alignment absent from marts. |
| index_weight | implemented | `tushare/index_weight/dt=YYYYMMDD/<run_id>.parquet`; `tushare_index_weight` | `stg_index_weight.sql` | `int_index_membership` -> `mart_dim_index` -> `canonical.dim_index` | reference/staging/intermediate/mart tests | required | Membership/weight path exists. |
| index_member | implemented | `tushare/index_member/dt=YYYYMMDD/<run_id>.parquet`; `tushare_index_member` | `stg_index_member.sql` | `int_index_membership` -> `mart_dim_index` -> `canonical.dim_index` | reference/staging/intermediate/mart tests | required | Membership path exists. |
| index_classify | partial | `tushare/index_classify/dt=YYYYMMDD/<run_id>.parquet`; `tushare_index_classify` | `stg_index_classify.sql` | none found | reference/staging tests | deferrable | Industry/index taxonomy staged only. |
| trade_cal | partial | `tushare/trade_cal/dt=YYYYMMDD/<run_id>.parquet`; `tushare_trade_cal` | `stg_trade_cal.sql` | none found | reference/staging tests | required | Calendar is not yet used for trading-day gates or fills. |
| stock_company | implemented | `tushare/stock_company/dt=YYYYMMDD/<run_id>.parquet`; `tushare_stock_company` | `stg_stock_company.sql` | `int_security_master` -> `mart_dim_security` -> `canonical.dim_security` | reference/staging/intermediate/mart tests | required | Security enrichment path exists. |
| namechange | implemented | `tushare/namechange/dt=YYYYMMDD/<run_id>.parquet`; `tushare_namechange` | `stg_namechange.sql` | latest row in `int_security_master` -> `mart_dim_security` | reference/staging/intermediate/mart tests | required | Security alias/name context exists. |
| anns | implemented | `tushare/anns/dt=YYYYMMDD/<run_id>.parquet`; `tushare_anns` | `stg_anns.sql` | `int_event_timeline` -> `mart_fact_event` -> `canonical.fact_event` | event/staging/intermediate/mart tests | required | Event fact excludes body/content by design. |
| suspend_d | implemented | `tushare/suspend_d/dt=YYYYMMDD/<run_id>.parquet`; `tushare_suspend_d` | `stg_suspend_d.sql` | `int_event_timeline` -> `mart_fact_event` -> `canonical.fact_event` | event/staging/intermediate/mart tests | required | Suspension event path exists. |
| dividend | implemented | `tushare/dividend/dt=YYYYMMDD/<run_id>.parquet`; `tushare_dividend` | `stg_dividend.sql` | `int_event_timeline` -> `mart_fact_event` -> `canonical.fact_event` | event/staging/intermediate/mart tests | required | Dividend event path exists. |
| share_float | implemented | `tushare/share_float/dt=YYYYMMDD/<run_id>.parquet`; `tushare_share_float` | `stg_share_float.sql` | `int_event_timeline` -> `mart_fact_event` -> `canonical.fact_event` | event/staging/intermediate/mart tests | required | Unlock/share float event path exists. |
| stk_holdernumber | implemented | `tushare/stk_holdernumber/dt=YYYYMMDD/<run_id>.parquet`; `tushare_stk_holdernumber` | `stg_stk_holdernumber.sql` | `int_event_timeline` -> `mart_fact_event` -> `canonical.fact_event` | event/staging/intermediate/mart tests | required | Holder number event path exists. |
| disclosure_date | implemented | `tushare/disclosure_date/dt=YYYYMMDD/<run_id>.parquet`; `tushare_disclosure_date` | `stg_disclosure_date.sql` | `int_event_timeline` -> `mart_fact_event` -> `canonical.fact_event` | event/staging/intermediate/mart tests | required | Disclosure event path exists. |
| income | implemented | `tushare/income/dt=YYYYMMDD/<run_id>.parquet`; `tushare_income` | `stg_income.sql` | `int_financial_reports_latest` -> `mart_fact_financial_indicator` -> `canonical.fact_financial_indicator` | financial/staging/intermediate/mart tests | required | Core financial source. |
| balancesheet | implemented | `tushare/balancesheet/dt=YYYYMMDD/<run_id>.parquet`; `tushare_balancesheet` | `stg_balancesheet.sql` | `int_financial_reports_latest` -> financial mart/canonical | financial/staging/intermediate/mart tests | required | Core financial source. |
| cashflow | implemented | `tushare/cashflow/dt=YYYYMMDD/<run_id>.parquet`; `tushare_cashflow` | `stg_cashflow.sql` | `int_financial_reports_latest` -> financial mart/canonical | financial/staging/intermediate/mart tests | required | Core financial source. |
| fina_indicator | implemented | `tushare/fina_indicator/dt=YYYYMMDD/<run_id>.parquet`; `tushare_fina_indicator` | `stg_fina_indicator.sql` | `int_financial_reports_latest` -> financial mart/canonical | financial/staging/intermediate/mart tests | required | Blueprint explicitly names it as degraded-but-important. |
| stk_limit | partial | `tushare/stk_limit/dt=YYYYMMDD/<run_id>.parquet`; `tushare_stk_limit` | `stg_stk_limit.sql` | none found | market/staging tests | required | Limit-up/down context staged only. |
| block_trade | partial | `tushare/block_trade/dt=YYYYMMDD/<run_id>.parquet`; `tushare_block_trade` | `stg_block_trade.sql` | none found | event/staging tests | deferrable | Raw/staging exists, but event mart excludes it. |
| moneyflow | partial | `tushare/moneyflow/dt=YYYYMMDD/<run_id>.parquet`; `tushare_moneyflow` | `stg_moneyflow.sql` | none found | market/staging tests | required | Fund-flow signal staged only. |
| forecast | partial | `tushare/forecast/dt=YYYYMMDD/<run_id>.parquet`; `tushare_forecast` | `stg_forecast.sql` | none found | forecast/staging tests | required | Forward earnings signal staged only. |
| unnamed target APIs 29-40 | missing | none found | none found | none found | no tests found | required | Blueprint requires 40 Tushare APIs but docs reviewed here do not enumerate the remaining 12 names. Treat as P1b gap until target list is formalized or descoped. |

## Evidence Paths

- Adapter/raw declarations: `data-platform/src/data_platform/adapters/tushare/assets.py`
- Adapter/raw runner: `data-platform/src/data_platform/adapters/tushare/adapter.py`
- Raw writer contract: `data-platform/src/data_platform/raw/`
- Staging models: `data-platform/src/data_platform/dbt/models/staging/`
- Staging sources/tests: `data-platform/src/data_platform/dbt/models/staging/_sources.yml`, `_schema.yml`
- Intermediate models: `data-platform/src/data_platform/dbt/models/intermediate/`
- Mart models: `data-platform/src/data_platform/dbt/models/marts/`
- Canonical writer: `data-platform/src/data_platform/serving/canonical_writer.py`
- Adapter tests: `data-platform/tests/adapters/test_tushare*.py`
- dbt tests: `data-platform/tests/dbt/test_tushare_staging_models.py`, `test_intermediate_models.py`, `test_marts_models.py`, `test_dbt_test_coverage.py`
- Serving tests: `data-platform/tests/serving/test_canonical_writer.py`

## Risk Notes

- The current state is 28 API/staging, not the blueprint's 40 API/staging target.
- 8 declared APIs have raw + staging coverage but no mart/canonical downstream evidence. Six of these are MVP-relevant for market state, calendar, valuation/fund-flow, or forward fundamentals.
- The missing 12 APIs cannot be named from the reviewed blueprint/docs; this is itself a planning gap because coverage cannot be verified endpoint-by-endpoint against a formal 40-API target list.
- `daily_refresh` can write all mart canonical tables only when all assets are selected; partial asset selection writes only `canonical.stock_basic` and skips canonical marts.
