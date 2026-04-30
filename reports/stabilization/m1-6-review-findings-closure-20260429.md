# M1.6-R Review Findings Closure

**Round:** M1.6-R
**Date:** 2026-04-29
**Status:** Review-findings closure only. No blueprint/milestone edits. No compose, production fetch, P5 shadow-run, M2/M3/M4 work, legacy retirement, xfail removal, or `FORBIDDEN_*_FIELDS` extension.

**Supersession note (2026-04-30):** This report is historical M1.6-R
evidence. Its blocker wording was true for M1.6-R only. `block_trade` was
promoted in M1.8; the 8 candidate sources were refined from
`BLOCKED_NO_STAGING` to `BLOCKED_NO_LOCAL_SCHEMA` in M1.9, schema-checked
in M1.11, and promoted in M1.13. M1.14 closed M1 with 0 xfails.

## Scope

Close the 10 Codex review findings raised after M1.6. This round fixes CI/test protection, lineage attribution, public-reader fail-closed behavior, formal source-leak guards, paired v2 timestamps, and stale evidence wording. It does not claim production daily-cycle proof or P5 readiness.

## Closure Table

| finding | status | files changed | verification |
|---|---|---|---|
| F1 — M1 provider-neutrality/v2/formal gate tests untracked | **Fixed** | Staged new gate tests and v2/lineage dbt model dirs in `data-platform` index: `tests/ddl/test_canonical_provider_neutrality.py`, `tests/serving/test_canonical_writer_provider_neutrality.py`, `tests/dbt/test_marts_provider_neutrality.py`, `tests/serving/test_canonical_datasets_v2_cutover.py`, `tests/serving/test_formal_no_source_leak.py`, `tests/cycle/test_current_cycle_inputs_lineage_absent.py`, `src/data_platform/dbt/models/marts_v2/`, `src/data_platform/dbt/models/marts_lineage/`. | `git -C data-platform status --short` shows these as `A`, not `??`. No commit was made. |
| F2 — Composite lineage loses real source runs | **Fixed** | Intermediate models now preserve component source/run metadata: `int_security_master.sql`, `int_price_bars_adjusted.sql`, `int_market_daily_features.sql`, `int_financial_reports_latest.sql`, `int_index_membership.sql`. Lineage marts now encode component-aware `source_interface_id`, `source_run_id`, and max component `raw_loaded_at`. | Full data-platform sweep passed; provider-neutrality dbt test now asserts `mart_lineage_dim_security.sql` references stock_basic, stock_company, namechange, and their component run ids. |
| F3 — Forecast PK contract disagrees with implementation | **Fixed** | `provider_catalog/registry.py` adds `update_flag` to `financial_forecast_event.primary_key` and fields. | `tests/provider_catalog` passed in targeted sweep; full data-platform sweep passed. |
| F4 — v2 stock_basic can read unpublished head | **Fixed** | `serving/reader.py` includes `canonical_v2.stock_basic` in the v2 manifest-pinned mart set. `tests/serving/test_reader.py` adds a fail-closed test for `get_canonical_stock_basic()` under `DP_CANONICAL_USE_V2=1` when the v2 manifest is missing. | Targeted reader tests passed; v2 lane passed. |
| F5 — Nested formal fields bypass data-platform guard | **Fixed** | `serving/formal.py` recursively walks `pa.Schema` struct/list fields and rejects exact forbidden names plus source/provider naming patterns. `frontend-api` sanitizer now uses the same pattern rule. | `tests/serving/test_formal_no_source_leak.py` includes nested and pattern-field cases; frontend-api route tests passed. |
| F6 — V2 lane is manual-only | **Fixed** | `data-platform/.github/workflows/ci.yml` adds `canonical-v2-default-on`, running the v2 lane with `DP_CANONICAL_USE_V2=1`. `canonical-v2-default-on-test-proof-20260428.md` documents CI protection. | Local v2 lane JUnit: 198 tests, 0 failures, 22 skipped/xfail (`176 passed, 5 skipped, 17 xfailed`). |
| F7 — Paired `canonical_loaded_at` is not paired | **Fixed** | `canonical_writer.py` now computes one `paired_canonical_loaded_at` per `load_canonical_v2_marts()` call and injects it into every v2 and lineage prepared load. `test_canonical_writer.py` asserts v2/lineage `canonical_loaded_at` sets match. | Targeted canonical writer tests passed; full data-platform sweep passed. |
| F8 — Stale event-source wording remains | **Fixed** | Updated stale comments/descriptions in DDL, writer, dbt schema headers, tests, and evidence to say `fact_event` covered 7 promoted source interfaces after M1.6; at that point `block_trade` and 8 unstaged candidates remained blocked. This wording is superseded by M1.8/M1.13 promotions. | Stale-string `rg` no longer found the old source-count / pre-M1.6 wording in the edited surfaces. |
| F9 — Formal proof overstates coverage | **Fixed** | `formal-serving-no-source-leak-runtime-proof-20260428.md` now distinguishes exact-key set from pattern rule, documents recursive schema guard, and attributes frontend tests as 4 in `test_no_source_leak.py` plus 6 in `test_cycle_routes.py`. | Frontend-api regression: 10 passed. Data-platform formal tests included in full sweep. |
| F10 — Event/P5 evidence wording under-specified | **Fixed** | `event-timeline-m1-6-promotion-proof-20260429.md` now lists the P5 blocker stack as G1 canonical retirement, G2/M2.6 production daily-cycle proof, G3 same-cycle production consumption, G4 live-PG/downstream bridge closure, plus legacy retirement. It also states 7 covered sources and 9 blocked sources without the stale "10 sources" wording. | Evidence reviewed by `rg`; no production proof/P5 readiness claim added. |

## Commands Run

```sh
cd data-platform && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
  -p no:cacheprovider \
  tests/provider_catalog \
  tests/serving/test_reader.py \
  tests/serving/test_formal_no_source_leak.py \
  tests/serving/test_canonical_writer.py \
  tests/dbt/test_intermediate_models.py \
  tests/dbt/test_marts_models.py \
  tests/dbt/test_marts_provider_neutrality.py \
  tests/serving/test_canonical_datasets_v2_cutover.py -q
```

Result: passed, with only expected skips/xfails.

```sh
cd data-platform && DP_CANONICAL_USE_V2=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
  -p no:cacheprovider tests/serving tests/cycle/test_current_cycle_inputs.py \
  tests/cycle/test_current_cycle_inputs_lineage_absent.py tests/test_assets.py \
  --junitxml=/tmp/project_ult_v2_lane.xml -q --disable-warnings
```

Result: 198 tests, 0 failures, 22 skipped/xfail (`176 passed, 5 skipped, 17 xfailed`).

```sh
cd data-platform && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
  -p no:cacheprovider tests/ddl tests/serving tests/dbt tests/provider_catalog \
  tests/cycle/test_current_cycle_inputs.py tests/cycle/test_current_cycle_inputs_lineage_absent.py \
  tests/integration/test_daily_refresh.py tests/test_assets.py \
  --junitxml=/tmp/project_ult_default_sweep.xml -q --disable-warnings
```

Result: 338 tests, 0 failures, 57 skipped/xfail (`281 passed, 13 skipped, 44 xfailed`).

```sh
cd data-platform && DP_ENFORCE_M1D_PROVIDER_NEUTRALITY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
  -p no:cacheprovider tests/ddl/test_canonical_provider_neutrality.py \
  tests/serving/test_canonical_writer_provider_neutrality.py \
  tests/dbt/test_marts_provider_neutrality.py \
  --junitxml=/tmp/project_ult_override.xml -q --disable-warnings
```

Result: 78 tests, 44 expected failures, 34 passed. This is the legacy-retirement scoreboard under enforcement, not a default CI failure.

```sh
cd frontend-api && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest \
  -p no:cacheprovider tests/test_cycle_routes.py tests/test_no_source_leak.py -q
```

Result: 10 passed.

```sh
git -C data-platform diff --check
git -C frontend-api diff --check
git -C assembly diff --check
```

Result: all clean.

## Historical Remaining Blockers At M1.6-R

- `block_trade` was `BLOCKED_NO_STABLE_KEY` at M1.6-R; superseded by M1.8 promotion.
- 8 event_timeline candidate sources were `BLOCKED_NO_STAGING` at M1.6-R; superseded by M1.9 `BLOCKED_NO_LOCAL_SCHEMA`, M1.11 schema check-in, and M1.13 promotion.
- Controlled Lite-compose v2 proof had not executed at M1.6-R; superseded by M1.10 controlled compose proof.
- Legacy `canonical.*` retirement had not executed at M1.6-R; superseded by M1.12 + M1.14.
- `_M1D_LEGACY_RETIREMENT_XFAIL` remained in place at M1.6-R; superseded by M1.14 removal.
- `FORBIDDEN_SCHEMA_FIELDS` / `FORBIDDEN_PAYLOAD_FIELDS` were not extended at M1.6-R; superseded by M1.12.
- P5 remains blocked on post-M1 gates, especially M2.6 production daily-cycle proof, G3 same-cycle consumption, and G4 live PG/downstream bridge closure.

## Hard-Rule Declarations

- `project_ult_v5_0_1.md` unchanged.
- `ult_milestone.md` unchanged.
- compose / production fetch / P5 shadow-run not started.
- M2 / M3 / M4 not entered.
- API-6 / sidecar / frontend write API / Kafka/Flink/Temporal / news/Polymarket not touched.
- Tushare remains a `provider="tushare"` source adapter only.
- `/Users/fanjie/Desktop/BIG/FrontEnd` not modified.
- Legacy `canonical.*` specs/load specs/dbt marts not deleted.
- No `git init`, no commit, no push.
