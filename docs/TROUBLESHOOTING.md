# Troubleshooting

Use this guide with [STARTUP_GUIDE.md](STARTUP_GUIDE.md) and the release audit
rules in [VERSION_LOCK.md](VERSION_LOCK.md).

## Missing Environment

Symptom: `render-profile`, `bootstrap`, `healthcheck`, `smoke`, `contract-suite`,
or `e2e` fails before running probes and reports missing keys.

Check:

```bash
PYTHONPATH=src python3 -m assembly.cli.main render-profile \
  --profile lite-local \
  --env-file .env
```

Fix the `.env` entry or export the key in the shell. Process environment values
override `.env` values.

## PostgreSQL Unhealthy

Symptom: `healthcheck` reports a blocked PostgreSQL probe, or `smoke` fails
before module smoke hooks run.

Check that `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, and
`POSTGRES_PASSWORD` match the host-level endpoint exposed by the selected
compose file. A blocked PostgreSQL result blocks Lite because PostgreSQL is a
core service.

## Neo4j Unhealthy

Symptom: `healthcheck` reports Neo4j as blocked.

Check `NEO4J_URI`, `NEO4J_USER`, and `NEO4J_PASSWORD`. For local compose runs,
the URI should refer to the host-level published port used by the CLI probes.
A blocked Neo4j result blocks Lite because Neo4j is a core service.

## Dagster Webserver Unhealthy

Symptom: Dagster daemon or Dagster webserver probes do not converge.

Check `DAGSTER_HOME`, `DAGSTER_HOST`, and `DAGSTER_PORT`. The webserver must be
reachable from the host-level probe endpoint used by `healthcheck`. If Docker is
running, inspect the container logs and the compose-published host port before
changing profile values.

## Orchestrator Entrypoint

Symptom: `e2e` fails with an orchestrator public CLI import or protocol error.

Check `module-registry.yaml` and `MODULE_REGISTRY.md` for the `orchestrator`
entry with a public `cli` entrypoint. Assembly must not import private module
paths. If the public entrypoint is unavailable, raise a Blocker for the module
owner instead of adding a private import.

## Contract Mismatch

Symptom: `contract-suite` fails with version, public API, SDK, or orchestrator
loadability errors.

Check:

```bash
PYTHONPATH=src python3 -m assembly.cli.main contract-suite \
  --profile lite-local \
  --reports-dir reports/contract
```

Use the contract report JSON to identify the failed public boundary. Do not edit
`compatibility-matrix.yaml` to `verified` manually; promotion remains the job of
`contract-suite --promote` and `promote_matrix_entry(...)`.

## Optional Bundle Credentials

Symptom: `full-dev --extra-bundles=...` fails with missing optional credential
or env reference errors.

Optional bundle env keys must be declared by the profile and assigned when that
bundle is selected. For example, `grafana` requires `GRAFANA_ADMIN_USER` and
`GRAFANA_ADMIN_PASSWORD`, and `superset` requires `SUPERSET_SECRET_KEY`.
Default `full-dev` does not enable optional bundles.

## Host Probe vs Container Healthcheck

Assembly health convergence uses host-level probes: the CLI reads the resolved
profile and checks the endpoint visible from the host process, usually through a
published Docker port. Docker container healthchecks run inside the container
network namespace and may use container-local ports or service names.

Do not treat a host port override as a container healthcheck conclusion. A
host-level probe can fail because the published port is wrong while the
container healthcheck is healthy, and a container healthcheck can fail even when
a host-level port is open. Keep these two meanings separate in reports and in
compose changes.
