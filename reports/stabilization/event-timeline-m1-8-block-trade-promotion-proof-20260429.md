# Event Timeline M1.8 — block_trade Controlled Promotion Proof

**Round:** M1.8
**Date:** 2026-04-29
**Status:** Fixture / static / unit proof only. NOT production daily-cycle proof. NOT Lite-compose proof. NOT live Iceberg proof. NOT P5 readiness.

## Outcome

| metric | value |
|---|---|
| Sources promoted in M1.8 | **1** (`block_trade`) |
| canonical_v2.fact_event coverage | **8 source interfaces** (was 7 after M1.6) |
| Still-blocked sources | **8** (all `BLOCKED_NO_STAGING`) |
| Production code touched | dbt SQL + dbt schema yml + dbt tests + evidence ONLY |
| Serving runtime touched | NONE |

## Promoted source

**`block_trade`** — added as the 8th UNION branch in [int_event_timeline.sql](data-platform/src/data_platform/dbt/models/intermediate/int_event_timeline.sql) reading [stg_block_trade.sql](data-platform/src/data_platform/dbt/models/staging/stg_block_trade.sql).

### Derivation

| field | derivation | source column |
|---|---|---|
| `event_type` | constant `'block_trade'` | n/a |
| `source_interface_id` | constant `'block_trade'` | n/a |
| `ts_code` | passthrough | `ts_code` |
| `event_date` | direct | `trade_date` |
| `title` | constant `'Block trade'` | n/a |
| `summary` | `concat('buyer=', coalesce(buyer, ''), ';seller=', coalesce(seller, ''), ';price=', coalesce(price, ''), ';vol=', coalesce(vol, ''), ';amount=', coalesce(amount, ''))` | buyer / seller / price / vol / amount |
| `event_subtype` | NULL | n/a |
| `related_date` | direct | `trade_date` |
| `reference_url` | NULL | n/a |
| `rec_time` | NULL | n/a |
| `source_run_id` / `raw_loaded_at` | passthrough | from `stg_latest_raw` macro |

### Canonical PK derivation in marts (unchanged from M1-G2)

`event_key = md5(concat_ws('|', source_interface_id, event_type, coalesce(title, ''), coalesce(summary, ''), coalesce(event_subtype, ''), coalesce(cast(related_date as varchar), ''), coalesce(reference_url, ''), coalesce(rec_time, '')))`

For block_trade, `summary` carries buyer / seller / price / vol / amount, which are the per-row distinguishing fields; `event_key` therefore varies per intra-day row even when `(event_type, ts_code, event_date)` is identical.

## Contract change (M1.8)

**Exact change:** the `int_event_timeline.unique_combination_of_columns` test in [intermediate/_schema.yml](data-platform/src/data_platform/dbt/models/intermediate/_schema.yml) was widened from:

```yaml
combination_of_columns: ["event_type", "ts_code", "event_date", "title", "related_date", "reference_url"]
```

to:

```yaml
combination_of_columns: ["event_type", "source_interface_id", "ts_code", "event_date", "title", "related_date", "reference_url", "summary"]
```

**This is an intentional weakening of the intermediate duplicate guard.** The narrower M1.6 6-column key would have caught two rows that differ only in `summary` (or `source_interface_id`) as duplicates; the wider 8-column key permits them. We are accepting that weakening because:

1. Block_trade genuinely emits multiple rows per `(ts_code, trade_date)` (different buyer / seller / price / vol on the same trading day) — these are real events, not duplicates, and the prior key cannot represent them.
2. Canonical row identity is enforced **downstream**, not at the intermediate, by:
   - **`event_key` md5 derivation** in `mart_fact_event_v2.sql` and `mart_lineage_fact_event.sql` (byte-identical hash inputs in both marts).
   - **v2 / lineage canonical-PK parity test** `test_event_v2_and_lineage_marts_preserve_block_trade_fixture` (and the existing `_preserve_namechange_fixture`) which asserts `v2_pk_rows == lineage_pk_rows` over the canonical PK `(event_type, entity_id, event_date, event_key)`.
   - **Writer-side canonical-PK validation** in `canonical_writer._validate_unique_canonical_keys` and `_validate_canonical_v2_mart_pairings`, which fires before publication.

The narrower 6-column key was never the load-bearing canonical-PK guard; it was a sanity check at the intermediate boundary. M1.8 makes that role-shift explicit.

## Files changed

- [data-platform/src/data_platform/dbt/models/intermediate/int_event_timeline.sql](data-platform/src/data_platform/dbt/models/intermediate/int_event_timeline.sql) — added 8th UNION branch reading `stg_block_trade`.
- [data-platform/src/data_platform/dbt/models/intermediate/_schema.yml](data-platform/src/data_platform/dbt/models/intermediate/_schema.yml) — widened `unique_combination_of_columns`; added `block_trade` to event_type and source_interface_id accepted_values; rewrote description to record the contract change.
- [data-platform/src/data_platform/provider_catalog/registry.py](data-platform/src/data_platform/provider_catalog/registry.py) — updated `block_trade.source_primary_key` to the full row-shape dedupe identity `(ts_code, trade_date, buyer, seller, price, vol, amount)` because Tushare exposes no immutable execution id.
- [data-platform/src/data_platform/dbt/models/marts_v2/_schema.yml](data-platform/src/data_platform/dbt/models/marts_v2/_schema.yml) — extended `mart_fact_event_v2.event_type` accepted_values with `'block_trade'`; updated header comment + model description to the current 8-source coverage.
- [data-platform/src/data_platform/dbt/models/marts_lineage/_schema.yml](data-platform/src/data_platform/dbt/models/marts_lineage/_schema.yml) — extended `mart_lineage_fact_event.source_interface_id` accepted_values with `'block_trade'`; updated header comment + model description.
- [data-platform/src/data_platform/dbt/models/marts_v2/mart_fact_event_v2.sql](data-platform/src/data_platform/dbt/models/marts_v2/mart_fact_event_v2.sql) — comment-only update reflecting 8-source coverage; `event_key` derivation expression unchanged.
- [data-platform/src/data_platform/dbt/models/marts_lineage/mart_lineage_fact_event.sql](data-platform/src/data_platform/dbt/models/marts_lineage/mart_lineage_fact_event.sql) — comment-only update reflecting 8-source coverage; `event_key` derivation expression unchanged.
- [data-platform/tests/dbt/test_intermediate_models.py](data-platform/tests/dbt/test_intermediate_models.py) — added `'block_trade'` to expected `event_types` list (alphabetic position between `announcement` and `disclosure_date`).
- [data-platform/tests/dbt/test_marts_models.py](data-platform/tests/dbt/test_marts_models.py) — bumped `event_summary` from `(7, 7)` to `(8, 8)`; added `test_event_v2_and_lineage_marts_preserve_block_trade_fixture` parity test with two same-day block_trade rows (v2/lineage canonical PK parity, distinct event_key rows, lineage column presence, v2 column absence, source_interface_id='block_trade').
- [data-platform/tests/provider_catalog/test_provider_catalog.py](data-platform/tests/provider_catalog/test_provider_catalog.py) — pinned the block_trade full row-shape source key and registry natural key.

## Runtime / schema surfaces NOT changed (per hard rules)

- fact_event v2 and lineage mart `event_key` derivation expression — unchanged; the new UNION branch flows through identically.
- Iceberg DDL (`iceberg_tables.py`) — table schemas unchanged.
- Canonical writer specs (`canonical_writer.py`) — load specs unchanged.
- Dataset routing (`canonical_datasets.py`) — unchanged.
- Serving runtime (`reader.py`, `formal.py`) — unchanged.
- Legacy `canonical.*` specs / load specs / dbt marts — NOT deleted.
- `_M1D_LEGACY_RETIREMENT_XFAIL` — NOT removed.
- `FORBIDDEN_SCHEMA_FIELDS` / `FORBIDDEN_PAYLOAD_FIELDS` — NOT extended.

## Tests run + results

```sh
$ cd data-platform && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
    -p no:cacheprovider \
    tests/dbt/test_intermediate_models.py \
    tests/dbt/test_marts_models.py
==> 10 passed, 2 skipped in 1.83s
```

The new `test_event_v2_and_lineage_marts_preserve_block_trade_fixture` is among the 10 passing. It exercises the full int → mart_fact_event_v2 + mart_lineage_fact_event pipeline against a real DuckDB-backed raw fixture with two block_trade rows sharing the same `(ts_code, trade_date)` and differing by buyer/seller/price/vol/amount, asserts `block_trade` flows through both marts, and asserts v2/lineage canonical-PK parity with two distinct block_trade event_key rows.

## What this proves

- `int_event_timeline` materialises a row with `event_type='block_trade'` and `source_interface_id='block_trade'` from the staging fixture.
- `mart_fact_event_v2` materialises a row with `event_type='block_trade'`, the canonical-renamed `entity_id` column, and `event_key` that varies per row via md5(... summary ...).
- `mart_lineage_fact_event` materialises a row with `source_interface_id='block_trade'`, `source_provider`, `source_run_id`, `raw_loaded_at` (lineage columns); `mart_fact_event_v2` does NOT carry any of those lineage columns.
- The v2 and lineage marts produce **byte-identical** `(event_type, entity_id, event_date, event_key)` row sets over the full multi-source UNION (8 sources), so the canonical-writer pairing validator passes by construction.

## What this does NOT prove (do NOT misclaim)

- This is **NOT** a production daily-cycle proof. No production daily refresh executed.
- This is **NOT** a Lite-compose v2 proof. No compose started; no PostgreSQL / Neo4j / Dagster daemon launched.
- This is **NOT** a live live-Iceberg proof. The DuckDB fixture exercises raw → staging → intermediate → mart locally; no real Iceberg catalog write.
- This is **NOT** P5 readiness. P5 still blocked by M2.6 (production daily-cycle proof) and the legacy retirement Phase B.

## canonical_v2.fact_event coverage status

`canonical_v2.fact_event` now covers **8 source interfaces** (was 7 after M1.6):
- anns, suspend_d, dividend, share_float, stk_holdernumber, disclosure_date (M1-G2)
- namechange (M1.6)
- block_trade (M1.8)

Full event_timeline coverage (16 known registry/candidate sources) is still **NOT** achieved. The 8 PROMOTION_CANDIDATE_MAPPINGS sources (pledge_*, repurchase, stk_holdertrade, limit_list_*, hm_detail, stk_surv) remain `BLOCKED_NO_STAGING` — see [event-timeline-m1-7-source-closure-audit-20260429.md §C](assembly/reports/stabilization/event-timeline-m1-7-source-closure-audit-20260429.md) for the 5-step adapter-build checklist.

### event_type taxonomy after M1.8

```
{'announcement', 'suspend', 'dividend', 'share_float', 'holder_number', 'disclosure_date', 'name_change', 'block_trade'}
```
8 entries.

### source_interface_id accepted set after M1.8

```
{'anns', 'suspend_d', 'dividend', 'share_float', 'stk_holdernumber', 'disclosure_date', 'namechange', 'block_trade'}
```
8 entries.

## Status declarations

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
- Pre-existing dirty files NOT reverted.
- No `git init`. No commits. No push.
