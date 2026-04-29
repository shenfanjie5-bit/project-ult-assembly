# Event Timeline M1.7 Source Closure Audit

**Round:** M1.7-1 + M1.7-2
**Date:** 2026-04-29
**Status:** Audit-only. NO production code change. Re-audits the 9 sources still blocked after M1.6 to confirm verdicts hold and document the resolution path forward for each.

## Purpose

After M1.6 promoted `namechange` (event_type='name_change') into the safe-subset of `canonical_v2.fact_event`, 9 event_timeline sources remain BLOCKED:
- 1 promoted-but-not-yet-in-UNION: `block_trade`.
- 8 candidate sources without staging: `pledge_stat`, `pledge_detail`, `repurchase`, `stk_holdertrade`, `limit_list_ths`, `limit_list_d`, `hm_detail`, `stk_surv`.

This audit verifies whether any of the 9 can be promoted in a fixture-only / test-level safe way without production fetch, compose start, or contract changes that require owner sign-off.

## Inputs read

- [registry.py:880-1010](data-platform/src/data_platform/provider_catalog/registry.py:880) — `PROVIDER_MAPPINGS` (block_trade) + `PROMOTION_CANDIDATE_MAPPINGS` (8 candidates).
- [tushare_available_interfaces.csv](data-platform/src/data_platform/provider_catalog/tushare_available_interfaces.csv) — `access_status` and `completeness_status` per source.
- [adapters/tushare/assets.py:803-852](data-platform/src/data_platform/adapters/tushare/assets.py:803) — `TUSHARE_ASSETS` listing.
- [int_event_timeline.sql](data-platform/src/data_platform/dbt/models/intermediate/int_event_timeline.sql) — current 7-branch UNION.
- [intermediate/_schema.yml:210-239](data-platform/src/data_platform/dbt/models/intermediate/_schema.yml:210) — uniqueness contract + accepted_values.
- [stg_block_trade.sql](data-platform/src/data_platform/dbt/models/staging/stg_block_trade.sql) — staging columns.
- [tests/dbt/test_tushare_staging_models.py](data-platform/tests/dbt/test_tushare_staging_models.py) — `_write_all_tushare_raw_fixtures` coverage.
- [mart_fact_event_v2.sql](data-platform/src/data_platform/dbt/models/marts_v2/mart_fact_event_v2.sql) — mart-level event_key derivation.
- M1.6 evidence: [event-timeline-m1-6-source-promotion-audit-20260429.md](assembly/reports/stabilization/event-timeline-m1-6-source-promotion-audit-20260429.md), [event-timeline-m1-6-promotion-proof-20260429.md](assembly/reports/stabilization/event-timeline-m1-6-promotion-proof-20260429.md).

## A. Per-source verdict table

| source | registry status | staging | TUSHARE_ASSETS | raw fixture | source PK (registry) | proposed event_type | proposed event_date | event_key inputs (mart) | unique on canonical PK? | verdict | owner / next action |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `block_trade` | promoted (registry.py:901) | YES (`stg_block_trade.sql`) | YES (assets.py:803-852) | YES (1 row in `_write_all_tushare_raw_fixtures`) | `(ts_code, trade_date)` | `'block_trade'` | `trade_date` | `summary` (encoded buyer/seller/price/vol/amount) — varies per intra-day row | YES at mart level (event_key hashes summary); NO at int_event_timeline level (existing uniqueness key cannot distinguish multiple trades per day) | **BLOCKED_NO_STABLE_KEY** at the int_event_timeline contract level | dedicated round to widen int_event_timeline uniqueness key OR rewrite title to be row-distinguishing |
| `pledge_stat` | candidate (registry.py:1003) | NO | NO | NO | `(ts_code, end_date)` | unrecorded | unrecorded | n/a | n/a | **BLOCKED_NO_STAGING** | adapter-build round (TUSHARE_ASSETS entry + fixture writer + staging + intra-day uniqueness verification + canonical event_type decision) |
| `pledge_detail` | candidate (registry.py:1004) | NO | NO | NO | `(ts_code, ann_date)` | unrecorded | unrecorded | n/a | n/a | **BLOCKED_NO_STAGING** | same |
| `repurchase` | candidate (registry.py:1005) | NO | NO | NO | `(ts_code, ann_date)` | unrecorded | unrecorded | n/a | n/a | **BLOCKED_NO_STAGING** | same |
| `stk_holdertrade` | candidate (registry.py:1006) | NO | NO | NO | `(ts_code, ann_date)` | unrecorded | unrecorded | n/a | n/a | **BLOCKED_NO_STAGING** | same |
| `limit_list_ths` | candidate (registry.py:1007) | NO | NO | NO | `(trade_date, ts_code)` | unrecorded | unrecorded | n/a | n/a | **BLOCKED_NO_STAGING** | same |
| `limit_list_d` | candidate (registry.py:1008) | NO | NO | NO | `(trade_date, ts_code)` | unrecorded | unrecorded | n/a | n/a | **BLOCKED_NO_STAGING** | same |
| `hm_detail` | candidate (registry.py:1009) | NO | NO | NO | `(trade_date, ts_code)` | unrecorded | unrecorded | n/a | n/a | **BLOCKED_NO_STAGING** | same |
| `stk_surv` | candidate (registry.py:1010) | NO | NO | NO | `(ts_code, ann_date)` | unrecorded | unrecorded | n/a | n/a | **BLOCKED_NO_STAGING** | same |

**Counts:** 0 SAFE_TO_PROMOTE, 1 BLOCKED_NO_STABLE_KEY (block_trade), 8 BLOCKED_NO_STAGING.

Tushare CSV `access_status` is `available` for all 9 sources, but availability is the API-tier label — it is NOT a measure of adapter readiness. `TUSHARE_ASSETS` is the actual adapter wiring; only block_trade is in it.

## B. block_trade re-audit — uniqueness analysis

`stg_block_trade.sql` produces the seven columns `ts_code, trade_date, price, vol, amount, buyer, seller` plus `source_run_id` / `raw_loaded_at` from the `stg_latest_raw` macro. The macro selects ALL rows from the latest raw artifact; it does NOT dedupe by source PK. Tushare's block_trade endpoint genuinely emits multiple rows per `(ts_code, trade_date)` (different buyer / seller / price / vol within the same trading day).

The current int_event_timeline uniqueness key (intermediate/_schema.yml:213-214) is:
```yaml
unique_combination_of_columns:
  combination_of_columns: ["event_type", "ts_code", "event_date", "title", "related_date", "reference_url"]
```

For a hypothetical block_trade UNION branch with the existing constant-title pattern:
- `event_type` = constant `'block_trade'`
- `ts_code` = passthrough
- `event_date` = `trade_date`
- `title` = literal `'Block trade'` (constant per row, matching the 5 other constant-title sources)
- `related_date` = `trade_date` (constant per row)
- `reference_url` = NULL (constant)

For two block trades on the same `(ts_code, trade_date)` with different buyer/seller/price/vol, the 6-column tuple is **identical**. `dbt run` can materialize the intermediate and mart models, but `dbt test` fails before canonical publication.

Only `summary` (which would carry buyer/seller/price/vol/amount) varies per intra-day row. `summary` is NOT in the int_event_timeline uniqueness key.

The mart-level canonical PK `(event_type, entity_id, event_date, event_key)` would resolve correctly because [mart_fact_event_v2.sql:31-40](data-platform/src/data_platform/dbt/models/marts_v2/mart_fact_event_v2.sql:31) computes `event_key = md5(concat_ws('|', source_interface_id, event_type, ..., coalesce(summary, ''), ...))`. summary IS already in the mart-level event_key derivation. So canonical_v2.fact_event would have unique rows, but `dbt test` would block publication; writer-side canonical PK validation remains the second line of defense.

### Resolution paths (each requires a deliberate round, NOT M1.7)

**Path 1: Widen the int_event_timeline uniqueness key to include `summary`.**
- Change [intermediate/_schema.yml:213-214](data-platform/src/data_platform/dbt/models/intermediate/_schema.yml:213) to `combination_of_columns: ["event_type", "source_interface_id", "ts_code", "event_date", "title", "related_date", "reference_url", "summary"]`.
- Adding `summary` weakens the intermediate duplicate guard: it cannot create new uniqueness failures, but it can allow rows that the narrower key would have caught. This path is acceptable only if the owner explicitly shifts row identity enforcement to the mart-level `event_key`, canonical PK parity tests, and writer-side canonical PK validation.
- Then add the block_trade UNION branch with title='Block trade', summary=`concat('buyer=', coalesce(buyer, ''), ';seller=', coalesce(seller, ''), ';price=', coalesce(price, ''), ';vol=', coalesce(vol, ''), ';amount=', coalesce(amount, ''))`.
- Pros: recommended minimal contract-change path; cleanly follows the constant-title pattern of the other event sources when paired with explicit dbt tests and writer validation.
- Cons: weakens the upstream intermediate duplicate guard and changes the uniqueness contract (a deliberate decision needing owner sign-off).

**Path 2: Embed buyer/seller into title for block_trade specifically.**
- e.g. `title = concat('Block trade ', coalesce(buyer, '?'), '->', coalesce(seller, '?'))`.
- Pros: no uniqueness key change needed.
- Cons: makes title row-distinguishing rather than constant, breaking the constant-title pattern of the 6 other sources. Title becomes semantically "row identifier" instead of "event class label".

**Path 3: Synthetic intra-day row hash in the staging layer.**
- Add `row_hash = md5(concat_ws('|', ts_code, trade_date, buyer, seller, price, vol, amount))` to `stg_block_trade.sql`, then propagate into int_event_timeline as a column included in the uniqueness key.
- Pros: distinguishes rows at the staging layer, semantically correct.
- Cons: deviates from the `stg_latest_raw` macro pattern; requires adding a column to the int_event_timeline schema and changing the uniqueness contract anyway.

Each requires owner sign-off and a dedicated round. Path 1 is the cleanest minimal change; Path 2 is the smallest diff but breaks pattern consistency; Path 3 introduces new design surface.

### Files that a future block_trade promotion round would touch

For Path 1 (recommended):
- [intermediate/_schema.yml](data-platform/src/data_platform/dbt/models/intermediate/_schema.yml) — widen uniqueness key + add `'block_trade'` to event_type accepted_values + add `'block_trade'` to source_interface_id accepted_values.
- [int_event_timeline.sql](data-platform/src/data_platform/dbt/models/intermediate/int_event_timeline.sql) — add 8th UNION branch reading `stg_block_trade`.
- [marts_v2/_schema.yml](data-platform/src/data_platform/dbt/models/marts_v2/_schema.yml) — add `'block_trade'` to mart_fact_event_v2.event_type accepted_values.
- [marts_lineage/_schema.yml](data-platform/src/data_platform/dbt/models/marts_lineage/_schema.yml) — add `'block_trade'` to mart_lineage_fact_event.source_interface_id accepted_values.
- [tests/dbt/test_intermediate_models.py](data-platform/tests/dbt/test_intermediate_models.py) — extend `event_types` assertion (alphabetic position: 'block_trade' before 'disclosure_date').
- [tests/dbt/test_marts_models.py](data-platform/tests/dbt/test_marts_models.py) — update `event_summary` from `(7, 7)` to `(8, 8)`.

The scope is similar to M1.6's namechange addition (~6 files, ~30 lines of changes). The substantive difference is the uniqueness-key widening, which is the deliberate contract decision that M1.7 declines to make unilaterally.

## C. 8 candidates — staging feasibility

All 8 candidate sources require, at minimum:
1. **Tushare adapter asset** — a new entry in [adapters/tushare/assets.py:803-852](data-platform/src/data_platform/adapters/tushare/assets.py:803) with the source-specific column list, partition-by-date pattern, and any source-specific row-pattern handling (e.g., the `anns` multi-row pattern that block_trade follows per the assets.py:550 comment).
2. **Fixture writer entry** — a new branch in `_write_all_tushare_raw_fixtures` ([tests/dbt/test_tushare_staging_models.py](data-platform/tests/dbt/test_tushare_staging_models.py)) writing a deterministic raw parquet fixture for the source with at least 1 row.
3. **Staging model** — a new `stg_<source>.sql` using the `stg_latest_raw` macro with the source-specific column list and casts.
4. **Intra-day uniqueness verification per source** — analogous to the block_trade analysis above. Sources with `(trade_date, ts_code)` PK (limit_list_ths, limit_list_d, hm_detail) likely have multiple intra-day rows and inherit the same uniqueness-key dilemma as block_trade. Sources with `(ts_code, ann_date)` or `(ts_code, end_date)` PK (pledge_stat, pledge_detail, repurchase, stk_holdertrade, stk_surv) are likely natural per-event-row but require verification.
5. **Per-source canonical event_type constant decision** — semantic naming requires owner sign-off. M1.6 audit suggested `'pledge'` / `'pledge_detail'` / `'repurchase'` / `'holder_trade'` / `'limit_up_ths'` / `'limit_up'` / `'hot_money_trade'` / `'institution_survey'` as candidates, but these are domain inferences and not authoritative until the registry's `field_mapping` and a designated event-type taxonomy document records them.

None of these steps is mechanical. Each requires per-source product/data-engineering decisions. M1.7 declines to add adapter wiring or fixture stubs for sources whose canonical event semantics are not yet pinned.

The 8 candidates remain `BLOCKED_NO_STAGING`. Owner: a dedicated adapter-build round (likely after M2.1 runtime preflight or as a parallel M1.7+ track that focuses on adapter coverage rather than canonical promotion).

## D. Conservative verdict

**0 sources promoted in M1.7.** The audit re-confirms the M1.6 verdicts:
- block_trade: BLOCKED_NO_STABLE_KEY (resolution path documented).
- 8 candidates: BLOCKED_NO_STAGING (adapter-wiring requirement documented).

This is an **intentional no-code promotion round.** The deliverable is the per-source audit + path-forward documentation. M1.7-3 (Safe Increment Implementation) is SKIPPED.

## E. Acceptance

- Every blocked source has a concrete documented reason and named owner / next action.
- block_trade has 3 enumerated resolution paths; each is a deliberate decision deferred to a future round.
- 8 candidates have a 5-step adapter-build checklist to enable a future promotion round.
- No production code change in this round.
- Conservative bias upheld: when in doubt about uniqueness or semantic-rule clarity, BLOCK.

## F. Status declarations

- This is an **AUDIT-ONLY** round. NO production code changed.
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
