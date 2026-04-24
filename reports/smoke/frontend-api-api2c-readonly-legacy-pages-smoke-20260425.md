# frontend-api API-2C Read-Only Legacy Pages Smoke Evidence

Recorded: 2026-04-24T17:46:44Z

Scope:

- Verify the existing frontend legacy pages can consume the API-2B
  artifact-backed read-only endpoints in Project ULT mode.
- Promote only the safe legacy pages that have matching `frontend-api` read
  sources: market overview, pool, and recommendations.
- Confirm higher-risk legacy pages still redirect to System Map until their
  Project ULT read sources exist.
- Keep this evidence outside the verified compatibility matrix rows; no matrix
  `module_set` promotion is implied.

Commits under smoke:

- Frontend: `5072168410e5e45eb39f5f5fd991e4e512a90d25`
- frontend-api: `18f527630a5c69136cba1f4ee648ce13d7a4d476`
- data-platform: `d56efd5e1c76912369ba20c824f3f6ae76ba53c8`
- assembly report repo base: `5a72961caf31118967e3a6eedb839dd36cc0151b`

Runtime:

- `frontend-api`: `http://127.0.0.1:8701`
- Frontend dev server:
  `VITE_PROJECT_ULT_API_BASE=http://127.0.0.1:8701 npm run dev -- --host 127.0.0.1 --port 5173`

Frontend checks:

```text
npm run check       -> passed
npm run lint        -> passed
npm run build       -> passed
git diff --check    -> passed
```

Browser route checks:

```text
http://127.0.0.1:5173/?data_mode=projectUlt
  final route: /?data_mode=projectUlt
  requests:
    GET /api/project-ult/health -> 200
    GET /api/world-state/latest -> 200
    GET /api/pool/latest        -> 200

http://127.0.0.1:5173/pool?data_mode=projectUlt
  final route: /pool?data_mode=projectUlt
  requests:
    GET /api/project-ult/health -> 200
    GET /api/pool/latest        -> 200

http://127.0.0.1:5173/recommend?data_mode=projectUlt
  final route: /recommend?data_mode=projectUlt
  requests:
    GET /api/project-ult/health       -> 200
    GET /api/recommendations/latest   -> 200

http://127.0.0.1:5173/admin?data_mode=projectUlt
http://127.0.0.1:5173/subsystems?data_mode=projectUlt
http://127.0.0.1:5173/audit?data_mode=projectUlt
  final route: /project-ult/system
  requests:
    GET /api/project-ult/health   -> 200
    GET /api/project-ult/modules  -> 200
    GET /api/project-ult/profiles -> 200
    GET /api/project-ult/compat   -> 200
```

Observed UI state:

- Market Overview rendered API-2B artifact-backed world-state and pool data.
- Pool Management rendered API-2B artifact-backed pool data.
- Recommendations rendered API-2B artifact-backed recommendation data.
- Market Overview displayed `/subsystems/status` and `/admin/health` as
  unavailable in Project ULT mode and did not request them.
- Admin, Subsystems, and Audit routes redirected to System Map.

Boundary checks:

- No unsupported `/api/subsystems/status` or `/api/admin/health` request was
  observed in Project ULT mode.
- Browser console had no error or warning entries during the smoke.
- No Project ULT command, run, freeze, release-freeze, or POST route was used.
- This is frontend/API smoke evidence only; existing verified compatibility
  matrix rows remain unchanged.
