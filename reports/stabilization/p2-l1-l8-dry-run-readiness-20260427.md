# P2 L1-L8 Dry-Run Readiness / Hard-Stop Preflight

Date: 2026-04-27
Role: Project ULT backend role B
Scope: orchestrator, reasoner-runtime, graph-engine, data-platform, audit-eval
Gate context: P1 real-data mini-cycle close-loop passed supervisor review at assembly commit `3806aa0`. This report is P2 planning/readiness evidence only. It does not claim P2 dry run completion and does not create any recommendation output.

## Executive Status

P2 dry-run readiness is blocked until main-core provides a real L1-L8 asset provider that consumes P1 real data and reasoner-runtime, writes formal recommendation/audit/replay outputs, and refuses to publish if LLM infrastructure is unavailable.

Low-risk hardening was applied in orchestrator: Phase 2 now exposes `l1` through `l8` in the contract surface, and focused test fixtures were updated so Phase 3 publish depends on L8 rather than L7.

## Blueprint Requirements Checked

- P2 must connect to real P1 data-platform/dbt outputs and reasoner-runtime.
- P2 must produce an auditable `recommendation_snapshot`.
- LLM infrastructure-level failure must hard-stop the cycle.
- Formal output must not be historical, fixture, or synthetic recommendation data.
- LLM formal calls must persist replay fields: `sanitized_input`, `input_hash`, `raw_output`, `parsed_result`, `output_hash`, with lineage/cost metadata.
- Frontend scope remains read-only evidence display only; no new write API is allowed.

## Repository Findings

### orchestrator

Ready pieces:
- Phase 0 LLM health check is wired as a blocking AssetCheck and maps failure to `fail_run`.
- Core infra resources are guarded through `infra_unavailable_hard_stop`.
- Phase 3 has formal commit before `cycle_publish_manifest`, plus repair-only manifest failure handling.
- Dagster/Temporal parity checks use contract stage keys.

Gap fixed:
- `PHASE2_STAGE_KEYS` previously ended at `l7`; P2 requires L1-L8. The contract now includes `l8`, and test fakes make `formal_objects_commit` depend on L8.

Remaining blocker:
- orchestrator still only owns scheduling/gate contracts. It does not implement real L1-L8 business assets. A main-core/provider integration must supply real L1-L8 assets and resources.

### reasoner-runtime

Ready pieces:
- Single entrypoints `generate_structured()` and `generate_structured_with_replay()` centralize provider calls.
- `ReasonerRequest.max_retries` is explicit and validated.
- Provider fallback classifies exhausted infrastructure failures as `infra_level` and parse failures as `task_level`.
- LiteLLM/Instructor client creation passes explicit `max_retries`.
- PII scrub runs before provider calls; replay bundle stores sanitized input, raw output, parsed result, hashes, and lineage.
- Callback layer records minimal trace/cost/failure metadata without raw prompt/output leakage.

Remaining blocker:
- P2 needs real provider configuration and credentials validated in the target runtime environment before any dry run.

### graph-engine

Ready pieces:
- Graph status state machine supports `ready`, `rebuilding`, and `failed`.
- Read paths guard `graph_status == ready`.
- Consistency check, cold reload status transitions, promotion, propagation, and snapshot generation have focused tests.
- Read-only local impact simulation is separate from formal snapshot generation.

Readiness note:
- P2 independent mode can run without graph/subsystems per blueprint, but if graph-engine is connected, Phase 1 must publish real `graph_snapshot` / `graph_impact_snapshot` from Layer A/Neo4j, not synthetic benchmark data.

### data-platform

Ready pieces:
- Real Tushare adapter/dbt surface exists for P1 structured data.
- `cycle_candidate_selection` freezes accepted candidates in a PG transaction.
- `cycle_publish_manifest` requires required formal table keys and positive Iceberg snapshot ids.
- Required formal objects include `world_state_snapshot`, `official_alpha_pool`, `alpha_result_snapshot`, and `recommendation_snapshot`.

Remaining blocker:
- Formal serving/writer path for P2 real `recommendation_snapshot` must be invoked by main-core after real L8 aggregation. Shared fixtures prove contract shape only and must not be used as formal output.

### audit-eval

Ready pieces:
- Audit/replay contracts require replay bundle fields when `llm_lineage.called` is true.
- Replay query is manifest-bound and `read_history` only; tests block network/model calls during replay.
- Manifest binding prevents replay records from pointing to snapshots outside `cycle_publish_manifest`.

Remaining blocker:
- P2 real cycle needs real audit/replay rows generated from current L4/L6/L7 LLM calls, not fixture records.

## Hard Blockers Before P2 Dry Run

P1:
- Real main-core L1-L8 provider is not present in this inspected scope; orchestrator has only contract/fake provider coverage.
- Real reasoner-runtime provider credentials/config must pass Phase 0 health check in the dry-run environment.
- `recommendation_snapshot` formal writer must write current-cycle output and audit/replay records before `cycle_publish_manifest` is inserted.
- Formal publish must reject any fixture/historical/synthetic recommendation as current-cycle output.

P2:
- P2 preflight should assert selected Phase 2 asset keys are exactly L1-L8 and that Phase 3 formal commit depends on L8.
- P2 should add a no-LLM hard-stop integration test where all providers fail and no formal commit/manifest materializes.
- P2 should add an audit completeness test for real L4/L6/L7 calls: replay fields, lineage provider/model/fallback, and cost metrics.

P3:
- Frontend can display manifest-bound read-only evidence after publish, but must not add write endpoints or manual publish controls.
- Graph-engine connection can remain optional for P2 independent mode, but any connected graph input must be manifest/snapshot-bound.

## Parallel Work Split

Backend A:
- Implement or expose main-core real L1-L8 Dagster assets.
- Ensure L8 aggregates dashboard/report/audit/replay inputs and is the only dependency into Phase 3 formal commit.
- Wire current-cycle formal object writers, including `recommendation_snapshot`.

Backend B:
- Keep orchestrator preflight/gates aligned to L1-L8 and hard-stop semantics.
- Add current-cycle-output guardrails against fixture/historical/synthetic recommendation publish.
- Verify reasoner-runtime config/health probe wiring in the target runtime profile.

Testing:
- Add no-LLM hard-stop e2e: provider chain unavailable, L4/L6/L7 cannot materialize, no formal commit, no manifest.
- Add current-cycle recommendation provenance test: cycle_id, L8 dependency, manifest snapshot ids, audit/replay linkage.
- Add fixture leakage test: audit-eval fixtures may be replay inputs only, never P2 formal write inputs.

Frontend:
- Read-only evidence display only: manifest, snapshot ids, audit/replay links, hard-stop status.
- No new write API, publish button, repair trigger, or recommendation mutation endpoint.

## Verification Run

- orchestrator: `.venv/bin/python -m pytest tests/integration/test_phase2_main_core_wiring.py tests/integration/test_daily_cycle_four_phase.py tests/integration/test_phase3_publish_wiring.py tests/integration/test_phase3_manifest_repair_flow.py tests/integration/test_phase2_pool_failure_gate.py tests/integration/test_infra_hard_stop.py tests/temporal/test_workflow.py -q`
- reasoner-runtime: `.venv/bin/python -m pytest tests/unit/test_engine.py tests/unit/test_providers.py tests/unit/test_replay.py tests/unit/test_scrub.py tests/unit/test_callbacks.py -q`
- graph-engine: `.venv/bin/python -m pytest tests/unit/test_status.py tests/unit/test_snapshots.py tests/unit/test_promotion.py tests/regression/test_with_shared_fixtures_graph.py -q`
- audit-eval: `.venv/bin/python -m pytest tests/test_contracts_write_bundle.py tests/test_replay_query.py tests/test_contracts_retrospective.py -q`
- data-platform: `.venv/bin/python -m pytest tests/cycle/test_publish_manifest.py tests/cycle/test_freeze_cycle_candidates.py tests/regression/test_with_shared_fixtures.py tests/serving/test_formal_manifest_consistency.py -q`

All listed verification commands passed in the local environment. Some orchestrator/data-platform integration tests were skipped by existing local test conditions.

## Explicit Non-Claims

- P2 dry run was not started.
- No recommendation was generated.
- No fixture, historical, or synthetic recommendation was promoted as formal output.
- No frontend write capability was added.
