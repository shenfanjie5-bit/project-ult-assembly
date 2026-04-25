# frontend-api Read-Only Release Handoff

Recorded: 2026-04-25T12:12:38Z

Scope:

- Summarize the Project ULT frontend-api + FrontEnd read-only integration handoff.
- Documentation and release handoff evidence only.
- No backend endpoint is added.
- No frontend behavior is changed.
- No sidecar runtime is implemented.
- No command, run, freeze, release-freeze, compat-run, e2e-run, min-cycle,
  replay trigger, or graph simulate surface is exposed.
- Keep this handoff outside the verified compatibility matrix rows; no matrix
  `module_set` promotion or `verified_at` update is implied.

Repository heads at handoff:

```text
FrontEnd:
  ad4ada5fd6ab8e22342ba907f69f6ded9f4817a2
  Document Project ULT sidecar runtime status

frontend-api:
  fedcca048aed4b2479ced342065c977472201497
  docs(runtime): add API-5B sidecar design

assembly:
  96983d3d7ad817511dd5e63707f600e3fc3a5fbd
  docs(smoke): record frontend API-5C readiness audit

data-platform:
  1c362cf
  Add API-3A frontend data artifacts

entity-registry:
  1aaea0f
  Add API-3A frontend entity artifacts

graph-engine:
  63bc514
  Add API-3C frontend graph artifacts

reasoner-runtime:
  0ed3802
  Add API-4A frontend reasoner artifacts

audit-eval:
  837bab7
  Add API-4A frontend audit artifacts

orchestrator:
  598259d
  Add API-4A frontend orchestrator artifacts
```

Delivered read-only surfaces:

```text
API-1 System / Assembly:
  GET /api/project-ult/health
  GET /api/project-ult/modules
  GET /api/project-ult/profiles
  GET /api/project-ult/compat
  FrontEnd page: /project-ult/system

API-2 Cycle / Formal / Legacy Read-only:
  GET /api/project-ult/cycles
  GET /api/project-ult/cycles/{cycle_id}
  GET /api/project-ult/formal/{object_type}
  GET /api/project-ult/formal/{object_type}/{cycle_id}
  GET /api/project-ult/manifests/latest
  GET /api/world-state/latest
  GET /api/pool/latest
  GET /api/recommendations/latest
  FrontEnd pages: /project-ult/cycles, /, /pool, /recommend

API-3 Entity / Data / Graph Read-only:
  GET /api/project-ult/entities/search
  GET /api/project-ult/entities/{entity_id}
  GET /api/project-ult/data/canonical/{table}
  GET /api/project-ult/data/raw/{source}
  GET /api/project-ult/graph/subgraph
  GET /api/project-ult/graph/paths
  GET /api/project-ult/graph/impact
  FrontEnd pages: /project-ult/data, /project-ult/graph

API-4 Evidence Read-only:
  GET /api/project-ult/reasoner/providers
  GET /api/project-ult/reasoner/results
  GET /api/project-ult/audit/{cycle_id}
  GET /api/project-ult/replay/{cycle_id}
  GET /api/project-ult/backtests
  GET /api/project-ult/backtests/{backtest_id}
  GET /api/project-ult/orchestrator/runs
  GET /api/project-ult/orchestrator/runs/{run_id}
  FrontEnd page: /project-ult/evidence

API-5 Packaging / Runtime Docs:
  External backend mode documented for browser and Tauri dev.
  Sidecar runtime design documented in frontend-api only.
  Tauri sidecar auto-start is not configured.
```

Runtime mode:

```text
Current mode:
  external backend mode

Frontend API base:
  VITE_PROJECT_ULT_API_BASE or VITE_PROJECT_ULT_API_BASE_URL

Default backend during smoke:
  http://127.0.0.1:8701

Default FrontEnd dev during smoke:
  http://127.0.0.1:1420

Tauri:
  devUrl=http://127.0.0.1:1420
  no frontend-api sidecar auto-start
  no managed backend lifecycle
```

Read-only boundary:

- `frontend-api` OpenAPI has 24 `/api/project-ult/*` routes and all are GET.
- Project ULT FrontEnd hooks/pages do not call POST, PUT, PATCH, or DELETE.
- Legacy admin write helpers still exist outside the Project ULT read-only
  surface and remain guarded away in `projectUlt` mode.
- Backend unavailable state is rendered as API unavailable / error envelope,
  not as a blank page.
- Over-limit graph and evidence query parameters are clamped before requests
  reach FastAPI validation bounds.

Explicitly unsupported at handoff:

- command endpoints
- compat/e2e run endpoints
- release-freeze endpoints
- graph simulate endpoint
- replay trigger endpoint
- min-cycle trigger endpoint
- sidecar auto-start
- Tauri-managed frontend-api process lifecycle
- any Project ULT frontend POST/PUT/PATCH/DELETE call

Verified matrix boundary:

```text
compatibility-matrix.yaml verified rows:
  lite-local::default  frontend-api=False
  full-dev::default    frontend-api=False
  full-dev::minio      frontend-api=False

Interpretation:
  frontend-api is registered in assembly as a public module and has smoke
  evidence, but it is not included in the old verified compatibility baselines.
  Any future promotion requires fresh matching contract/smoke/e2e evidence and
  a deliberate matrix update.
```

Evidence inventory:

```text
API-1:
  reports/smoke/frontend-api-api1-public-smoke-20260425.md

API-2:
  reports/smoke/frontend-api-api2a-readonly-no-source-smoke-20260425.md
  reports/smoke/frontend-api-api2b-artifact-success-smoke-20260425.md
  reports/smoke/frontend-api-api2c-readonly-legacy-pages-smoke-20260425.md
  reports/smoke/frontend-api-api2d-readonly-polish-smoke-20260425.md

API-3:
  reports/smoke/frontend-api-api3a-entity-data-readonly-smoke-20260425.md
  reports/smoke/frontend-api-api3b-data-explorer-polish-smoke-20260425.md
  reports/smoke/frontend-api-api3c-graph-readonly-smoke-20260425.md

API-4:
  reports/smoke/frontend-api-api4b-evidence-console-smoke-20260425.md
  reports/smoke/frontend-api-api4c-evidence-contract-polish-smoke-20260425.md

API-5:
  reports/smoke/frontend-api-api5a-packaging-preflight-smoke-20260425.md
  reports/smoke/frontend-api-api5b-sidecar-design-smoke-20260425.md
  reports/smoke/frontend-api-api5c-readonly-release-readiness-20260425.md
```

Operational handoff:

- Start or keep `frontend-api` externally on `127.0.0.1:8701`.
- Start FrontEnd dev on `127.0.0.1:1420`.
- Use `data_mode=projectUlt` or select Project ULT API in the footer.
- Validate the main read-only pages:
  `/project-ult/system`, `/project-ult/cycles`, `/project-ult/data`,
  `/project-ult/graph`, `/project-ult/evidence`, `/`, `/pool`, `/recommend`.
- Treat `/admin`, `/subsystems`, `/audit`, legacy `/graph`, and stock detail
  routes as guarded surfaces in `projectUlt` mode.

Residual risks and next gates:

- This handoff is not a verified compatibility matrix promotion.
- Sidecar runtime remains design-only.
- Release-freeze remains intentionally unexposed through HTTP and FrontEnd.
- Future write/control surfaces need a separate design with confirmation token,
  dry-run behavior, allowlist, audit log, and fresh review.
