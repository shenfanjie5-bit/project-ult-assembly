# Project ULT v5.0.1 Audit Stage 1-4 Landing - 2026-05-01

## Verdict

**LANDED AS LOCAL SUBREPO COMMITS. No gate status changes.**

The Stage 1-4 audit repairs were split into local commits across the affected
subrepos after targeted validation. Stage 5 remains paused.

This evidence is a landing ledger only. It does not claim M2.6 full proof, M3.3
same-cycle graph consumption, P4 bridge readiness, or P5 shadow-run readiness.

## Scope

Included:

- Stage 1 dependency/version/baseline alignment.
- Stage 2 runtime observability and `python -O` fail-closed hardening.
- Stage 3 security-boundary hardening.
- Stage 4 code/spec alignment items already approved by the project owner.

Excluded:

- Stage 5 schema/protocol single-source-of-truth RFC work.
- M2.6 `graph_snapshot` / `GraphImpactSnapshot` blocker repair.
- P5, shadow-run, P6+, P8, P9, P10, P11.
- Full-stack components outside Lite P1-P5.

## Local Commit Ledger

| Repo | Branch | Local Head | Commit |
|---|---|---:|---|
| `contracts` | `main` | `d7a861e` | `Audit stage 1 contracts baseline alignment` |
| `main-core` | `m2-3a-2-regime-reader` | `b181735` | `Audit stage 1 shared fixture pin` |
| `data-platform` | `m2-6f1-iceberg-canonical-graph-writer-v2` | `84ccedf` | `Audit stage 2 data-platform runtime hardening` |
| `entity-registry` | `main` | `031d2b0` | `Audit stage 1 shared fixture pin` |
| `reasoner-runtime` | `main` | `72c4b11` | `Audit stage 4 reasoner callback hardening` |
| `graph-engine` | `m2-6f1-real-canonical-writer` | `17b5699` | `Audit stage 4 graph runtime hardening` |
| `orchestrator` | `m2-3a-2-phase1-wiring` | `41c11d2` | `Audit stage 3 orchestrator alerting hardening` |
| `audit-eval` | `m2-5-live-pg-roundtrip` | `0a94ec6` | `Audit stage 2 retrospective hook hardening` |
| `frontend-api` | `main` | `9b4ea57` | `Audit stage 3 frontend API boundary hardening` |
| `subsystem-news` | `main` | `d999318` | `Audit stage 1 shared fixture pin` |
| `subsystem-announcement` | `m4-7-docling-llamaindex-preflight` | `1e6d386` | `Audit stage 1 announcement dependency pins` |
| `subsystem-sdk` | `main` | `468b519` | `Audit stage 1 shared fixture pin` |
| `assembly` | `m2-baseline-2026-04-29` | this report commit pending | landing ledger only |

All subrepo commits above are local at the time of this report. They were not
pushed by this landing step.

## Validation

Commands run before committing:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/contracts
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
  tests/test_version.py tests/test_ci_pipeline.py tests/test_pyproject.py -q
```

Result: `30 passed`.

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/reasoner-runtime
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
  tests/unit/test_stage4_trace_metadata.py \
  tests/unit/test_langfuse_callback.py \
  tests/unit/test_callbacks.py -q
```

Result: `37 passed`.

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/orchestrator
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
  tests/alerting/test_dispatcher.py -q
```

Result: `24 passed`.

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/frontend-api
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
  tests/test_security_guard.py -q
```

Result: `17 passed`.

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/graph-engine
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=.:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
.venv/bin/python -m pytest -p no:cacheprovider \
  tests/unit/test_stage4_world_state_guard.py \
  tests/integration/test_live_closure.py -q
```

Result: `5 passed, 1 skipped`.

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=src:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
.venv/bin/python -m pytest -p no:cacheprovider \
  tests/raw/test_writer.py \
  tests/raw/test_health.py \
  tests/cycle/test_current_selection.py -q
```

Result: `43 passed, 2 skipped`.

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/audit-eval
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
  tests/test_retro_compute.py tests/test_retro_summary.py -q
```

Result: `34 passed`.

Hygiene:

```bash
git diff --check
```

Result: clean in `contracts`, `reasoner-runtime`, `orchestrator`,
`frontend-api`, `graph-engine`, `data-platform`, `audit-eval`,
`subsystem-announcement`, `main-core`, `entity-registry`, `subsystem-news`, and
`subsystem-sdk`.

`ruff check`:

- `graph-engine` touched live-closure test: `All checks passed!`
- `reasoner-runtime`, `orchestrator`, and `frontend-api` current local venvs do
  not include `ruff`; no ruff result is claimed for those repos.

## Review Findings Closed By This Landing

- `contracts` baseline test no longer depends on untracked baseline files; the
  `0.1.3/json_schema` artifact and package-data copies were committed.
- `reasoner-runtime` LiteLLM `input_callback` now mutates direct-call message
  content through the scrubber before provider dispatch and logs the bypass.
- Langfuse and OTEL now receive `cycle_id`, `ticker`, `analyzer_type`, and
  `regime_label` trace metadata; derived `session_id`, `user_id`, and tags are
  emitted when enough fields are present.
- LiteLLM callback backend exceptions are logged instead of silently swallowed.
- `orchestrator` webhook SSRF guard resolves and checks all returned IPv4/IPv6
  addresses with deterministic DNS tests.
- `frontend-api` no longer constructs a guarded app at module import time.
- `graph-engine` live closure fixture no longer violates the N-1
  `world_state_ref` guard before exercising the live closure path.
- `subsystem-announcement` dependency lock wording now states it is a partial
  audit pin, not a full transitive `--require-hashes` lock.

## Explicit Non-Claims

- This is not M2.6 full production daily-cycle proof.
- This is not M3.3 production same-cycle graph consumption.
- This is not P4 bridge acceptance.
- This is not M4.7 PASS; M4.7 remains `PARTIAL / PREFLIGHT ARTIFACT`.
- This is not P5 readiness and does not start shadow-run.
- This does not start Stage 5.

## Next Step

Resume the P2/M2.6 primary path only after this landing ledger is committed:

1. Repair the active `graph_snapshot` blocker where `GraphImpactSnapshot`
   currently has no target entity for `CYCLE_20260415`.
2. Rerun the full production daily-cycle proof.
3. Update `production-daily-cycle-full-proof-20260501.md` with the real pass or
   the next blocker.
