# Event Timeline M1.9 — Candidate Contract Audit

**Round:** M1.9-1 (Candidate Source Contract Audit)
**Date:** 2026-04-29
**Status:** Audit-only. NO production code change. Strict no-invent verdicts for the 8 remaining `event_timeline` candidate sources still blocked after M1.8.

## Purpose

After M1.8 promoted `block_trade` (8th source interface in `canonical_v2.fact_event`), 8 `PROMOTION_CANDIDATE_MAPPINGS` sources remain BLOCKED:
`pledge_stat`, `pledge_detail`, `repurchase`, `stk_holdertrade`, `limit_list_ths`, `limit_list_d`, `hm_detail`, `stk_surv`.

This audit re-verifies whether any of the 8 has **enough local artifact evidence** (adapter code, fixture writer, staging model, or schema YAML) to safely promote in a fixture-only round without live Tushare fetch.

The hard rule for M1.9-1 is explicit: **"Do not invent source schemas. If source columns cannot be verified from local code/evidence, mark `BLOCKED_NO_LOCAL_SCHEMA`."**

## Inputs read

- [registry.py:880-1020](data-platform/src/data_platform/provider_catalog/registry.py:880) — `PROVIDER_MAPPINGS` + `PROMOTION_CANDIDATE_MAPPINGS` for event_timeline.
- [tushare_available_interfaces.csv](data-platform/src/data_platform/provider_catalog/tushare_available_interfaces.csv) — interface inventory; columns: `provider, source_interface_id, doc_api, label, level1, level2, level3, level4, doc_url, storage_mode, split_by_symbol, access_status, access_reason, completeness_status, check_confidence`. **No column-list field**.
- [adapters/tushare/assets.py](data-platform/src/data_platform/adapters/tushare/assets.py) — `TUSHARE_ASSETS` listing.
- [int_event_timeline.sql](data-platform/src/data_platform/dbt/models/intermediate/int_event_timeline.sql) — current 8-branch UNION.
- [intermediate/_schema.yml:210-249](data-platform/src/data_platform/dbt/models/intermediate/_schema.yml:210) — uniqueness contract + accepted_values.
- [staging/](data-platform/src/data_platform/dbt/models/staging) — staging model directory.
- [tests/dbt/test_tushare_staging_models.py](data-platform/tests/dbt/test_tushare_staging_models.py) — `_write_all_tushare_raw_fixtures`.
- M1.7 + M1.8 evidence: [event-timeline-m1-7-source-closure-audit-20260429.md](assembly/reports/stabilization/event-timeline-m1-7-source-closure-audit-20260429.md), [event-timeline-m1-8-block-trade-promotion-proof-20260429.md](assembly/reports/stabilization/event-timeline-m1-8-block-trade-promotion-proof-20260429.md).

## Local artifact survey

Across the entire data-platform repo, the **only** local references to any of the 8 candidates are:

| Source | registry.py | tushare_available_interfaces.csv | TUSHARE_ASSETS | staging model | raw fixture | dbt schema yml |
|---|---|---|---|---|---|---|
| All 8 | source_primary_key tuple ONLY (line 1010-1017 of `PROMOTION_CANDIDATE_MAPPINGS`) | one row each (description + doc_url, no columns) | ABSENT | ABSENT (no `stg_<source>.sql` file exists) | ABSENT (`_write_all_tushare_raw_fixtures` does NOT cover any) | ABSENT (no entry in any `_schema.yml`) |

The CSV's `doc_url` field links to external Tushare documentation pages. Those pages are not local artifacts; consulting them would require either (a) an out-of-band web fetch (forbidden by hard rule "no production fetch") or (b) prior owner check-in of the column lists into the repo.

The CSV's `label` field provides a Chinese natural-language description (e.g., 股权质押统计数据 for `pledge_stat`). This is sufficient to **name** the source but not sufficient to derive a **schema**.

The registry's `source_primary_key` tuple gives the candidate **PK columns**, not the full column list. PK alone cannot drive a staging model or an event_type/event_date/event_key derivation rule.

## A. Per-candidate verdict table

| source_interface_id | local Tushare asset exists? | raw fixture support exists? | staging model exists? | local schema known? | event_type proposal | event_date proposal | event_key inputs | verdict |
|---|---|---|---|---|---|---|---|---|
| `pledge_stat` | NO | NO | NO | **NO** | suggested `'pledge_stat'` (per M1.6 audit, NOT authoritative) | unrecorded (PK has `end_date`; semantic role unclear without column list) | n/a (no business columns local) | **BLOCKED_NO_LOCAL_SCHEMA** |
| `pledge_detail` | NO | NO | NO | **NO** | suggested `'pledge_detail'` | unrecorded (PK has `ann_date`) | n/a | **BLOCKED_NO_LOCAL_SCHEMA** |
| `repurchase` | NO | NO | NO | **NO** | suggested `'repurchase'` | unrecorded | n/a | **BLOCKED_NO_LOCAL_SCHEMA** |
| `stk_holdertrade` | NO | NO | NO | **NO** | suggested `'holder_trade'` (distinct from existing `'holder_number'`) | unrecorded | n/a | **BLOCKED_NO_LOCAL_SCHEMA** |
| `limit_list_ths` | NO | NO | NO | **NO** | suggested `'limit_up_ths'` | unrecorded | n/a | **BLOCKED_NO_LOCAL_SCHEMA**; PK `(trade_date, ts_code)` shared with block_trade so even with schema, intra-day uniqueness verification needed |
| `limit_list_d` | NO | NO | NO | **NO** | suggested `'limit_up'` | unrecorded | n/a | **BLOCKED_NO_LOCAL_SCHEMA**; same intra-day uniqueness concern |
| `hm_detail` | NO | NO | NO | **NO** | suggested `'hot_money_trade'` | unrecorded | n/a | **BLOCKED_NO_LOCAL_SCHEMA**; same intra-day uniqueness concern |
| `stk_surv` | NO | NO | NO | **NO** | suggested `'institution_survey'` | unrecorded | n/a | **BLOCKED_NO_LOCAL_SCHEMA** |

**Counts:** 0 IMPLEMENTABLE, 8 BLOCKED_NO_LOCAL_SCHEMA.

## B. Why every candidate is BLOCKED_NO_LOCAL_SCHEMA

The 6 prior M1.7 audit candidates were classified `BLOCKED_NO_STAGING`. M1.9-1 refines that verdict to the more specific `BLOCKED_NO_LOCAL_SCHEMA` — the staging model is missing **because the column list is missing**, not because nobody has typed up the staging YAML. Staging cannot be written without knowing which columns to project.

Every M1.9 candidate fails ONE OR MORE of the four required local proofs:

1. **Adapter asset** (`TUSHARE_ASSETS` entry): all 8 are absent. Adding a typed asset entry requires the column list, which is not in the repo.
2. **Raw fixture support** (`_write_all_tushare_raw_fixtures` branch): all 8 are absent. Writing a fixture requires the column list to construct row data.
3. **Staging model** (`stg_<source>.sql`): all 8 are absent. The `stg_latest_raw` macro accepts a column list and a select-list of casts; both depend on knowing the source's column schema.
4. **Local schema artifact** (anything in the repo that documents the source's columns): none exist.

Because (4) is the precondition for (1), (2), and (3), the binding blocker is **schema knowledge**, not staging implementation effort.

## C. Path to closing each candidate (out of M1.9 scope)

For each candidate, a future round must:

1. **Owner check-in of the column list** into a local artifact (e.g., extend `tushare_available_interfaces.csv` with a `columns` column, or add a typed Python dataclass per source under `adapters/tushare/`). This is a one-time documentation pass, **not** a production fetch — owner pulls the column list from Tushare docs (the doc_url already in the CSV) and records it in the repo. M1.9 does not claim this is "trivial" — it requires owner sign-off on canonical column names since some sources expose Chinese-named columns that may need transliteration.
2. **Per-source canonical event_type constant decision**: M1.6 audit suggested values (`'pledge'`, `'repurchase'`, `'holder_trade'`, `'limit_up_ths'`, `'limit_up'`, `'hot_money_trade'`, `'institution_survey'`) but these remain UNRECORDED in the registry's authoritative event_type taxonomy. Owner needs to confirm naming.
3. **Intra-day uniqueness verification per source**: 3 of the 8 sources (`limit_list_ths`, `limit_list_d`, `hm_detail`) share the `(trade_date, ts_code)` PK pattern with block_trade and likely need either the same `summary`-as-disambiguator approach (introduced in M1.8) or a per-source synthetic row hash. The other 5 sources have `(ts_code, ann_date)` or `(ts_code, end_date)` PKs that are likely natural per-event-row but require verification.
4. **Adapter + fixture + staging + UNION branch + parity test** — the 5-step implementation pattern that M1.6 and M1.8 followed for namechange and block_trade. Each step is mechanical once the schema is in the repo.

The audit deliberately stops at step 0 (no schema in repo). M1.9-2 / M1.9-3 / M1.9-4 / M1.9-5 are all SKIPPED.

## D. Conservative verdict

**0 sources promoted in M1.9.** The audit re-confirms but refines the M1.7 / M1.8 verdicts:
- 8 candidates: `BLOCKED_NO_LOCAL_SCHEMA` (refines the prior `BLOCKED_NO_STAGING` to identify the upstream blocker).

This is an **intentional no-code promotion round**, the same shape as M1.7. The deliverable is the per-source verdict + path-forward documented above.

`canonical_v2.fact_event` coverage stays at **8 source interfaces** (anns, suspend_d, dividend, share_float, stk_holdernumber, disclosure_date, namechange, block_trade) — unchanged from M1.8.

## E. Acceptance

- Every blocked source has a concrete documented reason (`BLOCKED_NO_LOCAL_SCHEMA`).
- The binding blocker is identified as **schema knowledge in the repo**, not staging implementation effort.
- A 4-step closure path is documented for the future round (owner check-in of column lists is step 0).
- No production code change in this round.
- Conservative bias upheld: no candidate promoted without local schema proof.

## F. Status declarations

- This is an **AUDIT-ONLY** round. NO production code changed.
- `project_ult_v5_0_1.md` and `ult_milestone.md` UNCHANGED.
- compose / production fetch / P5 shadow-run NOT started.
- M2 / M3 / M4 NOT entered.
- API-6 / sidecar / frontend write API / Kafka/Flink/Temporal / news/Polymarket NOT touched.
- Tushare remains a `provider="tushare"` source adapter ONLY.
- Legacy `canonical.*` specs / load specs / dbt marts NOT deleted.
- `_M1D_LEGACY_RETIREMENT_XFAIL` NOT removed.
- `FORBIDDEN_SCHEMA_FIELDS` / `FORBIDDEN_PAYLOAD_FIELDS` NOT extended.
- `/Users/fanjie/Desktop/BIG/FrontEnd` NOT modified.
- Pre-existing dirty / staged files NOT reverted.
- No `git init`. No commits. No push.
