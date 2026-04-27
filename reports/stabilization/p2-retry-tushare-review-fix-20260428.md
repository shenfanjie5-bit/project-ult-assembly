# P2 Retry Safety And Tushare Coverage Review Fix - 2026-04-28

## Scope

This evidence records the multi-subagent review and fix for two P2 follow-up
findings:

- P1: audit/replay durable writes were not retry-safe after split audit/replay
  persistence.
- P3: real Tushare provider coverage did not directly exercise the production
  `DataPlatformTushareCurrentCycleInputProvider` handoff path.

This does not start P5 and does not promote production daily-cycle readiness.

## Result

Status: `passed`

Orchestrator commit:

- `e6d4a56c6bd3e9f60183e3ab77dcfa009d17404b`

Closed review findings:

- P1 retry-safety: `AuditEvalPersistencePort` persists one
  `AuditWriteBundle`; rebuilt P2 bundles now have retry-stable persisted
  audit/replay payloads across different Dagster rerun ids.
- P3 Tushare coverage: a job-level `daily_cycle_job` regression now exercises
  the default `DataPlatformTushareCurrentCycleInputProvider` path and asserts
  real Tushare symbols, candidate ids, source run ids, and no `ENT_P2_A/B`
  leakage.
- P1 declared test environment: `orchestrator[dev]` now includes the
  data-platform import dependencies needed by the regression lane.

## Implementation Evidence

Changed repo: `orchestrator`

Changed files:

- `pyproject.toml`
- `src/orchestrator_adapters/p2_dry_run.py`
- `tests/integration/test_p2_dry_run_handoff.py`

Key behavior:

- P2 audit/replay records use a stable cycle-level timestamp.
- `ReplayRecord.dagster_run_id` uses stable logical id
  `orchestrator-p2-current-cycle:{cycle_id}` so retrying the same logical
  cycle under a new Dagster run id does not create conflicting persisted
  payloads.
- The actual Dagster run id remains available in `AuditWriteBundle.metadata`
  for run diagnostics, but is not part of the audit-eval idempotency payload.
- Half-written audit rows recover by writing missing replay rows, and repeated
  retries do not duplicate audit/replay rows.
- `ENT_P2_A`, `ENT_P2_B`, and `synthetic-current-cycle` are covered in both
  frozen-candidate and Tushare staging rejection tests.

## Verification

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/orchestrator
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python \
  -m pytest -q tests/integration/test_p2_dry_run_handoff.py -rs
```

Result: `16 passed`. Warnings are existing Dagster/dbt/Pydantic
deprecations.

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/orchestrator
/opt/homebrew/bin/ruff check \
  src/orchestrator_adapters/p2_dry_run.py \
  tests/integration/test_p2_dry_run_handoff.py \
  pyproject.toml
```

Result: `All checks passed`.

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/audit-eval
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/audit-eval/src \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python \
  -m pytest -q tests/test_audit_writer.py -rs
```

Result: `35 passed`.

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/orchestrator
uv run --extra dev python -m pytest -q \
  tests/integration/test_p2_dry_run_handoff.py \
  -k 'handoff_uses_data_platform_tushare_provider or loads_current_cycle_evidence or rejects_synthetic' \
  -rs
```

Result: `8 passed, 8 deselected`.

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/orchestrator
git diff --check
```

Result: `passed`.

## Independent Review

Subagent retry-safety review:

- Agent: `019dcfce-09ad-7251-9d33-587e0bdf4897`
- Result after fix: P0/P1/P2/P3 `none`.
- Confirmed different actual Dagster run ids rebuild identical persisted
  audit/replay records; actual run id only remains in bundle metadata.

Subagent Tushare coverage review:

- Agent: `019dcfce-0963-7612-a874-99bf2ba2e092`
- Result after fix: P0/P1/P2/P3 `none`.
- Confirmed declared `orchestrator[dev]` targeted regression lane passes and
  job-level handoff uses the default Tushare provider.

## Boundary

This evidence only closes the review findings above. P5 remains blocked by the
separate production daily-cycle provider set, P3 live graph closure, and P4
live registry preflight gates.
