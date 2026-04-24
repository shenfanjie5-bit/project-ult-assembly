# assembly

System-integration module. Owns: profile definitions, module registry,
service-bundle manifests, bootstrap, contract-version + public-API
compatibility checks, smoke suite, minimal-cycle e2e runner, and the
`MODULE_REGISTRY` single source of truth. Does NOT own business logic
or any module-private implementation.

Source of truth:

- `docs/assembly.project-doc.md`
- `CLAUDE.md` (project-specific guardrails — boundary rules, blocker
  triggers, KPI baselines)

## Current state — Stage 5 closed (both lite-local + full-dev profiles verified)

- 12 of 14 module slots are `integration_status: verified` per
  `module-registry.yaml`. The two frozen slots (`feature-store`,
  `stream-layer`) stay `not_started` per master plan §1.1.
- Compatibility matrix records BOTH profiles as `verified` at
  `verified_at: 2026-04-24T05:24:14Z`:
  - `lite-local` re-verified after the audit-eval pin sync 0.2.2 →
    0.2.5 (fixture-only bumps; original Stage 4 §4.3 PASS was at
    `2026-04-22T06:08:55Z`).
  - `full-dev` newly verified via Stage 5
    `tests/e2e/test_runner.py::test_e2e_runner_consumes_audit_eval_fixtures_minimal_cycle_full_dev`,
    driven against the same 4-service Lite stack (default `full-dev`
    and `lite-local` resolve the same 3 core
    `enabled_service_bundles` per `docs/PROFILE_COMPARISON.md`).
- Test baseline: 290 passed, 1 skipped (the 1 skipped is the
  degraded-baseline gate that disables when cross-repo modules ARE
  importable — Stage 4 §4.1.5 design). Δ vs Stage 4 §4.3 baseline =
  +1 (the new full-dev e2e test).

## Lite stack quickstart

The four-process Lite profile runs Postgres + Neo4j + Dagster daemon +
Dagster webserver in `docker compose`. The Dagster image is built
locally because `dagster/dagster:1.7.16` is not published on Docker
Hub.

```bash
# from this directory (assembly/)
docker compose -f compose/lite-local.yaml --env-file .env up -d --build
docker compose -f compose/lite-local.yaml --env-file .env ps        # 4/4 should be healthy
docker compose -f compose/lite-local.yaml --env-file .env down -v   # tear down + drop volumes
```

Required `.env` keys (loaded by `lite-local.yaml` into all 4
containers): `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`,
`POSTGRES_PASSWORD`, `POSTGRES_DB`, `NEO4J_AUTH`, `NEO4J_HEAP_INITIAL`,
`NEO4J_HEAP_MAX`, `NEO4J_PAGECACHE`, `DAGSTER_HOME`,
`DAGSTER_POSTGRES_USER`, `DAGSTER_POSTGRES_PASSWORD`,
`DAGSTER_POSTGRES_DB`. The `.env` file is intentionally untracked.

Assembly's compose drift detector
(`src/assembly/compat/checks/service_bundle_drift.py`) literal-matches
each service's `image_or_command` and `env` block against the
declared bundle, so the locally-built image and pinned env map MUST
stay in lockstep with `bundles/dagster.yaml`.

## Test layout

Tests run on the Python 3.12 venv at `.venv-py312/` (Python 3.14
cannot install `dagster<1.10`). Every sibling repo is editable-installed
into this venv so e2e and compat tests can drive real cross-repo
public APIs.

```bash
.venv-py312/bin/python -m pytest                         # full suite (289 + 1 skipped)
.venv-py312/bin/python -m pytest tests/registry/         # registry consistency
.venv-py312/bin/python -m pytest tests/compat/           # cross-project compat audit
.venv-py312/bin/python -m pytest tests/e2e/              # minimal-cycle e2e (Lite stack must be up)
.venv-py312/bin/python -m pytest tests/profiles/         # profile artifact assertions
.venv-py312/bin/python -m pytest tests/release/          # release-freeze records
```

## Verified module set (post-§4.3)

| module_id | module_version | contract_version | role |
|---|---|---|---|
| contracts | 0.1.3 | v0.1.3 | canonical schema owner |
| data-platform | 0.1.1 | v0.1.3 | Layer A canonical truth |
| entity-registry | 0.1.1 | v0.1.3 | entity ID resolver |
| reasoner-runtime | 0.1.1 | v0.1.3 | LLM provider boundary |
| graph-engine | 0.1.1 | v0.1.3 | Ex-3 consumer + propagation |
| main-core | 0.1.1 | v0.1.3 | regime + recommendation |
| audit-eval | 0.2.5 | v0.1.3 | shared fixtures + replay |
| subsystem-sdk | 0.1.2 | v0.1.3 | producer-side preflight |
| orchestrator | 0.1.1 | v0.1.3 | Phase 0/1 + min-cycle CLI |
| assembly | 0.1.0 | v0.0.0 | system integration (this module) |
| subsystem-announcement | 0.1.1 | v0.1.3 | Ex-1/2/3 announcement domain |
| subsystem-news | 0.1.1 | v0.1.3 | Ex-1/2/3 news domain |
| feature-store | 0.0.0 | v0.0.0 | frozen slot |
| stream-layer | 0.0.0 | v0.0.0 | frozen slot |

`MODULE_REGISTRY.md` is the human-readable mirror of
`module-registry.yaml`. Every cell in both files must match — the
registry-consistency loader (`src/assembly/registry/loader.py`)
fails the test suite if MD ⇄ YAML drifts.

## Execution rules

1. Read `docs/assembly.project-doc.md` first.
2. Touch only assembly's own surface (registry / matrix / profiles /
   bundles / compose / bootstrap / health / smoke / e2e). Never import
   another module's private package or internal table.
3. `run_min_cycle_e2e()` MUST go through `orchestrator`. Never bypass.
4. Lite profile's 4 long-running daemons (Postgres + Neo4j + Dagster
   daemon + Dagster webserver) are frozen. Optional services (MinIO,
   Grafana, Superset, Temporal, Feast, Kafka/Flink) only enter via
   explicit additional service bundles, never auto-included.
5. Keep one issue focused on one assembly capability. Do not bundle
   registry + bootstrap + e2e into a single PR.

## Next steps

- Optional service bundles (MinIO / Grafana / Superset / Temporal /
  Feast / Kafka/Flink) — verify per-bundle health probes against
  `full-dev --extra-bundles=<bundle>` invocations of the e2e runner.
  Each bundle is currently structurally-tested only
  (`tests/profiles/test_full_dev.py`); a real-stack PASS would
  promote each to its own evidence row in the compatibility matrix.
- Stage-progress closure docs (`docs/VERSION_LOCK.md`,
  `docs/STARTUP_GUIDE.md`, `docs/TROUBLESHOOTING.md`,
  `docs/PROFILE_COMPARISON.md`) — already drafted; final cross-link
  + release-freeze workflow rehearsal pending.
