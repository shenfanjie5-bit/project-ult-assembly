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

## Current state — bounded gated canary/live production evidence passed

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
- M4.8 entity-resolution proof closeout is complete on 2026-05-07 as an
  assembly evidence aggregation. Entity-registry PR #60 merged at
  `6debd8cc137ee57572fd862959cd845c6dffcab5`, covering deterministic
  exact/code/rule resolution, ambiguous fuzzy candidates not being selected
  automatically, unresolved fail-closed behavior, `ResolutionCase` and audit
  payload shape, and contracts projection. The focused fuzzy backend is
  `injected_fake`, not a real Splink production rollout.
  `subsystem-holdings` PR #12 merged at
  `11c1b1cf62be32c49940293c2e04e89d93ae1ecc`, keeping
  `EntityRegistryAdapter` on public `lookup_alias` / `lookup_entity_refs`,
  preserving unresolved fail-closed behavior, and adding SDK entity preflight
  before queue submit. Holdings live graph proof PR #62 merged at
  `3736799bf362970670b0769e363c75bc15123f79` as adjacent handoff evidence.
  This closeout does not claim production entity registry rollout, production
  queue or live graph rollout, default/full propagation, M4.7 real-document
  completion, financial-doc scope, or contracts subtype work. Evidence:
  `reports/stabilization/m4-8-entity-resolution-proof-20260507.md`.
- M4.9 holdings handoff was updated on 2026-05-07:
  `subsystem-holdings` is the next P0 domain extension, and its producer
  scaffold now exists via PR #1 commit
  `e384b48a0260cf1b6636d3fd6de6177ca05f5db8`. Mart shape fidelity landed via
  PR #2 commit `b62cb0b98348f5d5f090397200430edfae2c54b4`; the read-only mart
  adapter proof landed via PR #3 commit
  `752c9842d75048a12b28472ed55c83615f7bd199`; evidence landed via PR #4 commit
  `41ac033125fab3f810b98ad5e7ad5c5606ae227a`. PR #5 blocker evidence landed
  via commit `abfa7603484acc3a0bb09887a4332d490be05046` at
  `subsystem-holdings/docs/evidence/live-producer-proof-blockers-20260506.md`.
  Data-platform PR #105 / #106 and `subsystem-holdings` PR #6 / #7 / #8 have
  since landed in sibling repos, and attempt2 live proof is reported as
  runtime-verified PASS. Tracked sibling evidence is now merged via
  data-platform PR #107 commit
  `841f7c0f95e8c613e5bac9fe0fe78c09e1f9f152` and `subsystem-holdings`
  PR #9 commit `b046ecf6b54220ceedf517089ebcc883571184d1`. The
  subsystem-holdings adapter fix for incomplete top-holder QoQ rows is
  fail-closed skip diagnostic behavior and is not a blocker for `CO_HOLDING` /
  `NORTHBOUND_HOLD`. The follow-on queue/freeze/promotion proof is now merged:
  `subsystem-sdk` PR #43 released `data_platform_queue` backend support as
  tag `v0.1.3` at merge
  `9c220b7a7a9f5f50b3c57131b501b83fab2e75ce`;
  `subsystem-holdings` PR #10 merged proof-only queue submit path commit
  `63a09b7ca6e6d152279a51857cd497fd8be60fb7`; data-platform PR #108 merged
  holdings Ex-3 queue/freeze bridge proof commit
  `138b78c27b68b1d9b5e7395aec0c396d99dc4202`; graph-engine PR #58 merged
  `edge_upsert` holdings Layer A promotion/query/channel proof commit
  `7eb363cc74325699de5ac46c1362e93cdf470651`. Graph-engine PR #59 then
  merged the scoped `graph-engine #55` holdings-only algorithms as commit
  `8a40fead9a57d67f0b232a52d4ed0d99db78a96e`, and issue #55 is closed.
  The #55 scope is limited to `CO_HOLDING` co-holding crowding and
  `NORTHBOUND_HOLD` northbound anomaly through explicit entry points only.
  This still does not claim production queue, live Neo4j graph propagation,
  default full-propagation rollout, provider/backfill execution from assembly,
  financial-doc scope, guarantees or related-party scope, `MAJOR_CUSTOMER` /
  `MAJOR_SUPPLIER`, or contracts/subtype change. `contracts #81` remains
  CLOSED / NOT_PLANNED. M4.7 remains partial; M4.8 proof is complete only as a
  bounded evidence closeout, not production rollout.
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
  `81f3a57ee3fde8d1dc2a157737af2cd2abba91e5`. That earlier no-live-backfill
  blocker was superseded by attempt2 bounded live backfill evidence merged in
  data-platform PR #107. The later PR #108 / #10 / #43 / #58 handoff proves
  queue submit shape, holdings queue/freeze, and offline Layer A promotion
  compatibility. Graph-engine PR #59 closes #55 with holdings-only algorithms,
  but this assembly handoff still does not enter production queue propagation,
  live Neo4j graph propagation, or default full-propagation rollout.
- M4.9 production hardening prerequisites are landed as guards, not as
  rollout completion. Entity-registry PR #61 merged at
  `ad00cb726ad0576330756f37bf2155a43e4b0e71` with the production readiness
  gate and evidence runner. Data-platform PR #110 merged at
  `74c12cd36b404882ec4425eea3f1b6a14fbfdf02` with Ex-3 `delta_id`
  idempotency, safe receipt, targeted freeze, and worker rejection metrics.
  Graph-engine PR #61 merged at
  `dea63caeec89b16bbd89fb7d5a4174b677e2c394` with rollout guard, canary,
  and evidence support while default propagation stays disabled.
  Subsystem-sdk PR #44 merged at
  `82177a4627d2ce1ac59738da2a13c6e4baee3994`, release PR #45 bumped the
  release, and tag `v0.1.4` points at
  `8d18ccb1877d4243196412322654ab2e8e9d999a`. Subsystem-holdings PR #13
  merged at `612bd5cda3c8054c06e5cbd51de66955a7f0ed58` with the production
  queue submit runner using SDK idempotent-required mode. Evidence:
  `reports/stabilization/holdings-production-hardening-prereqs-20260507.md`.
  That prerequisite state has been superseded by the bounded gated canary/live
  production evidence recorded below; the next step is production rollout
  operationalization and runbook hardening before any controlled
  opt-in/default propagation canary. This does not claim production rollout
  complete, default/full propagation enabled, M4.7 real-doc, financial-doc,
  contracts subtype, or new relations.
- M4.9 bounded gated canary/live production evidence passed on 2026-05-07.
  The curated assembly report records disposable PostgreSQL/Neo4j canary
  resources with data-platform migrations `0001` through `0006`, readiness
  ready over 55 payloads, selected queue execute/receipts/accepted count 46,
  worker accepted 46 and rejected 0, targeted freeze count 46, frozen reader
  relation counts `CO_HOLDING=45` and `NORTHBOUND_HOLD=1`, graph readback
  expected/readback edge count 46 with no missing edge ids and no disallowed
  relation types, and explicit holdings algorithm diagnostics with zero paths.
  Runtime environment details are redacted; no connection string, credential
  value, raw payload, security identifier, fund identifier, or local runtime
  path is recorded.
  Evidence:
  `reports/stabilization/holdings-bounded-canary-live-production-evidence-20260507.md`.
  This still does not claim production rollout complete, default/full
  propagation enabled, `run_full_propagation`, destructive cold reload, M4.7
  real-doc closure, financial-doc scope, contracts subtype, or new relations.
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

## Next Roadmap - post-canary rollout operationalization

Next assembly-owned planning focus is production rollout operationalization and
runbook hardening after assembly #66 passed bounded gated canary/live
production evidence. The next gate is a controlled opt-in/default propagation
canary only after rollback, monitoring, incident response, ownership, audit,
and fail-closed operating procedures are hardened. Keep the historical verified
compatibility matrix rows intact; the frontend-api-inclusive row already has
its own smoke/e2e/contract evidence, and any future frontend-api matrix change
needs a fresh context-bound evidence set.

Priority order:

1. **Operationalize post-canary production rollout runbooks**: harden rollback,
   monitoring, incident response, ownership, audit, and escalation procedures
   before any broader production rollout claim. This remains an operational
   hardening phase, not default/full propagation.
2. **Prepare controlled opt-in/default propagation canary**: keep propagation
   explicit, bounded, observable, auditable, and fail-closed for unresolved
   entities. Do not claim default/full propagation until a controlled canary
   passes and its rollback criteria are reviewable.
3. **Keep M4.1-M4.4 bridge closeout as historical evidence**: the direct SDK
   `data_platform_queue` backend is the selected bridge. Live
   `make smoke-p1c` evidence proves non-skipped PG queue/freeze behavior,
   and the Ex-3 proof shows `payload_type='Ex-3'` candidates validate
   through public queue/freeze outputs and become graph-engine promotion
   input with edge output.
4. **Keep M4.5 L6 graph-context proof bounded**: deterministic component proof
   is complete. Graph context injection stays on the orchestrator/main-core
   side; sanitized Ex-3 graph-delta summaries may enter reasoner input through
   `AlphaAnalysisContext.feature_bundle.graph_features`; do not add
   holdings-specific subtypes, financial-doc scope, graph-engine #55
   algorithms, or reasoner-runtime imports of graph-engine/data-platform.
5. **Keep M4.6 frontend read-only proof bounded**: deterministic component proof is
   complete. The merged frontend-api endpoint reads sanitized same-cycle
   Ex-3 signal artifacts through GET-only TestClient evidence. Live API/UI
   smoke remains blocked when required env/server setup is absent, and this
   proof does not close G4/P5.
6. **Keep M4.7/M4.8 validation gates explicit**: M4.7 remains partial until
   representative A-share documents parse successfully. M4.8 entity-resolution
   proof is complete as a bounded evidence closeout for deterministic
   exact/code/rule resolution, ambiguous fuzzy non-selection, unresolved
   fail-closed handling, `ResolutionCase` / audit payload shape, and contracts
   projection. Production entity registry rollout, real Splink production
   backend rollout, production queue/live graph rollout, and default/full
   propagation remain future planning work.
7. **Use M4.9 holdings scope decision as the domain boundary**: scope decision and handoff are recorded.
   `subsystem-holdings` is the next P0 domain extension. Its producer scaffold
   exists, the real read-only mart adapter proof is complete, and PR #5 blocker
   evidence is no longer the current terminal state. Data-platform PR #105 /
   #106 and `subsystem-holdings` PR #6 / #7 / #8 have landed, and attempt2
   live proof is reported as runtime PASS, with tracked sibling evidence merged
   via data-platform PR #107 commit
   `841f7c0f95e8c613e5bac9fe0fe78c09e1f9f152` and `subsystem-holdings`
   PR #9 commit `b046ecf6b54220ceedf517089ebcc883571184d1`.
   Follow-on proof work is now landed through `subsystem-sdk` PR #43
   (`v0.1.3`), `subsystem-holdings` PR #10, data-platform PR #108, and
   graph-engine PR #58: proof-only queue submit path, holdings Ex-3
   queue/freeze bridge, and offline Layer A promotion/query/channel proof.
   Graph-engine PR #59 then landed and closed #55 with explicit-entry-only
   holdings algorithms: `CO_HOLDING` co-holding crowding and `NORTHBOUND_HOLD`
   northbound anomaly. Assembly still claims no production queue propagation,
   live Neo4j graph propagation, default full-propagation rollout,
   provider/backfill execution from assembly, financial-doc scope, guarantees
   or related-party scope, `MAJOR_CUSTOMER` / `MAJOR_SUPPLIER`, or
   contracts/subtype change. It must continue to use existing
   `Ex3CandidateGraphDelta` submission through `subsystem-sdk` and avoid
   contract/subtype changes. Relations are limited to `CO_HOLDING` /
   `NORTHBOUND_HOLD`; top-shareholder and pledge facts stay on `OWNERSHIP`
   plus properties. `contracts #81` remains CLOSED / NOT_PLANNED.
   `subsystem-financial-doc` remains gated behind M4.7 real-document validation
   and holdings usefulness.
8. **Treat M4.9 hardening/canary as passed evidence, not rollout completion**: prerequisites and guards are
   landed across entity-registry PR #61, data-platform PR #110, graph-engine
   PR #61, subsystem-sdk PR #44 / release `v0.1.4`, and subsystem-holdings
   PR #13. Assembly records this as prerequisites/guards landed only, followed
   by a bounded gated canary/live production evidence pass recorded at
   `reports/stabilization/holdings-bounded-canary-live-production-evidence-20260507.md`.
   Production rollout remains not default-enabled, and this is not production
   rollout complete, default/full propagation enabled, M4.7 real-doc closure,
   financial-doc scope, contracts subtype, or new relation scope.
9. **Graph-engine #55 follow-up**: graph-engine #55 is closed through PR #59,
   narrowed to holdings-only algorithms. It remains explicit-entry-only and
   does not shift into production live graph writeback, default full
   propagation, financial-doc, guarantees, related-party, or contracts subtype
   scope.

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

- **Production rollout operationalization/runbook hardening** — this is the
  current next step after assembly #66 passed bounded gated canary/live
  production evidence. Harden rollback, monitoring, incident response,
  ownership, audit, and fail-closed operating procedures before any broader
  rollout claim.
- **Controlled opt-in/default propagation canary preparation** — after
  runbooks are hardened, prepare a bounded, explicit opt-in/default
  propagation canary with observable acceptance/rejection metrics and rollback
  criteria. Do not enable or claim default/full propagation before that canary
  passes.
- **M4.8 entity-resolution proof closeout** — use
  `reports/stabilization/m4-8-entity-resolution-proof-20260507.md` as the
  bounded evidence handoff. Entity-registry PR #60, subsystem-holdings PR #12,
  and holdings live graph proof PR #62 are merged. This proves deterministic
  resolution and fail-closed integration behavior only; it does not claim
  production entity registry rollout, production queue or live graph rollout,
  default/full propagation, M4.7 real-document completion, financial-doc scope,
  or contracts subtype work.
- **M4.9 holdings scope handoff** — use
  `reports/stabilization/m4-9-holdings-scope-decision-20260506.md` as the
  boundary for the next P0 domain extension. Data-platform PR #102 through
  #108 are merged, `subsystem-holdings` PR #1 through #10 have landed,
  `subsystem-sdk` PR #43 is merged and tagged `v0.1.3`, and graph-engine
  PR #58 is merged. Attempt2 live proof is reported as runtime PASS, and
  sibling evidence is merged in data-platform PR #107 commit
  `841f7c0f95e8c613e5bac9fe0fe78c09e1f9f152` plus `subsystem-holdings`
  PR #9 commit `b046ecf6b54220ceedf517089ebcc883571184d1`. Queue/freeze/
  promotion proof is merged via data-platform PR #108 commit
  `138b78c27b68b1d9b5e7395aec0c396d99dc4202`, subsystem-holdings PR #10
  commit `63a09b7ca6e6d152279a51857cd497fd8be60fb7`, subsystem-sdk PR #43
  commit `9c220b7a7a9f5f50b3c57131b501b83fab2e75ce` with tag `v0.1.3`, and
  graph-engine PR #58 commit `7eb363cc74325699de5ac46c1362e93cdf470651`.
  Graph-engine PR #59 is merged at commit
  `8a40fead9a57d67f0b232a52d4ed0d99db78a96e` and closes #55 with
  holdings-only algorithms: `CO_HOLDING` co-holding crowding and
  `NORTHBOUND_HOLD` northbound anomaly.
  Do not use M4.9 to claim production queue propagation, live Neo4j graph
  propagation, default full-propagation rollout, production entity registry
  rollout, M4.7, financial-doc work, guarantees or related-party scope,
  `MAJOR_CUSTOMER` /
  `MAJOR_SUPPLIER`, or contracts subtype changes.
- **M4.7 validation gate** — M4.7 remains partial until real-document parsing
  is validated on representative A-share documents.
- **M4.9 production hardening prerequisites** — use
  `reports/stabilization/holdings-production-hardening-prereqs-20260507.md`
  as the handoff for landed prerequisites/guards. Entity-registry PR #61,
  data-platform PR #110, graph-engine PR #61, subsystem-sdk PR #44 / release
  `v0.1.4`, and subsystem-holdings PR #13 are merged. Its historical next
  step was bounded gated canary/live production evidence; that gate has since
  passed via assembly #66, so current planning moves to rollout
  operationalization/runbook hardening.
- **M4.9 bounded gated canary evidence** — use
  `reports/stabilization/holdings-bounded-canary-live-production-evidence-20260507.md`
  as the curated assembly report for the passed canary/live production
  evidence. It records only counts, statuses, merge references, and redacted
  environment status. Production rollout remains not default-enabled. Do not
  use this handoff to claim production rollout complete, default/full
  propagation enabled, M4.7 real-doc closure, financial-doc work, contracts
  subtype, or new relations.
- **M4 bridge evidence upkeep** — keep the M4.1-M4.6 bridge and
  read-only evidence linked to their recorded reports. The current holdings
  handoff now points to merged sibling attempt2 evidence PRs #107 and #9, plus
  queue/freeze/promotion proof PRs #108, #10, #43, and #58, plus #55
  holdings-only algorithm PR #59, but it must not be treated as production
  queue or live Neo4j graph propagation closure.
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
