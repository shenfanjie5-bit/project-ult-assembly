# FrontEnd Raw Route Alignment Fix - 2026-04-28

## Verdict

Status: PASS for the scoped FrontEnd/frontend-api raw route alignment fix.

This closes the narrow finding that the FrontEnd Data Explorer still called
`/api/project-ult/data/raw/{source}` after frontend-api removed that route from
the default production read-only surface.

This does not claim P5 readiness, does not promote raw/debug routes to
production, and does not add write/control endpoints.

## Scope

Changed files:

- `/Users/fanjie/Desktop/BIG/FrontEnd/src/pages/DataExplorer/index.tsx`
- `/Users/fanjie/Desktop/BIG/FrontEnd/src/api/projectUlt/hooks.ts`
- `/Users/fanjie/Desktop/Cowork/project-ult/frontend-api/README.md`

Pre-existing FrontEnd dirty files retained:

- `/Users/fanjie/Desktop/BIG/FrontEnd/README.md`
- `/Users/fanjie/Desktop/BIG/FrontEnd/src/mocks/data/projectUltData.ts`

## What Changed

- Data Explorer no longer imports or calls `useProjectUltRawData`.
- Data Explorer no longer renders the production Raw Data card, raw source
  selector, `raw_limit` URL sync, or `tushare_stock_basic` source-specific
  default.
- Project ULT Data Explorer banner now lists only business read-only GET
  surfaces:
  - `/project-ult/entities/search`
  - `/project-ult/entities/{entity_id}`
  - `/project-ult/data/canonical/{table}`
- FrontEnd projectUlt hooks no longer define a default
  `/project-ult/data/raw/{source}` query.
- frontend-api README no longer lists
  `/api/project-ult/data/raw/{source}` as a default release surface. It now
  documents raw artifacts as optional debug-only through
  `/api/project-ult/debug/data/raw/{source}` when
  `PROJECT_ULT_FRONTEND_API_ENABLE_RAW_DEBUG_ROUTES=1`.

## Validation

FrontEnd source scan:

```text
cd /Users/fanjie/Desktop/BIG/FrontEnd
rg -n "useProjectUltRawData|/project-ult/data/raw|/api/project-ult/data/raw|tushare_stock_basic" src

result:
no matches
```

FrontEnd type check:

```text
cd /Users/fanjie/Desktop/BIG/FrontEnd
npm run check -- --pretty false

result:
passed
```

frontend-api focused tests:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/frontend-api
PYTHONDONTWRITEBYTECODE=1 /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python \
  -m pytest -p no:cacheprovider -q \
  tests/test_no_source_leak.py tests/test_entity_data_routes.py

result:
13 passed
```

Whitespace checks:

```text
cd /Users/fanjie/Desktop/BIG/FrontEnd
git diff --check
result: passed

cd /Users/fanjie/Desktop/Cowork/project-ult/frontend-api
git diff --check
result: passed
```

## Findings

- P0: none.
- P1: none for this scoped FrontEnd/backend raw route alignment.
- P2: none for this scoped alignment.
- P3: raw debug route tests still mention `tushare_stock_basic`, but only under
  explicit debug-route test coverage. The default FrontEnd production path no
  longer exposes that source-specific raw selector.

## Residual Risk

This fix closes only the FrontEnd/backend route mismatch. It does not address
the larger P1/P2 findings from
`project-ult-v5-0-1-supervisor-review-20260428.md`, including production
daily-cycle proof, canonical physical schema alignment, Raw manifest v2
source-interface validation, formal DDL registry, or P4 live PG/downstream
proof.
