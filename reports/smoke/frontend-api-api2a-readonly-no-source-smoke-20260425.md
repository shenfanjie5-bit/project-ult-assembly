# frontend-api API-2A Read-Only No-Source Smoke Evidence

Recorded: 2026-04-24T17:25:16Z

Scope:

- Verify the frontend and `frontend-api` can consume API-2A read-only cycle,
  manifest, and formal-object routes in the current local no-source state.
- Confirm the frontend renders expected unavailable/error-envelope states instead
  of blank pages.
- Confirm Project ULT mode still avoids legacy unsupported route calls.
- This is not compatibility-matrix evidence and does not promote
  `frontend-api` into existing verified matrix rows.

Commits under smoke:

- Frontend: `b09f579c7986b298557b52b09bed6ee0850a71d6`
- frontend-api: `5639ec30a288ad9aa4dbe8bd50144f7453014d40`
- data-platform: `ff2d2915e4ca7f76417afa7ccc0429d8fc10f288`
- assembly report repo: `e5fe1d0e11c64e245f6ba4f758d91a042be89d7b`

Runtime:

- `frontend-api`: `http://127.0.0.1:8701`
- Frontend dev server:
  `VITE_PROJECT_ULT_API_BASE=http://127.0.0.1:8701 npm run dev -- --host 127.0.0.1 --port 5173`

Endpoint checks:

```text
GET /api/project-ult/health                         -> 200 healthy
GET /api/project-ult/cycles                         -> 200 source_status=unavailable, total=0
GET /api/project-ult/manifests/latest               -> 503 PROJECT_ULT_MANIFEST_SOURCE_UNAVAILABLE
GET /api/project-ult/formal/world_state_snapshot    -> 503 PROJECT_ULT_FORMAL_SOURCE_UNAVAILABLE
```

Browser checks:

```text
http://127.0.0.1:5173/project-ult/system?data_mode=projectUlt
  - rendered System Map
  - showed frontend-api healthy
  - showed 15 modules, 2 profiles, 3 compat rows
  - console had only React DevTools info

http://127.0.0.1:5173/project-ult/cycles?data_mode=projectUlt
  - rendered Cycle / Formal page
  - showed Cycle Source unavailable and total 0
  - showed manifest 503 error envelope
  - showed formal object 503 error envelope
  - console had only the two expected 503 resource logs

http://127.0.0.1:5173/?data_mode=projectUlt
  - redirected to /project-ult/system
  - console had only React DevTools info
  - no unsupported legacy 404s were observed
```

Boundary checks:

- No Project ULT command, run, freeze, release-freeze, or POST route was used.
- The two 503 console resource logs are expected in the current local state
  because there is no artifact-backed manifest/formal source yet.
- API-2B should add an artifact-backed success-state fixture/source before the
  frontend can smoke real 200 manifest/formal payloads.
