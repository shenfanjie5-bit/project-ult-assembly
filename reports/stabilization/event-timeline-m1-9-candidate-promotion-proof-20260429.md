# Event Timeline M1.9 — Candidate Promotion Proof

**Round:** M1.9
**Date:** 2026-04-29
**Status:** Intentional no-code promotion round. NOT production daily-cycle proof. NOT Lite-compose proof. NOT live Iceberg proof. NOT P5 readiness.

**Supersession note (2026-04-30):** This file is historical M1.9
evidence. The `BLOCKED_NO_LOCAL_SCHEMA` verdict below was superseded by
M1.11 schema check-in and M1.13 promotion of all 8 candidates; M1.14 then
closed M1 with 9/9 retirement preconditions done and 0 xfails. Use this
report only to understand the M1.9 decision boundary, not current M1/G1
status.

## Outcome

| metric | value |
|---|---|
| Sources promoted in M1.9 | **0** |
| canonical_v2.fact_event coverage | **8 source interfaces** (unchanged from M1.8) |
| Still-blocked sources | **8** (all `BLOCKED_NO_LOCAL_SCHEMA` — refines prior `BLOCKED_NO_STAGING`) |
| Production code touched | NONE |
| Tests added | 0 |
| Evidence files added | **2** (audit + this proof) |
| Current supersession | M1.13 promoted all 8; current event_timeline coverage is 16/16 |

## Promoted sources (M1.9)

**0.** This is an intentional no-code promotion round. The deliverable is the per-source contract audit + path-forward documented in [event-timeline-m1-9-candidate-contract-audit-20260429.md](assembly/reports/stabilization/event-timeline-m1-9-candidate-contract-audit-20260429.md).

## Historical M1.9 blocked sources (superseded)

| source | verdict | exact blocker reason |
|---|---|---|
| `pledge_stat` | `BLOCKED_NO_LOCAL_SCHEMA` | No local artifact records the column list. Only the source_primary_key tuple `(ts_code, end_date)` is in the repo (registry.py:1010). Adapter, fixture, staging, schema yml all absent. |
| `pledge_detail` | `BLOCKED_NO_LOCAL_SCHEMA` | Same. PK `(ts_code, ann_date)` (registry.py:1011). |
| `repurchase` | `BLOCKED_NO_LOCAL_SCHEMA` | Same. PK `(ts_code, ann_date)` (registry.py:1012). |
| `stk_holdertrade` | `BLOCKED_NO_LOCAL_SCHEMA` | Same. PK `(ts_code, ann_date)` (registry.py:1013). Suggested event_type 'holder_trade' must be distinct from existing 'holder_number'. |
| `limit_list_ths` | `BLOCKED_NO_LOCAL_SCHEMA` | Same. PK `(trade_date, ts_code)` (registry.py:1014). PK pattern shared with block_trade — even with schema, intra-day uniqueness verification needed per the M1.8 contract pattern. |
| `limit_list_d` | `BLOCKED_NO_LOCAL_SCHEMA` | Same. PK `(trade_date, ts_code)` (registry.py:1015). Same intra-day uniqueness concern. |
| `hm_detail` | `BLOCKED_NO_LOCAL_SCHEMA` | Same. PK `(trade_date, ts_code)` (registry.py:1016). Same intra-day uniqueness concern. |
| `stk_surv` | `BLOCKED_NO_LOCAL_SCHEMA` | Same. PK `(ts_code, ann_date)` (registry.py:1017). |

The `tushare_available_interfaces.csv` has 15 columns (`provider, source_interface_id, doc_api, label, level1..4, doc_url, storage_mode, split_by_symbol, access_status, access_reason, completeness_status, check_confidence`) — none of which is a column list. The CSV proves the source is accessible (`access_status=available`); it does NOT provide the schema needed to drive a staging model.

## Source-by-source reason summary

The binding blocker for ALL 8 candidates is **schema knowledge in the repo**, not staging implementation effort. M1.9 deliberately refines the M1.7 verdict from `BLOCKED_NO_STAGING` to `BLOCKED_NO_LOCAL_SCHEMA` because:

- `BLOCKED_NO_STAGING` could be misread as "implementation backlog — just write the staging models". Implementation is mechanical IF column lists are known.
- `BLOCKED_NO_LOCAL_SCHEMA` is the truthful upstream blocker: column lists are NOT in the repo, and adding them requires owner sign-off (canonical column naming + per-source intra-day uniqueness verification + per-source canonical event_type constant decision). This is documentation work, not coding work.

Per the M1.9 hard rule "Do not invent source schemas", and the operational hard rule "no production fetch", M1.9 could not resolve this blocker. The audit documented the resolution path. That future path later landed as M1.11 schema check-in and M1.13 promotion, so the blocker is not current.

## Test commands and results

No production code changed by M1.9, but M1.9-7 re-ran both sweeps as a regression sanity check. Exact M1.9 historical results below; both lanes were green for the M1.9 baseline. Do not cite these as current test counts after M1.12-M1.14 retirement.

```sh
$ cd data-platform && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
    -p no:cacheprovider \
    tests/dbt/test_intermediate_models.py \
    tests/dbt/test_marts_models.py \
    tests/dbt/test_dbt_skeleton.py \
    tests/dbt/test_dbt_test_coverage.py \
    tests/dbt/test_marts_provider_neutrality.py \
    tests/provider_catalog
==> 58 passed, 2 skipped, 8 xfailed in 2.08s
```

```sh
$ cd data-platform && DP_CANONICAL_USE_V2=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
    -p no:cacheprovider \
    tests/serving \
    tests/cycle/test_current_cycle_inputs.py \
    tests/cycle/test_current_cycle_inputs_lineage_absent.py \
    tests/test_assets.py
==> 176 passed, 5 skipped, 17 xfailed in 3.66s
```

At M1.9, the 8 xfails (default sweep) and 17 xfails (v2 lane) were the
`_M1D_LEGACY_RETIREMENT_XFAIL` provider-neutrality scoreboard tests. That
state is superseded by M1.14, where the final marker was removed and the
full data-platform sweep reported 624 passed / 74 skipped / 0 xfailed.

## What this does NOT prove (do NOT misclaim)

- This is **NOT** a production daily-cycle proof.
- This is **NOT** a Lite-compose v2 proof.
- This is **NOT** a live live-Iceberg proof.
- This is **NOT** P5 readiness.
- This is **NOT** evidence that the 8 candidates are impossible to promote — it is evidence that promoting them requires owner schema check-in, which M1.9 cannot do unilaterally.

## canonical_v2.fact_event coverage status

`canonical_v2.fact_event` continues to cover **8 source interfaces** (unchanged from M1.8):
- anns, suspend_d, dividend, share_float, stk_holdernumber, disclosure_date (M1-G2)
- namechange (M1.6)
- block_trade (M1.8)

At M1.9, full event_timeline coverage (16 known registry/candidate
sources) was **NOT** achieved, and the 8 candidates remained
`BLOCKED_NO_LOCAL_SCHEMA`. Current status is superseded: M1.11 supplied
local schema + uniqueness evidence, M1.13 promoted all 8, and M1.14 closed
M1.

### event_type taxonomy after M1.9

```
{'announcement', 'suspend', 'dividend', 'share_float', 'holder_number', 'disclosure_date', 'name_change', 'block_trade'}
```
8 entries (unchanged from M1.8).

### source_interface_id accepted set after M1.9

```
{'anns', 'suspend_d', 'dividend', 'share_float', 'stk_holdernumber', 'disclosure_date', 'namechange', 'block_trade'}
```
8 entries (unchanged from M1.8).

## Historical blockers after M1.9 (superseded for M1/G1)

| gate | description | status after M1.9 | current supersession |
|---|---|---|---|
| **M1 event_timeline closure** | All 16 registry/candidate event sources flow into canonical_v2.fact_event | PARTIAL — 8 of 16 promoted; 8 `BLOCKED_NO_LOCAL_SCHEMA` | PASS after M1.13, 16/16 promoted |
| **G1** | canonical provider-neutral closure / legacy retirement | BLOCKED — preconditions 6, 7, 8 of retirement-readiness were open in M1.9 | PASS after M1.12 + M1.14 |
| **G2** | production daily-cycle full proof / M2.6 | BLOCKED — out of M1 scope | Still blocked pending M2.6 proof |
| **G3** | same-cycle production consumption | BLOCKED — gated on G2 | Still blocked pending M2.6 + M3.2/M3.3 |
| **G4** | live PG / downstream bridge closure | BLOCKED — gated on G2 | Still blocked pending M4 bridge/live PG downstream proof |

M1.9 did not advance these gates. Its contribution was naming the schema-documentation blocker truthfully so later rounds could target the right work.

## Historical M1.9 status declarations

- These declarations describe M1.9 only; they do not describe the current
  post-M1.14 state.
- `project_ult_v5_0_1.md` UNCHANGED in M1.9.
- `ult_milestone.md` UNCHANGED in M1.9.
- compose NOT started.
- production fetch NOT enabled.
- P5 shadow-run NOT started.
- M2 / M3 / M4 NOT entered.
- API-6 / sidecar / frontend write API / Kafka/Flink/Temporal / news/Polymarket NOT touched.
- Tushare remains a `provider="tushare"` source adapter ONLY.
- Legacy `canonical.*` specs / load specs / dbt marts NOT deleted in M1.9.
- `_M1D_LEGACY_RETIREMENT_XFAIL` NOT removed in M1.9.
- `FORBIDDEN_SCHEMA_FIELDS` / `FORBIDDEN_PAYLOAD_FIELDS` NOT extended in M1.9.
- `/Users/fanjie/Desktop/BIG/FrontEnd` NOT modified (read-only).
- Pre-existing staged / unstaged files NOT reverted.
- No `git init`. No commits. No push.
