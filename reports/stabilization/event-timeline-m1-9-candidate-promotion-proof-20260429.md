# Event Timeline M1.9 — Candidate Promotion Proof

**Round:** M1.9
**Date:** 2026-04-29
**Status:** Intentional no-code promotion round. NOT production daily-cycle proof. NOT Lite-compose proof. NOT live Iceberg proof. NOT P5 readiness.

## Outcome

| metric | value |
|---|---|
| Sources promoted in M1.9 | **0** |
| canonical_v2.fact_event coverage | **8 source interfaces** (unchanged from M1.8) |
| Still-blocked sources | **8** (all `BLOCKED_NO_LOCAL_SCHEMA` — refines prior `BLOCKED_NO_STAGING`) |
| Production code touched | NONE |
| Tests added | 0 |
| Evidence files added | **2** (audit + this proof) |

## Promoted sources (M1.9)

**0.** This is an intentional no-code promotion round. The deliverable is the per-source contract audit + path-forward documented in [event-timeline-m1-9-candidate-contract-audit-20260429.md](assembly/reports/stabilization/event-timeline-m1-9-candidate-contract-audit-20260429.md).

## Still-blocked sources

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

Per the M1.9 hard rule "Do not invent source schemas", and the operational hard rule "no production fetch", M1.9 cannot resolve this blocker. The audit documents the resolution path; the resolution itself belongs in a future round triggered by an owner column-list check-in.

## Test commands and results

No production code changed by M1.9, but M1.9-7 re-ran both sweeps as a regression sanity check. Exact M1.9 results below; both lanes are green.

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

The 8 xfails (default sweep) and 17 xfails (v2 lane) are the `_M1D_LEGACY_RETIREMENT_XFAIL` provider-neutrality scoreboard tests — unchanged from M1.8 because M1.9 did not touch legacy specs.

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

Full event_timeline coverage (16 known registry/candidate sources) is still **NOT** achieved. The 8 candidates remain BLOCKED_NO_LOCAL_SCHEMA. M1 closure remains pending until the schema documentation gap is closed in a future round.

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

## Remaining blockers for M1 / P5

| gate | description | status after M1.9 |
|---|---|---|
| **M1 event_timeline closure** | All 16 registry/candidate event sources flow into canonical_v2.fact_event | PARTIAL — 8 of 16 promoted; 8 BLOCKED_NO_LOCAL_SCHEMA |
| **G1** | canonical provider-neutral closure / legacy retirement | BLOCKED — preconditions 6, 7, 8 of retirement-readiness still NOT STARTED |
| **G2** | production daily-cycle full proof / M2.6 | BLOCKED — out of M1 scope |
| **G3** | same-cycle production consumption | BLOCKED — gated on G2 |
| **G4** | live PG / downstream bridge closure | BLOCKED — gated on G2 |

M1.9 does not advance any of these gates. Its contribution is naming the schema-documentation blocker truthfully so future rounds can target the right work.

## Status declarations

- `project_ult_v5_0_1.md` UNCHANGED.
- `ult_milestone.md` UNCHANGED.
- compose NOT started.
- production fetch NOT enabled.
- P5 shadow-run NOT started.
- M2 / M3 / M4 NOT entered.
- API-6 / sidecar / frontend write API / Kafka/Flink/Temporal / news/Polymarket NOT touched.
- Tushare remains a `provider="tushare"` source adapter ONLY.
- Legacy `canonical.*` specs / load specs / dbt marts NOT deleted.
- `_M1D_LEGACY_RETIREMENT_XFAIL` NOT removed.
- `FORBIDDEN_SCHEMA_FIELDS` / `FORBIDDEN_PAYLOAD_FIELDS` NOT extended.
- `/Users/fanjie/Desktop/BIG/FrontEnd` NOT modified (read-only).
- Pre-existing staged / unstaged files NOT reverted.
- No `git init`. No commits. No push.
