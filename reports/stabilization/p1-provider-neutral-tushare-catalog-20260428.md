# P1 Provider-Neutral Tushare Catalog Boundary Evidence - 2026-04-28

## Status

PARTIAL PASS / BOUNDARY EVIDENCE. This evidence implements the provider-neutral
catalog and no-source-leak guardrails for the current Tushare expansion plan. It
does not certify a full production `daily_cycle_job` pass and does not unblock
P5 shadow-run readiness.

## Scope

This batch treats `/Users/fanjie/Desktop/Cowork/tushare全部可用接口.csv` as the
current `provider=tushare` availability inventory. Tushare remains a source
adapter only. Raw/staging may remain source-specific, but curated marts,
canonical writer, formal serving inputs, graph, reasoner, frontend-api, and
production daily-cycle consumers must bind to provider-neutral canonical dataset
contracts.

Out of scope for this batch:

- P5 shadow-run.
- API-6, sidecar, frontend write APIs, Kafka/Flink/Temporal.
- Production news/Polymarket flows.
- Fake Wind/Choice/internal adapters.

## Catalog Result

Committed provider catalog:

- `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/provider_catalog/tushare_available_interfaces.csv`

Registry implementation:

- `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/provider_catalog/registry.py`

Artifact:

- `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/p1-provider-neutral-tushare-catalog-artifacts/provider-neutral-tushare-catalog-20260428.json`

Observed counts:

- Tushare provider inventory rows: 138.
- Unique `source_interface_id`: 138.
- Unique raw `doc_api`: 137.
- Known duplicate raw `doc_api`: `trade_cal`.
- Existing promoted typed mappings: 28.
- Promotion candidate mappings: 13.
- Generic unpromoted provider inventory: 107.
- Canonical datasets declared: 17.
- Future provider targets recorded for compatibility planning: `choice`, `internal`, `wind`.

Important correction: the source CSV contains two real `trade_cal` rows with
different Tushare doc URLs/scopes: futures trading calendar and stock trading
calendar. The committed provider catalog therefore uses `source_interface_id`
as the unique provider interface key while preserving the true `doc_api` for
source lineage. The stock trading-calendar mapping is explicitly anchored to
`trade_cal_stock`.

## Canonical Boundary

The registry separates source availability from canonical business contracts:

- Source-specific layer: Raw Zone, `stg_tushare_*`, Tushare provider adapter,
  live/local corpus probe.
- Provider-neutral layer: intermediate, curated marts, canonical writer,
  formal serving input, graph, reasoner, frontend-api, production daily-cycle
  business consumption.

Every promoted mapping must declare:

- canonical dataset id.
- source-to-canonical field mapping.
- canonical primary key and source primary key.
- unit policy and currency/ratio/factor handling.
- date policy such as trade date, announcement date, report period, or
  effective date.
- adjustment policy such as raw price, factor-only, reported values, or not
  applicable.
- update policy and late-arriving/null policy.
- coverage and entity scope.

Interfaces without a declared mapping remain provider inventory only. They may
enter Raw/generic staging, but they cannot be selected by production daily-cycle
or served as business/formal output.

## Current Mapping Decisions

The existing 28 typed Tushare assets now have a provider mapping or explicit
legacy status. Ten existing typed assets are not present in the current CSV and
are marked `legacy_typed_not_in_catalog` rather than silently treated as current
provider inventory:

- `adj_factor`
- `index_daily`
- `index_weight`
- `index_member`
- `anns`
- `suspend_d`
- `income`
- `balancesheet`
- `cashflow`
- `fina_indicator`

First promotion-candidate mappings are recorded as decisions, not automatic
business consumption:

- `index_dailybasic`
- `margin`
- `margin_detail`
- `pledge_stat`
- `pledge_detail`
- `repurchase`
- `stk_holdertrade`
- `limit_list_ths`
- `limit_list_d`
- `hm_detail`
- `stk_surv`
- `express`
- `fina_mainbz`

Older suggested APIs that are not in the source CSV, such as
`top10_floatholders`, `top_list`, and `top_inst`, were not promoted by guesswork.

## No-Source-Leak Gates

Added tests:

- `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/tests/provider_catalog/test_provider_catalog.py`
- `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/tests/provider_catalog/test_no_source_leak.py`
- `/Users/fanjie/Desktop/Cowork/project-ult/frontend-api/tests/test_no_source_leak.py`

Strengthened existing formal serving test:

- `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/tests/serving/test_formal.py`

Guardrails now check:

- Provider catalog is normalized and does not commit local paths, tokens, or
  DSNs.
- Existing typed assets have canonical mapping or explicit legacy status.
- Generic unpromoted interfaces cannot be selected as business mappings.
- Curated marts do not expose `doc_api`, `tushare_`, `stg_tushare_`, direct
  source references, or direct staging refs.
- Formal serving rejects source-specific object type names such as
  `tushare_stock_basic`, `stg_tushare_daily`, and `doc_api`.
- Frontend-api business read-only route/adapters do not leak `doc_api`,
  `stg_tushare_`, or `tushare_` source asset names. Raw debug lineage remains
  out of that business-surface test.

## Verification

Data-platform focused gate:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest -q \
  tests/provider_catalog \
  tests/dbt/test_dbt_skeleton.py \
  tests/serving/test_formal.py::test_formal_table_identifier_validates_object_type
```

Result:

```text
12 passed
```

Frontend-api no-source-leak gate:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/frontend-api
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest -q \
  tests/test_no_source_leak.py
```

Result:

```text
1 passed
```

Lint:

```text
data-platform ruff check src/data_platform/provider_catalog tests/provider_catalog tests/serving/test_formal.py
All checks passed

frontend-api ruff check tests/test_no_source_leak.py
All checks passed
```

## Remaining Blockers

- P1/P2 production daily-cycle still needs a full provider-neutral consumer
  proof. Existing bounded production evidence remains PARTIAL/BLOCKED until the
  Dagster production provider set consumes canonical datasets end to end.
- Orchestrator source-provider code should be audited/refactored in the next
  batch so production Phase 2 cannot rely directly on Tushare staging or raw
  provider field names.
- P5 remains blocked by production daily-cycle proof, P4 bridge hardening, and
  provider-neutral boundary gates.

## Findings

- P0: none.
- P1: none in this catalog/no-source-leak slice.
- P2: production daily-cycle provider-neutral consumption is not yet certified;
  this evidence only installs catalog contracts and guardrails.
- P3: raw `doc_api` uniqueness in the source CSV is false for `trade_cal`; the
  implemented unique key is `source_interface_id`, with the duplicate explicitly
  documented.
