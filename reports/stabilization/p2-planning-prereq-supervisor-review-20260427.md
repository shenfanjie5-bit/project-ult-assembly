# P2 Planning Prerequisite Supervisor Review - 2026-04-27

## Scope

This supervisor review covers the first P2 planning prerequisite batch after the P1 real-data mini-cycle close-loop gate.

Reviewed commits:

- `audit-eval` `627f9241be79d4d31780244d3ea42003de7e07b3` (`feat: bind replay smoke to data-platform cycles`)
- `assembly` `6d56c04507837ebba5373534a3bcb107fb2335de` (`docs: record audit real cycle binding evidence`)
- `orchestrator` `0e2f7b29eb2c984f7632e77056da34389ce1aa61` (`Align Phase 2 contract with L1-L8`)
- `orchestrator` `16f35bf` (`test: align phase2 L8 evidence checks`)
- `assembly` `9c121c4482a661f1ed3f5b13e80c431be06ad472` (`docs: record P2 L1-L8 dry-run readiness`)

Primary evidence:

- `reports/stabilization/audit-real-cycle-binding-20260427.md`
- `reports/stabilization/audit-real-cycle-binding-20260427-artifacts/`
- `reports/stabilization/p2-l1-l8-dry-run-readiness-20260427.md`

This review accepts P2 planning/prerequisite evidence only. It does not claim P2 real L1-L8 dry-run completion, P5 shadow-run readiness, or full v5.0.1 completion.

## Review Results

### Audit Real-Cycle Binding

Accepted for planning evidence.

Verified properties:

- `audit-eval` now has a read-only data-platform binding through `DataPlatformManifestGateway` and `DataPlatformFormalSnapshotGateway`.
- The smoke path calls `data_platform.cycle.get_publish_manifest` and `data_platform.serving.formal.get_formal_by_snapshot`.
- The smoke artifact records `binding_source=data-platform-published-cycle`.
- The smoke artifact records `fixture_replay_used=false`.
- The smoke artifact records `recommendation_generated=false`.
- Manifest refs use explicit `data-platform://formal/<object_ref>/snapshots/<snapshot_id>` refs.
- Existing `replay_cycle_object` manifest-binding validation remains in the path.

Supervisor validation:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/audit-eval
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest tests/test_real_cycle_binding.py tests/test_replay_query.py -q
```

Result: `27 passed`.

Additional audit-eval contract/read-history validation:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/audit-eval
.venv/bin/python -m pytest tests/test_contracts_write_bundle.py tests/test_replay_query.py tests/test_contracts_retrospective.py -q
```

Result: `44 passed`.

Remaining caveat:

- This is a real manifest/formal snapshot query smoke with an in-memory technical replay repository. It is not production audit/replay table persistence.

### P2 L1-L8 Readiness

Accepted for planning evidence after follow-up correction.

Verified properties:

- `PHASE2_STAGE_KEYS` now covers `l1` through `l8`.
- Phase 3 fake formal commit wiring is aligned to depend on the final Phase 2 boundary (`l8`).
- The readiness report explicitly states that P2 dry run was not started and no recommendation was generated.
- The readiness report preserves hard blockers: missing real main-core L1-L8 provider, missing target-runtime LLM health validation, missing current-cycle recommendation writer, and missing real audit/replay persistence.

Initial independent review found a P2 evidence issue:

- Some local orchestrator validation had been weakened by Python 3.14 Dagster/dagster-dbt compatibility skips.
- Two skipped assertions still referenced stale L7 expectations.

Correction:

- `orchestrator` commit `16f35bf` updated the stale test expectations from L7 to L8.
- Validation was re-run with Python 3.12, matching the orchestrator `pyproject.toml` `requires-python` range.
- The Python 3.12 runtime command placed `/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin` on `PATH` so `dbt` was available to the integration fixtures.

Targeted L8 validation:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/orchestrator
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
  /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest \
  tests/integration/test_phase2_main_core_wiring.py::test_phase2_provider_contributes_daily_cycle_assets_and_checks \
  tests/integration/test_phase3_publish_wiring.py::test_phase3_formal_commit_without_phase2_dependency_is_rejected \
  tests/integration/test_phase2_pool_failure_gate.py::test_daily_cycle_phase2_pool_failure_rate_gate_fails_and_alerts \
  tests/integration/test_phase2_pool_failure_gate.py::test_daily_cycle_phase2_pool_failure_rate_gate_allows_without_alert \
  -q -rs
```

Result: `4 passed`, with no skipped summary.

Expanded orchestrator validation:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/orchestrator
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
  /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest \
  tests/integration/test_phase2_main_core_wiring.py \
  tests/integration/test_daily_cycle_four_phase.py \
  tests/integration/test_phase3_publish_wiring.py \
  tests/integration/test_phase3_manifest_repair_flow.py \
  tests/integration/test_phase2_pool_failure_gate.py \
  tests/integration/test_infra_hard_stop.py \
  tests/temporal/test_workflow.py \
  -q -rs
```

Result: `18 passed`, with no skipped summary.

Independent re-review of `16f35bf`:

- Result: no P0/P1/P2/P3 findings.
- Targeted command result: `4 passed`.
- Expanded B-line command result: `25 passed`.
- Stale L7 search over target test files returned no matches.
- The prior P2 finding is closed.

Other focused validations reviewed:

- `reasoner-runtime`: focused unit command passed.
- `graph-engine`: focused graph/status/snapshot/promotion command passed.
- `data-platform`: focused manifest/freeze/serving command passed with existing local skips.

## Secret And File Hygiene

Secret scan was performed against the committed P2 planning reports/artifacts using active local values from `assembly/.env`.

Result: no Tushare token or PostgreSQL DSN matches in committed evidence.

No forbidden local files were committed in the reviewed target commits.

Known uncommitted local files remain outside this gate:

- `assembly`: `.env`, `.venv-py312/`, `PROJECT_REPORT.md`, pycache, egg-info, and temporary review directories.
- `orchestrator`: `.orchestrator/`, `dbt_stub/.user.yml`, `dbt_stub/dagster_home/`, `dbt_stub/logs/`, `dbt_stub/target/`.
- `audit-eval`: `PROJECT_REPORT.md`, `build/`, `dist/`, `src/project_ult_audit_eval.egg-info/`.
- `data-platform`: existing modified `docs/spike/iceberg-write-chain.md`, `.orchestrator/`, and `tmp/`.

These files must remain uncommitted unless separately reviewed and authorized.

## Gate Decision

P2 planning/prerequisite evidence is accepted.

The following evidence is now usable for the next planning step:

- audit-eval can perform a read-only real data-platform published manifest/formal snapshot smoke.
- orchestrator Phase 2 contract surface is aligned to L1-L8.
- the previous L8 evidence weakness has been corrected and independently re-reviewed.

This is not a P2 dry-run pass.

## Blocking Items Before Actual P2 Dry Run

P1 blockers:

- A real main-core L1-L8 provider must consume P1 real data-platform outputs and reasoner-runtime.
- Target-runtime LLM provider credentials/config must pass Phase 0 health checks.
- Current-cycle `recommendation_snapshot` formal output must be produced by L8, not by fixture, historical, or synthetic rows.
- Formal publish must reject fixture/historical/synthetic recommendations as current-cycle output.
- Real audit/replay rows must persist the v5.0.1 replay fields for L4/L6/L7 LLM calls.

P2 blockers:

- Add no-LLM hard-stop evidence where provider chain failure prevents L4/L6/L7 materialization and prevents formal commit/manifest publication.
- Add current-cycle recommendation provenance checks that bind cycle_id, L8 dependency, formal snapshot ids, and audit/replay linkage.
- Replace the audit real-cycle smoke's in-memory technical repository with persisted audit/replay storage once the P2 writer exists.

Frontend constraint:

- Frontend work remains read-only evidence presentation only. No publish, repair, freeze, command/run, or recommendation mutation interface is authorized.

## Next Supervisor Assignments

Backend next batch:

- Implement no-LLM hard-stop integration evidence in orchestrator/reasoner-runtime without generating recommendations.
- Design the smallest real L1-L8 provider slice needed for a true P2 dry-run candidate.
- Add current-cycle recommendation provenance guardrails before any formal publish path can accept a recommendation snapshot.

Testing next batch:

- Independently verify that no-LLM hard-stop produces no formal objects and no `cycle_publish_manifest`.
- Independently verify that any future `recommendation_snapshot` is current-cycle, L8-derived, and backed by audit/replay rows.

Frontend next batch:

- No action until backend P2 evidence exists.
