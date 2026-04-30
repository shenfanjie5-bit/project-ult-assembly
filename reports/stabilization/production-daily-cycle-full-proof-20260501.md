# M2.6 Full Production Daily-Cycle Proof Attempt - 2026-05-01

## Verdict

**BLOCKED. M2.6 is not passed.**

The May 1 repair moved the proof past the previous Phase 1
`graph_promotion` blocker. The latest full Dagster run materialized
`graph_promotion`, proving the proof path now reaches the real Phase 1
write-back surface. The run then failed closed at `graph_snapshot` because the
configured Neo4j instance does not expose the GDS procedure used by graph
propagation:

```text
RuntimeError: GDS plugin not available
Neo.ClientError.Procedure.ProcedureNotFound: gds.graph.exists
```

Current blocker:

- `graph_snapshot` failed because Neo4j GDS is unavailable in the local proof
  graph runtime.
- Only 5 artifact-backed materializations were recorded, not the required full
  daily-cycle materialization set.
- Phase 2, Phase 3, audit/replay, and retrospective hook were not reached.

This is not a Codex quota blocker. The reasoner health probe was reachable and
reported `quota_status: ok` during the bounded proof.

## v5.0.1 Alignment

`project_ult_v5_0_1.md` remains unchanged and authoritative.

This attempt stayed inside the Lite P1-P5 path:

- no Kafka, Flink, Temporal, Milvus, Grafana, Superset, or Feast introduced;
- Layer A/Iceberg remains canonical truth;
- Neo4j remains a hot mirror and status/propagation target, not truth;
- Phase 0 validates graph status and does not write graph deltas;
- Phase 1 graph promotion/write-back ran before the snapshot blocker;
- P5/shadow-run did not start.

## Branch And Head Snapshot

The latest proof artifact records repo heads and dirty state in
`production-daily-cycle-proof.json`. The run used local in-flight changes from
this repair round, so several repos are intentionally marked dirty.

| Repo | Branch | Head Recorded | State |
|---|---|---:|---|
| `data-platform` | `m2-6f1-iceberg-canonical-graph-writer-v2` | `8374504` | clean in artifact |
| `main-core` | `m2-3a-2-regime-reader` | `3def30a` | clean in artifact |
| `graph-engine` | `m2-6f1-real-canonical-writer` | `2eb9e11` | dirty: validation-error wrapping patch |
| `orchestrator` | `m2-3a-2-phase1-wiring` | `0ccae67` | dirty: Phase 1 provider/status wiring patch |
| `audit-eval` | `m2-5-live-pg-roundtrip` | `a7d05b7` | clean in artifact |
| `reasoner-runtime` | `main` | `025db5b` | clean in artifact |
| `assembly` | `m2-baseline-2026-04-29` | `eac730f` | dirty: proof-runner artifact improvements |

## Commands

Graph-engine targeted suite:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/graph-engine
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=.:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
.venv/bin/python -m pytest -p no:cacheprovider \
  tests/unit/test_phase1_from_env.py \
  tests/unit/test_phase1_provider.py \
  tests/unit/test_promotion.py -q
```

Result: `48 passed, 1 skipped`.

Orchestrator targeted suite:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/orchestrator
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
  tests/integration/test_production_daily_cycle_provider.py \
  tests/integration/test_production_daily_cycle_phase1_wired.py \
  tests/integration/test_phase1_graph_provider_wiring.py -q
```

Result: `16 passed, 8 skipped`.

Assembly proof-runner unit tests:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/assembly
PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python -m pytest \
  -p no:cacheprovider tests/scripts/test_production_daily_cycle_proof.py -q
```

Result: `8 passed`.

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

Latest full proof artifact root:

```text
assembly/reports/stabilization/p1-p2-production-daily-cycle-proof-artifacts/20260430T210918Z/
```

Key full-proof artifacts:

| Artifact | Purpose |
|---|---|
| `production-daily-cycle-proof.json` | top-level proof report, command metadata, repo revisions, verdict, blockers, file manifest |
| `graph-status-initialization.json` | proof-only isolated DB `neo4j_graph_status` bootstrap and readback |
| `dagster-execution-evidence.json` | Dagster run id, selected assets, materialization records, failure step |
| `daily-refresh.json` | data-platform daily refresh evidence |
| `data-platform-current-selection-tests.stdout.txt` | current-selection focused test stdout |
| `orchestrator-dbt-compile.stdout.txt` | orchestrator dbt stub compile stdout |

Full proof run id:

```text
b78a94ef-b3c1-4668-b07f-0b4747baa778
```

## Phase Status

| Area | Status | Artifact-backed evidence |
|---|---|---|
| Runtime preflight | PASS | `20260430T210918Z/production-daily-cycle-proof.json` |
| Reasoner health/quota | PASS | `quota_status: ok` in full proof JSON |
| Data-platform refresh/current selection | PASS | `20260430T210918Z/daily-refresh.json`; current-selection stdout |
| Isolated PG bootstrap | PASS | `postgres_bootstrap` in `production-daily-cycle-proof.json` |
| Graph status initialization | PASS | `graph-status-initialization.json`; ready row readback, `phase0_graph_delta_writes: 0` |
| Phase 0 candidate freeze | PASS | Dagster materialization event for `candidate_freeze` |
| Phase 0 dbt heartbeat | PASS | Dagster materialization event for `heartbeat` |
| Phase 0 readiness ping | PASS | Dagster materialization event for `phase0_readiness_ping` |
| Phase 0 graph status | PASS | Dagster materialization event for `graph_status`; graph consistency asset check passed |
| Phase 1 graph promotion/write-back | PASS | Dagster materialization event for `graph_promotion` |
| Phase 1 graph snapshot | BLOCKED | failure step `graph_snapshot`: Neo4j GDS procedure missing |
| Phase 2 reasoner L1-L8 | NOT REACHED | dependency failure after `graph_snapshot` |
| Phase 3 formal outputs/publish manifest | NOT REACHED | dependency failure after upstream graph/Phase 2 steps |
| Audit/replay/retrospective hook | NOT REACHED | dependency failure after publish manifest |

Dagster event/materialization evidence:

```text
event_count: 77
materialized_asset_count: 5
unique_materialized_asset_count: 5
selected_asset_count: 17
selected_materializations_complete: false
unique_materialized_asset_keys:
  - candidate_freeze
  - graph_promotion
  - graph_status
  - heartbeat
  - phase0_readiness_ping
failure_step: graph_snapshot
full daily-cycle materialization claim supported: false
artifact_backed_pass_claim: false
```

## Blocker Classification

Primary blocker class: **Phase 1 graph snapshot / Neo4j GDS availability**.

The prior blockers are closed for this proof path:

- `graph-engine` normalizes SQLAlchemy-style PostgreSQL DSNs before direct
  `psycopg` use.
- The assembly proof runner seeds and verifies a proof-only ready
  `neo4j_graph_status` row in the isolated PostgreSQL database.
- The proof runner now sets `GRAPH_PHASE1_SNAPSHOT_ARTIFACT_ROOT`.
- Dagster reached and materialized `graph_promotion`, so the earlier
  fail-closed missing Phase 1 runtime bundle is no longer the active failure.

The active failure is later:

```text
RuntimeError: GDS plugin not available
```

Current structured blocker list includes:

```text
full production daily_cycle_job Dagster proof has not passed
Dagster failure step: graph_snapshot
production provider status is blocked
```

Recommended next repair round:

1. Decide the Lite-mode policy for graph snapshot propagation when Neo4j GDS is
   unavailable: provide a GDS-enabled Neo4j proof image/config, or add an
   explicitly approved non-GDS propagation fallback if that matches
   `project_ult_v5_0_1.md`.
2. Keep Phase 0 graph-status seeding proof-only for isolated proof databases;
   do not treat it as production graph delta writing.
3. Rerun the same full proof command and require
   `dagster-execution-evidence.json` to support the full selected-asset
   materialization claim.
4. Reconcile the historic "15 materializations" target with the current
   `daily_cycle_job` selected asset set, which currently resolves to 17 asset
   keys; do not claim pass while this count is unresolved.

## Explicit Non-Claims

- This does not pass M2.6.
- This does not start or pass P5.
- This does not prove M3.3 production same-cycle graph snapshot consumption.
- This does not prove P4/M4 bridge readiness.
- This does not change `project_ult_v5_0_1.md`.
- This does not introduce Full-stack components outside Lite mode.
