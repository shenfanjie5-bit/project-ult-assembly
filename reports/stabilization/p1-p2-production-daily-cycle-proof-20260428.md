# P1/P2 Production Daily-Cycle Proof - 2026-04-28

## Status

PARTIAL PASS / BLOCKED. This is not a production daily-cycle pass certificate
and not P5 shadow-run readiness.

This 2026-04-28 update advances the state from the 2026-04-27 blocker evidence:

- P3 live GDS closure is now PASS and should no longer be counted as an open
  production daily-cycle blocker.
- Data-platform current-cycle selector and PG wrapper tests are strengthened,
  but live Tushare and live PG freeze proof are blocked in this shell because
  `DP_TUSHARE_TOKEN`, `DP_PG_DSN`, and `DATABASE_URL` are missing.
- Audit-eval retrospective hook now validates full persisted audit/replay
  payload provenance and durable manifest/audit/replay queryability.
- Orchestrator production provider status now reports the remaining blockers
  as configured runtime/provider gaps, not as missing P3 GDS evidence.

## Artifact

- JSON artifact:
  `assembly/reports/stabilization/p1-p2-production-daily-cycle-proof-artifacts/20260427T175306Z/production-daily-cycle-proof.json`

The JSON intentionally records `cycle_id`, trade date, frozen candidate IDs,
formal snapshot IDs, manifest row, and serving readback as null/not-run for the
production Dagster proof. Archived selector evidence is recorded separately and
must not be treated as a production `daily_cycle_job` pass.

## Commits Reviewed

- data-platform: `912d099098122840c5c92d78f60cfd475aa6c0eb`
  - Adds PG-backed current-cycle wrapper tests.
  - Archived selector probe selected `CYCLE_20260331` from ingested artifacts.
- graph-engine: `fc4e083e1328333f0320fa7c0afa96d0b0dd6b37`
  - P3 live GDS zero-skip proof.
  - Candidate deltas flow through promotion, GDS propagation, graph/impact
    snapshots, Layer A artifact, `ArtifactCanonicalReader`, and cold reload.
- audit-eval: `a038ce172da711951500296f2c39862da1d53b6b`
  - Retrospective hook validates full persisted replay/audit payload provenance
    and realized outcome provenance.
- orchestrator: `08898f3e3e7fd93fcf06dd5f661b4a10de4155fc`
  - Production status removes stale `live_gds_zero_skip_proof` blocker.
  - Production status keeps current-cycle/PG, graph runtime, reasoner runtime,
    pool failure-rate, audit hook, and full Dagster run blockers.

## Environment Probe

Command:

```text
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python - <<'PY'
import os
for k in [
    'DP_TUSHARE_TOKEN', 'DP_PG_DSN', 'DATABASE_URL',
    'NEO4J_URI', 'NEO4J_USER', 'NEO4J_PASSWORD',
    'P2_REASONER_PROVIDER', 'P2_REASONER_MODEL', 'OPENAI_API_KEY',
    'AUDIT_EVAL_DUCKDB_PATH', 'ORCHESTRATOR_POLICY_PATH',
    'ORCHESTRATOR_MODULE_FACTORIES',
]:
    print(f'{k}=' + ('present' if os.environ.get(k) else 'missing'))
PY
```

Result:

```text
DP_TUSHARE_TOKEN=missing
DP_PG_DSN=missing
DATABASE_URL=missing
NEO4J_URI=missing
NEO4J_USER=missing
NEO4J_PASSWORD=missing
P2_REASONER_PROVIDER=missing
P2_REASONER_MODEL=missing
OPENAI_API_KEY=missing
AUDIT_EVAL_DUCKDB_PATH=missing
ORCHESTRATOR_POLICY_PATH=missing
ORCHESTRATOR_MODULE_FACTORIES=missing
```

## Validation

Data-platform:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
.venv/bin/python -m pytest tests/cycle/test_current_selection.py -q -rs

result:
8 passed, 2 skipped
skipped because DATABASE_URL / DP_PG_DSN are missing
```

Graph-engine live P3 closure:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/graph-engine
env PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
  NEO4J_URI=bolt://localhost:17687 \
  NEO4J_USER=neo4j \
  NEO4J_PASSWORD=p3-live-closure-pass \
  NEO4J_DATABASE=neo4j \
  /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python \
  -m pytest -q -rs \
  tests/integration/test_promotion_sync.py \
  tests/integration/test_full_propagation.py \
  tests/integration/test_propagation_snapshot.py \
  tests/integration/test_reload.py \
  tests/integration/test_live_closure.py

result:
6 passed, 0 skipped
```

Audit-eval:

```text
pytest tests/test_retro_hook.py
result: 15 passed

pytest
result: 423 passed, 1 skipped, 2 warnings
```

Orchestrator focused production provider checks:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/orchestrator
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest -q \
  tests/integration/test_production_daily_cycle_provider.py

result:
6 passed, 1 skipped
```

Orchestrator broader focused integration set:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/orchestrator
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest -q -rs \
  tests/integration/test_production_daily_cycle_provider.py \
  tests/integration/test_daily_cycle_four_phase.py \
  tests/integration/test_phase2_main_core_wiring.py \
  tests/integration/test_phase3_publish_wiring.py \
  tests/integration/test_p2_dry_run_handoff.py

result:
17 passed, 17 skipped
skipped tests require dbt CLI in the execution environment
```

Orchestrator lint:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/orchestrator
ruff check src/orchestrator_adapters/production_daily_cycle.py \
  tests/integration/test_production_daily_cycle_provider.py

result:
All checks passed
```

## Current Blockers

| Priority | Blocker | Evidence |
| --- | --- | --- |
| P1 | Live current-cycle Tushare selection and PG freeze cannot be rerun in this shell because `DP_TUSHARE_TOKEN`, `DP_PG_DSN`, and `DATABASE_URL` are missing. | `p1-tushare-40-api-target-list-20260428.md` |
| P1 | Production `daily_cycle_job` still needs configured graph Phase 0 status runtime and graph Phase 1 runtime resources. The default providers intentionally fail closed. | `orchestrator/src/orchestrator_adapters/production_daily_cycle.py` |
| P1 | Production `daily_cycle_job` still needs configured Codex/reasoner-runtime provider profile in the execution shell. | environment probe above |
| P1 | Production Phase 2 pool failure-rate event is still env-backed and must be derived from the current-cycle P2 outputs before this can be a production pass. | `orchestrator/src/orchestrator_adapters/production_daily_cycle.py` |
| P1 | Full `daily_cycle_job.execute_in_process(tags={"cycle_id": selector.cycle_id})` has not run with real Phase 0/1/2/3/audit resources. | JSON artifact |
| P2 | Audit hook hardening is complete, but no production Dagster run has yet produced and consumed the final audit hook artifact. | `audit-eval/src/audit_eval/retro/hook.py` |
| P3 | The 12 missing Tushare APIs remain an authoritative target-list planning gap, not an implementation task. | `p1-tushare-40-api-target-list-20260428.md` |

## Findings

- P0: none.
- P1: production daily-cycle remains blocked by configured runtime/provider
  gaps and missing live env, not by P3 GDS.
- P2: audit hook production artifact remains unproven in a full Dagster run.
- P3: 40-API target-list still requires data/product owner naming for the
  remaining 12 APIs.
