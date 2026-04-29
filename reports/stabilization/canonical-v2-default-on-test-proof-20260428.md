# Canonical v2 Default-On Test Lane Proof

**Round:** M1.5-3
**Date:** 2026-04-28
**Status:** TEST-LEVEL PROOF ONLY. NOT a production daily-cycle proof. NOT a Lite-compose run. NO live `dbt run`. NO production fetch. NO P5 shadow-run. M1.6-R adds a GitHub Actions CI lane for this command shape.

## Purpose

Show that the data-platform's core reader / cycle / formal-serving paths work correctly under `DP_CANONICAL_USE_V2=1` at the test level — i.e., they do NOT silently fall back to legacy `canonical.*` mappings when the v2 flag is set. This is one precondition for legacy retirement (per [m1-legacy-canonical-retirement-readiness-20260428.md](assembly/reports/stabilization/m1-legacy-canonical-retirement-readiness-20260428.md) §5 step 2), but it is NOT itself a production proof.

## Exact command

```sh
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
DP_CANONICAL_USE_V2=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
    -p no:cacheprovider \
    tests/serving \
    tests/cycle/test_current_cycle_inputs.py \
    tests/cycle/test_current_cycle_inputs_lineage_absent.py \
    tests/test_assets.py -q
```

## Result

```
176 passed, 5 skipped, 17 xfailed
```

The earlier default-mode regression baseline from M1.5 was also green, but its
pre-M1.6-R count is no longer repeated here because the CI-protected v2 lane
above is the current evidence value.

The v2 lane is green by construction. The 17 xfails are the `_M1D_LEGACY_RETIREMENT_XFAIL`-decorated provider-neutrality scoreboard tests.

## CI protection

[data-platform/.github/workflows/ci.yml](data-platform/.github/workflows/ci.yml) now includes `canonical-v2-default-on`, a dedicated GitHub Actions job that runs the same v2 lane with `DP_CANONICAL_USE_V2=1`. This closes the prior gap where v2 default-on behavior was only a local/report command and not PR-protected.

## Failures fixed in this round

The first v2-lane run surfaced 7 fixture-level failures. None were production-code regressions; all were test-level legacy-only assumptions. Fixes (test-only, no production code changed):

| # | Test | Root cause | Fix |
|---|------|-----------|-----|
| 1 | [test_canonical_datasets.py::test_canonical_dataset_ids_map_explicitly_to_iceberg_tables](data-platform/tests/serving/test_canonical_datasets.py) | Asserted legacy `canonical.dim_security` literal; under v2 flag `canonical_table_identifier_for_dataset` returns `canonical_v2.dim_security`. | Added `monkeypatch.delenv(USE_CANONICAL_V2_ENV_VAR, raising=False)` and a docstring noting the v2-flag-on equivalent is parametrized in `test_canonical_datasets_v2_cutover.py`. |
| 2 | [test_reader.py::test_read_canonical_dataset_uses_explicit_mapping](data-platform/tests/serving/test_reader.py) | Mocked `reader.read_canonical` directly, but under v2 flag `read_canonical_dataset` resolves the v2 identifier via `_read_table_expression` (different code path that calls `get_settings()` and `_canonical_mart_snapshot_entry`); without further monkeypatches the test triggers a Pydantic Settings validation error. | Added `monkeypatch.delenv(USE_CANONICAL_V2_ENV_VAR, raising=False)` and a docstring pinning the test to the legacy code path. |
| 3 | [test_current_cycle_inputs.py::test_current_cycle_inputs_loads_provider_neutral_rows](data-platform/tests/cycle/test_current_cycle_inputs.py) | `_CanonicalReaderFixture.datasets["security_master"]` and `["price_bar"]` provided only `ts_code`; production code under v2 flag requested `security_id` via `canonical_alias_column_for_dataset`. | Extended fixture to provide BOTH `ts_code` AND `security_id` columns (same values); the fixture is now flag-agnostic. |
| 4 | [test_current_cycle_inputs.py::test_current_cycle_inputs_output_does_not_leak_source_fields](data-platform/tests/cycle/test_current_cycle_inputs.py) | Same fixture issue as #3. | Same fix (fixture now provides both columns). |
| 5 | [test_current_cycle_inputs.py::test_current_cycle_inputs_can_read_explicit_snapshot_set](data-platform/tests/cycle/test_current_cycle_inputs.py) | `as_of_snapshot` dict keyed by legacy `canonical.dim_security` table identifier; under v2 flag the production code looks up `canonical_v2.dim_security` and the legacy key is silently bypassed. This is intentional v2 routing, not a regression. | Added `monkeypatch.delenv("DP_CANONICAL_USE_V2", raising=False)` and a docstring; the v2 form is exercised via `test_canonical_datasets_v2_cutover.py` and the `dataset_id`-keyed form (which works under both flag states) is exercised by the upstream `test_current_cycle_inputs_loads_provider_neutral_rows`. |
| 6 | [test_current_cycle_inputs.py::test_current_cycle_inputs_fails_closed_when_entity_row_missing](data-platform/tests/cycle/test_current_cycle_inputs.py) | Same fixture issue as #3 (fixture's `read_canonical_dataset` mock failed `pa.Table.select(["security_id", ...])`). | Same fix as #3. |
| 7 | [test_current_cycle_inputs.py::test_current_cycle_inputs_fails_closed_when_candidate_price_missing](data-platform/tests/cycle/test_current_cycle_inputs.py) | Same fixture issue, but the test inline-replaces `fixture.datasets["price_bar"]` with a fresh table that only carries `ts_code`. | Updated the inline replacement to provide BOTH `ts_code` AND `security_id` columns. |

## What this proves

- The 9 canonical mart datasets resolve to `canonical_v2.<table>` identifiers under flag (parametrized in [test_canonical_datasets_v2_cutover.py::test_v2_flag_routes_every_dataset_to_canonical_v2](data-platform/tests/serving/test_canonical_datasets_v2_cutover.py)).
- All 10 alias columns flip to canonical names under flag (`security_id` / `index_id` / `entity_id`) and stay legacy (`ts_code` / `index_code`) without flag.
- `read_canonical_dataset("event_timeline")` under flag reads the `canonical_v2/_mart_snapshot_set.json` v2 manifest and the v2 metadata path — NOT the legacy `canonical/_mart_snapshot_set.json` (locked by [test_reader.py::test_read_canonical_dataset_routes_event_timeline_to_v2_under_flag](data-platform/tests/serving/test_reader.py)).
- `current_cycle_inputs` end-to-end works under both flag states using the dataset_id-form snapshot key (the recommended invariant form).
- Formal serving runtime guard (M1-G4) enforces the 14-field exact-key set plus source/provider naming-pattern checks, including nested schema fields.

## What this does NOT prove (do NOT misclaim)

- This is **NOT** a production daily-cycle proof. No `dbt run` was executed against the new v2 marts. No live Iceberg catalog write. No live formal table read. M2.1 owns the runtime preflight that delivers those.
- This is **NOT** a Lite-compose v2 cycle proof. No compose was started. No PostgreSQL / Neo4j / Dagster daemon launched. The controlled production-like proof referenced in [m1-legacy-canonical-retirement-readiness-20260428.md](assembly/reports/stabilization/m1-legacy-canonical-retirement-readiness-20260428.md) §5 step 2 / §7 Phase A step 4 is still pending.
- This is **NOT** evidence that legacy `canonical.*` can be retired. Legacy specs / load specs / dbt marts remain intact; xfail decorator remains; FORBIDDEN_*_FIELDS remains scoped to `submitted_at`/`ingest_seq`.
- Test fixtures providing BOTH `ts_code` AND `security_id` columns are a test-level convenience for flag-agnostic fixture reuse. In production, only one column will be in the canonical_v2 mart (`security_id`); the legacy `canonical.<mart>` retains `ts_code`. Production routing picks the correct column at the dataset boundary.

## Remaining blockers (M1.5 → M1.6 / M2 transition)

| blocker | owner | reference |
|---|---|---|
| Controlled Lite-compose v2 cycle (dbt run + load_canonical_v2_marts + read smoke) | M1.5 → M2.1 transition | retirement-readiness §5 step 2 |
| `block_trade` int_event_timeline UNION branch + stable key rule | M1.7+ | event-timeline-m1-6-source-promotion-audit §block_trade |
| 8 candidate event_timeline sources (pledge_*, repurchase, stk_holdertrade, limit_list_*, hm_detail, stk_surv) | M1.7+ / staging-then-promotion track | event-timeline-m1-6-source-promotion-audit §candidate sources |
| Direct `read_canonical("<bare_mart>")` callers in src code | none found in M1.5-1 audit | reader-cutover-audit §"Verdict" |
| Legacy `CANONICAL_MART_LOAD_SPECS` / `CANONICAL_MART_TABLE_SPECS` deletion | retirement Phase B | retirement-readiness §7 |
| `FORBIDDEN_SCHEMA_FIELDS` / `FORBIDDEN_PAYLOAD_FIELDS` extension to lineage fields | retirement Phase B (after legacy specs deleted) | retirement-readiness §4 |
| `_M1D_LEGACY_RETIREMENT_XFAIL` removal | retirement Phase B | retirement-readiness §7 |
| Entity-store migration (`canonical.canonical_entity` / `canonical.entity_alias` → v2) | entity-registry owner | reader-cutover-audit §"INTENTIONAL_ENTITY_STORE_READ" |

## Status declarations

- This is a **TEST-LEVEL PROOF ONLY**. NOT production daily-cycle proof.
- `project_ult_v5_0_1.md` and `ult_milestone.md` UNCHANGED.
- compose / production fetch / P5 shadow-run NOT started.
- API-6 / sidecar / frontend write API / Kafka/Flink/Temporal / news/Polymarket NOT touched.
- Tushare remains a `provider="tushare"` source adapter ONLY.
- Legacy `canonical.*` specs/load specs/dbt marts NOT deleted.
- `_M1D_LEGACY_RETIREMENT_XFAIL` NOT removed.
- `FORBIDDEN_SCHEMA_FIELDS` / `FORBIDDEN_PAYLOAD_FIELDS` NOT extended.
- `/Users/fanjie/Desktop/BIG/FrontEnd` NOT modified.
- Pre-existing dirty files NOT reverted.
- No `git init`. No commits. No push.
