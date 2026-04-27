# P1/P2 Production Daily-Cycle Proof - 2026-04-28

## Status

PARTIAL PASS / BLOCKED. This is not a production daily-cycle pass certificate
and not P5 shadow-run readiness.

This 2026-04-28 update advances the state from the 2026-04-27 blocker evidence:

- P3 live GDS closure is now PASS and should no longer be counted as an open
  production daily-cycle blocker.
- Data-platform current-cycle selector and PG wrapper tests are strengthened,
  and the 2026-04-28 bounded runner now proves live Tushare refresh,
  current-cycle selection, PG candidate validation, and PG transaction freeze
  for the scoped symbols.
- Audit-eval retrospective hook now validates full persisted audit/replay
  payload provenance and durable manifest/audit/replay queryability.
- Orchestrator production provider status now reports the remaining blockers
  as configured runtime/provider gaps, not as missing env or missing P3 GDS
  evidence.

## Artifact

- Bounded current-cycle proof artifact:
  `assembly/reports/stabilization/p1-p2-production-daily-cycle-proof-artifacts/20260427T194817Z/production-daily-cycle-proof.json`
- Runtime preflight JSON artifact:
  `assembly/reports/stabilization/p1-p2-production-daily-cycle-proof-artifacts/20260427T194812Z/production-daily-cycle-proof.json`

The 20260427T194817Z JSON is a bounded partial proof. It proves redacted
runtime readiness, live Tushare `trade_cal`/`stock_basic`/`daily` refresh,
current-cycle selection for `CYCLE_20260415`, two accepted Ex-1 candidates,
and PG-backed freeze. It intentionally records no formal snapshot IDs,
manifest row, serving readback, or production Dagster pass. The preflight-only
artifact is supporting evidence and must not be treated as a production
`daily_cycle_job` pass.

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
- orchestrator: `efb5d1e8e7f152af324817135a6f7a96b10ca81c`
  - Production status removes stale `live_gds_zero_skip_proof` blocker.
  - Phase 2 pool failure-rate gate derives from L8 or a persisted metric
    artifact, rejects stale cycle IDs against the Dagster run tag, and keeps
    inline env JSON labeled as a non-production fallback only.

## Runtime Environment Preflight

Command:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/assembly
.venv-py312/bin/python scripts/production_daily_cycle_proof.py \
  --preflight-only \
  --run-current-selection-tests
```

Result:

```text
RUNTIME_PREFLIGHT_PASS /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/p1-p2-production-daily-cycle-proof-artifacts/20260427T194812Z/production-daily-cycle-proof.json
```

Redacted runtime checks:

- PostgreSQL connect: PASS, `SELECT 1` succeeded through the configured DSN;
  DSN value is redacted.
- data-platform current-selection tests: PASS, return code 0 with
  `.......... [100%]`.
- Codex reasoner health: PASS, provider `openai-codex`, model `gpt-5.5`,
  reachable true, quota `ok`.
- Audit DuckDB write/read: PASS, managed audit/replay write and repository
  readback succeeded.
- Env presence: `DP_TUSHARE_TOKEN`, `DP_PG_DSN`, `DATABASE_URL`, Neo4j,
  reasoner, audit, policy, and module factory inputs are set. `OPENAI_API_KEY`
  is missing but is not required for the configured Codex OAuth path.

## Validation

Data-platform:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/assembly
.venv-py312/bin/python scripts/production_daily_cycle_proof.py \
  --run-current-selection-tests \
  --drop-isolated-pg

result:
PARTIAL_PASS_BLOCKED /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/p1-p2-production-daily-cycle-proof-artifacts/20260427T194817Z/production-daily-cycle-proof.json
exit code: 2, expected for a bounded partial/blocker proof
```

Bounded data-platform proof details:

- Live Tushare mode: `mock=false`.
- Selected inputs: `trade_cal`, `stock_basic`, `daily`.
- Selected cycle: `CYCLE_20260415`, trade date `2026-04-15`.
- Symbols: `600519.SH`, `000001.SZ`.
- Raw row counts: `trade_cal=1`, `stock_basic=5510`, `daily=5494`.
- Candidate validation: `accepted=2`, `rejected=0`.
- Candidate freeze: `candidate_count=2`, frozen IDs `[1, 2]`, status `phase0`.
- Isolated PostgreSQL database cleanup: PASS.

Graph-engine live P3 closure:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/graph-engine
env PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
  NEO4J_URI=bolt://localhost:17687 \
  NEO4J_USER=neo4j \
  NEO4J_PASSWORD=<redacted> \
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

Orchestrator focused production provider and Phase 2 pool gate checks:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/orchestrator
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest -q \
  tests/integration/test_production_daily_cycle_provider.py \
  tests/integration/test_phase2_pool_failure_gate.py \
  tests/checks/test_phase2_pool_gate.py

result:
26 passed
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

Bounded proof runner:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/assembly
.venv-py312/bin/python -m py_compile scripts/production_daily_cycle_proof.py
.venv-py312/bin/python scripts/production_daily_cycle_proof.py --help
```

result:

```text
py_compile passed
--help printed the bounded runner options
```

## Current Blockers

| Priority | Blocker | Evidence |
| --- | --- | --- |
| P1 | Production `daily_cycle_job` still needs configured graph Phase 0 status runtime and graph Phase 1 runtime resources. The default providers intentionally fail closed. | `orchestrator/src/orchestrator_adapters/production_daily_cycle.py` |
| P1 | Production Phase 2 pool failure-rate can now derive from current-cycle L8 output or a persisted metric artifact, with stale-cycle and inline-artifact regressions covered, but no full production Dagster run has exercised that handoff yet. | `orchestrator/src/orchestrator_adapters/production_daily_cycle.py`; `orchestrator/src/orchestrator/checks/phase2.py` |
| P1 | Full `daily_cycle_job.execute_in_process(tags={"cycle_id": selector.cycle_id})` has not run with real Phase 0/1/2/3/audit resources. Provider wiring and full Dagster proof remain pending unless that proof actually runs and passes. | JSON artifact |
| P2 | Audit hook hardening is complete, but no production Dagster run has yet produced and consumed the final audit hook artifact. | `audit-eval/src/audit_eval/retro/hook.py` |
| P3 | The 12 missing Tushare APIs remain an authoritative target-list planning gap, not an implementation task. | `p1-tushare-40-api-target-list-20260428.md` |

## Findings

- P0: none.
- P1: production daily-cycle remains blocked by configured runtime/provider
  gaps and missing full Dagster proof, not by missing env or P3 GDS.
- P2: audit hook production artifact remains unproven in a full Dagster run.
- P3: 40-API target-list still requires data/product owner naming for the
  remaining 12 APIs.
