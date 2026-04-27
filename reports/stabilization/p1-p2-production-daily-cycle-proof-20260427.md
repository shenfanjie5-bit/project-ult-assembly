# P1/P2 Production Daily-Cycle Proof - 2026-04-27

## Status

Blocked. This file is intentionally not a pass certificate.

The current repos can prove P1 data-platform hardening and P2 durable
real-data Codex closure, but they still cannot honestly prove a production
Dagster `daily_cycle_job` execution with real providers across Phase 0-3.

Update after commit `0ebe82a975c2e33239e5d0fdda458a038ca437ea`: orchestrator
now has an env-addressable
`orchestrator_adapters.production_daily_cycle:production_daily_cycle_provider`
entrypoint for the real supported P2/Phase 3/audit-persistence slice. It
fails closed and records the missing production Phase 0, Phase 1, and
audit-hook surfaces instead of synthesizing fake assets.

## What Passed

Orchestrator baseline command:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/orchestrator
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/orchestrator/src:/Users/fanjie/Desktop/Cowork/project-ult/main-core/src:/Users/fanjie/Desktop/Cowork/project-ult/reasoner-runtime:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src:/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src:/Users/fanjie/Desktop/Cowork/project-ult/audit-eval/src \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest -q -rs \
  tests/integration/test_daily_cycle_four_phase.py \
  tests/integration/test_phase2_main_core_wiring.py \
  tests/integration/test_phase3_publish_wiring.py \
  tests/integration/test_p2_dry_run_handoff.py
```

Result: `23 passed`.

Data-platform manifest/formal baseline command:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
PYTHONPATH=src \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest \
  tests/cycle/test_freeze_cycle_candidates.py \
  tests/cycle/test_publish_manifest.py \
  tests/serving/test_formal.py \
  tests/serving/test_formal_manifest_consistency.py -q -rs
```

Result: passed with PostgreSQL-dependent cases skipped when
`DATABASE_URL`/`DP_PG_DSN` is not exported in the test shell.

## Existing Real-Data Evidence

The P2 durable real-data Codex closure remains valid evidence for:

- Tushare current-cycle input: `CYCLE_20260415`, trade date `2026-04-15`,
  symbols `600519.SH`, `000001.SZ`.
- Candidate freeze: 2 candidates accepted and frozen.
- Real `openai-codex` reasoner-runtime calls.
- Durable audit/replay IDs persisted and queryable.
- Real formal writer + `cycle_publish_manifest`.
- Manifest-bound formal serving readback.
- Negative gates for no LLM, audit persistence failure, and forbidden
  smoke/fixture/historical provenance.

Evidence:

- `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/p2-durable-real-data-codex-dry-run-closure-20260427.md`
- `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/p2-durable-real-data-codex-dry-run-artifacts/20260427T113854Z/p2-durable-real-data-codex-dry-run.json`

## Blockers

| Priority | Blocker | Evidence |
| --- | --- | --- |
| P0 | Full production `daily_cycle_job` remains blocked because real Phase 0 data-platform candidate freeze/readiness assets, real Phase 1 graph promotion/snapshot assets, and real audit-eval retrospective hook assets are not yet checked in. | `/Users/fanjie/Desktop/Cowork/project-ult/orchestrator/src/orchestrator_adapters/production_daily_cycle.py` |
| P0 | The P2 durable real-data closure executes `daily_cycle_job`, but it injects fake Phase 0 and fake Phase 1 providers. It must not be labeled full production daily-cycle proof. | `/Users/fanjie/Desktop/Cowork/project-ult/assembly/scripts/p2_durable_real_data_codex_dry_run.py` |
| P1 | Production current-cycle binding now requires Dagster run tag `cycle_id`; a fixed `CYCLE_20260415` fallback is rejected for the production provider slice, but latest-cycle selection from Tushare `trade_cal` still needs the full production runner proof. | `/Users/fanjie/Desktop/Cowork/project-ult/orchestrator/src/orchestrator_adapters/p2_dry_run.py` |
| P1 | P3 graph is improved but not fully closed: GDS is enabled in assembly and artifact-backed cold reload exists, but the graph-engine live suite still must pass against the GDS-enabled project Neo4j profile with zero GDS skips. | `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/p3-graph-live-closure-20260427.md` |
| P1 | Default test shell lacks `DATABASE_URL`/`DP_PG_DSN`, so PostgreSQL-dependent manifest/formal tests skip outside the temp-DB closure runner. | Data-platform command above |

## Non-Claims

- This is not P5 shadow-run readiness.
- This is not a production daily-cycle pass.
- This does not update compatibility matrix or registry verified rows.
- Existing P2 closure may be reused as current-cycle L1-L8 evidence, but it
  cannot replace production Phase 0/1 graph readiness or a production
  `orchestrator.definitions:defs` run with real module factories.

## Next Required Backend Work

1. Run graph-engine P3 live tests against the GDS-enabled project Neo4j
   profile and require zero GDS skips.
2. Add real production module factories/assets for data-platform Phase 0,
   graph-engine Phase 1, and audit-eval retrospective hook.
3. Re-run a bounded current-cycle `daily_cycle_job` through
   `orchestrator.definitions:defs` with those factories, then write the final
   proof artifact with cycle ID, dates, symbols, snapshot IDs, audit/replay
   IDs, and negative gates.
