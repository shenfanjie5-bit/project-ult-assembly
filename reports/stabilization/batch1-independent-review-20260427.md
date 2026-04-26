# Batch 1 Independent Review Evidence

Recorded: 2026-04-26T19:11:06Z

Scope:

- Independent review of Stabilization Batch 1 items S1-01 through S1-09.
- Read-only review; no code edits, commits, or pushes were made by the reviewer.
- No release-freeze, command, run, compat-run, e2e-run, min-cycle, sidecar, or
  frontend-api endpoint work was performed.

Review result:

```text
S1-01 closed
S1-02 closed
S1-03 closed
S1-04 closed
S1-05 closed
S1-06 closed
S1-07 closed
S1-08 closed
S1-09 closed
```

Reviewer conclusion:

- Batch 1 gate can be marked `closed`.
- No Batch 1 blocking findings remain.
- The reviewer noted unrelated local tracked modifications in
  `reasoner-runtime` during review; those were Batch 2 work and were not part
  of the Batch 1 review.

Commands run:

```text
contracts:
  PYTHON=.venv/bin/python bash scripts/ci.sh
    passed
    installed .[dev,shared-fixtures]
    pulled audit-eval from pinned v0.2.4 at commit 519aeb4235d...

  .venv/bin/python -m pytest
    477 passed

  git diff --check
    passed

  git diff --exit-code -- \
    src/contracts/baselines/0.1.0/json_schema \
    artifacts/baselines/0.1.0/json_schema
    passed

contracts spot check:
  ResolutionCase matched/ambiguous branches require
  candidate_entities minItems=1.
  ResolutionCase unresolved branch has no candidate minItems and allows [].

entity-registry:
  make test with default python3
    inconclusive environment failure: missing audit_eval_fixtures

  PYTHON=.venv/bin/python make test
    354 passed, 1 skipped

  make contract
    15 passed

  PYTHON=.venv/bin/python make contract
    15 passed

  git diff --check
    passed

entity-registry spot check:
  Source grep found no monkey patch of contracts.schemas.ResolutionCase.
  Public alias points to the official contracts model.

main-core:
  bash scripts/check_boundaries.sh with ambient PATH
    failed because lint-imports was not on PATH

  PATH="$PWD/.venv/bin:$PATH" bash scripts/check_boundaries.sh
    passed
    import-linter: 3 kept, 0 broken
    package boundary: 7 passed

  .venv/bin/python -m pytest
    370 passed, 2 skipped

  targeted contract/L8/public tests
    36 passed

  git diff --check
    passed

main-core spot check:
  project-ult-contracts pin is v0.1.3.
  L8 key is canonical "report".
  Envelope roundtrip tests cover AlphaResultSnapshot and
  RecommendationSnapshot.

subsystem-sdk:
  .venv/bin/python -m pytest
    411 passed, 1 skipped

  git diff --check
    passed

subsystem-announcement:
  .venv/bin/python -m pytest
    306 passed, 6 skipped

  git diff --check
    passed

subsystem-news:
  .venv/bin/python -m pytest
    376 passed, 1 skipped

  git diff --check
    passed

subsystem smoke shape spot check:
  Manual assembly SmokeResult.model_validate(...) passed for lite-local,
  full-dev, and bad profile across subsystem-sdk, subsystem-announcement,
  and subsystem-news.
  Top-level keys are only:
    duration_ms
    failure_reason
    hook_name
    module_id
    passed

reasoner-runtime:
  PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
    .venv/bin/python -m pytest \
    tests/unit/test_config.py \
    tests/unit/test_codex_auth.py \
    tests/unit/test_codex_client.py \
    tests/unit/test_claude_code_cli_client.py \
    -q
    53 passed

  git diff --check
    passed

reasoner-runtime selector spot check:
  minimax selector loads one minimax profile.
  codex selector loads one openai-codex profile.
  claude_code selector loads one claude-code profile.
  unknown selector fails with ValueError.
  no selector on three-backend example fails validation, so there is no
  implicit three-backend fallback.

assembly:
  PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python -m pytest -q \
    -p no:cacheprovider \
    tests/cli/test_setup.py \
    tests/cli/test_main.py \
    tests/bootstrap/test_plan.py
    59 passed

  git diff --check
    passed

assembly spot check:
  Grep confirmed docs/setup/compose say MiniMax is container-ready, while
  Codex/Claude are host-managed/runtime-only and container-not-ready unless
  future sidecar/container packaging installs CLIs and mounts auth.
```

Closed items:

- S1-01: contracts CI/version/shared fixture pin drift
- S1-02: entity-registry ResolutionCase monkey patch removal
- S1-03: main-core contract pin and L8 report key alignment
- S1-04: subsystem smoke hook shape alignment
- S1-05: ResolutionCase exported JSON Schema candidate invariant
- S1-06: 0.1.0 contracts baseline immutability
- S1-07: exact ResolutionCase compat allowlist
- S1-08: loadable reasoner-runtime three-backend provider example
- S1-09: assembly Codex/Claude host-only boundary

Boundary:

- This review evidence does not promote any module into verified matrix rows.
- `compatibility-matrix.yaml`, `module-registry.yaml`, `MODULE_REGISTRY.md`,
  and assembly `README.md` are unchanged by this evidence.
