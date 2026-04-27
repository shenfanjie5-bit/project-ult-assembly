# Batch 3 Independent Review Evidence

Recorded: 2026-04-27T04:07:34Z

Scope:

- Independent review of Stabilization Batch 3 execution and write-boundary
  fixes.
- Read-only review; no code edits, commits, or pushes were made by the
  reviewer.
- No release-freeze, command, run, compat-run, e2e-run, min-cycle workflow,
  sidecar, FrontEnd, or frontend-api endpoint work was performed by this
  evidence step.

Commits reviewed:

- orchestrator:
  `c004ee32666097ce67b431869a94b428852c59ad`
  `Harden required artifact paths`
- graph-engine:
  `bee527bc1380880733581e6eab9a4b4159bdb004`
  `Harden reload timeout and readonly writes`
- data-platform:
  `7feebcb39d2321f3d3fe5d030a0b9ba06e3e6a3c`
  `Validate artifact refs and formal manifests`

Review result:

```text
S3-01 orchestrator required_artifacts path traversal: closed
S3-02 graph-engine timeout after background writes: closed
S3-03 graph-engine readonly simulation drop barrier: closed
S3-04 data-platform artifact refs + manifest formal key validation: closed
```

Reviewer conclusion:

- Findings: none.
- Batch 3 gate can be marked `closed`.
- The reviewer did not find evidence that the four risks remain open.

Key review points:

```text
orchestrator:
  File:
    /Users/fanjie/Desktop/Cowork/project-ult/orchestrator/src/orchestrator/cli/min_cycle.py
  Key location:
    line 338
  Result:
    required_artifacts validation rejects empty paths, absolute paths,
    traversal, non-POSIX paths, and non-file targets.
    It uses a resolved root check to catch symlink escape.
    Valid nested relative paths such as nested/cycle_summary still emit a
    relative artifact path.

graph-engine reload timeout:
  File:
    /Users/fanjie/Desktop/Cowork/project-ult/graph-engine/graph_engine/reload/service.py
  Key locations:
    line 166
    line 208
  Result:
    timeout expires a write barrier.
    Neo4j write and status write proxies check that barrier and reject
    post-timeout background writes.

graph-engine readonly simulation:
  File:
    /Users/fanjie/Desktop/Cowork/project-ult/graph-engine/graph_engine/query/simulation.py
  Key location:
    line 296
  Result:
    readonly simulation only allows owned/scoped GDS projection project/drop.
    live mutation writes raise PermissionError.

data-platform:
  Files:
    /Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/raw/writer.py
    /Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/cycle/manifest.py
    /Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/formal_registry.py
  Key locations:
    raw/writer.py line 417
    cycle/manifest.py line 288
    formal_registry.py line 30
  Result:
    artifact ref validation rejects unsafe refs.
    formal manifest key validation is registry-aligned.
```

Commands run by independent reviewer:

```text
orchestrator targeted:
  command:
    .venv/bin/python -m pytest tests/cli/test_min_cycle.py -q
  result:
    27 passed, 1 skipped

orchestrator full:
  command:
    .venv/bin/python -m pytest -q
  result:
    passed

graph-engine targeted:
  command:
    .venv/bin/python -m pytest \
      tests/unit/test_reload.py \
      tests/unit/test_simulation.py \
      tests/boundary/test_red_lines.py \
      -q
  result:
    passed

graph-engine full:
  command:
    .venv/bin/python -m pytest -q
  result:
    passed

data-platform targeted:
  command:
    .venv/bin/python -m pytest \
      tests/raw/test_writer.py \
      tests/cycle/test_publish_manifest.py \
      tests/serving/test_formal.py \
      tests/serving/test_formal_manifest_consistency.py \
      -q
  result:
    passed

data-platform full:
  command:
    .venv/bin/python -m pytest -q
  result:
    passed
```

Backend role validation previously reported:

```text
orchestrator:
  .venv/bin/python -m pytest tests/cli/test_min_cycle.py \
    tests/regression/test_with_shared_fixtures.py -q
    passed
  .venv/bin/python -m pytest -q
    passed
  git diff --check
    passed

graph-engine:
  .venv/bin/python -m pytest tests/unit/test_reload.py \
    tests/unit/test_simulation.py tests/boundary/test_red_lines.py -q
    passed
  .venv/bin/python -m pytest -q
    passed
  git diff --check
    passed

data-platform:
  .venv/bin/python -m pytest tests/raw/test_writer.py \
    tests/cycle/test_publish_manifest.py \
    tests/serving/test_formal.py \
    tests/serving/test_formal_manifest_consistency.py \
    tests/cycle/test_cycle_metadata.py -q
    passed
  .venv/bin/python -m pytest -q
    passed
  git diff --check
    passed
```

Post-push status reported by backend role:

```text
orchestrator:
  ## main...origin/main
  only local .orchestrator and dbt runtime state remain untracked

graph-engine:
  ## main...origin/main
  only local PROJECT_REPORT.md remains untracked

data-platform:
  ## main...origin/main
  only local .orchestrator remains untracked
```

Boundary:

- Batch 3 did not modify FrontEnd or frontend-api.
- Batch 3 did not add endpoints or write APIs.
- Batch 3 did not add command/run/freeze/release-freeze/min-cycle/e2e-run
  surfaces.
- Local `.orchestrator`, `.env`, virtualenv, cache, tmp, dbt runtime state,
  build, dist, egg-info, and report scratch files were not staged or
  committed.
- This evidence does not promote any module into verified compatibility matrix
  rows.
