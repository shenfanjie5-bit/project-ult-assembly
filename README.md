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

## Current state — stabilization gate passed + M4.9 holdings blockers recorded

- 13 of 15 module slots are `integration_status: verified` per
  `module-registry.yaml`. The two frozen slots (`feature-store`,
  `stream-layer`) stay `not_started` per master plan §1.1.
- `frontend-api` is registered with standard public entrypoints and
  read-only API-1 through API-5C smoke/release-readiness evidence. It is
  folded only into the frontend-api-inclusive `lite-local-readonly-ui`
  verified matrix row; the historical `lite-local`/`full-dev` rows keep
  their original evidence identities.
- Stabilization final gate passed on 2026-04-27. Batch 1
  contract/schema cleanup, Batch 2 LLM/replay hardening, Batch 3
  execution/write-boundary hardening, and FrontEnd read-only polish are
  closed in `reports/stabilization/stabilization-master-checklist-20260427.md`.
- `frontend-api` matrix promotion evidence is recorded in
  `reports/stabilization/frontend-api-readonly-ui-promotion-20260427.md`.
  The promoted row keeps old verified rows intact and binds the
  frontend-api-inclusive matrix context to matching smoke/e2e/contract
  evidence.
- M4.3/M4.4 live PostgreSQL bridge evidence was produced on 2026-05-03:
  `make smoke-p1c` passed against an isolated PG database and
  `scripts/m4_ex3_queue_promotion_proof.py` proved public data-platform
  queue/freeze output for a real Ex-3 candidate through graph-engine
  `PromotionPlan`. Closeout evidence:
  `reports/stabilization/m4-bridge-live-proof-20260503.md` and
  `reports/stabilization/m4-ex3-queue-promotion-proof-20260503.json`.
  The proof uses public queue/freeze/graph-reader outputs and artifacts;
  assembly does not read private data-platform tables.
- M3.5 L6 graph-context decision was recorded on 2026-05-05:
  M4.5 may attach graph context only through
  `AlphaAnalysisContext.feature_bundle.graph_features` as
  main-core-managed context. M4.5 deterministic component proof is complete
  and shows sanitized Ex-3 graph context survives reasoner input without
  changing contracts or adding reasoner-runtime imports of graph-engine or
  data-platform. Evidence:
  `reports/stabilization/l6-graph-context-decision-20260505.md`,
  `reports/stabilization/l6-graph-context-decision-20260505.json`,
  `reports/stabilization/m4-ex3-reasoner-consumption-proof-20260505.md`,
  and `reports/stabilization/m4-ex3-reasoner-consumption-proof-20260505.json`.
- M4.6 Ex-3 frontend read-only component proof is complete as deterministic
  TestClient evidence against merged `frontend-api origin/main` PR #2 commit
  `3eee856c4f0ae72acd91a526e46582def0c94151`, with orchestrator PR #115
  commit `947a3a06cfb8c448bf8423bb23ada4147057c57f` referenced as the
  artifact writer. The proof reads a same-cycle synthetic orchestrator
  Ex-3 signal fixture through the read-only API, verifies sanitized response
  fields and GET-only route registration, and records live API/UI smoke as
  blocked when `PROJECT_ULT_FRONTEND_URL` / `PROJECT_ULT_API_BASE` are absent.
  It does not claim live PG e2e, G4/P5 completion, write-path coverage, or
  frontend UI changes. Evidence:
  `reports/stabilization/m4-ex3-frontend-readonly-proof-20260505.md` and
  `reports/stabilization/m4-ex3-frontend-readonly-proof-20260505.json`.
- M4.9 holdings handoff was updated on 2026-05-06:
  `subsystem-holdings` is the next P0 domain extension, and its producer
  scaffold now exists via PR #1 commit
  `e384b48a0260cf1b6636d3fd6de6177ca05f5db8`. Mart shape fidelity landed via
  PR #2 commit `b62cb0b98348f5d5f090397200430edfae2c54b4`; the read-only mart
  adapter proof landed via PR #3 commit
  `752c9842d75048a12b28472ed55c83615f7bd199`; evidence landed via PR #4 commit
  `41ac033125fab3f810b98ad5e7ad5c5606ae227a`. PR #5 blocker evidence landed
  via commit `abfa7603484acc3a0bb09887a4332d490be05046` at
  `subsystem-holdings/docs/evidence/live-producer-proof-blockers-20260506.md`.
  Assembly was already aligned at the boundary level and is now synced to the
  PR #5 exact blockers: `DP_TUSHARE_LIVE_HOLDINGS_BACKFILL` is missing; the
  configured DuckDB target is missing; no available DuckDB/database contains
  all required holdings mart tables; processed data and data storage root
  targets are missing; and complete mart plus lineage inputs are not available
  for live producer proof. The completed proof remains non-live, fixture/local
  DuckDB backed, and limited to a read-only SELECT path. No live producer
  proof, live holdings backfill, provider call from `subsystem-holdings`,
  production queue/live graph proof, graph-engine #55 entry, or
  contracts/subtype change is claimed. `contracts #81` remains CLOSED /
  NOT_PLANNED. M4.7 remains partial; M4.8 remains a future validation gate.
  Evidence:
  `reports/stabilization/m4-9-holdings-scope-decision-20260506.md` and
  `reports/stabilization/m4-9-holdings-scope-decision-20260506.json`.
- M4.9 post-PR1-3 readiness handoff is recorded. Data-platform holdings live
  smoke covers all five promoted interfaces with curated evidence at
  `data-platform/docs/evidence/holdings-live-smoke-20260506.md` and redacted
  credential/code scope status only. Backfill orchestration is merged via
  data-platform PR #102 commit `9629604dae9ed64dafd4d6c223e8b89941f6ad72`
  with bounded inputs, default plan-only mode, and explicit live opt-in.
  Derivation marts are merged via PR #103 commit
  `32289f14252d530fab6cc1aed46c2f0cd5b7c39e` as read-only producer inputs:
  top-holder QoQ change, fund co-holding, and northbound z-score.
  Data-platform evidence/docs are merged via PR #104 commit
  `81f3a57ee3fde8d1dc2a157737af2cd2abba91e5`. Live backfill was not
  executed; credential status was redacted and the explicit live opt-in gate
  was absent.
- Compatibility matrix records 4 verified rows:
  - `lite-local` (default): `verified_at: 2026-04-24T05:24:14Z` (Stage
    5 re-verification after audit-eval pin sync 0.2.2 → 0.2.5;
    original Stage 4 §4.3 PASS was `2026-04-22T06:08:55Z`).
  - `lite-local-readonly-ui` (frontend-api-inclusive): `verified_at:
    2026-04-27T05:34:25.425611Z` (fresh read-only UI
    contract/smoke/e2e evidence bound to this exact matrix context).
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
- Current stabilization gate on this workspace:
  `tests/release/test_docs.py tests/smoke tests/registry tests/compat`
  passed on 2026-04-27.

## Production bridge closure plan

Next assembly-owned planning focus is M4 production bridge closure. Keep the
historical verified compatibility matrix rows intact; the frontend-api-inclusive
row already has its own smoke/e2e/contract evidence, and any future
frontend-api matrix change needs a fresh context-bound evidence set.

M4 priority order:

1. **M4.1-M4.4 bridge closeout**: the direct SDK
   `data_platform_queue` backend is the selected bridge. Live
   `make smoke-p1c` evidence proves non-skipped PG queue/freeze behavior,
   and the Ex-3 proof shows `payload_type='Ex-3'` candidates validate
   through public queue/freeze outputs and become graph-engine promotion
   input with edge output.
2. **M4.5 L6 graph-context implementation**: deterministic component proof
   is complete. Graph context injection stays on the orchestrator/main-core
   side; sanitized Ex-3 graph-delta summaries may enter reasoner input through
   `AlphaAnalysisContext.feature_bundle.graph_features`; do not add
   holdings-specific subtypes, financial-doc scope, graph-engine #55
   algorithms, or reasoner-runtime imports of graph-engine/data-platform.
3. **M4.6 frontend read-only proof**: deterministic component proof is
   complete. The merged frontend-api endpoint reads sanitized same-cycle
   Ex-3 signal artifacts through GET-only TestClient evidence. Live API/UI
   smoke remains blocked when required env/server setup is absent, and this
   proof does not close G4/P5.
4. **M4.7/M4.8 validation gates**: M4.7 remains partial until
   representative A-share documents parse successfully; M4.8 remains the
   future validation gate for entity resolution and fail-closed unresolved
   cases.
5. **M4.9 subsystem scope decision**: scope decision and handoff are recorded.
   `subsystem-holdings` is the next P0 domain extension. Its producer scaffold
   exists, the real read-only mart adapter proof is complete, and PR #5 exact
   live producer blockers are recorded. The proof is non-live, fixture/local
   DuckDB backed, and limited to read-only SELECT access. No live producer
   proof, live holdings backfill, provider call from `subsystem-holdings`,
   production queue/live graph proof, graph-engine #55 entry, or
   contracts/subtype change is claimed. It must continue to use existing
   `Ex3CandidateGraphDelta` submission through `subsystem-sdk` and avoid
   contract/subtype changes. Relations are limited to `CO_HOLDING` /
   `NORTHBOUND_HOLD`; top-shareholder and pledge facts stay on `OWNERSHIP`
   plus properties. `contracts #81` remains CLOSED / NOT_PLANNED.
   `subsystem-financial-doc` remains gated behind M4.7 real-document validation
   and holdings usefulness.
6. **Graph-engine #55 follow-up**: graph-engine #55 remains not entered and
   unimplemented. This handoff does not shift #56/#55 scope, and the old
   financial-doc/contracts-subtype #55 scope must not be revived through M4.9.

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

In the local workspace, `assembly/.env` is a symlink to `../.env`. Keep real
credentials in the workspace-level `project-ult/.env`; the subproject `.env`
path exists only so compose and `assembly --env-file .env` commands continue
to work from this directory. Update or rotate values in `../.env`, not by
creating a second local copy.

Required `.env` keys (loaded by `lite-local.yaml` into all 4
containers): `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`,
`POSTGRES_PASSWORD`, `POSTGRES_DB`, `NEO4J_AUTH`, `NEO4J_HEAP_INITIAL`,
`NEO4J_HEAP_MAX`, `NEO4J_PAGECACHE`, `DAGSTER_HOME`,
`DAGSTER_POSTGRES_USER`, `DAGSTER_POSTGRES_PASSWORD`,
`DAGSTER_POSTGRES_DB`. The `.env` file is intentionally untracked.

LLM backend setup is intentionally narrow. `assembly setup --backend
minimax` writes API env values that are container-ready for compose.
`assembly setup --backend codex` and `assembly setup --backend
claude-code` only write host-managed/runtime-only gates after checking
host auth or host CLI availability. Docker compose currently passes
those gates through as env only; it does not auto-start Codex or Claude,
install their CLIs in the Dagster image, mount host auth/keychain state,
or package a sidecar. Codex/Claude container readiness requires a later
sidecar/container packaging change.

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

## Registered module set

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

- **M4.9 holdings scope handoff** — use
  `reports/stabilization/m4-9-holdings-scope-decision-20260506.md` as the
  boundary for the next P0 domain extension. Data-platform PR #102 / #103 /
  #104 are merged, and `subsystem-holdings` PR #1 / #2 / #3 / #4 prove the
  scaffold plus real read-only mart adapter path. Treat that proof as
  non-live, fixture/local DuckDB backed, and read-only SELECT only: it does not
  close live producer execution, live holdings backfill, production queue
  propagation, live graph propagation, M4.7, or M4.8. Do not use M4.9 to start
  financial-doc work or graph-engine #55 propagation.
- **M4.7/M4.8 validation gates** — M4.7 remains partial until
  real-document parsing is validated on representative A-share documents.
  M4.8 remains the future entity-resolution validation gate with unresolved
  cases handled fail-closed.
- **M4 production bridge closure upkeep** — keep the M4.1-M4.6 bridge and
  read-only evidence linked to their recorded reports. The current holdings
  adapter proof is intentionally non-live and must not be treated as production
  producer or graph propagation closure.
- **frontend-api matrix evidence upkeep** — keep the
  `lite-local-readonly-ui` verified row bound to its recorded
  smoke/e2e/contract-suite evidence. Do not mutate historical verified
  rows; future frontend-api-inclusive matrix changes require fresh
  evidence for that exact context.
- **Real-data mini cycle** — only after the M4 bridge review lands cleanly
  or explicitly defers follow-on validation gates.
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
