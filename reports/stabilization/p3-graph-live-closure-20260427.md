# P3 Graph Live Closure Evidence - 2026-04-27

## Verdict

Status: PARTIAL PASS.

This evidence closes the assembly GDS enablement prerequisite and the
artifact-backed Layer A cold-reload reader prerequisite. It does not yet close
full P3 because the graph-engine live integration suite still has to be rerun
against the GDS-enabled project Neo4j profile with zero GDS skips.

## Commits

- assembly: `f15549840580b8d631c8577416cd060dd385f7be`
  - Pins Neo4j to `neo4j:5.26.25`.
  - Adds `NEO4J_PLUGINS='["graph-data-science"]'` to Lite/full-dev/bundle
    Neo4j configuration.
  - Adds `p3-gds-enablement-addendum-20260427.md`.
- graph-engine: `dce45c658934c031ae3fe3cc3b4992394ae0444b`
  - Adds `ArtifactCanonicalReader` for persisted Layer A/formal-readable
    graph artifacts.
  - Adds cold-reload artifact reader tests, including persisted artifact
    readback and invalid/missing artifact failures.
- graph-engine follow-up: `41fed9e6db2da802dad9e0d2a53bb076effb5fa4`
  - Validates direct `ColdReloadPlan` artifacts for node/edge count
    consistency instead of accepting internally inconsistent plans.

## Validation

Assembly GDS config:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/assembly
PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python -m pytest -q -p no:cacheprovider \
  tests/bootstrap/test_plan.py \
  tests/profiles/test_lite_local_artifacts.py \
  tests/profiles/test_full_dev.py

result:
40 passed
```

Disposable Neo4j GDS smoke:

```text
neo4j:5.26.25 + NEO4J_PLUGINS='["graph-data-science"]'
SHOW PROCEDURES ... gds.* -> 423 procedures
CALL gds.version() -> "2.13.9"
```

Graph cold-reload artifact reader:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/graph-engine
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
python3 -m pytest tests/unit/test_reload_artifact_reader.py tests/unit/test_reload.py -q

result:
25 passed
```

Subagent graph validation also ran:

```text
PYTHONPATH=../contracts/src python3 -m pytest \
  tests/unit tests/contract tests/boundary tests/integration/test_reload.py -q

result:
passed, 1 skipped
```

## What This Proves

- The assembly Neo4j profiles now install GDS through the official Docker
  plugin path and have a pinned Neo4j patch version known to resolve a
  compatible GDS artifact.
- A persisted graph artifact can now be converted into a concrete
  `ColdReloadPlan` through `ArtifactCanonicalReader`.
- Invalid, missing, impact-only, and internally inconsistent direct reload-plan
  artifacts fail closed instead of being treated as reloadable graph snapshots.

## Remaining Blockers

- Run the graph-engine live P3 suite against the GDS-enabled project Neo4j
  profile and require zero GDS skips.
- Use the new artifact-backed reader in an end-to-end cold reload from a real
  Layer A graph snapshot produced by Phase 1.
- Do not start P5 until the above live proof is clean.

## Findings

- P0: none.
- P1: none.
- P2: none.
- P3: full P3 remains open until the live GDS suite and real Layer A cold
  reload proof pass without skips.
