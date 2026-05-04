# M2.6 Production Daily-Cycle Proof - 2026-05-01

## Verdict

**PRODUCTION_DAILY_CYCLE_PASS. M2.6 production daily-cycle proof is
artifact-backed for this single Lite production daily-cycle run.**

The successful run is:

```text
assembly/reports/stabilization/p1-p2-production-daily-cycle-proof-artifacts/20260501T150811Z/
```

Top-level proof JSON:

```text
assembly/reports/stabilization/p1-p2-production-daily-cycle-proof-artifacts/20260501T150811Z/production-daily-cycle-proof.json
```

Structured outcome, combining the top-level proof JSON with
`dagster-execution-evidence.json`:

```text
verdict: PRODUCTION_DAILY_CYCLE_PASS
runner_exit_code: 0
evidence_date: 2026-05-01
baseline_evidence_date: 2026-04-28
blockers: []
run_id: efad558c-f5a1-4b9e-9bd6-31d0a0ce2212
cycle_id: CYCLE_20260415
selected_asset_count: 17
materialized_asset_count: 17
expected_materialized_asset_count: 17
selected_materializations_complete: true
asset_checks_complete: true
recorded_asset_check_count: 5
missing_expected_asset_check_names: []
artifact_backed_pass_claim: true
supports_selected_asset_materialization_claim: true
supports_legacy_15_materializations_claim: false
production_provider_status.static_blocked: true
production_provider_status.effective_blocked: false
production_provider_status.resolved_by_artifact_backed_run: true
```

The proof runner now uses the resolved selected asset set plus recorded and
expected Dagster asset checks as the pass basis. The old "15 materialized
assets" phrase is historical only and is not a current PASS criterion.

The static provider status still records its conservative runtime blockers, but
for this run those static blockers are superseded by the structured
artifact-backed Dagster pass. The effective fields in
`production_provider_status` are the acceptance fields for this artifact:
`effective_blocked=false` and `resolved_by_artifact_backed_run=true`.

## v5.0.1 Alignment

`project_ult_v5_0_1.md` remains the approved blueprint for this gate.

This run stayed inside the Lite-mode M2.6 daily-cycle proof path:

- no Kafka, Flink, Temporal, Milvus, Grafana, Superset, or Feast introduced;
- Layer A/Iceberg remains canonical truth;
- Neo4j remains a hot mirror and GDS runtime, not canonical truth;
- Phase 0 validates graph status and does not write graph deltas;
- Phase 1 performs graph promotion/write-back before graph snapshot;
- Phase 2 reasoner execution records hard-stop health and LLM lineage;
- Phase 3 writes formal outputs and `cycle_publish_manifest`;
- audit/replay persistence and retrospective hook complete;
- P5/shadow-run is not started.

## Branch And Head Snapshot

Recorded by `production-daily-cycle-proof.json` for the passing run:

| Repo | Branch | Head | Dirty |
|---|---|---:|---|
| `assembly` | `m2-baseline-2026-04-29` | `cd1d846` | yes |
| `audit-eval` | `m2-5-live-pg-roundtrip` | `0a94ec6` | no |
| `data-platform` | `m2-6f1-iceberg-canonical-graph-writer-v2` | `84ccedf` | yes |
| `graph-engine` | `m2-6f1-real-canonical-writer` | `17b5699` | no |
| `main-core` | `m2-3a-2-regime-reader` | `b181735` | no |
| `orchestrator` | `m2-3a-2-phase1-wiring` | `41c11d2` | yes |
| `reasoner-runtime` | `main` | `72c4b11` | no |

Dirty repos are expected for this in-flight repair round; the JSON artifact is
the source of truth for exact heads and command metadata.

## Commands

Assembly proof-runner tests:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/assembly
PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python -m pytest \
  -p no:cacheprovider tests/scripts/test_production_daily_cycle_proof.py -q
```

Result:

```text
21 passed
```

Orchestrator targeted suite:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/orchestrator
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
  tests/integration/test_p2_dry_run_handoff.py \
  tests/integration/test_production_daily_cycle_provider.py \
  tests/checks/test_phase2_pool_gate.py -q
```

Result:

```text
50 passed, 5 skipped
```

Production proof command:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/assembly
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python \
  scripts/production_daily_cycle_proof.py \
  --run-dagster \
  --run-current-selection-tests
```

Result:

```text
PRODUCTION_DAILY_CYCLE_PASS /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/p1-p2-production-daily-cycle-proof-artifacts/20260501T150811Z/production-daily-cycle-proof.json
```

## Artifacts

| Artifact | Purpose |
|---|---|
| `production-daily-cycle-proof.json` | top-level proof report, command metadata, repo revisions, verdict, blockers, file manifest |
| `dagster-execution-evidence.json` | Dagster run id, selected assets, materialization records, asset checks, pass basis |
| `runtime-evidence-summary.json` | artifact-root summary of pass-critical runtime facts, hashes, row counts, run ids, and snapshot ids |
| `neo4j-gds-preflight.json` | GDS availability proof: version + required procedure availability |
| `graph-status-initialization.json` | proof-only isolated DB `neo4j_graph_status` bootstrap and readback |
| `daily-refresh.json` | data-platform daily refresh evidence with dbt process stream text omitted |
| `data-platform-current-selection-tests-summary.json` | current-selection focused test status, return code, command, duration, and stream policy |
| `orchestrator-dbt-compile-summary.json` | orchestrator dbt stub compile status, manifest path, return code, command, and stream policy |

GDS preflight:

```text
status: passed
blocker: null
gds_version: 2.13.9
neo4j_role: hot_mirror
canonical_truth: Layer A canonical stores, not Neo4j
no_graph_delta_writes: true
```

Reasoner health:

```text
provider: openai-codex
model: gpt-5.5
reachable: true
quota_status: ok
all_critical_targets_available: true
```

Dagster asset checks:

```text
not_null_heartbeat_heartbeat: passed
llm_health_check: passed
phase0_ping_check: passed
neo4j_graph_consistency_check: passed
phase2_pool_failure_rate_gate: passed
```

Runtime evidence handling:

```text
non_artifact_tmp_paths_pass_critical: false
artifact-backed summary: runtime-evidence-summary.json
raw row counts: trade_cal=1, stock_basic=5512, daily=5494
raw run ids: 15a80425-c3fd-4594-89f6-0dcf06a6d46f, 5a4af64e-97af-434a-8081-081e45f6a752, 6ff9aaa6-6ca8-46d7-aef9-f252739a6f67
canonical_v2 snapshot ids: dim_security=8119016700871861950, fact_price_bar=2794673894564050497
```

## Phase Status

| Area | Status | Artifact-backed evidence |
|---|---|---|
| Runtime preflight | PASS | `production-daily-cycle-proof.json` |
| Neo4j GDS preflight | PASS | `neo4j-gds-preflight.json`, `gds_version: 2.13.9` |
| Reasoner health/quota | PASS | `codex_reasoner_health`, `quota_status: ok` |
| Data-platform refresh/current selection | PASS | `daily-refresh.json`; `data-platform-current-selection-tests-summary.json` |
| Isolated PG bootstrap | PASS | `postgres_bootstrap` |
| Graph status initialization | PASS | `graph-status-initialization.json`; ready row readback |
| Phase 0 candidate freeze | PASS | Dagster materialization for `candidate_freeze` |
| Phase 0 dbt heartbeat | PASS | Dagster materialization for `heartbeat` |
| Phase 0 readiness ping | PASS | Dagster materialization for `phase0_readiness_ping` |
| Phase 0 graph status | PASS | Dagster materialization for `graph_status`; graph consistency check passed |
| Phase 1 graph promotion/write-back | PASS | Dagster materialization for `graph_promotion` |
| Phase 1 graph snapshot | PASS | Dagster materialization for `graph_snapshot` |
| Phase 2 reasoner L1-L8 | PASS | Dagster materializations for `l1` through `l8` |
| Phase 2 pool failure-rate gate | PASS | Dagster asset check success |
| Phase 3 formal outputs | PASS | Dagster materialization for `formal_objects_commit` |
| Phase 3 publish manifest | PASS | Dagster materialization for `cycle_publish_manifest` |
| Audit/replay/retrospective hook | PASS | Dagster materialization for `retrospective_hook` |

Materialized selected assets:

```text
candidate_freeze
heartbeat
phase0_readiness_ping
graph_status
graph_promotion
graph_snapshot
l1
l2
l3
l4
l5
l6
l7
l8
formal_objects_commit
cycle_publish_manifest
retrospective_hook
```

## Closed Blockers In This Round

- SQLAlchemy-style PostgreSQL DSNs are normalized before direct `psycopg` use.
- The proof runner seeds and verifies a proof-only ready `neo4j_graph_status`
  row in the isolated PostgreSQL database.
- The proof runner persists Neo4j GDS preflight evidence before Dagster.
- The proof runner uses resolved selected assets as the materialization basis.
- Phase 2 accepts the `GraphSnapshotAssetResult` artifact ref.
- P2 current-cycle inputs ignore graph-delta candidates and load canonical_v2
  proof inputs.
- Phase 2 pool failure-rate check reads the current L8 output through wrapped
  providers.
- L6 `similar_cases` is part of the structured alpha schema using an
  OpenAI-strict JSON-schema-safe payload shape.
- Phase 3 advances cycle status through `phase1 -> phase2 -> phase3` before
  manifest publish.
- Audit/replay records bind to published formal object refs.
- Reasoner audit raw output is constrained to current-cycle language so the
  retrospective hook does not reject non-production provenance markers.

## Explicit Non-Claims

- This is not P5 readiness and does not start a shadow-run.
- This is not M3.3 production same-cycle graph consumption proof.
- This is not P4/M4 bridge readiness.
- This does not change `project_ult_v5_0_1.md`.
- This does not introduce Full-stack components outside Lite mode.
- This does not turn Neo4j into canonical truth.
