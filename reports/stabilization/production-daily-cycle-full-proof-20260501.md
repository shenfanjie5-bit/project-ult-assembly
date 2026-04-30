# M2.6 Full Production Daily-Cycle Proof Attempt - 2026-05-01

## Verdict

**BLOCKED. M2.6 is not passed.**

The May 1 repair cleared the earlier Phase 0 `graph_status` PostgreSQL DSN
blocker and added proof artifacts for graph-status initialization plus Dagster
event/materialization capture. The rerun reached Dagster, passed the Phase 0
`graph_status` path, and then failed closed at Phase 1 `graph_promotion`.

Current blocker:

- `graph_promotion` failed because the production Phase 1 runtime bundle is not
  configured.
- The fail-closed message requires real `candidate_reader`, `canonical_writer`,
  Neo4j client/status, regime reader, and formal artifact snapshot writer
  resources.
- Only 4 artifact-backed materializations were recorded, not the required 15.

This is not a Codex quota blocker. The reasoner health probe was reachable and
reported `quota_status: ok` during both preflight and full proof.

## v5.0.1 Alignment

`project_ult_v5_0_1.md` remains unchanged and authoritative.

This attempt stayed inside the Lite P1-P5 path:

- no Kafka, Flink, Temporal, Milvus, Grafana, Superset, or Feast introduced;
- Layer A/Iceberg remains canonical truth;
- Neo4j remains a hot mirror and status target, not truth;
- Phase 0 validates graph status and does not write graph deltas;
- Phase 1 graph write-back remains the next blocked stage;
- P5/shadow-run did not start.

## Branch And Head Snapshot

| Repo | Branch | Head Used / Repair State | Status |
|---|---|---:|---|
| `data-platform` | `m2-6f1-iceberg-canonical-graph-writer-v2` | `8374504` | clean |
| `main-core` | `m2-3a-2-regime-reader` | `3def30a` | clean |
| `graph-engine` | `m2-6f1-real-canonical-writer` | `2eb9e11` | DSN repair state used by the proof run |
| `orchestrator` | `m2-3a-2-phase1-wiring` | `0ccae67` | clean |
| `audit-eval` | `m2-5-live-pg-roundtrip` | `a7d05b7` | clean |
| `reasoner-runtime` | `main` | `025db5b` | clean |
| `assembly` | `m2-baseline-2026-04-29` | this evidence commit | proof runner/evidence artifacts committed in this round |

## Commands

Graph-engine DSN compatibility test and targeted provider suite:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/graph-engine
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=.:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
.venv/bin/python -m pytest -p no:cacheprovider \
  tests/unit/test_phase0_status_provider.py \
  tests/unit/test_phase1_from_env.py \
  tests/unit/test_phase1_provider.py \
  tests/unit/test_postgresql_status_store.py -q
```

Result: passed (`35 passed, 1 skipped`).

Assembly proof-runner unit tests:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/assembly
PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python -m pytest \
  -p no:cacheprovider tests/scripts/test_production_daily_cycle_proof.py -q
```

Result: `3 passed`.

Runtime preflight:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/assembly
PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python \
  scripts/production_daily_cycle_proof.py \
  --preflight-only \
  --run-current-selection-tests
```

Result: `RUNTIME_PREFLIGHT_PASS`.

Full proof rerun:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/assembly
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python \
  scripts/production_daily_cycle_proof.py \
  --run-dagster \
  --run-current-selection-tests
```

Result: `PARTIAL_PASS_BLOCKED`.

## Artifacts

Preflight artifact root:

```text
assembly/reports/stabilization/p1-p2-production-daily-cycle-proof-artifacts/20260430T195759Z/
```

Full proof artifact root:

```text
assembly/reports/stabilization/p1-p2-production-daily-cycle-proof-artifacts/20260430T200916Z/
```

Key full-proof artifacts:

| Artifact | Purpose |
|---|---|
| `production-daily-cycle-proof.json` | top-level proof report, verdict, blockers, file manifest |
| `graph-status-initialization.json` | proof-only isolated DB `neo4j_graph_status` bootstrap and readback |
| `dagster-execution-evidence.json` | Dagster run id, events, materializations, failure step |
| `daily-refresh.json` | data-platform daily refresh evidence |
| `data-platform-current-selection-tests.stdout.txt` | current-selection focused test stdout |
| `orchestrator-dbt-compile.stdout.txt` | orchestrator dbt stub compile stdout |

Full proof run id:

```text
e33b8861-7b32-4b86-86c4-e2b15bcbf39c
```

## Phase Status

| Area | Status | Artifact-backed evidence |
|---|---|---|
| Runtime preflight | PASS | `20260430T195759Z/production-daily-cycle-proof.json` |
| Reasoner health/quota | PASS | `quota_status: ok` in preflight and full proof JSON |
| Data-platform refresh/current selection | PASS | `20260430T200916Z/daily-refresh.json`; current-selection stdout |
| Isolated PG bootstrap | PASS | `postgres_bootstrap` in `production-daily-cycle-proof.json` |
| Graph status initialization | PASS | `graph-status-initialization.json`; ready row readback, `phase0_graph_delta_writes: 0` |
| Phase 0 candidate freeze | PASS | Dagster materialization event for `candidate_freeze` |
| Phase 0 dbt heartbeat | PASS | Dagster materialization event for `heartbeat` |
| Phase 0 readiness ping | PASS | Dagster materialization event for `phase0_readiness_ping` |
| Phase 0 graph status | PASS | Dagster materialization event for `graph_status`; asset check `neo4j_graph_consistency_check` has `passed: true` |
| Phase 1 graph promotion/write-back | BLOCKED | failure step `graph_promotion` in `dagster-execution-evidence.json` |
| Phase 1 graph snapshot | NOT REACHED | dependency failure after `graph_promotion` |
| Phase 2 reasoner L1-L8 | NOT REACHED | dependency failure after `graph_promotion` |
| Phase 3 formal outputs/publish manifest | NOT REACHED | dependency failure after upstream graph/Phase 2 steps |
| Audit/replay/retrospective hook | NOT REACHED | dependency failure after publish manifest |

Dagster event/materialization evidence:

```text
event_count: 68
materialized_asset_count: 4
selected_asset_count: 0
selected_materializations_complete: false
unique_materialized_asset_keys:
  - candidate_freeze
  - graph_status
  - heartbeat
  - phase0_readiness_ping
failure_step: graph_promotion
15-asset claim supported: false
artifact_backed_pass_claim: false
```

## Blocker Classification

Primary blocker class: **Phase 1 graph promotion runtime dependencies**.

The prior blocker is closed for this proof path:

- `graph-engine` now normalizes `postgresql+psycopg://...` to
  `postgresql://...` before calling `psycopg.connect(...)`.
- The assembly proof runner seeds and verifies a proof-only ready
  `neo4j_graph_status` row in the isolated PostgreSQL database.
- The Dagster rerun reached and passed the `graph_status` asset and graph
  consistency check.

The active failure is later:

```text
RuntimeError: Graph Phase 1 runtime dependencies are not configured; provide
real candidate_reader, canonical_writer, Neo4j client/status, regime_reader,
and formal artifact snapshot writer resources.
```

Current structured blocker list:

```text
full production daily_cycle_job Dagster proof has not passed
Dagster failure step: graph_promotion
production provider status is blocked
production provider runtime pending: configured_graph_phase1_runtime
```

Recommended next repair round:

1. Configure the production `graph_phase1_runtime` bundle for this proof path:
   candidate reader, canonical writer, Neo4j client/status, regime reader, and
   formal artifact snapshot writer.
2. Keep Phase 0 graph-status seeding proof-only for isolated proof databases;
   do not treat it as production graph delta writing.
3. Rerun the same full proof command and require
   `dagster-execution-evidence.json` to support the 15-materialization claim.
4. Do not claim M2.6 pass until `daily_cycle_job.execute_in_process(...)`
   succeeds and Phase 0-3 plus audit/replay/retrospective hook evidence are
   captured.

## Explicit Non-Claims

- This does not pass M2.6.
- This does not start or pass P5.
- This does not prove M3.3 production same-cycle graph snapshot consumption.
- This does not prove P4/M4 bridge readiness.
- This does not change `project_ult_v5_0_1.md`.
- This does not introduce Full-stack components outside Lite mode.
