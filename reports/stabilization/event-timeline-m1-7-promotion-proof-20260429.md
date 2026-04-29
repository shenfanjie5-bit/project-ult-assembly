# Event Timeline M1.7 Promotion Proof

**Round:** M1.7
**Date:** 2026-04-29
**Status:** Intentional no-code promotion round. NOT production daily-cycle proof. NOT Lite-compose proof. NOT P5 readiness.
**Note (added after M1.8):** the `block_trade` BLOCKED_NO_STABLE_KEY verdict in this report is **superseded for `block_trade` by [event-timeline-m1-8-block-trade-promotion-proof-20260429.md](assembly/reports/stabilization/event-timeline-m1-8-block-trade-promotion-proof-20260429.md)**, which executed M1.7 audit §B Path 1 (widen `int_event_timeline` uniqueness key to include `summary`) and added the block_trade UNION branch + parity test. The historical M1.7 audit conclusion is preserved as-is below; current safe-subset coverage is **8 source interfaces** (was 7 at the time of this report). The 8 candidate sources remain BLOCKED_NO_STAGING per M1.7's verdict.

## Outcome

| metric | value |
|---|---|
| Sources promoted in M1.7 | **0** |
| Still-blocked sources | **9** (block_trade + 8 candidates) |
| Production code changed | **NONE** |
| Tests added | **0** |
| Evidence files added | **2** (this file + the M1.7-1 audit) |

## Promoted sources

**0.** This is an intentional no-code promotion round. The deliverable is the per-source audit + path-forward documented in [event-timeline-m1-7-source-closure-audit-20260429.md](assembly/reports/stabilization/event-timeline-m1-7-source-closure-audit-20260429.md).

## Still-blocked sources

| source | verdict | reason |
|---|---|---|
| `block_trade` | **BLOCKED_NO_STABLE_KEY** | int_event_timeline uniqueness key `(event_type, ts_code, event_date, title, related_date, reference_url)` cannot distinguish multiple block trades on the same `(ts_code, trade_date)`; only `summary` (encoding buyer/seller/price/vol/amount) varies per intra-day row. Promotion requires extending the int_event_timeline uniqueness contract — a deliberate decision out of M1.7 scope. See M1.7-1 audit §B for 3 enumerated resolution paths. |
| `pledge_stat` | **BLOCKED_NO_STAGING** | No Tushare adapter, no fixture, no staging. |
| `pledge_detail` | **BLOCKED_NO_STAGING** | Same. |
| `repurchase` | **BLOCKED_NO_STAGING** | Same. |
| `stk_holdertrade` | **BLOCKED_NO_STAGING** | Same. |
| `limit_list_ths` | **BLOCKED_NO_STAGING** | Same. Plus likely intra-day uniqueness gap (PK `(trade_date, ts_code)` shared with block_trade). |
| `limit_list_d` | **BLOCKED_NO_STAGING** | Same. Plus likely intra-day uniqueness gap. |
| `hm_detail` | **BLOCKED_NO_STAGING** | Same. Plus likely intra-day uniqueness gap. |
| `stk_surv` | **BLOCKED_NO_STAGING** | Same. |

## Intentional no-code promotion declaration

This round does NOT modify production code. The audit identified that:

1. **block_trade** has all infrastructure (registry-promoted, TUSHARE_ASSETS entry, fixture writer, staging model) BUT promotion requires a deliberate uniqueness-contract decision. The 3 resolution paths are documented in the M1.7-1 audit §B; each requires owner sign-off and belongs in a separate round.

2. **The 8 candidates** lack Tushare adapter wiring entirely. `tushare_available_interfaces.csv` lists them as `access_status=available` (the API tier), but `TUSHARE_ASSETS` excludes them — meaning the adapter has no schema, fixture writer, or staging code for any of them. Promoting any requires building adapter + fixture + staging from scratch (5-step checklist in M1.7-1 §C), which is a dedicated adapter-build round.

Per the M1.7 hard rule "能确定就 promote，不能确定就保留 blocked，并把 derivation gap 写清楚", the conservative response is: 0 promoted, both BLOCKED categories documented with named owners and next actions.

## Safe-subset coverage status (unchanged from M1.6)

`canonical_v2.fact_event` continues to cover **7 source interfaces**: `anns`, `suspend_d`, `dividend`, `share_float`, `stk_holdernumber`, `disclosure_date`, `namechange`. Full event_timeline coverage is NOT achieved: the current tracked scope is 7 covered + 9 blocked = 16 known registry/candidate source interfaces.

`event_type` taxonomy unchanged: `{'announcement', 'suspend', 'dividend', 'share_float', 'holder_number', 'disclosure_date', 'name_change'}`.

`source_interface_id` accepted set unchanged: `{'anns', 'suspend_d', 'dividend', 'share_float', 'stk_holdernumber', 'disclosure_date', 'namechange'}`.

## NOT-claims

- This is **NOT** a production daily-cycle proof.
- This is **NOT** a Lite-compose proof.
- This is **NOT** P5 readiness.
- This is **NOT** evidence that legacy `canonical.*` can be retired.
- This is **NOT** evidence that block_trade is impossible to promote — it is evidence that promoting block_trade requires a deliberate contract decision that should not be made unilaterally inside an audit round.

## P5 blockers (re-confirmed)

P5 shadow-run remains BLOCKED. The blocker categories (per [m1-legacy-canonical-retirement-readiness-20260428.md](assembly/reports/stabilization/m1-legacy-canonical-retirement-readiness-20260428.md) and [m1-legacy-retirement-preconditions-progress-20260428.md](assembly/reports/stabilization/m1-legacy-retirement-preconditions-progress-20260428.md)):

| gate | description | status |
|---|---|---|
| **G1** | canonical provider-neutral closure / legacy retirement | BLOCKED — preconditions 6, 7, 8 of the retirement-readiness plan still NOT STARTED (FORBIDDEN_*_FIELDS extension, xfail removal, legacy spec deletion) |
| **G2** | production daily-cycle full proof / M2.6 | BLOCKED — out of M1 scope; depends on M2.1 runtime preflight |
| **G3** | same-cycle production consumption (downstream consumers verified end-to-end) | BLOCKED — gated on G2 |
| **G4** | live PG / downstream bridge closure | BLOCKED — gated on G2 |

M1.7 does not advance any of these gates. M1.7's contribution is keeping the audit trail clean: every still-blocked source has a documented reason and named owner.

## Acceptance

- 2 evidence files added under `assembly/reports/stabilization/` (this file + the M1.7-1 audit).
- 0 production source files changed.
- 0 test files changed.
- 0 schema yml files changed.
- The optional precondition-9 wording update in [m1-legacy-retirement-preconditions-progress-20260428.md](assembly/reports/stabilization/m1-legacy-retirement-preconditions-progress-20260428.md) reflects the M1.7 status change ("M1.7 audit re-confirmed BLOCKED for block_trade + 8 candidates; 0 sources newly promoted").

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
- `/Users/fanjie/Desktop/BIG/FrontEnd` NOT modified.
- Pre-existing dirty files NOT reverted.
- No `git init`. No commits. No push.
