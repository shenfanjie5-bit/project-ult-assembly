# Batch 2 LLM / Replay Smoke Evidence

Recorded: 2026-04-26T19:11:06Z

Scope:

- Record Stabilization Batch 2 evidence for the LLM / replay chain.
- Repos changed:
  - `reasoner-runtime`
  - `audit-eval`
- No Codex OAuth token handling logic was changed.
- No Claude Code CLI subprocess invocation logic was changed.
- No frontend-api endpoint, sidecar runtime, command, run, freeze,
  release-freeze, compat-run, e2e-run, min-cycle, replay trigger, or graph
  simulate surface was added.

Commits under smoke:

- reasoner-runtime:
  `f5183f4765f4`
  `Fix replay contract projection and dependency hash`
- audit-eval:
  `2f41580078c0`
  `Validate audit replay hashes and manifest binding`

Resolved risks:

```text
S2-01:
  reasoner-runtime requirements.txt carried a stale litellm 1.83.0 wheel hash.
  The lock now matches the PyPI wheel hash observed with no cache.

S2-02:
  ReplayBundle.to_contract() previously projected to the base
  ContractReasonerReplay fields and dropped the five replay fields.
  It now returns the contract-backed ReplayBundle instance, preserving:
    sanitized_input
    input_hash
    raw_output
    parsed_result
    output_hash

S2-03:
  audit-eval AuditRecord previously required replay hash fields when
  llm_lineage.called=true, but did not recompute input/output hashes.
  It now recomputes sha256(sanitized_input) and sha256(raw_output), rejects
  malformed or mismatched hashes, and verifies llm_lineage hash copies when
  present.

S2-04:
  audit-eval manifest_cycle_id semantics were coupled to execution cycle_id.
  The semantics are now explicit:
    cycle_id is the audit/replay execution cycle axis.
    manifest_cycle_id is the published manifest axis used to bind formal
    snapshot refs.
    replay queries allow these identifiers to differ when the loaded manifest
    published_cycle_id matches replay_record.manifest_cycle_id.
```

Validation:

```text
reasoner-runtime targeted:
  command:
    PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
      .venv/bin/python -m pytest \
      tests/unit/test_contract_exports.py \
      tests/integration/test_generate_structured_replay.py \
      tests/unit/test_replay.py \
      tests/unit/test_dep_lock.py \
      tests/unit/test_config.py \
      -q
  result:
    43 passed

reasoner-runtime broad:
  command:
    PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
      .venv/bin/python -m pytest -q \
      --ignore=tests/regression/test_with_shared_fixtures.py
  result:
    passed

reasoner-runtime dependency hash:
  command:
    pip download --no-deps --no-cache-dir --require-hashes \
      litellm==1.83.0 \
      --hash=sha256:88c536d339248f3987571493015784671ba3f193a328e1ea6780dbebaa2094a8
  result:
    successfully downloaded litellm-1.83.0-py3-none-any.whl

reasoner-runtime dependency lock script:
  command:
    .venv/bin/python scripts/verify_deps.py requirements.txt --all \
      litellm instructor httpx httpcore h11 anyio idna certifi
  result:
    passed

audit-eval targeted:
  command:
    .venv/bin/python -m pytest \
      tests/test_contracts_audit_record.py \
      tests/test_contracts_write_bundle.py \
      tests/test_replay_query.py \
      tests/test_audit_writer.py \
      tests/test_retro_compute.py \
      tests/test_retro_multi_horizon.py \
      -q
  result:
    passed

audit-eval full:
  command:
    .venv/bin/python -m pytest -q
  result:
    passed with 1 skipped and existing evidently/numpy deprecation warnings

audit-eval lint target:
  command:
    .venv/bin/python -m ruff check \
      src/audit_eval/contracts/audit_record.py \
      src/audit_eval/contracts/write_bundle.py \
      src/audit_eval/audit/query.py \
      tests/test_contracts_audit_record.py \
      tests/test_contracts_write_bundle.py \
      tests/test_replay_query.py
  result:
    All checks passed.

diff checks:
  reasoner-runtime:
    git diff --check
    passed

  audit-eval:
    git diff --check
    passed
```

Post-push status:

```text
reasoner-runtime:
  HEAD == origin/main == f5183f4765f4
  working tree clean

audit-eval:
  HEAD == origin/main == 2f41580078c0
  only pre-existing local untracked report/build/dist/egg-info artifacts remain
```

Boundary:

- Batch 2 did not modify `frontend-api`, FrontEnd, assembly matrix, assembly
  registry, or release-freeze surfaces.
- Local `.orchestrator`, `.env`, virtualenv, cache, tmp, build, dist, egg-info,
  and report scratch files were not staged or committed.
- This evidence does not promote any module into verified compatibility matrix
  rows.
