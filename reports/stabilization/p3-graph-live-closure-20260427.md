# P3 Graph Live Closure Evidence - 2026-04-27

## Verdict

Status: PARTIAL PASS.

This evidence closes the assembly GDS enablement prerequisite and the
artifact-backed Layer A cold-reload reader prerequisite. It does not yet close
full P3 because the graph-engine live integration suite still has to be rerun
against the GDS-enabled project Neo4j profile with zero GDS skips.

Update after graph-engine commit `14c32f2fb092c57246789353eb45f9765e99b2e1`:
Phase 1 provider assets and graph snapshot artifact writing are now checked in.
The gate remains PARTIAL because local live GDS validation still skipped when
the worker Neo4j runtime did not expose GDS procedures.

Follow-up commit `78019a73cd83e32534829b3fcbf44468d7738c1e` clears the
independent review P3 findings around candidate-freeze ref synthesis and
numeric checksum parsing. P3 still remains PARTIAL only because live GDS
zero-skip proof is not yet available.

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
- graph-engine provider-set follow-up: `14c32f2fb092c57246789353eb45f9765e99b2e1`
  - Adds `graph_engine.providers.phase1` with `graph_promotion` and
    `graph_snapshot` provider assets.
  - Adds `graph_engine.snapshots.artifact_writer` for Layer A/formal-readable
    graph snapshot artifacts.
  - Keeps missing GDS/runtime boundaries fail-closed.
- graph-engine review follow-up: `78019a73cd83e32534829b3fcbf44468d7738c1e`
  - Requires explicit Phase 0 frozen candidate `selection_ref`.
  - Prevents numeric checksum suffixes from being parsed as
    `graph_generation_id` by artifact writer/reader.

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

Graph Phase 1 provider slice:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/graph-engine
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
python3 -m pytest -q tests/unit/test_phase1_provider.py tests/unit/test_reload_artifact_reader.py

result:
15 passed, 1 skipped
```

Subagent graph validation also ran:

```text
PYTHONPATH=../contracts/src python3 -m pytest \
  tests/unit tests/contract tests/boundary tests/integration/test_reload.py -q

result:
passed, 1 skipped
```

Live GDS suite status from the provider-set worker:

```text
graph-engine live GDS integration suite

result:
4 skipped because local Neo4j did not expose GDS procedures
```

## What This Proves

- The assembly Neo4j profiles now install GDS through the official Docker
  plugin path and have a pinned Neo4j patch version known to resolve a
  compatible GDS artifact.
- A persisted graph artifact can now be converted into a concrete
  `ColdReloadPlan` through `ArtifactCanonicalReader`.
- Invalid, missing, impact-only, and internally inconsistent direct reload-plan
  artifacts fail closed instead of being treated as reloadable graph snapshots.
- Phase 1 provider assets can be assembled and produce a persisted graph
  snapshot artifact for downstream Layer A/cold-reload consumers.
- Phase 1 no longer synthesizes frozen candidate refs when Phase 0 output is
  malformed.
- Artifact generation no longer mistakes an all-numeric checksum suffix for a
  graph generation id.

## Remaining Blockers

- Run the graph-engine live P3 suite against the GDS-enabled project Neo4j
  profile and require zero GDS skips.
- Use the new artifact-backed reader in an end-to-end cold reload from a real
  Layer A graph snapshot produced by Phase 1.
- Do not start P5 until the above live proof is clean.

## Findings

- P0: none.
- P1: live GDS closure remains open because the latest worker run still skipped
  GDS tests when the local Neo4j runtime lacked GDS procedures.
- P2: none.
- P3: independent review P3 findings were fixed in
  `78019a73cd83e32534829b3fcbf44468d7738c1e`; full P3 remains open until the
  live GDS suite and real Layer A cold reload proof pass without skips.
