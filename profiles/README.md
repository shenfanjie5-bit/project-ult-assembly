# Profiles

YAML files in this directory validate as `EnvironmentProfile` (schema
in `src/assembly/contracts/models.py`). Each profile is a named
runtime configuration that pairs a set of enabled modules with a set
of enabled service bundles plus the environment variables required
to wire them together.

## Required schema fields

- `profile_id`
- `mode`
- `enabled_modules`
- `enabled_service_bundles`
- `required_env_keys`
- `optional_env_keys`
- `storage_backends`
- `resource_expectation`
- `max_long_running_daemons`
- `notes`

## Current profiles

| profile_id | status | enabled_modules | enabled_service_bundles | max_long_running_daemons |
|---|---|---|---|---|
| `lite-local` | **verified** at `2026-04-22T06:08:55Z` | 12 active modules (11 subsystems + `assembly`) | `postgres`, `neo4j`, `dagster` | 4 |
| `full-dev` | `draft` | same 12 active modules | `postgres`, `neo4j`, `dagster` + optional bundles per issue scope | 4 (same Lite baseline; optional bundles don't change the Lite baseline count) |

Both profiles pull the SAME 12 active modules — the Stage 4 §4.1.5
harmonization left no profile-specific module gap. The difference
between them is which service bundles are wired and which environment
keys are required; `full-dev` adds optional bundles case-by-case.

The `lite-local` promotion to `verified` requires a real Lite-stack
e2e PASS recorded in `compatibility-matrix.yaml` (`verified_at`
timestamp matches the PASS run). `full-dev` stays `draft` until a
separate `run_min_cycle_e2e("full-dev", ...)` PASS is recorded — the
per-profile evidence boundary was a codex review #10 strict call
(Stage 4 §4.3 must not over-promote `full-dev` by riding on the
Lite-stack PASS).

## CLAUDE.md §10 invariants profiles enforce by construction

- **#2 — Lite long-running daemons fixed at 4**: Postgres + Neo4j +
  Dagster daemon + Dagster webserver. `max_long_running_daemons: 4`
  + `enabled_service_bundles` pinned to `[postgres, neo4j, dagster]`.
- **#3 — Optional bundles off by default**: MinIO, Grafana, Superset,
  Temporal, Feast, Kafka/Flink NEVER auto-enabled in Lite profiles.
- **#4 — DuckDB / dbt Core are embedded, not daemons**: they never
  appear in `enabled_service_bundles` (they're Python-package-level
  concerns owned by `data-platform`'s pyproject).
- **#5 — Iceberg is a format+catalog, not a daemon**: it never appears
  as a standalone service.

## Required env keys (lite-local)

Loaded via `.env` at `assembly/.env` (untracked) and consumed by all
4 compose containers:

| key | consumer | purpose |
|---|---|---|
| `POSTGRES_HOST` / `POSTGRES_PORT` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | postgres container + host-side tests | Postgres connection |
| `NEO4J_AUTH` / `NEO4J_HEAP_INITIAL` / `NEO4J_HEAP_MAX` / `NEO4J_PAGECACHE` | neo4j container | Neo4j config |
| `DAGSTER_HOME` | dagster daemon + webserver | Dagster state dir |
| `DAGSTER_POSTGRES_USER` / `DAGSTER_POSTGRES_PASSWORD` / `DAGSTER_POSTGRES_DB` | dagster daemon + webserver | Postgres-backed run/event/schedule storage |

Inter-container DNS uses the compose service name (e.g.
`DAGSTER_POSTGRES_HOST: postgres` literal in the compose env block);
host-side test code uses `POSTGRES_HOST: localhost` via `.env`. The
two must not be conflated — the bundle manifest pins the former
literal so assembly's compose drift detector catches the mismatch.

## Test coverage

`tests/profiles/test_lite_local_artifacts.py` asserts each required
env key is declared, each enabled module appears in the active-module
set, and the 4-daemon invariant holds. Updates to this profile
require re-running:

```bash
.venv-py312/bin/python -m pytest tests/profiles/
```
