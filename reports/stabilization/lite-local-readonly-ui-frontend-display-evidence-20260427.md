# lite-local-readonly-ui FrontEnd Display Evidence

Date: 2026-04-27

Scope: read-only verification for the FrontEnd and frontend-api display path for the new `lite-local-readonly-ui` profile and draft compatibility matrix row.

## Result

- No FrontEnd code change was required.
- `SystemMapPage` consumes `/api/project-ult/health`, `/modules`, `/profiles`, and `/compat` through dynamic query hooks.
- The real API display path maps `profiles.items` and `compat.items` directly. It does not filter to `lite-local` or `full-dev`.
- Demo/mock data still contains static `lite-local` and `full-dev` fixture rows, but that is isolated to demo mode and does not block the real `projectUlt` API path.
- `frontend-api` registers no Project ULT write routes.

## Evidence

FrontEnd files inspected:

- `/Users/fanjie/Desktop/BIG/FrontEnd/src/pages/SystemMap/index.tsx`
- `/Users/fanjie/Desktop/BIG/FrontEnd/src/api/projectUlt/hooks.ts`
- `/Users/fanjie/Desktop/BIG/FrontEnd/src/api/projectUlt/contracts.ts`
- `/Users/fanjie/Desktop/BIG/FrontEnd/src/mocks/data/projectUltData.ts`

Key display behavior:

- `profiles.items.map(...)` renders every profile returned by `/api/project-ult/profiles`.
- `compat.items.map(...)` renders every matrix row returned by `/api/project-ult/compat`.
- `ProjectUltCompatStatus` is `string`-extensible, so `draft` is not type-blocked.
- `getCompatRowKey(row)` keys rows as `profile_id::sorted(extra_bundles)`, so the default `lite-local-readonly-ui` draft row is representable.

Adapter check:

```text
profiles = ['full-dev', 'lite-local-readonly-ui', 'lite-local']
compat = [
  ('lite-local', 'verified', []),
  ('lite-local-readonly-ui', 'draft', []),
  ('full-dev', 'verified', []),
  ('full-dev', 'verified', ['minio'])
]
```

Route inspection:

```text
project_ult_write_routes = []
```

## Verification Commands

frontend-api:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/frontend-api
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q
```

Result:

```text
58 passed
```

FrontEnd:

```bash
cd /Users/fanjie/Desktop/BIG/FrontEnd
npm run check
npm run lint
npm run build
npm run test -- --run
```

Results:

```text
npm run check: passed
npm run lint: passed
npm run build: passed
npm run test -- --run: failed, package.json has no "test" script
```

## Frontend Blockers

None for the real `projectUlt` SystemMap display path.

Residual note: demo mode fixture data is static and does not yet mirror the new profile row. It is not used when the UI reads from the external `frontend-api` backend.
