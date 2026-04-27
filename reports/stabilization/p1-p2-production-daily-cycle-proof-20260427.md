# P1/P2 Production Daily-Cycle Proof - 2026-04-27

## Status

PARTIAL PASS / BLOCKED. This file is intentionally not a production pass
certificate and not P5 readiness.

The current batch moved the production provider set from "missing checked-in
surfaces" to "checked-in surfaces with fail-closed runtime blockers":

- data-platform now exposes a production current-cycle selector and Phase 0
  candidate-freeze wrapper.
- graph-engine now exposes Phase 1 graph promotion/snapshot provider assets and
  Layer A artifact writing/cold-reload helpers.
- audit-eval now exposes a real retrospective hook callable that validates
  durable audit/replay queryability and forbidden provenance.
- orchestrator now composes Phase 0 + Phase 1 + P2 L1-L8 + Phase 3 manifest +
  audit hook under `ORCHESTRATOR_DEFINITIONS_PROFILE=p5`.

It still does not prove a live production `daily_cycle_job` execution with real
Neo4j GDS, real graph-status runtime, real audit-eval runtime, and a manifest
readback artifact from that Dagster run.

## Commits

- data-platform: `587f9895660c5f347768b66402c793d024934415`
  - Adds `data_platform.cycle.current_selection`.
  - Selects latest open Tushare trade date from ingested artifacts.
  - Generates `CYCLE_YYYYMMDD`.
  - Fails closed on missing trade calendar, symbol artifacts, or freeze
    prerequisites.
- graph-engine: `14c32f2fb092c57246789353eb45f9765e99b2e1`
  - Adds Phase 1 provider assets for `graph_promotion` and `graph_snapshot`.
  - Adds Layer A/formal-readable artifact writer.
  - Keeps missing GDS/runtime conditions fail-closed.
- graph-engine follow-up: `78019a73cd83e32534829b3fcbf44468d7738c1e`
  - Requires Phase 1 to consume explicit `candidate_freeze.selection_ref`
    instead of synthesizing a frozen selection ref.
  - Fixes graph-generation parsing so numeric checksum suffixes are not
    mistaken for generation IDs.
- audit-eval: `fd6ac282c24337241c8addd76809c67deb41e11b`
  - Adds real retrospective hook callable.
  - Validates manifest presence, audit/replay IDs, queryability, and
    smoke/fixture/historical provenance rejection.
  - Records pending/placeholder status when T+1 metrics are not mature.
- audit-eval follow-up: `13cff871d9aacfed9772179c16a156a8b2e84da0`
  - Adds `require_manifest_gateway=True` for production retrospective hooks.
  - Rejects in-memory manifest rows that do not match the durable manifest
    gateway result.
- orchestrator: `89863e9723b2154c9c5aac9ab973f10c29669cb0`
  - Composes the production daily-cycle provider set.
  - Requires explicit Dagster `cycle_id` tag for P2.
  - Returns enriched `P2PublishedManifest` for audit-eval handoff.
  - Keeps runtime blockers explicit in provider status.
- orchestrator follow-up: `f43e4cd50ab667442e0cd60e6637c7f5e92a4076`
  - Requires `cycle_id` tag before `candidate_freeze` can call
    `freeze_current_cycle_candidates()`.
  - Replaces the dry-run fake Phase 2 pool gate resource with an env-backed
    fail-closed production resource.
  - Wires the audit hook runtime to `DataPlatformManifestGateway` with durable
    manifest lookup required.

## What Passed

Data-platform focused validation:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
.venv/bin/python -m pytest tests/cycle/test_current_selection.py -q

result:
8 passed
```

Data-platform broader cycle/public validation:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
.venv/bin/python -m pytest tests/cycle tests/test_public_api.py -q

result:
44 passed, 20 skipped
```

Graph-engine focused validation:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/graph-engine
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
python3 -m pytest -q tests/unit/test_phase1_provider.py tests/unit/test_reload_artifact_reader.py

result:
s............... [16 tests total, 15 passed, 1 skipped]
```

Graph-engine local broad validation:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/graph-engine
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
python3 -m pytest tests/unit tests/contract tests/boundary tests/smoke -q

result:
passed, 1 skipped
```

Audit-eval validation:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/audit-eval
uv run python -m pytest tests/test_retro_hook.py tests/test_retro_compute.py \
  tests/test_replay_storage_integration.py tests/test_real_cycle_binding.py -q

result:
31 passed
```

Orchestrator production provider assembly and regression validation:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/orchestrator
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/orchestrator/src:/Users/fanjie/Desktop/Cowork/project-ult/main-core/src:/Users/fanjie/Desktop/Cowork/project-ult/reasoner-runtime:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src:/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src:/Users/fanjie/Desktop/Cowork/project-ult/audit-eval/src:/Users/fanjie/Desktop/Cowork/project-ult/graph-engine \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest -q \
  tests/integration/test_production_daily_cycle_provider.py \
  tests/integration/test_p2_dry_run_handoff.py \
  tests/integration/test_audit_eval_wiring.py \
  tests/integration/test_phase1_graph_provider_wiring.py

result:
30 passed
```

Orchestrator static checks:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/orchestrator
/opt/homebrew/bin/ruff check \
  src/orchestrator_adapters/production_daily_cycle.py \
  src/orchestrator_adapters/p2_dry_run.py \
  tests/integration/test_production_daily_cycle_provider.py

result:
All checks passed
```

## Existing Real-Data Evidence

The P2 durable real-data Codex closure remains valid evidence for the isolated
current-cycle L1-L8 chain:

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

## Current Blockers

| Priority | Blocker | Evidence |
| --- | --- | --- |
| P1 | Live GDS closure is still not complete. The graph-engine live suite still skipped GDS tests because the local Neo4j runtime used by the worker did not expose GDS procedures. | `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/p3-graph-live-closure-20260427.md` |
| P1 | Production `daily_cycle_job` has not yet run with configured real graph Phase 0 status runtime, graph Phase 1 runtime, audit-eval runtime, and current-cycle tag in one Dagster execution. | `/Users/fanjie/Desktop/Cowork/project-ult/orchestrator/src/orchestrator_adapters/production_daily_cycle.py` |
| P1 | The default production graph-status provider intentionally fails closed until wired to a real Neo4j/project graph status store. | `/Users/fanjie/Desktop/Cowork/project-ult/orchestrator/src/orchestrator_adapters/production_daily_cycle.py` |
| P1 | The production Phase 2 pool failure-rate resource now fails closed unless `ORCHESTRATOR_PHASE2_POOL_FAILURE_RATE_EVENT_JSON` is configured with a real current-cycle metric event. | `/Users/fanjie/Desktop/Cowork/project-ult/orchestrator/src/orchestrator_adapters/production_daily_cycle.py` |
| P1 | Data-platform PostgreSQL freeze integration was not proven in this local worker shell because no PG test DSN was available to that worker. | `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/cycle/current_selection.py` |
| P2 | The orchestrator audit hook runtime now requires durable manifest lookup plus durable audit/replay queryability, but the full production Dagster run has not yet produced and consumed the final audit hook artifact. | `/Users/fanjie/Desktop/Cowork/project-ult/audit-eval/src/audit_eval/retro/hook.py` |

## Non-Claims

- This is not P5 shadow-run readiness.
- This is not a production daily-cycle pass certificate.
- This does not update compatibility matrix or registry verified rows.
- This does not claim news, Polymarket, API-6, sidecar, frontend write API,
  Kafka, Flink, or Temporal.
- Existing P2 closure can be reused as current-cycle L1-L8 evidence, but it
  cannot replace live Phase 1 graph proof or a production Dagster run with real
  providers.

## Required Next Gate

1. Start disposable Neo4j with GDS and run the graph-engine live suite with
   zero GDS skips.
2. Wire the production provider resources for graph status, graph Phase 1, and
   audit-eval runtime into a bounded `daily_cycle_job.execute_in_process(...)`.
3. Run with selector-produced `cycle_id` tag and record cycle ID, trade date,
   symbols, frozen candidate IDs, graph snapshot IDs, formal snapshot IDs,
   audit/replay IDs, manifest row, serving readback, and negative gates.
4. Only after that evidence is clean should this file be replaced by a
   production daily-cycle pass certificate.

## Findings

- P0: none.
- P1: live GDS proof and production Dagster run remain open.
- P2: audit hook production artifact remains unproven in a real daily-cycle
  execution, although durable manifest/audit/replay lookup boundaries are now
  enforced.
- P3: local graph-engine broad lint has pre-existing untouched ruff findings;
  changed graph-engine files passed focused ruff.
