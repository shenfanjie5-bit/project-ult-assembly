# M2.6 Full Production Daily-Cycle Proof Attempt - 2026-05-01

## Verdict

**PARTIAL_PASS_BLOCKED. M2.6 is not passed.**

The May 1 follow-up closed the previous Neo4j GDS runtime blocker for the
local proof path. The running Lite Neo4j container was non-destructively
recreated from `neo4j:5.26.25` with
`NEO4J_PLUGINS='["graph-data-science"]'`, and the proof runner now persists a
GDS preflight artifact before Dagster execution.

The latest full proof reached real Dagster execution, materialized
`graph_promotion`, and executed GDS-backed graph snapshot logic. It then failed
closed at `graph_snapshot` with a new Phase 1 blocker:

```text
ValueError: GraphImpactSnapshot requires at least one target entity for cycle_id='CYCLE_20260415', world_state_ref='world-state:latest', graph_generation_id=1
```

Current blocker:

- `graph_snapshot` no longer fails because GDS is missing; GDS version `2.13.9`
  is artifact-backed.
- `graph_snapshot` now fails because the generated impact snapshot has no
  target entity for the proof cycle.
- 5 artifact-backed materializations were recorded out of the 17 selected
  daily-cycle assets.
- Phase 2, Phase 3, audit/replay, and retrospective hook were not reached.

This is not a Codex quota blocker. The reasoner health probe was reachable and
reported `quota_status: ok`.

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

The latest full proof artifact records repo heads and dirty state in
`production-daily-cycle-proof.json`. The run used local in-flight changes from
this repair round.

| Repo | Branch | Head Recorded | State In Artifact |
|---|---|---:|---|
| `data-platform` | `m2-6f1-iceberg-canonical-graph-writer-v2` | `8374504` | dirty |
| `main-core` | `m2-3a-2-regime-reader` | `3def30a` | clean |
| `graph-engine` | `m2-6f1-real-canonical-writer` | `ef6700a` | dirty: GDS availability probe |
| `orchestrator` | `m2-3a-2-phase1-wiring` | `a9f5f57` | clean |
| `audit-eval` | `m2-5-live-pg-roundtrip` | `a7d05b7` | clean |
| `reasoner-runtime` | `main` | `025db5b` | clean |
| `assembly` | `m2-baseline-2026-04-29` | `0ff0d30` | dirty: proof-runner GDS/evidence changes |

## Commands

Non-destructive Neo4j/GDS runtime repair:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/assembly
docker compose --env-file .env -f compose/lite-local.yaml up -d --force-recreate neo4j
docker exec compose-neo4j-1 cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
  "CALL gds.version() YIELD gdsVersion RETURN gdsVersion"
docker exec compose-neo4j-1 cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
  "CALL gds.graph.exists('__m2_6_probe__') YIELD exists RETURN exists"
```

Result: container image `neo4j:5.26.25`; GDS version `2.13.9`;
`gds.graph.exists` returned `FALSE`.

Graph-engine targeted suite:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/graph-engine
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=.:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
.venv/bin/python -m pytest -p no:cacheprovider \
  tests/unit/test_phase0_status_provider.py \
  tests/unit/test_phase1_from_env.py \
  tests/unit/test_phase1_provider.py \
  tests/unit/test_gds_availability.py
```

Result: `37 passed, 1 skipped`.

Assembly proof-runner unit tests:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/assembly
PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python -m pytest \
  -p no:cacheprovider tests/scripts/test_production_daily_cycle_proof.py -q
```

Result: `11 passed`.

Runtime preflight:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/assembly
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
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
assembly/reports/stabilization/p1-p2-production-daily-cycle-proof-artifacts/20260430T213645Z/
```

Key full-proof artifacts:

| Artifact | Purpose |
|---|---|
| `production-daily-cycle-proof.json` | top-level proof report, command metadata, repo revisions, verdict, blockers, file manifest |
| `neo4j-gds-preflight.json` | GDS availability proof: version + required procedure availability |
| `graph-status-initialization.json` | proof-only isolated DB `neo4j_graph_status` bootstrap and readback |
| `dagster-execution-evidence.json` | Dagster run id, selected assets, materialization records, failure step/root cause |
| `daily-refresh.json` | data-platform daily refresh evidence |
| `data-platform-current-selection-tests.stdout.txt` | current-selection focused test stdout |
| `orchestrator-dbt-compile.stdout.txt` | orchestrator dbt stub compile stdout |

Latest full proof run id:

```text
b93c74e7-23e6-40e6-9219-cf47da449f0c
```

GDS preflight:

```text
status: passed
blocker: null
gds_version: 2.13.9
gds_graph_exists_probe.procedure_available: true
neo4j_role: hot_mirror
canonical_truth: Layer A canonical stores, not Neo4j
no_graph_delta_writes: true
```

## Phase Status

| Area | Status | Artifact-backed evidence |
|---|---|---|
| Runtime preflight | PASS | `20260430T213645Z/production-daily-cycle-proof.json` |
| Neo4j GDS preflight | PASS | `neo4j-gds-preflight.json`, `gds_version: 2.13.9` |
| Reasoner health/quota | PASS | `quota_status: ok` in full proof JSON |
| Data-platform refresh/current selection | PASS | `daily-refresh.json`; current-selection stdout |
| Isolated PG bootstrap | PASS | `postgres_bootstrap` in `production-daily-cycle-proof.json` |
| Graph status initialization | PASS | `graph-status-initialization.json`; ready row readback, `phase0_graph_delta_writes: 0` |
| Phase 0 candidate freeze | PASS | Dagster materialization event for `candidate_freeze` |
| Phase 0 dbt heartbeat | PASS | Dagster materialization event for `heartbeat` |
| Phase 0 readiness ping | PASS | Dagster materialization event for `phase0_readiness_ping` |
| Phase 0 graph status | PASS | Dagster materialization event for `graph_status`; graph consistency asset check passed |
| Phase 1 graph promotion/write-back | PASS | Dagster materialization event for `graph_promotion` |
| Phase 1 graph snapshot | BLOCKED | `GraphImpactSnapshot requires at least one target entity` |
| Phase 2 reasoner L1-L8 | NOT REACHED | dependency failure after `graph_snapshot` |
| Phase 3 formal outputs/publish manifest | NOT REACHED | dependency failure after upstream graph/Phase 2 steps |
| Audit/replay/retrospective hook | NOT REACHED | dependency failure after publish manifest |

Dagster event/materialization evidence:

```text
event_count: 77
materialized_asset_count: 5
unique_materialized_asset_count: 5
selected_asset_count: 17
expected_materialized_asset_count: 17
selected_asset_count_matches_materialization_basis: true
selected_materializations_complete: false
materialized_asset_keys:
  - candidate_freeze
  - graph_promotion
  - graph_status
  - heartbeat
  - phase0_readiness_ping
failure_step: graph_snapshot
failure_root_cause: ValueError: GraphImpactSnapshot requires at least one target entity for cycle_id='CYCLE_20260415', world_state_ref='world-state:latest', graph_generation_id=1
artifact_backed_pass_claim: false
supports_legacy_15_materializations_claim: false
supports_selected_asset_materialization_claim: false
```

## Blocker Classification

Primary blocker class: **Phase 1 graph snapshot input/impact-target coverage**.

The prior blockers are closed for this proof path:

- SQLAlchemy-style PostgreSQL DSNs are normalized before direct `psycopg` use.
- The assembly proof runner seeds and verifies a proof-only ready
  `neo4j_graph_status` row in the isolated PostgreSQL database.
- The proof runner sets `GRAPH_PHASE1_SNAPSHOT_ARTIFACT_ROOT`.
- Dagster reached and materialized `graph_promotion`.
- Neo4j GDS is present and artifact-backed (`gds_version: 2.13.9`).

The active failure is later:

```text
Dagster failure step: graph_snapshot
Dagster failure root cause: ValueError: GraphImpactSnapshot requires at least one target entity for cycle_id='CYCLE_20260415', world_state_ref='world-state:latest', graph_generation_id=1
production provider runtime pending: configured_graph_phase1_runtime
```

Recommended next repair round:

1. Inspect the Phase 1 graph promotion output and live Neo4j graph produced for
   `CYCLE_20260415`.
2. Decide whether the proof seed/candidate set must create at least one
   GraphImpactSnapshot target entity, or whether graph-engine should treat an
   empty impact-target set as a valid empty snapshot for this cycle.
3. Keep this as a Phase 1 graph snapshot repair only; do not broaden into
   Phase 2/P5/M3.3 work.
4. Rerun the same full proof command and require
   `dagster-execution-evidence.json` to support all 17 selected asset
   materializations before any M2.6 PASS claim.

## Explicit Non-Claims

- This does not pass M2.6.
- This does not start or pass P5.
- This does not prove M3.3 production same-cycle graph snapshot consumption.
- This does not prove P4/M4 bridge readiness.
- This does not change `project_ult_v5_0_1.md`.
- This does not introduce Full-stack components outside Lite mode.
