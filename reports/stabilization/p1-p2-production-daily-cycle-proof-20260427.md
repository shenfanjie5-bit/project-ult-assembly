# P1/P2 Production Daily-Cycle Proof - 2026-04-27

## Status

Blocked. This file is intentionally not a pass certificate.

The current repos can prove P1 data-platform hardening and P2 durable
real-data Codex closure, but they still cannot honestly prove a production
Dagster `daily_cycle_job` execution with real providers across Phase 0-3.

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
| P0 | The real production `orchestrator.definitions:defs` path depends on `ORCHESTRATOR_MODULE_FACTORIES`, but no checked-in real provider factory set proves production Phase 0-3 end-to-end on the current-cycle Tushare data. | `/Users/fanjie/Desktop/Cowork/project-ult/orchestrator/src/orchestrator/definitions.py` |
| P0 | The P2 durable real-data closure executes `daily_cycle_job`, but it injects fake Phase 0 and fake Phase 1 providers. It must not be labeled full production daily-cycle proof. | `/Users/fanjie/Desktop/Cowork/project-ult/assembly/scripts/p2_durable_real_data_codex_dry_run.py` |
| P1 | P3 graph functional slice is not closed: graph delta wire-shape normalization, post-promotion status refresh, and graph snapshot to cold-reload proof still need graph-engine work. | Independent P3 review, 2026-04-27 |
| P1 | Default test shell lacks `DATABASE_URL`/`DP_PG_DSN`, so PostgreSQL-dependent manifest/formal tests skip outside the temp-DB closure runner. | Data-platform command above |

## Non-Claims

- This is not P5 shadow-run readiness.
- This is not a production daily-cycle pass.
- This does not update compatibility matrix or registry verified rows.
- Existing P2 closure may be reused as current-cycle L1-L8 evidence, but it
  cannot replace production Phase 0/1 graph readiness or a production
  `orchestrator.definitions:defs` run with real module factories.

## Next Required Backend Work

1. Close P3 graph functional slice first: Ex-3 delta normalization,
   promotion status refresh, graph snapshot persistence, and cold reload from
   persisted snapshot evidence.
2. Add or identify real production module factories for data-platform,
   graph-engine, main-core/P2, Phase 3 publish, and audit-eval.
3. Re-run a bounded current-cycle `daily_cycle_job` through
   `orchestrator.definitions:defs` with those factories, then write the final
   proof artifact with cycle ID, dates, symbols, snapshot IDs, audit/replay
   IDs, and negative gates.

