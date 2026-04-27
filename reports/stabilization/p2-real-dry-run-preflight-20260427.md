# P2 Real Dry-Run Preflight Gate Evidence - 2026-04-27

## Verdict

Status: PASS for P2 real dry-run preflight/gate.

This is not a full P2 completion claim. The verified scope is the minimum
current-cycle L8 handoff preflight: reasoner-runtime-backed L4/L6 generation,
LLM-unavailable hard stop, L4/L6/L7/L8 audit/replay ID contract binding, and
data-platform recommendation provenance fail-closed checks before manifest
publish.

## Backend Commits

- orchestrator: `3e3634b1bb40a8eb7294e1ddeadbaca2c154b2b1`
  - Added optional `orchestrator_adapters.p2_dry_run` provider.
  - Wires L1-L8, formal commit, and manifest publish for a current-cycle P2
    dry-run path.
  - L4 and L6 call `reasoner_runtime.generate_structured_with_replay()`.
  - Builds an audit-eval `AuditWriteBundle` for L4/L6/L7/L8 evidence before
    manifest handoff.
  - Rejects missing audit/replay evidence and smoke/fixture/historical ID
    markers before publish handoff.

- data-platform: `27dfc59965e2338d3ada8a9a217c79f782961e07`
  - Added explicit `source_kind="smoke"` rejection to recommendation
    provenance preflight.
  - Expanded publish manifest tests to cover smoke provenance rejection.

## Supervisor Validation

- orchestrator targeted P2 dry-run handoff:
  - Command:
    `PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/orchestrator/src:/Users/fanjie/Desktop/Cowork/project-ult/main-core/src:/Users/fanjie/Desktop/Cowork/project-ult/reasoner-runtime:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src:/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src:/Users/fanjie/Desktop/Cowork/project-ult/audit-eval/src PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest tests/integration/test_p2_dry_run_handoff.py -q -rs`
  - Result: `3 passed`.

- orchestrator related integration regression:
  - Command:
    `PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/orchestrator/src:/Users/fanjie/Desktop/Cowork/project-ult/main-core/src:/Users/fanjie/Desktop/Cowork/project-ult/reasoner-runtime:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src:/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src:/Users/fanjie/Desktop/Cowork/project-ult/audit-eval/src PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest tests/integration/test_p2_dry_run_handoff.py tests/integration/test_phase2_main_core_wiring.py tests/integration/test_phase3_publish_wiring.py tests/integration/test_daily_cycle_four_phase.py -q -rs`
  - Result: pass.

- orchestrator core boundary scan:
  - Command:
    `PYTHONPATH=src /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python scripts/check_boundaries.py --root .`
  - Result: exit code `0`.

- data-platform manifest/provenance tests without PG DSN:
  - Command:
    `PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest tests/cycle/test_publish_manifest.py -q -rs`
  - Result: `28 passed / 15 skipped`.

- data-platform PG-backed manifest/provenance tests:
  - Command:
    `DP_PG_DSN=<constructed from local docker compose-postgres-1; not printed> PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest tests/cycle/test_publish_manifest.py -q -rs`
  - Result: `43 passed`.

## Independent Gate Review

Reviewer: Sartre, orchestrator P2 dry-run gate

- Findings: no P0/P1/P2.
- P3: audit bundle is validated in memory only. The adapter returns an
  `AuditWriteBundle`, but does not persist it through an audit-eval writer.
- Verification:
  - `tests/integration/test_p2_dry_run_handoff.py`: `3 passed`.
  - `scripts/check_boundaries.py --root .`: exit `0`.
  - `git show --check 3e3634b1bb40a8eb7294e1ddeadbaca2c154b2b1`: clean.
  - Read-only provenance probe produced `L8 current-cycle 4 4`.
- Gate decision: allow assembly evidence.

Reviewer: Epicurus, data-platform provenance gate

- Findings: no P0/P1/P2.
- P3: existing P1C smoke path can still call `publish_manifest()` with
  `source_kind="current-cycle"` and smoke-shaped audit/replay IDs. This is not
  production handoff evidence.
- Verification:
  - Non-PG `tests/cycle/test_publish_manifest.py`: `28 passed / 15 skipped`.
  - PG-backed `tests/cycle/test_publish_manifest.py`: `43 passed`.
  - Extra preflight probe confirmed missing audit/replay IDs, forbidden
    source kinds, and current-cycle mismatch fail closed.
- Gate decision: allow assembly evidence with narrow wording.

## What Is Proven

- P2 dry-run L4 and L6 can route through reasoner-runtime structured replay
  APIs, rather than using historical recommendations as formal output.
- LLM health unavailable fails the Dagster run before L8 and before
  `formal_objects_commit` or `cycle_publish_manifest`.
- The handoff requires L4/L6/L7/L8 audit and replay IDs.
- Smoke, fixture, and historical ID markers are rejected by the P2 adapter
  before publish handoff.
- data-platform preflight explicitly rejects `source_kind="smoke"` and still
  rejects missing provenance, non-current source kind, cycle mismatch, snapshot
  mismatch, and missing audit/replay IDs.

## Residual Risk

- Audit/replay evidence is contract-validated in memory only for this preflight.
  Durable audit-eval persistence is still pending.
- P1C smoke remains a smoke path and must not be counted as production P2
  handoff evidence.
- This does not prove a live production LLM run, full durable audit/replay
  storage, formal serving replay, or 20-trading-day P5 shadow-run readiness.

## Next Required Step

Implement and validate durable audit/replay persistence for the P2 dry-run
handoff, then rerun the same hard-stop and provenance gates with persisted
audit/replay IDs bound to manifest publication.
