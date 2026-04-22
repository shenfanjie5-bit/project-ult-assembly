# Service Bundles

YAML files in this directory validate as `ServiceBundleManifest`
(schema in `src/assembly/contracts/models.py`). Each bundle declares
one logical service group that a profile can pull in.

## Required schema fields

- `bundle_name`
- `services` — list of service entries
- `startup_order`
- `health_checks`
- `required_profiles`
- `optional`
- `shutdown_order`

Each service entry:

- `name`
- `image_or_cmd`
- `health_probe`
- `env` (optional, defaults to `{}`)

## Current bundles

| bundle | services | profile inclusion |
|---|---|---|
| `postgres.yaml` | Postgres 15 | `lite-local`, `full-dev` (required — canonical Layer A backend) |
| `neo4j.yaml` | Neo4j 5 | `lite-local`, `full-dev` (required — live-graph mirror) |
| `dagster.yaml` | `dagster-daemon` + `dagster-webserver` (image `project-ult/dagster-lite:1.7.16`) | `lite-local`, `full-dev` (required) |
| `minio.yaml` | MinIO S3-compatible object store | optional |
| `feast.yaml` | Feast feature store | optional |
| `grafana.yaml` | Grafana dashboards | optional |
| `superset.yaml` | Superset BI | optional |
| `temporal.yaml` | Temporal workflow engine | optional |
| `kafka-flink.yaml` | Kafka + Flink stream stack | optional |

The four required bundles map 1:1 to the four long-running daemons
CLAUDE.md §10 #2 freezes for Lite profiles (Postgres + Neo4j +
Dagster daemon + Dagster webserver). Optional bundles NEVER enter
Lite profiles automatically — only via explicit
`enabled_service_bundles` entries in full-dev or other profiles.

## Dagster image build

`dagster/dagster:1.7.16` is NOT published on Docker Hub, so the
Dagster bundle consumes a locally-built image
`project-ult/dagster-lite:1.7.16`. The Dockerfile + config live under
`../compose/dagster/`:

```
compose/dagster/
├── Dockerfile        # python:3.12-slim base; pins dagster 1.7.16 + dagster-webserver 1.7.16 + dagster-postgres 0.23.16 + psycopg2-binary 2.9.9
├── dagster.yaml      # unified Postgres-backed storage block (DAGSTER_POSTGRES_* env)
└── workspace.yaml    # empty load_from: [] — probe-only mode
```

Compose files in `../compose/lite-local.yaml` + `../compose/full-dev.yaml`
carry `build: { context: ./dagster, dockerfile: Dockerfile }` alongside
the `image:` pin so `docker compose up --build` rebuilds if the
Dockerfile changes. Assembly's compose drift detector
(`src/assembly/compat/checks/service_bundle_drift.py`) literal-matches
the image string and environment block against this bundle — keeping
the compose YAML and this bundle in lockstep is mandatory.

## Drift-detection invariants

`_validate_image_or_command` and `_validate_environment` assert that
each compose service's declared image and env block match the bundle
manifest exactly. Violations fail the assembly test suite. When
updating:

1. Bump the bundle manifest first (`dagster.yaml` here).
2. Mirror the same image + env keys into `compose/lite-local.yaml`
   AND `compose/full-dev.yaml`.
3. Re-run `.venv-py312/bin/python -m pytest tests/compat/` from the
   assembly root to confirm drift is clean.
