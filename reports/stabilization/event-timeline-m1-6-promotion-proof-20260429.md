# Event Timeline M1.6 Promotion Proof

**Round:** M1.6 (Tasks M1.6-2 through M1.6-5)
**Date:** 2026-04-29
**Status:** Fixture / static / unit proof only. NOT production daily-cycle proof. NOT Lite-compose proof. NOT P5 readiness.

## Purpose

Document the M1.6 controlled promotion of `namechange` into the `int_event_timeline` UNION + `canonical_v2.fact_event` mart, and explicitly enumerate the 9 sources that remain BLOCKED. Updates the covered source-interface taxonomy from 6 to 7.

## Promoted source

**`namechange`** — new UNION branch in [int_event_timeline.sql](data-platform/src/data_platform/dbt/models/intermediate/int_event_timeline.sql) reading [stg_namechange.sql](data-platform/src/data_platform/dbt/models/staging/stg_namechange.sql).

### Derivation (per M1.6-1 audit)

| field | derivation | source column |
|---|---|---|
| `event_type` | constant `'name_change'` | n/a |
| `source_interface_id` | constant `'namechange'` | n/a |
| `ts_code` | passthrough | `ts_code` |
| `event_date` | direct | `start_date` (effective date of the new name) |
| `title` | constant `'Name change'` | n/a |
| `summary` | direct | `name` (the new security name) |
| `event_subtype` | direct | `change_reason` |
| `related_date` | direct | `ann_date` (announcement date) |
| `reference_url` | NULL | n/a |
| `rec_time` | NULL | n/a |
| `source_run_id` / `raw_loaded_at` | passthrough | from `stg_latest_raw` macro |

### Canonical PK derivation in marts (unchanged from M1-G2)

`event_key = md5(concat_ws('|', source_interface_id, event_type, coalesce(title, ''), coalesce(summary, ''), coalesce(event_subtype, ''), coalesce(cast(related_date as varchar), ''), coalesce(reference_url, ''), coalesce(rec_time, '')))`

For namechange, this yields a stable hash over `('namechange', 'name_change', 'Name change', <new_name>, <change_reason>, <ann_date>, '', '')`. Two distinct namechange events for the same security on the same start_date are disambiguated by either name, change_reason, or ann_date.

## Still-blocked sources

### `block_trade` — `BLOCKED_NO_STABLE_KEY`

The Tushare `block_trade` endpoint genuinely emits multiple rows per `(ts_code, trade_date)` (different buyer / seller / price / vol on the same day). The `stg_latest_raw` macro does NOT dedupe by source PK — it picks all rows from the latest raw artifact. With constant `title='Block trade'` and `related_date=trade_date`, the int_event_timeline uniqueness key `(event_type, ts_code, event_date, title, related_date, reference_url)` cannot distinguish multiple trades on the same day. Promoting block_trade requires either an upstream synthetic row hash, a registry source_primary_key correction (Tushare provides no intra-day disambiguator natively), or extending the upstream uniqueness contract — each is a non-trivial design decision out of M1.6 scope. See [event-timeline-m1-6-source-promotion-audit-20260429.md](assembly/reports/stabilization/event-timeline-m1-6-source-promotion-audit-20260429.md) §"block_trade — BLOCKED_NO_STABLE_KEY".

### 8 candidates — `BLOCKED_NO_STAGING`

`pledge_stat`, `pledge_detail`, `repurchase`, `stk_holdertrade`, `limit_list_ths`, `limit_list_d`, `hm_detail`, `stk_surv` — none of these have a `stg_<source>.sql` staging model. Without staging, there is no reproducible row source for the intermediate. Adding 8 staging models, deciding canonical event_type constants per source, and verifying intra-day uniqueness for each is a dedicated round of work. Owner: M1.7+ or a separate staging-then-promotion track.

## Files changed (M1.6)

- [data-platform/src/data_platform/dbt/models/intermediate/int_event_timeline.sql](data-platform/src/data_platform/dbt/models/intermediate/int_event_timeline.sql) — added 7th UNION branch for `namechange`.
- [data-platform/src/data_platform/dbt/models/intermediate/_schema.yml](data-platform/src/data_platform/dbt/models/intermediate/_schema.yml) — extended `event_type` accepted_values with `name_change`; extended `source_interface_id` accepted_values with `namechange`. Updated description.
- [data-platform/src/data_platform/dbt/models/marts_v2/_schema.yml](data-platform/src/data_platform/dbt/models/marts_v2/_schema.yml) — extended `mart_fact_event_v2.event_type` accepted_values with `name_change`. Updated description.
- [data-platform/src/data_platform/dbt/models/marts_lineage/_schema.yml](data-platform/src/data_platform/dbt/models/marts_lineage/_schema.yml) — extended `mart_lineage_fact_event.source_interface_id` accepted_values with `namechange`. Updated description.
- [data-platform/tests/dbt/test_intermediate_models.py](data-platform/tests/dbt/test_intermediate_models.py) — extended `test_intermediate_models_execute_with_duckdb_raw_fixture` event_types assertion to include `name_change` (alphabetic position between `holder_number` and `share_float`).
- [data-platform/tests/dbt/test_marts_models.py](data-platform/tests/dbt/test_marts_models.py) — M1.6-R added `test_event_v2_and_lineage_marts_preserve_namechange_fixture`, which materializes `mart_fact_event_v2` and `mart_lineage_fact_event` from the DuckDB raw fixture and checks v2/lineage PK parity.

## Files NOT changed (per hard rules)

- v2 mart SQL ([mart_fact_event_v2.sql](data-platform/src/data_platform/dbt/models/marts_v2/mart_fact_event_v2.sql)) — event_key derivation expression is unchanged; the new UNION branch flows through identically.
- Lineage mart SQL ([mart_lineage_fact_event.sql](data-platform/src/data_platform/dbt/models/marts_lineage/mart_lineage_fact_event.sql)) — same.
- Iceberg DDL ([iceberg_tables.py](data-platform/src/data_platform/ddl/iceberg_tables.py)) — table schemas unchanged.
- Canonical writer specs ([canonical_writer.py](data-platform/src/data_platform/serving/canonical_writer.py)) — load specs unchanged.
- Dataset routing ([canonical_datasets.py](data-platform/src/data_platform/serving/canonical_datasets.py)) — unchanged.
- Legacy `canonical.*` specs / load specs / dbt marts — NOT deleted.
- `_M1D_LEGACY_RETIREMENT_XFAIL` — NOT removed.
- `FORBIDDEN_SCHEMA_FIELDS` / `FORBIDDEN_PAYLOAD_FIELDS` — NOT extended.
- The int_event_timeline uniqueness combination itself — NOT changed (the existing 6-column key continues to hold for namechange because `(ts_code, start_date, ann_date)` distinguishes namechange rows).

## Tests run + results

```sh
$ cd data-platform && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
    -p no:cacheprovider \
    tests/dbt/test_dbt_skeleton.py \
    tests/dbt/test_dbt_test_coverage.py \
    tests/dbt/test_marts_provider_neutrality.py \
    tests/dbt/test_tushare_staging_models.py
==> 46 passed, 1 skipped, 8 xfailed
```

```sh
$ cd data-platform && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
    -p no:cacheprovider \
    tests/dbt/test_dbt_skeleton.py \
    tests/dbt/test_dbt_test_coverage.py \
    tests/dbt/test_marts_provider_neutrality.py \
    tests/dbt/test_intermediate_models.py
==> 41 passed, 1 skipped, 8 xfailed
```

The 8 xfailed are the `_M1D_LEGACY_RETIREMENT_XFAIL` provider-neutrality scoreboard tests (unchanged by this round).

M1.6-R review-closure proof for the v2/lineage pair:

```sh
$ cd data-platform && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
    -p no:cacheprovider tests/dbt/test_marts_models.py -q
==> 5 passed, 1 skipped
```

## What this proves

- `namechange` is now in the int_event_timeline UNION with deterministic derivation rules.
- The accepted_values taxonomy on `event_type` accepts `name_change`, on `source_interface_id` accepts `namechange`, in both the intermediate and the v2 + lineage marts.
- The live dbt fixture test (`test_intermediate_models_execute_with_duckdb_raw_fixture`) materialises int_event_timeline with the 7th source row visible at the SQL output — this is a real DuckDB run against a real raw artifact fixture, NOT a string mock.
- The v2/lineage fixture test (`test_event_v2_and_lineage_marts_preserve_namechange_fixture`) materialises `mart_fact_event_v2` and `mart_lineage_fact_event`, verifies `name_change` appears in v2, verifies `namechange` appears in lineage, verifies v2 excludes raw/source lineage columns while lineage includes them, and verifies the full `(event_type, entity_id, event_date, event_key)` PK set matches exactly between the two marts.
- The 8 PROMOTION_CANDIDATE_MAPPINGS sources (pledge_*, repurchase, stk_holdertrade, limit_list_*, hm_detail, stk_surv) are explicitly BLOCKED with a documented reason (`BLOCKED_NO_STAGING`).
- `block_trade` is explicitly BLOCKED with a documented reason (`BLOCKED_NO_STABLE_KEY`) covering the intra-day-row uniqueness gap.

## What this does NOT prove (do NOT misclaim)

- This is **NOT** a production daily-cycle proof. No real production daily refresh executed.
- This is **NOT** a Lite-compose v2 proof. No compose started. No PostgreSQL / Neo4j / Dagster daemon launched.
- This is **NOT** a live live-Iceberg proof. The fixture test runs DuckDB-only against raw parquet artifacts; no real Iceberg catalog write.
- This is **NOT** P5 readiness. P5 remains blocked by the full gate stack:
  G1 canonical provider-neutral closure must retire legacy parity failures;
  G2 production daily-cycle full proof / M2.6 must run on the v2 path;
  G3 same-cycle production consumption must prove P3 consumers read the
  canonical_v2 output; and G4 live-PG/downstream bridge closure must prove the
  P4 serving bridge. Legacy retirement Phase B is also still pending.

## Canonical_v2.fact_event coverage status

`canonical_v2.fact_event` now covers **7 source interfaces** (anns, suspend_d, dividend, share_float, stk_holdernumber, disclosure_date, namechange), up from 6. Full event_timeline coverage is NOT achieved: `block_trade` plus the 8 promotion-candidate sources remain BLOCKED, so 9 known source interfaces are still outside the v2 event mart. M1 closure remains pending until those gaps are either promoted or explicitly excluded by a later milestone decision.

## Event_type taxonomy after M1.6

```
{'announcement', 'suspend', 'dividend', 'share_float', 'holder_number', 'disclosure_date', 'name_change'}
```

7 entries. Unchanged from this round forward unless block_trade or candidates are promoted.

## source_interface_id accepted set after M1.6

```
{'anns', 'suspend_d', 'dividend', 'share_float', 'stk_holdernumber', 'disclosure_date', 'namechange'}
```

7 entries.

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
