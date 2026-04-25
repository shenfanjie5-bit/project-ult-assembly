# frontend-api API-5B Sidecar Design Smoke Evidence

Recorded: 2026-04-25T12:01:57Z

Scope:

- Record API-5B sidecar runtime design evidence.
- Confirm API-5B is design-only and does not implement sidecar auto-start.
- Confirm FrontEnd documents and displays the current external backend mode.
- Confirm the read-only browser surface still renders with the external
  `frontend-api` service and degrades to explicit API unavailable states when
  the API base is unreachable.
- Keep this evidence outside the verified compatibility matrix rows; no matrix
  `module_set` promotion or `verified_at` update is implied.

Commits under smoke:

- frontend-api sidecar design doc:
  `fedcca048aed4b2479ced342065c977472201497`
- FrontEnd API-5B read-only banner/docs:
  `ad4ada5fd6ab8e22342ba907f69f6ded9f4817a2`
- assembly report repo base: `b490d92`

Design evidence:

```text
frontend-api/docs/sidecar-runtime-design.md
  Status states API-5B is design only.
  API-5B does not implement automatic startup, sidecar runtime, packaging, or
  lifecycle management.
  Non-goals include no command endpoints, no direct module reads from the
  frontend, no release-freeze/min-cycle/replay/run/freeze write operations, and
  no multi-user/SaaS/remote deployment work.
  External backend mode remains:
    project-ult-frontend-api serve --host 127.0.0.1 --port 8701
    VITE_PROJECT_ULT_API_BASE=http://127.0.0.1:8701
  The design says API-5B does not change the current read-only route surface.
```

FrontEnd evidence:

```text
FrontEnd README.md
  Documents API-5B as sidecar runtime planning only.
  Current mode remains external backend mode.
  Browser and Tauri dev connect through VITE_PROJECT_ULT_API_BASE or
  VITE_PROJECT_ULT_API_BASE_URL.
  No frontend-api sidecar is auto-started.
  No control entry, write operation, command/run/freeze/min-cycle/replay
  surface is added.

FrontEnd ProjectUltReadOnly banner
  Displays external backend mode.
  Displays that Tauri will not auto-start the frontend-api sidecar.
  Displays that backend unavailable states show Project ULT API unavailable
  instead of a blank page.
```

Tauri dev boundary:

```text
FrontEnd README.md
  Tauri dev uses the external frontend-api service selected by VITE_* env.
  Tauri dev still connects to http://127.0.0.1:8701 when configured.
  The frontend-api backend is not bundled or auto-started by API-5B.

src-tauri/tauri.conf.json from API-5A remains the packaging preflight baseline:
  devUrl: http://127.0.0.1:1420
  beforeDevCommand: npm run dev -- --host 127.0.0.1 --port 1420
```

Runtime:

- `frontend-api`: `http://127.0.0.1:8701`
- Healthy browser dev server: `http://127.0.0.1:1420`
- Healthy browser dev env:
  `VITE_PROJECT_ULT_API_BASE=http://127.0.0.1:8701`
- Backend-unavailable browser dev server: `http://127.0.0.1:1421`
- Backend-unavailable browser dev env:
  `VITE_PROJECT_ULT_API_BASE=http://127.0.0.1:8799`

Backend-running browser smoke:

```text
http://127.0.0.1:1420/project-ult/system?data_mode=projectUlt
  final route: /project-ult/system?data_mode=projectUlt
  title: AI research operating system
  observed:
    Project ULT System Map visible
    frontend-api healthy visible
    Modules 15 and Compat 3 visible
    Project ULT artifact-backed read-only console visible
    Runtime external backend mode visible
    Tauri will not auto-start frontend-api sidecar visible
    No Failed to fetch or NETWORK_ERROR visible

http://127.0.0.1:1420/project-ult/data?data_mode=projectUlt
  final route: /project-ult/data?data_mode=projectUlt
  observed:
    Project ULT Data Explorer visible
    frontend-api healthy footer visible
    read-only Entity/Data Explorer banner visible

http://127.0.0.1:1420/project-ult/graph?data_mode=projectUlt
  final route: /project-ult/graph?data_mode=projectUlt
  observed:
    Project ULT Graph Explorer visible
    frontend-api healthy footer visible
    graph read-only mode banner visible
    no simulate or write action visible

http://127.0.0.1:1420/project-ult/evidence?data_mode=projectUlt
  final route: /project-ult/evidence?data_mode=projectUlt
  observed:
    Project ULT Evidence Console visible
    frontend-api healthy footer visible
    Evidence read-only mode banner visible
```

Backend-unavailable browser smoke:

```text
Simulation:
  launched temporary browser dev server on 127.0.0.1:1421 with
  VITE_PROJECT_ULT_API_BASE=http://127.0.0.1:8799.
  No backend was listening on 8799.
  The temporary 1421 dev server was shut down after the smoke.

http://127.0.0.1:1421/project-ult/system?data_mode=projectUlt
  observed:
    Project ULT System Map shell visible
    Project ULT API unavailable visible
    NETWORK_ERROR visible
    page not blank

http://127.0.0.1:1421/project-ult/data?data_mode=projectUlt
  observed:
    Project ULT Data Explorer shell visible
    Runtime external backend mode banner visible
    Project ULT API unavailable / Failed to fetch states visible
    page not blank

http://127.0.0.1:1421/project-ult/graph?data_mode=projectUlt
  observed:
    Project ULT Graph Explorer shell visible
    Runtime external backend mode banner visible
    Project ULT API unavailable visible
    NETWORK_ERROR visible
    page not blank

http://127.0.0.1:1421/project-ult/evidence?data_mode=projectUlt
  observed:
    Project ULT Evidence Console shell visible
    Runtime external backend mode banner visible
    Project ULT API unavailable visible
    NETWORK_ERROR visible
    page not blank

Note:
  Failed request logs are expected in the backend-unavailable simulation.
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

- API-5B is sidecar runtime design evidence only.
- API-5B does not implement a sidecar runtime.
- API-5B does not auto-start, bundle, or lifecycle-manage `frontend-api`.
- API-5B does not add a backend endpoint.
- `frontend-api` OpenAPI inspection returned no Project ULT `POST` routes:
  `[]`.
- No `POST`, `PUT`, or `DELETE` route is introduced or exercised in this
  smoke.
- No command, run, freeze, release-freeze, compat-run, e2e-run, min-cycle,
  replay POST, or graph simulate endpoint is introduced or exercised.

Matrix boundary:

- This report is API-5B sidecar design smoke evidence only.
- `compatibility-matrix.yaml` verified rows remain unchanged.
- `module-registry.yaml`, `MODULE_REGISTRY.md`, and `README.md` remain
  unchanged by this evidence.
- `frontend-api` and API-5 evidence are not bound to the old verified
  compatibility baseline.
- Future promotion into verified matrix rows requires a separate fresh
  contract/smoke/e2e evidence run and matching `verified_at` update.
