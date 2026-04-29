# Event Timeline M1.6 Source Promotion Audit

**Round:** M1.6-1
**Date:** 2026-04-29
**Status:** Audit-only. NO production code changed. Source-by-source verdict for the 10 still-blocked event_timeline sources after M1-G2 / M1.5.

## Purpose

Re-derive each blocked event_timeline source's `event_type` / `event_date` / `event_key` / `entity_id` derivation rule from the actual code (registry + staging models + int_event_timeline + macro behavior). Record per-source verdicts so M1.6-2 implements only the deterministic ones. Conservative by design: any source with a derivation gap stays BLOCKED with a documented reason.

## Inputs read

- [registry.py:880-1005](data-platform/src/data_platform/provider_catalog/registry.py:880) — provider→canonical mappings for event_timeline.
- [tushare_available_interfaces.csv](data-platform/src/data_platform/provider_catalog/tushare_available_interfaces.csv) — interface inventory.
- [int_event_timeline.sql](data-platform/src/data_platform/dbt/models/intermediate/int_event_timeline.sql) — current 6-branch UNION.
- [intermediate/_schema.yml:210-235](data-platform/src/data_platform/dbt/models/intermediate/_schema.yml:210) — current uniqueness contract.
- [stg_latest_raw.sql](data-platform/src/data_platform/dbt/macros/stg_latest_raw.sql) — staging macro behavior (picks latest raw artifact, does NOT dedupe by source PK).
- Staging directory listing: only `stg_namechange.sql` and `stg_block_trade.sql` exist among the 10 candidate sources.

## Critical macro behavior finding

`stg_latest_raw` selects ALL rows from the latest raw partition+run; it does NOT dedupe by source primary key. For sources where the registry's `source_primary_key` is genuinely unique in source data (one row per PK), this yields one row per PK at the staging output. For sources where the source PK is NOT actually unique in Tushare data (e.g., multiple block trades per trade_date for the same security), staging emits all rows and the intermediate UNION sees them all.

This matters for the int_event_timeline uniqueness test, which currently asserts uniqueness on `(event_type, ts_code, event_date, title, related_date, reference_url)`.

## Source inventory

| # | source_interface_id | staging model | Source PK (per registry) | Required fields present? | event_type rule | event_date rule | event_key rule | entity_id rule | verdict |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `namechange` | [stg_namechange.sql](data-platform/src/data_platform/dbt/models/staging/stg_namechange.sql) | `(ts_code, start_date)` | YES — ts_code, name, start_date, end_date, ann_date, change_reason | constant `'name_change'` | `start_date` (effective date of new name) | composite via existing md5 (title, summary=new_name, event_subtype=change_reason) | `ts_code → entity_id` | **PROMOTE_NOW** |
| 2 | `block_trade` | [stg_block_trade.sql](data-platform/src/data_platform/dbt/models/staging/stg_block_trade.sql) | `(ts_code, trade_date)` (registry) | YES — ts_code, trade_date, price, vol, amount, buyer, seller | candidate `'block_trade'` | `trade_date` | composite would need to include buyer/seller/price/vol/amount | `ts_code → entity_id` | **BLOCKED_NO_STABLE_KEY** |
| 3 | `pledge_stat` | NONE | `(ts_code, end_date)` | n/a | n/a | n/a | n/a | n/a | **BLOCKED_NO_STAGING** |
| 4 | `pledge_detail` | NONE | `(ts_code, ann_date)` | n/a | n/a | n/a | n/a | n/a | **BLOCKED_NO_STAGING** |
| 5 | `repurchase` | NONE | `(ts_code, ann_date)` | n/a | n/a | n/a | n/a | n/a | **BLOCKED_NO_STAGING** |
| 6 | `stk_holdertrade` | NONE | `(ts_code, ann_date)` | n/a | n/a | n/a | n/a | n/a | **BLOCKED_NO_STAGING** |
| 7 | `limit_list_ths` | NONE | `(trade_date, ts_code)` | n/a | n/a | n/a | n/a | n/a | **BLOCKED_NO_STAGING** |
| 8 | `limit_list_d` | NONE | `(trade_date, ts_code)` | n/a | n/a | n/a | n/a | n/a | **BLOCKED_NO_STAGING** |
| 9 | `hm_detail` | NONE | `(trade_date, ts_code)` | n/a | n/a | n/a | n/a | n/a | **BLOCKED_NO_STAGING** |
| 10 | `stk_surv` | NONE | `(ts_code, ann_date)` | n/a | n/a | n/a | n/a | n/a | **BLOCKED_NO_STAGING** |

**Counts:** 1 PROMOTE_NOW (namechange), 1 BLOCKED_NO_STABLE_KEY (block_trade), 8 BLOCKED_NO_STAGING.

## Detailed per-source analysis

### namechange — PROMOTE_NOW

**Source columns** (from staging): `ts_code` (varchar), `name` (varchar — the new security name), `start_date` (date — effective date of the new name), `end_date` (date — when this name was replaced; null if current), `ann_date` (date — announcement date), `change_reason` (varchar). Plus the standard `source_run_id` and `raw_loaded_at` from the macro.

**Derivation rules** (deterministic, no ambiguity):
- `event_type = 'name_change'` — matches the user's suggested taxonomy and registry-promoted status (registry.py:894).
- `source_interface_id = 'namechange'` — per-branch constant.
- `event_date = start_date` — the effective date of the rename. Source PK in registry is `(ts_code, start_date)`, so `start_date` IS the canonical event_date.
- `title = 'Name change'` (constant, follows the existing pattern of suspend_d / dividend / share_float / stk_holdernumber / disclosure_date which use constant titles).
- `summary = name` — the new security name.
- `event_subtype = change_reason` — the reason field from Tushare.
- `related_date = ann_date` — the announcement date (when distinct from start_date).
- `reference_url = NULL` (no URL in source).
- `rec_time = NULL` (no rec_time in source — not all sources have it; matches share_float / stk_holdernumber pattern).
- `entity_id = ts_code → entity_id` (mart_v2 rename, same as the 6 existing sources).

**Uniqueness compatibility:** the existing int_event_timeline uniqueness key `(event_type, ts_code, event_date, title, related_date, reference_url)` becomes `(event_type='name_change', ts_code, event_date=start_date, title='Name change', related_date=ann_date, reference_url=NULL)`. Source PK `(ts_code, start_date)` plus `ann_date` variation is sufficient — multiple namechange rows for the same (ts_code, start_date) would only collide if ann_date is also identical, which is the legitimate "true duplicate" case that stg_latest_raw selects from one raw artifact already.

**Verdict:** PROMOTE_NOW. Implement the UNION branch in M1.6-2.

### block_trade — BLOCKED_NO_STABLE_KEY

**Source columns** (from staging): `ts_code`, `trade_date`, `price`, `vol`, `amount`, `buyer`, `seller`. Plus standard `source_run_id` / `raw_loaded_at`.

**Why BLOCKED:**

The registry source_primary_key is `(ts_code, trade_date)` (registry.py:901), but Tushare's block_trade endpoint genuinely returns **multiple rows per `(ts_code, trade_date)`** when a security has more than one block trade on the same day (different buyer / seller / price / vol). `stg_latest_raw` does NOT dedupe by source PK (it selects the latest raw artifact and returns ALL rows from it), so all block trade rows flow into the intermediate.

The current int_event_timeline uniqueness test `(event_type, ts_code, event_date, title, related_date, reference_url)` cannot distinguish multiple block trades on the same day because `title` would be the constant `'Block trade'` and `related_date`/`reference_url` would not vary. The test would FAIL.

To promote block_trade safely, one of the following changes is required:
1. **Extend the int_event_timeline uniqueness key** to include `summary` (which would carry buyer/seller/price/vol/amount). This is a contract change to the upstream test; per M1.6-1 audit, summary-as-uniqueness-disambiguator works in principle but introduces a brittle dependency on Tushare's data quality (true duplicates with identical buyer/seller/price/vol/amount would collapse silently).
2. **Correct the registry source_primary_key** for block_trade to include an intra-day disambiguator. Tushare does NOT provide a deterministic intra-day row id for block_trade; a synthetic row hash would have to be added at the staging layer.
3. **Upstream dedup at staging** with a synthetic row hash. This deviates from the macro pattern and changes data semantics.

None of these are mechanical changes — each is a design decision that requires owner sign-off (data-platform owner + upstream provider catalog owner). Per the M1.6 hard rule "能确定就 promote，不能确定就保留 blocked", block_trade stays BLOCKED.

**Path forward (out of M1.6 scope):**
- Decide intra-day disambiguator strategy (synthetic row hash at staging vs. registry source_primary_key extension vs. uniqueness-by-summary).
- Apply that decision uniformly so the canonical PK `(event_type, entity_id, event_date, event_key)` remains stable and reproducible.
- Then promote in a future round.

### 8 candidates without staging — BLOCKED_NO_STAGING

`pledge_stat`, `pledge_detail`, `repurchase`, `stk_holdertrade`, `limit_list_ths`, `limit_list_d`, `hm_detail`, `stk_surv` all map to `event_timeline` in `PROMOTION_CANDIDATE_MAPPINGS` (registry.py:982-1005), but **none of them have a `stg_*.sql` staging model** under `data-platform/src/data_platform/dbt/models/staging/`. Without a staging model, there is no reproducible row source for the intermediate to UNION from.

**Path forward (out of M1.6 scope; M1.7+ or a dedicated staging round):**
1. Add a `stg_<source>.sql` for each, using the `stg_latest_raw` macro.
2. Decide canonical `event_type` constant per source (the user's suggested taxonomy is `pledge` / `repurchase` / `holder_trade` / `limit_up_ths` / `limit_up` / `hot_money_trade` / `institution_survey`, but these are domain inferences and need owner confirmation).
3. Verify each source's natural intra-day uniqueness (similar concern to block_trade — limit_list_d especially, where multiple limit-up events per day per security are possible).
4. THEN promote.

The 8 candidates are deferred to a dedicated staging-then-promotion round. This audit makes no commitment to that round's timing.

## Acceptance summary

- Every blocked source has a concrete documented reason.
- The single promoted source (namechange) has deterministic derivation rules with no ambiguity.
- No implementation has been written by this audit.
- Conservative bias upheld: when in doubt, BLOCK.

## Status declarations

- This is an AUDIT-ONLY round. NO production code changed.
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
