# P3 Graph Live Closure Evidence - 2026-04-28

## Verdict

Status: PASS for Backend-A P3 Graph Live Closure.

This closes the live GDS proof that was still open in the 2026-04-27 evidence:
candidate deltas now have an executable live proof through promotion, GDS
propagation, `graph_snapshot` + `graph_impact_snapshot`, Layer A/formal-readable
artifact writing, `ArtifactCanonicalReader`, and artifact-backed `cold_reload`.

This does not start P5 and does not add API-6, sidecar, frontend write API,
Kafka, Flink, Temporal, news, or Polymarket production flow.

## Scoped Repos

- graph-engine: `fc4e083e1328333f0320fa7c0afa96d0b0dd6b37`
  - Normalizes live Neo4j metric payloads to JSON-safe values before snapshot
    artifact serialization.
  - Rebuilds cold-reload GDS projections from existing supported relationship
    types only, avoiding GDS rejection of sparse graphs.
  - Adds a live integration test for candidate delta -> promotion -> GDS
    propagation -> graph/impact snapshots -> formal artifact ->
    `ArtifactCanonicalReader` -> live cold reload.
  - Cleans up the small benchmark integration's synthetic data and GDS
    projection after the test.
- assembly: this evidence report only.

No compatibility matrix verified rows were touched.

## Live GDS Runtime

Disposable Neo4j:

```text
docker run -d --name p3-graph-live-closure-20260428 \
  -p 127.0.0.1:17687:7687 \
  -p 127.0.0.1:17474:7474 \
  -e NEO4J_AUTH=neo4j/p3-live-closure-pass \
  -e NEO4J_PLUGINS='["graph-data-science"]' \
  neo4j:5.26.25
```

GDS verification:

```text
CALL gds.version() YIELD gdsVersion RETURN gdsVersion
result: "2.13.9"

CALL gds.graph.exists('p3_live_closure_probe') YIELD graphName, exists
RETURN graphName, exists
result: "p3_live_closure_probe", false

SHOW PROCEDURES YIELD name WHERE name STARTS WITH 'gds.'
RETURN count(name) AS gds_procedure_count
result: 423
```

Cleanup:

```text
docker rm -fv p3-graph-live-closure-20260428
result: removed; no p3-graph-live-closure-20260428 container remains
```

## Validation

Focused live P3 suite with zero GDS skips:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/graph-engine

env PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
  NEO4J_URI=bolt://localhost:17687 \
  NEO4J_USER=neo4j \
  NEO4J_PASSWORD=p3-live-closure-pass \
  NEO4J_DATABASE=neo4j \
  /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python \
  -m pytest -q -rs \
  tests/integration/test_promotion_sync.py \
  tests/integration/test_full_propagation.py \
  tests/integration/test_propagation_snapshot.py \
  tests/integration/test_reload.py \
  tests/integration/test_live_closure.py

result:
6 passed, 0 skipped
```

Focused unit/regression for changed graph-engine code:

```text
python3 -m ruff check \
  graph_engine/reload/projection.py \
  graph_engine/live_metrics.py \
  tests/unit/test_reload.py \
  tests/unit/test_live_metrics.py \
  tests/integration/test_live_closure.py \
  tests/integration/test_benchmark_neo4j.py

result:
All checks passed.
```

```text
env PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
  NEO4J_URI=bolt://localhost:17687 \
  NEO4J_USER=neo4j \
  NEO4J_PASSWORD=p3-live-closure-pass \
  NEO4J_DATABASE=neo4j \
  /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python \
  -m pytest -q \
  tests/unit/test_live_metrics.py \
  tests/unit/test_reload.py \
  tests/integration/test_benchmark_neo4j.py

result:
20 passed
```

Offline graph-engine unit/contract/boundary suite:

```text
env PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
  /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python \
  -m pytest -q -rs tests/unit tests/contract tests/boundary

result:
390 passed
```

Git whitespace check:

```text
git diff --check

result:
passed
```

## What This Proves

- Contract `CandidateGraphDelta` input can be promoted through the Phase 1
  graph service into Layer A canonical writer calls and the Neo4j live graph.
- GDS is present and used by the live propagation/snapshot path without GDS
  skips.
- Live Neo4j temporal values no longer prevent formal graph artifact
  serialization.
- The generated formal graph artifact can be read by `ArtifactCanonicalReader`
  into a concrete `ColdReloadPlan`.
- Artifact-backed `cold_reload` clears and rebuilds the live graph, recreates
  the GDS projection, verifies live metrics, and returns ready status.
- Sparse cold-reload graphs no longer fail GDS projection rebuild because absent
  relationship types are not sent to `gds.graph.project`.

## Non-Gating Observation

An exploratory broader Neo4j integration run that included non-closure query and
status tests still has two expectation failures outside this closure proof:

- `tests/integration/test_query.py::test_query_propagation_paths_uses_effective_channel_filter`
  expects path `properties` to exclude the live `propagation_channel` property.
- `tests/integration/test_status.py::test_live_graph_consistency_matches_snapshot_and_detects_mutation`
  expects a contract `GraphSnapshot` without explicit generation metadata to
  satisfy a generation-aware status consistency check.

These failures are not in the Backend-A live closure suite above and were not
expanded in this task.

## Findings

- P0: none.
- P1: none. The focused P3 live suite passed against GDS with zero skips.
- P2: none for Backend-A live closure.
- P3: non-gating query/status integration expectations listed above remain
  outside this closure scope.
