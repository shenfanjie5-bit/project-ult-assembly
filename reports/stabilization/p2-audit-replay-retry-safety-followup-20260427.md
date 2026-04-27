# P2 Audit/Replay Retry-Safety Follow-Up - 2026-04-27

## Scope

This follow-up closes the review finding that P2 durable audit/replay writes
were not retry-safe when audit rows were persisted before replay rows.

It also closes the direct Tushare provider regression coverage gap and records
the assembly evidence hygiene fixes made in the same batch.

## Result

Status: `passed`

Closed findings:

- P1: audit/replay durable writes are now bundle-level, retry-safe, and
  fail-closed for split-only storage adapters.
- P3: real Tushare provider and loader coverage now exercises current-cycle
  evidence, DuckDB staging reads, and `ENT_P2` fail-closed behavior.
- P3: future P2 durable Codex dry-run artifacts refresh redacted env status
  after runtime normalization; tracked `.DS_Store` is removed and ignored.

Machine-readable follow-up:

- `reports/stabilization/p2-audit-replay-retry-safety-followup-20260427.json`

## Implementation Evidence

Audit/replay retry safety:

- `audit-eval` adds `persist_audit_write_bundle()`.
- `ManagedDuckDBFormalAuditStorageAdapter.append_audit_write_bundle()` writes
  audit and replay rows inside one transaction.
- Managed writes are idempotent for identical retry payloads.
- Conflicting audit or replay payloads with the same ID are rejected.
- Split-only adapters fail closed for bundle persistence.
- `orchestrator` `AuditEvalPersistencePort` calls the bundle writer once.

Tushare provider regression:

- `DataPlatformTushareCurrentCycleInputProvider` has direct current-cycle
  evidence coverage.
- `_load_frozen_candidate_symbols()` rejects legacy `ENT_P2` synthetic IDs.
- `_load_tushare_staging_rows()` reads DuckDB `stg_daily` /
  `stg_stock_basic` and rejects synthetic source markers.

## Verification

```bash
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/audit-eval/src \
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python \
-m pytest \
/Users/fanjie/Desktop/Cowork/project-ult/audit-eval/tests/test_audit_writer.py \
/Users/fanjie/Desktop/Cowork/project-ult/audit-eval/tests/test_replay_storage_integration.py \
-q
```

Result: `36 passed`.

```bash
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/orchestrator/src:/Users/fanjie/Desktop/Cowork/project-ult/main-core/src:/Users/fanjie/Desktop/Cowork/project-ult/reasoner-runtime:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src:/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src:/Users/fanjie/Desktop/Cowork/project-ult/audit-eval/src \
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python \
-m pytest \
/Users/fanjie/Desktop/Cowork/project-ult/orchestrator/tests/integration/test_p2_dry_run_handoff.py \
-q -rs
```

Result: `10 passed`; warnings are existing Dagster/dbt/Pydantic deprecations.

```bash
git diff --check
git diff --cached --check
```

Result: `passed`.

## Review

Independent retry-safety re-review cleared P1/P2 after the fail-closed bundle
writer fix. Remaining P3 notes were addressed by adding an explicit
bundle-capable protocol and replay conflict coverage.

Independent Tushare/evidence re-review found no P0/P1/P2. Its conditional P3
`.DS_Store` hygiene note is closed by committing `.DS_Store` removal together
with the `.gitignore` rule.

## Boundary

This follow-up does not start P5 and does not expand the P2 real-data closure
scope to news or alternative information sources.
