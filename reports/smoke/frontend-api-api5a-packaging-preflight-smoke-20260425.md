# frontend-api API-5A Packaging / Tauri Read-Only Preflight Smoke Evidence

Recorded: 2026-04-25T09:35:26Z

Scope:

- Record API-5A packaging and Tauri read-only preflight smoke evidence.
- Confirm FrontEnd packaging configuration points browser/Tauri dev to the
  existing read-only `frontend-api` service.
- Confirm browser dev works when the backend is running and degrades cleanly
  when the backend is unavailable.
- No full Tauri desktop window or Rust compile was run in this smoke.
- Keep this evidence outside the verified compatibility matrix rows; no matrix
  `module_set` promotion or `verified_at` update is implied.

Commits under smoke:

- FrontEnd API-5A packaging preflight:
  `db70c45ed576a276b2d48921fbfcf28beb136de9`
- assembly report repo base: `d5746c7`

Runtime:

- `frontend-api`: `http://127.0.0.1:8701`
- Healthy browser dev server: `http://127.0.0.1:1420`
- Healthy browser dev env:
  `VITE_PROJECT_ULT_API_BASE=http://127.0.0.1:8701`
- Backend-unavailable browser dev server: `http://127.0.0.1:1421`
- Backend-unavailable browser dev env:
  `VITE_PROJECT_ULT_API_BASE=http://127.0.0.1:8799`

Config evidence:

```text
.env.example
  VITE_PROJECT_ULT_API_BASE=http://127.0.0.1:8701
  VITE_PROJECT_ULT_API_BASE accepts the service root; the frontend appends /api.
  VITE_PROJECT_ULT_API_BASE_URL=http://127.0.0.1:8701/api is documented as
  the direct API-root alternative.

README.md browser dev
  VITE_DATA_MODE=projectUlt \
  VITE_PROJECT_ULT_API_BASE=http://127.0.0.1:8701 \
  npm run dev -- --host 127.0.0.1 --port 1420

README.md Project ULT Tauri dev
  VITE_DATA_MODE=projectUlt \
  VITE_PROJECT_ULT_API_BASE=http://127.0.0.1:8701 \
  npm run tauri -- dev

README.md Tauri/backend boundary
  Tauri dev uses src-tauri/tauri.conf.json devUrl=http://127.0.0.1:1420.
  Tauri does not start a Project ULT sidecar.
  beforeDevCommand inherits the shell VITE_* environment.

src-tauri/tauri.conf.json
  build.devUrl: http://127.0.0.1:1420
  build.beforeDevCommand: npm run dev -- --host 127.0.0.1 --port 1420
```

Backend-running browser dev smoke:

```text
http://127.0.0.1:1420/project-ult/system?data_mode=projectUlt
  final route: /project-ult/system?data_mode=projectUlt
  title: AI 投研操作系统
  observed:
    Project ULT System Map visible
    healthy visible
    API-4A entry/context visible
    "CORS" not visible
    "404" not visible
    "Failed to fetch" not visible
    "NETWORK_ERROR" not visible

http://127.0.0.1:1420/project-ult/data?data_mode=projectUlt
  final route: /project-ult/data?data_mode=projectUlt
  title: AI 投研操作系统
  observed:
    Project ULT Data Explorer visible
    ENT_STOCK_600519.SH visible
    Kweichow Moutai visible
    CATL visible
    "CORS" not visible
    "404" not visible
    "Failed to fetch" not visible
    "NETWORK_ERROR" not visible

http://127.0.0.1:1420/project-ult/graph?data_mode=projectUlt
  final route: /project-ult/graph?data_mode=projectUlt
  title: AI 投研操作系统
  observed:
    Project ULT Graph visible
    ENT_STOCK_600519.SH visible
    Kweichow Moutai visible
    PATH_600519_TO_300750_EVENT visible
    "CORS" not visible
    "404" not visible
    "Failed to fetch" not visible
    "NETWORK_ERROR" not visible

http://127.0.0.1:1420/project-ult/evidence?data_mode=projectUlt
  final route: /project-ult/evidence?data_mode=projectUlt
  title: AI 投研操作系统
  observed:
    Project ULT Evidence Console visible
    reasoner_primary_structured visible
    BT_API4A_001 visible
    RUN_API4A_001 visible
    "CORS" not visible
    "404" not visible
    "Failed to fetch" not visible
    "NETWORK_ERROR" not visible

Browser console:
  error logs: []
```

Backend-unavailable browser dev smoke:

```text
Simulation:
  launched temporary browser dev server on 127.0.0.1:1421 with
  VITE_PROJECT_ULT_API_BASE=http://127.0.0.1:8799.
  No backend was listening on 8799.
  The temporary 1421 dev server was shut down after the smoke.

http://127.0.0.1:1421/project-ult/system?data_mode=projectUlt
  final route: /project-ult/system?data_mode=projectUlt
  title: AI 投研操作系统
  observed:
    Project ULT System Map shell visible
    Project ULT API unavailable visible
    NETWORK_ERROR visible
    page not blank
    uncaught runtime error count: 0

http://127.0.0.1:1421/project-ult/data?data_mode=projectUlt
  final route: /project-ult/data?data_mode=projectUlt
  title: AI 投研操作系统
  observed:
    Project ULT Data Explorer shell visible
    Project ULT API unavailable visible
    NETWORK_ERROR visible
    page not blank
    uncaught runtime error count: 0

http://127.0.0.1:1421/project-ult/graph?data_mode=projectUlt
  final route: /project-ult/graph?data_mode=projectUlt
  title: AI 投研操作系统
  observed:
    Project ULT Graph shell visible
    Project ULT API unavailable visible
    NETWORK_ERROR visible
    page not blank
    uncaught runtime error count: 0

http://127.0.0.1:1421/project-ult/evidence?data_mode=projectUlt
  final route: /project-ult/evidence?data_mode=projectUlt
  title: AI 投研操作系统
  observed:
    Project ULT Evidence Console shell visible
    Project ULT API unavailable visible
    NETWORK_ERROR visible
    page not blank
    uncaught runtime error count: 0

Note:
  Failed resource/request logs are expected in backend-unavailable simulation.
```

Route guard smoke:

```text
http://127.0.0.1:1420/admin?data_mode=projectUlt
  final route: /project-ult/system
  Project ULT System Map visible

http://127.0.0.1:1420/subsystems?data_mode=projectUlt
  final route: /project-ult/system
  Project ULT System Map visible

http://127.0.0.1:1420/audit?data_mode=projectUlt
  final route: /project-ult/system
  Project ULT System Map visible

http://127.0.0.1:1420/graph?data_mode=projectUlt
  final route: /project-ult/system
  Project ULT System Map visible
```

Read-only boundary:

- API-5A is packaging/Tauri preflight evidence only.
- API-5A does not add a backend endpoint.
- API-5A does not add or start a Project ULT sidecar.
- `frontend-api` OpenAPI inspection returned no Project ULT `POST`, `PUT`, or
  `DELETE` routes.
- No command, run, freeze, release-freeze, compat-run, e2e-run, min-cycle, or
  replay POST endpoint is present or used.
- No command/run/freeze UI path is introduced or exercised.

Matrix boundary:

- This report is API-5A packaging preflight smoke evidence only.
- `compatibility-matrix.yaml` verified rows remain unchanged.
- `frontend-api` and API-5 evidence are not bound to the old verified
  compatibility baseline.
- Future promotion into verified matrix rows requires a separate fresh
  contract/smoke/e2e evidence run and matching `verified_at` update.
