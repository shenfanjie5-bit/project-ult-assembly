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

## Validation

Commands run from `data-platform`:

- `PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest tests/cycle/test_publish_manifest.py -q`
  - result: `26 passed, 15 skipped`
- `PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m compileall -q src/data_platform/cycle tests/cycle/test_publish_manifest.py`
  - result: passed
- `ruff check src/data_platform/cycle/manifest.py src/data_platform/cycle/recommendation_provenance.py src/data_platform/cycle/__init__.py tests/cycle/test_publish_manifest.py`
  - result: passed

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
