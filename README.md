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

## Current state — Stage 5 closed + MinIO pilot + frontend-api API-1 registered

- 13 of 15 module slots are `integration_status: verified` per
  `module-registry.yaml`. The two frozen slots (`feature-store`,
  `stream-layer`) stay `not_started` per master plan §1.1.
- `frontend-api` is registered with standard public entrypoints and
  API-1 public smoke evidence, but is not folded into the existing
  verified compatibility matrix rows until fresh contract/smoke/e2e
  evidence exists for that matrix identity.
- Compatibility matrix records 3 verified rows:
  - `lite-local` (default): `verified_at: 2026-04-24T05:24:14Z` (Stage
    5 re-verification after audit-eval pin sync 0.2.2 → 0.2.5;
    original Stage 4 §4.3 PASS was `2026-04-22T06:08:55Z`).
  - `full-dev` (default, no extras): `verified_at:
    2026-04-24T05:24:14Z` (Stage 5 full-dev parallel, driven against
    the same 4-service Lite stack since both profiles resolve the
    same 3 core `enabled_service_bundles`).
  - `full-dev + extra_bundles=[minio]`: `verified_at:
    2026-04-24T06:51:23Z` (**first optional bundle pilot** — proves
    `run_min_cycle_e2e`'s new `extra_bundles` kwarg threads through
    render/healthcheck/bootstrap; the new `minio-ready`
    `SocketPortProbe` returned healthy against a MinIO container
    started in a separate compose project).
- Current full-suite baseline on this workspace: 316 passed, 4 skipped.

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
.venv-py312/bin/python -m pytest                         # full suite (316 + 4 skipped)
.venv-py312/bin/python -m pytest tests/registry/         # registry consistency
.venv-py312/bin/python -m pytest tests/compat/           # cross-project compat audit
.venv-py312/bin/python -m pytest tests/e2e/              # minimal-cycle e2e (Lite stack must be up)
.venv-py312/bin/python -m pytest tests/profiles/         # profile artifact assertions
.venv-py312/bin/python -m pytest tests/release/          # release-freeze records
```

## Verified module set (post-Stage 5)

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
| frontend-api | 0.1.0 | v0.1.3 | read-only System/Assembly BFF |
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

- **Remaining 5 optional bundles** (Grafana, Superset, Temporal, Feast,
  Kafka-Flink) — each follows the MinIO pilot template:
  1. Bring bundle service up in the `fulldev` compose project,
  2. Repair any compose/bundle healthcheck drift (MinIO's `curl` →
     `mc ready local` fix at Stage 5 is the canonical example),
  3. Add a built-in `SocketPortProbe` (or HTTP probe) conditionally in
     `src/assembly/health/probes_builtin.py::build_builtin_probes`,
  4. Add a parallel `test_e2e_runner_full_dev_with_<bundle>_extra_bundle`
     in `tests/e2e/test_runner.py`,
  5. Add a `(full-dev, extra_bundles=[<bundle>])` row to
     `compatibility-matrix.yaml` with a fresh `verified_at`.
- Stage-progress closure docs (`docs/VERSION_LOCK.md`,
  `docs/STARTUP_GUIDE.md`, `docs/TROUBLESHOOTING.md`,
  `docs/PROFILE_COMPARISON.md`) — already drafted; final cross-link
  + release-freeze workflow rehearsal pending.
