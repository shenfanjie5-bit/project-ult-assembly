# P3 GDS Enablement Addendum - 2026-04-27

## Scope

Assembly-owned P3 Graph Closure enablement only.

## Config Change

- Enabled Neo4j Graph Data Science for `compose/lite-local.yaml`.
- Enabled Neo4j Graph Data Science for `compose/full-dev.yaml`.
- Mirrored the same Neo4j plugin environment in `bundles/neo4j.yaml`.
- Pinned the assembly Neo4j image to `neo4j:5.26.25` because the mutable
  `neo4j:5` tag resolved locally to `5.26.21`, for which the Neo4j plugin
  index reported no compatible `graph-data-science` artifact.

Mechanism: Neo4j Docker startup plugin utility with
`NEO4J_PLUGINS='["graph-data-science"]'`, matching the official Neo4j Docker
plugin id for Graph Data Science.

References:

- https://neo4j.com/docs/graph-data-science/current/installation/installation-docker/
- https://neo4j.com/docs/operations-manual/current/docker/plugins/
- https://neo4j.com/docs/graph-data-science/current/installation/supported-neo4j-versions/

## Gate Wording Correction

Current P3 status remains blocked by:

- GDS live proof against a Neo4j instance that exposes `gds.*` procedures.
- Layer A CanonicalReader cold reload proof from persisted canonical graph
  snapshots.

This addendum does not close P3, does not unlock P5, and does not claim a
production daily-cycle proof. It replaces stale Ex-3 / announcement wording as
the active blocker framing for this assembly slice.

## Validation

YAML/config validation:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/assembly

.venv-py312/bin/python - <<'PY'
from pathlib import Path
import yaml
for path in [Path('compose/lite-local.yaml'), Path('compose/full-dev.yaml'), Path('bundles/neo4j.yaml')]:
    with path.open() as fh:
        data = yaml.safe_load(fh)
    print(f'{path}: ok ({type(data).__name__})')
PY

result:
compose/lite-local.yaml: ok (dict)
compose/full-dev.yaml: ok (dict)
bundles/neo4j.yaml: ok (dict)
```

```text
docker compose --env-file .env -f compose/lite-local.yaml config --quiet

result:
passed
```

```text
docker compose --env-file .env -f compose/full-dev.yaml config --quiet

result:
passed, with unrelated optional-service warnings for unset
GRAFANA_ADMIN_USER, GRAFANA_ADMIN_PASSWORD, and SUPERSET_SECRET_KEY.
```

```text
PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python -m pytest -q -p no:cacheprovider \
  tests/bootstrap/test_plan.py \
  tests/profiles/test_lite_local_artifacts.py \
  tests/profiles/test_full_dev.py

result:
40 passed
```

Disposable GDS smoke:

```text
docker volume create assembly_gds_smoke_<timestamp>
docker run -d \
  --name assembly-gds-smoke-<timestamp> \
  -v assembly_gds_smoke_<timestamp>:/data \
  -e NEO4J_AUTH=neo4j/assembly-gds-smoke-pass \
  -e NEO4J_PLUGINS='["graph-data-science"]' \
  neo4j:5.26.25
docker exec assembly-gds-smoke-<timestamp> cypher-shell -u neo4j -p assembly-gds-smoke-pass \
  "SHOW PROCEDURES YIELD name WHERE name STARTS WITH 'gds.' RETURN count(name) AS gds_procedure_count"
docker exec assembly-gds-smoke-<timestamp> cypher-shell -u neo4j -p assembly-gds-smoke-pass \
  "CALL gds.version()"
docker rm -f assembly-gds-smoke-<timestamp>
docker volume rm assembly_gds_smoke_<timestamp>

result:
gds_procedure_count
423
gdsVersion
"2.13.9"

cleanup check:
no assembly-gds-smoke containers or assembly_gds_smoke volumes remain.
```

Unpinned-tag exploratory result:

```text
docker run ... -e NEO4J_PLUGINS='["graph-data-science"]' neo4j:5

result:
Neo4j started, but the image resolved to Neo4j 5.26.21 community and logged:
No compatible "graph-data-science" plugin found for Neo4j 5.26.21 community.
SHOW PROCEDURES returned gds_procedure_count 0.
```

## Findings

- P0: none.
- P1: none.
- P2: none.
- P3: open until GDS live proof and Layer A CanonicalReader cold reload proof
  pass without skips.
