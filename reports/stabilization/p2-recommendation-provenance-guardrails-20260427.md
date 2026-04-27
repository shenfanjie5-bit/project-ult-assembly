# P2 Recommendation Provenance Guardrails - 2026-04-27

Role: Project ULT backend role D

Status: prerequisite guardrail patch completed. This is not a P2 dry run, does not
generate recommendations, and does not publish a formal recommendation.

## Boundary Review

- `data-platform` owns the smallest enforceable boundary: `publish_manifest()`
  is the formal visibility gate for `cycle_publish_manifest`.
- `audit-eval` owns audit/replay row contracts. Its existing
  `AuditRecord`, `ReplayRecord`, and `AuditWriteBundle` shapes already expose
  the row IDs needed for a future recommendation snapshot to bind back to
  audit/replay history.
- `orchestrator` Phase 3 owns gate classification and repair-only rerun
  planning. It should not carry recommendation business provenance logic.

## Implemented Guardrail

Repository: `data-platform`

- Added `data_platform.cycle.recommendation_provenance`.
- `publish_manifest()` now fails closed before database writes unless
  `formal.recommendation_snapshot` has explicit provenance proof.
- The proof requires:
  - `cycle_id == current_cycle_id`
  - `source_layer == "L8"`
  - `source_kind == "current-cycle"`
  - no fixture, historical, or synthetic source kind
  - recommendation snapshot ID matches the manifest snapshot ID
  - non-empty `audit_record_ids` and `replay_record_ids` for future binding

No recommendation data was generated. Existing fixture/historical/synthetic
recommendations remain unusable as current-cycle formal output at this publish
boundary.

## Follow-up Fix

After review, broader PG-backed focused tests exposed legitimate old
`publish_manifest()` callers in manifest-chain, formal-serving, cycle metadata,
and P1c smoke tests. Those callers now provide explicit provenance instead of
weakening the production guardrail.

The P1c smoke path still publishes a `recommendation_snapshot` table as a chain
smoke artifact. Its provenance is technical smoke provenance used to exercise
queue, cycle, manifest, and formal-serving mechanics. It is not meaningful P2
recommendation provenance and must not be interpreted as a generated or formal
P2 recommendation.

## Validation

Commands run from `data-platform`:

- `PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest tests/cycle/test_publish_manifest.py -q`
  - result: `26 passed, 15 skipped`
- `PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m compileall -q src/data_platform/cycle tests/cycle/test_publish_manifest.py`
  - result: passed
- `ruff check src/data_platform/cycle/manifest.py src/data_platform/cycle/recommendation_provenance.py src/data_platform/cycle/__init__.py tests/cycle/test_publish_manifest.py`
  - result: passed
- `DP_PG_DSN` constructed in-process from `compose-postgres-1`, then
  `PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest tests/spike/test_iceberg_publish_manifest_chain.py tests/serving/test_formal.py tests/serving/test_formal_manifest_consistency.py tests/cycle/test_cycle_metadata.py tests/integration/test_p1c_smoke.py -q -rs`
  - result: `43 passed`
  - warnings: six PyIceberg warnings that delete operations did not match any
    records

Note: a local `.venv/bin/python` also exists in `data-platform`, but it is Python
3.14. The py312 command above is the canonical verification for this prerequisite.

## Risk Notes

- P1: Low. The guardrail is fail-closed and touches the formal manifest publish
  path only.
- P2: Medium. Callers that already invoke `publish_manifest()` must now supply
  current-cycle recommendation provenance. This is intentional to prevent P2 dry
  run confusion, but integration callers may need a small update at their Phase 3
  handoff.
- P3: Low. The proof stores bindable audit/replay IDs in the preflight contract,
  but persistence of that provenance beside the manifest remains a future schema
  extension if audit needs queryable provenance metadata.

## Explicit Non-Completion Statement

This work does not mark P2 dry run completed. It only establishes a prerequisite
guardrail that prevents formal recommendation publish without current-cycle
provenance.
