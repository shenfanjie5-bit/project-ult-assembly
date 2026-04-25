# frontend-api API-3C Graph Read-Only Smoke Evidence

Recorded: 2026-04-25T05:40:11Z

Scope:

- Record API-3C Graph read-only frontend/backend smoke evidence.
- Confirm the FrontEnd Graph Explorer consumes the existing API-3C backend
  GET endpoints and clamps over-limit URL query params before requesting the
  backend.
- Keep this evidence outside the verified compatibility matrix rows; no matrix
  `module_set` promotion or `verified_at` update is implied.

Commits under smoke:

- Frontend graph smoke commit: `4a5fcc7ecbe6b17f8fbabae8b021adca81145e8b`
- Frontend contract audit commit in ancestry:
  `effe63b Align Project ULT cycle manifest contracts`
- frontend-api: `e5dd0d561c51a9bbd8c0b80b5ab5b78bc6648ae0`
- graph-engine: `63bc514b53b323b979787a1344c9b84352bdcbaa`
- assembly report repo base: `c86cfa1`

Runtime:

- `frontend-api`: `http://127.0.0.1:8701`
- Frontend dev server: `http://127.0.0.1:1420`
- Frontend dev env:
  `VITE_PROJECT_ULT_API_BASE=http://127.0.0.1:8701`

Backend API-3C route checks:

```text
GET /api/project-ult/graph/subgraph?seed=ENT_STOCK_600519.SH&depth=4&limit=500
  status: 200
  source_status: available
  total_nodes: 4
  total_edges: 3

GET /api/project-ult/graph/paths?seed=ENT_STOCK_600519.SH&depth=4&limit=200
  status: 200
  source_status: available
  total: 2

GET /api/project-ult/graph/impact?entity_id=ENT_STOCK_600519.SH
  status: 200
  source_status: available
  total: 2
  snapshot_id: api3c_impact_001
```

Frontend browser smoke:

```text
http://127.0.0.1:1420/project-ult/graph?data_mode=projectUlt
  final route: /project-ult/graph?data_mode=projectUlt
  title: AI 投研操作系统
  observed:
    Project ULT Graph visible
    ENT_STOCK_600519.SH visible
    Kweichow Moutai visible
    EDGE_600519_SECTOR_LIQUOR visible
    PATH_600519_TO_300750_EVENT visible
    api3c_impact_001 visible
    CATL visible
    "422" not visible

http://127.0.0.1:1420/project-ult/graph?data_mode=projectUlt&seed=ENT_STOCK_600519.SH&depth=99&subgraph_limit=9999&paths_limit=9999&entity_id=ENT_STOCK_600519.SH
  final route: /project-ult/graph?data_mode=projectUlt&seed=ENT_STOCK_600519.SH&depth=99&subgraph_limit=9999&paths_limit=9999&entity_id=ENT_STOCK_600519.SH
  title: AI 投研操作系统
  observed:
    Project ULT Graph visible
    ENT_STOCK_600519.SH visible
    Kweichow Moutai visible
    PATH_600519_TO_300750_EVENT visible
    api3c_impact_001 visible
    "422" not visible
    "Unprocessable Entity" not visible
  clamp evidence:
    active query state displayed depth 4
    depth input displayed 4
    subgraph_limit input displayed 500
    paths_limit input displayed 200
  backend clamped requests verified:
    GET /api/project-ult/graph/subgraph?seed=ENT_STOCK_600519.SH&depth=4&limit=500 -> 200
    GET /api/project-ult/graph/paths?seed=ENT_STOCK_600519.SH&depth=4&limit=200 -> 200

http://127.0.0.1:1420/graph?data_mode=projectUlt
  final route: /project-ult/system
  title: AI 投研操作系统
  observed:
    Project ULT System Map visible
    Data Explorer visible
    "422" not visible
```

Boundary checks:

- API-3C is read-only Graph evidence only.
- No backend endpoint was added in this smoke.
- No `POST`, `PUT`, or `DELETE` route is registered by `frontend-api`.
- No `/api/project-ult/graph/simulate` route is present or used.
- No command, run, freeze, release-freeze, compat-run, or e2e-run endpoint is
  present or used.
- No command/run/freeze UI path is introduced or exercised.

Matrix boundary:

- This report is API-3C read-only frontend/backend smoke evidence only.
- `compatibility-matrix.yaml` verified rows remain unchanged.
- `frontend-api` and graph smoke are not bound to the old verified
  compatibility baseline.
- Future promotion into verified matrix rows requires a separate fresh
  contract/smoke/e2e evidence run and matching `verified_at` update.
