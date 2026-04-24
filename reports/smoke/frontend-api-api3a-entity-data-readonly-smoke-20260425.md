# frontend-api API-3A Entity/Data Read-Only Smoke Evidence

Recorded: 2026-04-24T18:53:58Z

Scope:

- Record API-3A backend read-only Entity/Data routes backed by owning-module
  frontend-api artifacts.
- Record the FrontEnd Project ULT Data Explorer browser smoke that consumes the
  API-3A routes.
- Keep this evidence outside the verified compatibility matrix rows; no matrix
  `module_set` promotion is implied.

Commits under smoke:

- Frontend: `1164b0f40029c880461ff0b35094d68d37c3cbe6`
- frontend-api: `9928626eda3ed7a385db3c58d944b60e3f869803`
- data-platform: `1c362cfbd4168e05b3476b90fe08a3082f1d6f9d`
- entity-registry: `1aaea0ff5265c0f7ac07879c1895793035868f87`
- assembly report repo base: `64bafafb411cf6d7639472d0f8c4ddf1ae8c1c03`

Runtime:

- `frontend-api`: `http://127.0.0.1:8701`
- Frontend dev server: `http://127.0.0.1:1420`

Backend API checks:

```text
GET /api/project-ult/entities/search?limit=1
  status: 200
  source_status: available
  first item: ENT_STOCK_600519.SH
  next_cursor: "1"

GET /api/project-ult/entities/search?limit=1&cursor=1
  status: 200
  source_status: available
  first item: ENT_STOCK_300750.SZ
  next_cursor: null

GET /api/project-ult/entities/ENT_STOCK_600519.SH
  status: 200
  source_status: available
  profile.canonical_entity.canonical_entity_id: ENT_STOCK_600519.SH

GET /api/project-ult/data/canonical/stock_basic?limit=1
  status: 200
  source_status: available
  first item ts_code: 600519.SH
  next_cursor: "1"

GET /api/project-ult/data/raw/tushare_stock_basic?limit=1
  status: 200
  source_status: available
  first item ts_code: 600519.SH
  next_cursor: "1"
```

Frontend Data Explorer check:

```text
http://127.0.0.1:1420/project-ult/data?data_mode=projectUlt&entity_limit=1&entity_cursor=1
  final route: /project-ult/data?data_mode=projectUlt&entity_limit=1&entity_cursor=1
  observed state: Project ULT Data Explorer rendered entity page 2
  visible entity: CATL / ENT_STOCK_300750.SZ
  backend evidence:
    GET /api/project-ult/entities/search?limit=1&cursor=1 -> 200
    GET /api/project-ult/data/canonical/stock_basic?limit=... -> 200
    GET /api/project-ult/data/raw/tushare_stock_basic?limit=... -> 200
```

Source artifacts:

```text
entity-registry/artifacts/frontend-api/entities.json
data-platform/artifacts/frontend-api/data/canonical/stock_basic.json
data-platform/artifacts/frontend-api/data/raw/tushare_stock_basic.json
```

Boundary checks:

- API-3A routes are GET-only read endpoints.
- No Project ULT command, run, freeze, release-freeze, compat/run, e2e/run, or
  POST route is introduced or used by this smoke.
- `frontend-api` reads Entity/Data sources through owning-module stable
  artifacts for this smoke; it does not import sibling private repository or
  table implementations.
- `frontend-api` remains outside the existing verified compatibility matrix
  rows. This report is frontend/backend read-only smoke evidence only.
