# Profile Comparison

Use this comparison with [STARTUP_GUIDE.md](STARTUP_GUIDE.md) before changing
profile or bundle manifests.

## Profiles

| Selection | Mode | Default service bundles | Optional bundles | Long-running daemon limit |
| --- | --- | --- | --- | --- |
| `lite-local` | lite | `postgres`, `neo4j`, `dagster` | none | 4 |
| `full-dev` | full | `postgres`, `neo4j`, `dagster` | none by default | 13 |
| `full-dev --extra-bundles=...` | full | `postgres`, `neo4j`, `dagster` plus selected extras | explicit only | 13 |

Both `lite-local` and default `full-dev` resolve the same current module set in
`compatibility-matrix.yaml`. The difference is resource expectation and the
ability for `full-dev` to opt into extra service bundles.

## Lite Local

`lite-local` is the constrained baseline. It starts only PostgreSQL, Neo4j,
Dagster daemon, and Dagster webserver through the core bundle path. It must not
enable Full optional services by default.

Minimum command:

```bash
PYTHONPATH=src python3 -m assembly.cli.main bootstrap \
  --profile lite-local \
  --dry-run
```

## Full Dev Default

Default `full-dev` only includes the core service bundles:
`postgres`, `neo4j`, and `dagster`. It does not start MinIO, Grafana, Superset,
Temporal, Feast, or Kafka-Flink unless they are explicitly selected.

Minimum command:

```bash
PYTHONPATH=src python3 -m assembly.cli.main bootstrap \
  --profile full-dev \
  --dry-run
```

## Full Dev With Optional Bundles

Optional service bundles are selected explicitly with
`full-dev --extra-bundles=...`. Available optional slots are:

- `minio`
- `grafana`
- `superset`
- `temporal`
- `feast`
- `kafka-flink`

Example:

```bash
PYTHONPATH=src python3 -m assembly.cli.main bootstrap \
  --profile full-dev \
  --extra-bundles=minio,grafana,superset \
  --dry-run
```

Use the same `--extra-bundles` value when rendering, bootstrapping, health
checking, or shutting down a run that includes those optional services.
