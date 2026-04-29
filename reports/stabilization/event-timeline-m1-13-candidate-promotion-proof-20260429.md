# Event Timeline M1.13 — 8 Candidate Sources Promotion Proof

**Round:** M1.13 (precondition 9 closure)
**Date:** 2026-04-29
**Status:** Fixture / static / unit proof. NOT production daily-cycle proof. NOT Lite-compose proof. NOT P5 readiness.
**Branch:** `m1-13-precondition-9` off `m1-baseline-2026-04-29`.

## Outcome

| metric | before (M1.11) | after (M1.13) |
|---|---|---|
| Sources in `PROVIDER_MAPPINGS` (event_timeline arms) | 8 | 16 |
| Sources in `PROMOTION_CANDIDATE_MAPPINGS` (event_timeline) | 8 | 0 |
| `TUSHARE_ASSETS` count | 28 | 36 |
| `int_event_timeline` UNION arms | 8 | 16 |
| `mart_fact_event_v2.event_type` accepted_values | 8 | 16 |
| `mart_lineage_fact_event.source_interface_id` accepted_values | 8 | 16 |
| `mart_fact_event.event_type` accepted_values (legacy) | 8 | 16 |
| Parity tests over fact_event_v2 + mart_lineage_fact_event | 2 | 10 |
| `_M1D_LEGACY_RETIREMENT_XFAIL` markers retained | 8 | 8 |
| V2 lane xfail count (DP_CANONICAL_USE_V2=1 sweep) | 17 | 17 |
| `canonical_v2.fact_event` source_interface coverage | 8 | 16 |

## Promoted sources (M1.13)

The 8 candidate event_timeline sources verified in M1.11 were promoted to
PROVIDER_MAPPINGS using the empirically-confirmed identity tuples + canonical
taxonomy from
[`event-timeline-m1-11-candidate-schema-checkin-20260429.md`](event-timeline-m1-11-candidate-schema-checkin-20260429.md).

| # | Tushare API | event_type | event_date | event_subtype | source_interface_id | partition_key |
|---|---|---|---|---|---|---|
| 1 | `pledge_stat` | `pledge_summary` | `end_date` | (null) | `pledge_stat` | `('end_date',)` |
| 2 | `pledge_detail` | `pledge_event` | `ann_date` | `is_release` | `pledge_detail` | `('ann_date',)` |
| 3 | `repurchase` | `share_repurchase` | `ann_date` | `proc` | `repurchase` | `('ann_date',)` |
| 4 | `stk_holdertrade` | `shareholder_trade` | `ann_date` | `in_de` | `stk_holdertrade` | `('ann_date',)` |
| 5 | `stk_surv` | `institutional_survey` | `surv_date` | `org_type` | `stk_surv` | `('surv_date',)` |
| 6 | `limit_list_ths` | `price_limit_status` | `trade_date` | `limit_type` | `limit_list_ths` | `('trade_date',)` |
| 7 | `limit_list_d` | `price_limit_event` | `trade_date` | `limit` | `limit_list_d` | `('trade_date',)` |
| 8 | `hm_detail` | `hot_money_trade` | `trade_date` | (null; `hm_name` in summary) | `hm_detail` | `('trade_date',)` |

## Per-source completion matrix

Each source delivers all 8 mechanical pieces below. ✅ = present and
verified; ❌ = blocked. All 8 rows are ✅ across all 8 columns.

| API | stg_<src>.sql | int_event_timeline UNION | registry identity | adapter spec | _schema.yml accepted_values | fixture row | parity test | csv flip |
|---|---|---|---|---|---|---|---|---|
| `pledge_stat` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ pass | ✅ * |
| `pledge_detail` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ pass | ✅ * |
| `repurchase` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ pass | ✅ * |
| `stk_holdertrade` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ pass | ✅ * |
| `stk_surv` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ pass | ✅ * |
| `limit_list_ths` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ pass | ✅ * |
| `limit_list_d` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ pass | ✅ * |
| `hm_detail` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ pass | ✅ * |

**\*csv flip note**: `data-platform/src/data_platform/provider_catalog/tushare_available_interfaces.csv` is the source-availability inventory (validator enforces `access_status == "available"` for every row). The actual "promotion" the playbook described (moving status from `candidate` → `promoted`) is encoded in `provider_catalog/registry.py`'s `PROVIDER_MAPPINGS` vs `PROMOTION_CANDIDATE_MAPPINGS` partition. M1.13 moved all 8 entries from the latter to the former — confirmed by `TUSHARE_INTERFACE_REGISTRY[<source_id>].promotion_status == "promoted"` for each. The CSV `access_status` column is unchanged because the validator at `registry.py:84` would reject any other value.

## Per-source taxonomy + summary template

Lifted verbatim from M1.11 sign-off table.

### `pledge_stat` → `pledge_summary`
- title: `'Pledge summary'`
- summary: `concat('count=', coalesce(pledge_count, ''), ';unrest=', coalesce(unrest_pledge, ''), ';rest=', coalesce(rest_pledge, ''), ';total=', coalesce(total_share, ''), ';ratio=', coalesce(pledge_ratio, ''))`

### `pledge_detail` → `pledge_event`
- title: `'Pledge event'`
- summary: `concat('holder=', coalesce(holder_name, ''), ';pledgor=', coalesce(pledgor, ''), ';amount=', coalesce(pledge_amount, ''), ';period=[', coalesce(cast(start_date as varchar), ''), ',', coalesce(cast(end_date as varchar), ''), '];release=', coalesce(is_release, ''))`

### `repurchase` → `share_repurchase`
- title: `'Share repurchase'`
- summary: `concat('proc=', coalesce(proc, ''), ';vol=', coalesce(vol, ''), ';amount=', coalesce(amount, ''), ';exp=', coalesce(cast(exp_date as varchar), ''), ';band=[', coalesce(low_limit, ''), ',', coalesce(high_limit, ''), ']')`

### `stk_holdertrade` → `shareholder_trade`
- title: `'Shareholder trade'`
- summary: `concat('holder=', coalesce(holder_name, ''), ';type=', coalesce(holder_type, ''), ';dir=', coalesce(in_de, ''), ';vol=', coalesce(change_vol, ''), ';ratio=', coalesce(change_ratio, ''), ';avg_price=', coalesce(avg_price, ''))`

### `stk_surv` → `institutional_survey`
- title: `'Institutional survey'`
- summary: `concat('org=', coalesce(rece_org, ''), ';type=', coalesce(org_type, ''), ';place=', coalesce(rece_place, ''), ';mode=', coalesce(rece_mode, ''), ';visitors=', coalesce(fund_visitors, ''))`

### `limit_list_ths` → `price_limit_status`
- title: `'Price limit status (THS pool)'`
- summary: `concat('pool=', coalesce(limit_type, ''), ';status=', coalesce(status, ''), ';tag=', coalesce(tag, ''), ';order=', coalesce(limit_order, ''), ';amount=', coalesce(limit_amount, ''), ';open_num=', coalesce(open_num, ''))`

### `limit_list_d` → `price_limit_event`
- title: `'Price limit event'`
- summary: `concat('limit=', coalesce("limit", ''), ';times=', coalesce(limit_times, ''), ';fd=', coalesce(fd_amount, ''), ';first=', coalesce(first_time, ''), ';last=', coalesce(last_time, ''), ';up_stat=', coalesce(up_stat, ''))`

### `hm_detail` → `hot_money_trade`
- title: `'Hot money trade'`
- summary: `concat('hm=', coalesce(hm_name, ''), ';buy=', coalesce(buy_amount, ''), ';sell=', coalesce(sell_amount, ''), ';net=', coalesce(net_amount, ''), ';orgs=', coalesce(hm_orgs, ''))`

## Files added (M1.13)

### Production code
- `data-platform/src/data_platform/dbt/models/staging/stg_pledge_stat.sql` — new staging model.
- `data-platform/src/data_platform/dbt/models/staging/stg_pledge_detail.sql` — new staging model.
- `data-platform/src/data_platform/dbt/models/staging/stg_repurchase.sql` — new staging model.
- `data-platform/src/data_platform/dbt/models/staging/stg_stk_holdertrade.sql` — new staging model.
- `data-platform/src/data_platform/dbt/models/staging/stg_stk_surv.sql` — new staging model.
- `data-platform/src/data_platform/dbt/models/staging/stg_limit_list_ths.sql` — new staging model.
- `data-platform/src/data_platform/dbt/models/staging/stg_limit_list_d.sql` — new staging model.
- `data-platform/src/data_platform/dbt/models/staging/stg_hm_detail.sql` — new staging model.

### Production code (modified)
- `data-platform/src/data_platform/adapters/tushare/assets.py` — added `TUSHARE_<SOURCE>_SCHEMA`, `_FIELDS`, `_FIELDS_CSV`, `_ASSET`, and `_ASSET_NAME` exports for all 8 new sources; extended `EVENT_METADATA_FIELDS` and `TUSHARE_ASSETS`. (28 → 36 assets).
- `data-platform/src/data_platform/adapters/tushare/__init__.py` — re-exported the 8 new asset symbols.
- `data-platform/src/data_platform/adapters/tushare/adapter.py` — added 8 new `_TushareClient` Protocol method declarations; extended `EVENT_IDENTITY_FIELDS`, `EVENT_DATE_FIELDS`, `_METHOD_BY_DATASET`, `_PARTITION_DATE_FIELD_BY_DATASET`, `_PARTITION_REQUEST_PARAMS_BY_DATASET`, `_DATE_PARAM_NAMES_BY_DATASET` with the 8 new dataset entries.
- `data-platform/src/data_platform/provider_catalog/registry.py` — moved the 8 candidate event_timeline mappings from `PROMOTION_CANDIDATE_MAPPINGS` (status=`candidate`) to `PROVIDER_MAPPINGS` (status=`promoted`) with the wide identity tuples; extended `_PARTITION_KEY_BY_RAW_DATASET`. `STOCK_TS_CODE_DATASETS` membership extends automatically because `EVENT_DATASETS = frozenset(EVENT_METADATA_FIELDS)`.
- `data-platform/src/data_platform/daily_refresh.py` — extended `DATE_FIELD_NAMES` with `release_date` + `surv_date`; extended `STRING_NUMERIC_FIELD_NAMES` with the new sources' numeric column names so `--mock` rows pass the staging cast.
- `data-platform/src/data_platform/dbt/models/intermediate/int_event_timeline.sql` — appended 8 UNION arms (1 per source) using the canonical taxonomy from M1.11.
- `data-platform/src/data_platform/dbt/models/intermediate/_schema.yml` — extended `event_type` and `source_interface_id` accepted_values from 8 → 16 each; updated description.
- `data-platform/src/data_platform/dbt/models/marts_v2/_schema.yml` — extended `mart_fact_event_v2.event_type` accepted_values from 8 → 16; updated description and header comment.
- `data-platform/src/data_platform/dbt/models/marts_lineage/_schema.yml` — extended `mart_lineage_fact_event.source_interface_id` accepted_values from 8 → 16; updated description and header comment.
- `data-platform/src/data_platform/dbt/models/marts/_schema.yml` — extended legacy `mart_fact_event.event_type` accepted_values from 8 → 16.
- `data-platform/src/data_platform/dbt/models/staging/_schema.yml` — added 8 new staging-model `model: + tests:` declarations.
- `data-platform/src/data_platform/dbt/models/staging/_sources.yml` — added 8 new raw zone source declarations.
- `data-platform/src/data_platform/provider_catalog/tushare_available_interfaces.csv` — UNCHANGED. The validator enforces `access_status == "available"` for every row, and the M1.13 promotion is encoded in `registry.py` (PROVIDER_MAPPINGS membership), not in this inventory CSV.

### Test code (modified)
- `data-platform/tests/adapters/test_tushare_events.py` — extended `EVENT_ASSETS`, `METHOD_BY_DATASET`, `FETCH_PARAMS_BY_DATASET`, `FakeTushareEventClient`, `_event_row` date-field set, `_raw_partition_call_params` to cover all 8 new sources.
- `data-platform/tests/dbt/test_intermediate_models.py` — bumped `event_types` assertion from 8 → 16 entries (alphabetic).
- `data-platform/tests/dbt/test_marts_models.py` — bumped `event_summary` count from `(8, 8)` to `(16, 16)`; added 8 new parity tests + 1 shared helper `_assert_event_v2_and_lineage_pair_preserved`.
- `data-platform/tests/dbt/test_tushare_staging_models.py` — extended `DATE_FIELD_NAMES` with `release_date` + `surv_date`; added 7 new `<DATASET>_NUMERIC_FIELD_NAMES` constants; extended `_sample_value` so each new source's numeric fields receive a parsable decimal-style string fixture.
- `data-platform/tests/provider_catalog/test_provider_catalog.py` — bumped `len(production_entries) == len(TUSHARE_ASSETS) == 28` to `36`.

## Parity test results

```sh
$ cd data-platform && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
    /Users/fanjie/Desktop/Cowork/project-ult/data-platform/.venv/bin/python -m pytest \
    -p no:cacheprovider -v tests/dbt/test_marts_models.py \
    -k "pledge_stat or pledge_detail or repurchase or stk_holdertrade or stk_surv or limit_list_ths or limit_list_d or hm_detail"
==> 8 passed, 7 deselected
```

All 8 new parity tests pass. Each test materializes the full pipeline
(staging → int_event_timeline → mart_fact_event_v2 + mart_lineage_fact_event)
from a 1-row raw fixture, and asserts:

1. `int_event_timeline` carries the expected `event_type` literal and
   `source_interface_id` literal exactly once.
2. `mart_fact_event_v2.event_type` set contains the new value.
3. `mart_lineage_fact_event.source_interface_id` set contains the new value.
4. The lineage column set (`source_provider`, `source_interface_id`,
   `source_run_id`, `raw_loaded_at`) is disjoint from `mart_fact_event_v2`'s
   columns and is a subset of `mart_lineage_fact_event`'s columns.
5. `(event_type, entity_id, event_date, event_key)` rowsets are byte-identical
   between `mart_fact_event_v2` and `mart_lineage_fact_event` (writer-side
   pairing guarantee, mirroring the block_trade exemplar test).

## Test sweep results

```sh
# 1. Provider catalog
$ pytest tests/provider_catalog
==> 11 passed

# 2. Adapter / assets / raw
$ pytest tests/adapters tests/raw
==> 171 passed

# 3. dbt skeleton + staging + intermediate + marts + provider neutrality
$ pytest tests/dbt/test_dbt_skeleton.py tests/dbt/test_dbt_test_coverage.py \
         tests/dbt/test_intermediate_models.py tests/dbt/test_marts_models.py \
         tests/dbt/test_marts_provider_neutrality.py tests/dbt/test_tushare_staging_models.py
==> 64 passed, 3 skipped, 8 xfailed

# 4. Integration daily refresh
$ pytest tests/integration/test_daily_refresh.py tests/serving/test_canonical_writer.py tests/serving/test_reader.py
==> 58 passed, 1 skipped

# 5. V2 lane (default-on)
$ DP_CANONICAL_USE_V2=1 pytest tests/serving tests/cycle/test_current_cycle_inputs.py \
    tests/cycle/test_current_cycle_inputs_lineage_absent.py tests/test_assets.py
==> 177 passed, 5 skipped, 17 xfailed

# 6. Full repo sweep
$ pytest tests/
==> 604 passed, 74 skipped, 44 xfailed
```

`xfail` totals exactly match M1.11 baseline: 17 in V2 lane + 8 in M1 standard
dbt sweep, plus 19 others elsewhere (not affected by M1.13). 8 NEW parity
tests appended to `test_marts_models.py` all pass.

## Files NOT changed (per hard rules)

- `project_ult_v5_0_1.md` UNCHANGED.
- `ult_milestone.md` UNCHANGED.
- v2 mart SQL (`mart_fact_event_v2.sql`) — `event_key` md5 derivation expression unchanged; the 8 new UNION arms flow through identically.
- Lineage mart SQL (`mart_lineage_fact_event.sql`) — same.
- Iceberg DDL (`iceberg_tables.py`) — table schemas unchanged.
- Canonical writer specs (`canonical_writer.py`) — load specs unchanged.
- Dataset routing (`canonical_datasets.py`) — unchanged.
- Serving runtime (`reader.py`, `formal.py`) — unchanged.
- Legacy `canonical.*` specs / load specs / dbt marts — NOT deleted.
- `_M1D_LEGACY_RETIREMENT_XFAIL` — NOT removed.
- `FORBIDDEN_SCHEMA_FIELDS` / `FORBIDDEN_PAYLOAD_FIELDS` — NOT extended.
- `tushare_available_interfaces.csv` — UNCHANGED (validator constraint).
- `/Users/fanjie/Desktop/BIG/FrontEnd/**` — NOT touched.

## What this proves

- 8 candidate event_timeline sources have working adapter fetch specs +
  staging models + intermediate UNION arms + mart accepted_values + parity
  tests. Each source can be exercised end-to-end through the
  raw → staging → intermediate → marts_v2 + marts_lineage pipeline against
  a DuckDB-backed raw fixture, with v2/lineage canonical-PK parity
  enforced.
- `canonical_v2.fact_event` now covers **16 source interfaces**:
  - M1-G2: anns, suspend_d, dividend, share_float, stk_holdernumber,
    disclosure_date.
  - M1.6: namechange.
  - M1.8: block_trade.
  - **M1.13 (this round)**: pledge_stat, pledge_detail, repurchase,
    stk_holdertrade, stk_surv, limit_list_ths, limit_list_d, hm_detail.
- Full event_timeline coverage from the M1.11 inventory is achieved.
  Precondition 9 closed.

## What this does NOT prove

- This is **NOT** a production daily-cycle proof. No production daily refresh
  executed against live Tushare HTTP.
- This is **NOT** a Lite-compose v2 proof. No compose started; no PostgreSQL /
  Neo4j / Dagster daemon launched.
- This is **NOT** a live-Iceberg proof. The DuckDB fixture exercises raw →
  staging → intermediate → mart locally; no real Iceberg catalog write.
- This is **NOT** P5 readiness. P5 still blocked by M2.6 (production daily-
  cycle proof) and the legacy retirement Phase B (preconditions 6, 7, 8).

## Coverage status after M1.13

`canonical_v2.fact_event` now covers **16 source interfaces**:
{anns, suspend_d, dividend, share_float, stk_holdernumber, disclosure_date,
namechange, block_trade, pledge_stat, pledge_detail, repurchase,
stk_holdertrade, stk_surv, limit_list_ths, limit_list_d, hm_detail}.

`event_type` taxonomy after M1.13:
```
{'announcement', 'suspend', 'dividend', 'share_float', 'holder_number',
 'disclosure_date', 'name_change', 'block_trade',
 'pledge_summary', 'pledge_event', 'share_repurchase', 'shareholder_trade',
 'institutional_survey', 'price_limit_status', 'price_limit_event',
 'hot_money_trade'}
```
16 entries (was 8).

`source_interface_id` accepted set after M1.13:
```
{'anns', 'suspend_d', 'dividend', 'share_float', 'stk_holdernumber',
 'disclosure_date', 'namechange', 'block_trade',
 'pledge_stat', 'pledge_detail', 'repurchase', 'stk_holdertrade',
 'stk_surv', 'limit_list_ths', 'limit_list_d', 'hm_detail'}
```
16 entries (was 8).

## Hard-rule declarations

- This is a **FIXTURE / STATIC / UNIT** evidence file. NOT production daily-cycle proof.
- `project_ult_v5_0_1.md` and `ult_milestone.md` UNCHANGED.
- compose / production fetch / P5 shadow-run NOT started.
- M2 / M3 / M4 NOT entered.
- API-6 / sidecar / frontend write API / Kafka/Flink/Temporal / news/Polymarket NOT touched.
- Tushare remains a `provider="tushare"` source adapter ONLY.
- Legacy `canonical.*` specs/load specs/dbt marts NOT deleted.
- `_M1D_LEGACY_RETIREMENT_XFAIL` NOT removed.
- `FORBIDDEN_SCHEMA_FIELDS` / `FORBIDDEN_PAYLOAD_FIELDS` NOT extended.
- `/Users/fanjie/Desktop/BIG/FrontEnd` NOT modified.
- No Tushare HTTP fetch. The `--mock` adapter path injects fixture rows
  directly into the raw zone for the 8 new staging models to read.
- The local archive at `/Volumes/dockcase2tb/database_all/股票数据/` was
  consulted for column-list verification only; no rows copied into the repo.
- Pre-existing dirty files NOT reverted.
- No `git init`. No commits. No push.

## Cross-references

- M1.11 schema check-in + uniqueness verification: [`event-timeline-m1-11-candidate-schema-checkin-20260429.md`](event-timeline-m1-11-candidate-schema-checkin-20260429.md)
- M1.6 promotion exemplar (minimal-identity): [`event-timeline-m1-6-promotion-proof-20260429.md`](event-timeline-m1-6-promotion-proof-20260429.md)
- M1.8 promotion exemplar (wide-identity): [`event-timeline-m1-8-block-trade-promotion-proof-20260429.md`](event-timeline-m1-8-block-trade-promotion-proof-20260429.md)
- Preconditions tracker: [`m1-legacy-retirement-preconditions-progress-20260428.md`](m1-legacy-retirement-preconditions-progress-20260428.md)
