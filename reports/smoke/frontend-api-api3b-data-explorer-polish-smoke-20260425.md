# frontend-api API-3B Data Explorer Polish Smoke Evidence

Recorded: 2026-04-25T03:58:13Z

Scope:

- Record API-3B FrontEnd read-only polish for the Project ULT Data Explorer.
- Confirm API-3B keeps the API-3A backend surface unchanged and consumes the
  existing read-only Entity/Data routes from `frontend-api`.
- Keep this evidence outside the verified compatibility matrix rows; no matrix
  `module_set` promotion is implied.

Commits under smoke:

- Frontend: `f65894784e30ec1e43709819e24e020eaac23b4b`
- frontend-api: `9928626eda3ed7a385db3c58d944b60e3f869803`
- data-platform: `1c362cfbd4168e05b3476b90fe08a3082f1d6f9d`
- entity-registry: `1aaea0ff5265c0f7ac07879c1895793035868f87`
- assembly report repo base: `e44103d`

Runtime:

- `frontend-api`: `http://127.0.0.1:8701`
- Frontend dev server: `http://127.0.0.1:1420`
- Frontend dev env:
  `VITE_PROJECT_ULT_API_BASE=http://127.0.0.1:8701`

Backend route checks:

```text
GET /api/project-ult/entities/search?limit=1
  status: 200
  source_status: available
  first item: ENT_STOCK_600519.SH / Kweichow Moutai
  next_cursor: "1"

GET /api/project-ult/entities/search?limit=1&cursor=1
  status: 200
  source_status: available
  first item: ENT_STOCK_300750.SZ / CATL
  next_cursor: null

GET /api/project-ult/entities/ENT_STOCK_300750.SZ
  status: 200
  source_status: available
  profile.canonical_entity.canonical_entity_id: ENT_STOCK_300750.SZ
  profile.canonical_entity.display_name: CATL

GET /api/project-ult/data/canonical/stock_basic?limit=1&cursor=1
  status: 200
  source_status: available
  first item: 300750.SZ / CATL
  next_cursor: null

GET /api/project-ult/data/raw/tushare_stock_basic?limit=1&cursor=1
  status: 200
  source_status: available
  first item: 300750.SZ / CATL
  next_cursor: null
```

Browser route checks:

```text
http://127.0.0.1:1420/project-ult/data?data_mode=projectUlt
  final route: /project-ult/data?data_mode=projectUlt
  title: AI 投研操作系统
  observed:
    Project ULT Data Explorer visible
    ENT_STOCK_600519.SH visible
    Kweichow Moutai visible
    canonical/raw 600519.SH rows visible
    tushare raw source visible

http://127.0.0.1:1420/project-ult/data?data_mode=projectUlt&entity_limit=1&entity_cursor=1
  final route: /project-ult/data?data_mode=projectUlt&entity_limit=1&entity_cursor=1
  title: AI 投研操作系统
  request verified:
    GET /api/project-ult/entities/search?limit=1&cursor=1 -> 200
  observed:
    ENT_STOCK_300750.SZ visible
    CATL visible

http://127.0.0.1:1420/project-ult/data?data_mode=projectUlt&canonical_limit=1&canonical_cursor=1
  final route: /project-ult/data?data_mode=projectUlt&canonical_limit=1&canonical_cursor=1
  title: AI 投研操作系统
  request verified:
    GET /api/project-ult/data/canonical/stock_basic?limit=1&cursor=1 -> 200
  observed:
    300750.SZ visible
    CATL visible

http://127.0.0.1:1420/project-ult/data?data_mode=projectUlt&raw_limit=1&raw_cursor=1
  final route: /project-ult/data?data_mode=projectUlt&raw_limit=1&raw_cursor=1
  title: AI 投研操作系统
  request verified:
    GET /api/project-ult/data/raw/tushare_stock_basic?limit=1&cursor=1 -> 200
  observed:
    300750.SZ visible
    CATL visible

http://127.0.0.1:1420/project-ult/system?data_mode=projectUlt
  final route: /project-ult/system?data_mode=projectUlt
  title: AI 投研操作系统
  observed:
    Project ULT System Map visible
    Data Explorer entry visible
```

Risk route redirect checks:

```text
http://127.0.0.1:1420/stock/600519.SH?data_mode=projectUlt
  final route: /project-ult/system
  observed:
    Project ULT System Map visible
    Data Explorer entry visible

http://127.0.0.1:1420/graph?data_mode=projectUlt
  final route: /project-ult/system
  observed:
    Project ULT System Map visible
    Data Explorer entry visible

http://127.0.0.1:1420/admin?data_mode=projectUlt
  final route: /project-ult/system
  observed:
    Project ULT System Map visible
    Data Explorer entry visible
```

Boundary checks:

- API-3B is frontend read-only polish only; no backend endpoint was added.
- No Project ULT `POST`, `PUT`, or `DELETE` route is registered by
  `frontend-api`.
- No command, run, freeze, release-freeze, compat-run, or e2e-run route is
  introduced or used by this smoke.
- Existing API-3A backend routes continue to read from public/stable artifacts.
- `frontend-api` remains outside the existing verified compatibility matrix
  rows. This report is frontend/backend read-only smoke evidence only.
