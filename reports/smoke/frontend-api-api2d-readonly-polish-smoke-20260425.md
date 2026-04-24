# frontend-api API-2D Read-Only Polish Smoke Evidence

Recorded: 2026-04-24T18:01:56Z

Scope:

- Verify the frontend API-2D read-only workspace polish on top of API-2B
  artifact-backed data and API-2C legacy-page enablement.
- Confirm System Map, Cycle/Formal, Market Overview, Pool, and Recommendations
  now expose consistent Project ULT read-only context and navigation.
- Confirm unsupported legacy pages still redirect to System Map.
- Keep this evidence outside the verified compatibility matrix rows; no matrix
  `module_set` promotion is implied.

Commits under smoke:

- Frontend: `4d6806fdb1064a85dac21481566d171b1c7876a7`
- frontend-api: `18f527630a5c69136cba1f4ee648ce13d7a4d476`
- data-platform: `d56efd5e1c76912369ba20c824f3f6ae76ba53c8`
- assembly report repo base: `34b3aa0ffb43218bf693aa680c597ee4460ce6e0`

Runtime:

- `frontend-api`: `http://127.0.0.1:8701`
- Frontend dev server: `http://127.0.0.1:1420`

Frontend checks:

```text
npm run check       -> passed
npm run lint        -> passed
npm run build       -> passed
git diff --check    -> passed
```

Browser route checks:

```text
http://127.0.0.1:1420/project-ult/system?data_mode=projectUlt
  final route: /project-ult/system?data_mode=projectUlt
  title: Project ULT System Map
  requests:
    GET /api/project-ult/health   -> 200
    GET /api/project-ult/modules  -> 200
    GET /api/project-ult/profiles -> 200
    GET /api/project-ult/compat   -> 200

http://127.0.0.1:1420/project-ult/cycles?data_mode=projectUlt
  final route: /project-ult/cycles?data_mode=projectUlt
  title: Project ULT Cycle / Formal
  requests:
    GET /api/project-ult/health                    -> 200
    GET /api/project-ult/cycles                    -> 200
    GET /api/project-ult/manifests/latest          -> 200
    GET /api/project-ult/formal/world_state_snapshot -> 200

http://127.0.0.1:1420/?data_mode=projectUlt
  final route: /?data_mode=projectUlt
  title: 市场总览
  requests:
    GET /api/project-ult/health -> 200
    GET /api/world-state/latest -> 200
    GET /api/pool/latest        -> 200

http://127.0.0.1:1420/pool?data_mode=projectUlt
  final route: /pool?data_mode=projectUlt
  title: 池管理
  requests:
    GET /api/project-ult/health -> 200
    GET /api/pool/latest        -> 200

http://127.0.0.1:1420/recommend?data_mode=projectUlt
  final route: /recommend?data_mode=projectUlt
  title: 建议总览
  requests:
    GET /api/project-ult/health       -> 200
    GET /api/recommendations/latest   -> 200
```

Blocked route checks:

```text
http://127.0.0.1:1420/admin?data_mode=projectUlt
http://127.0.0.1:1420/subsystems?data_mode=projectUlt
http://127.0.0.1:1420/audit?data_mode=projectUlt
http://127.0.0.1:1420/graph?data_mode=projectUlt
http://127.0.0.1:1420/stock/600519.SH?data_mode=projectUlt
  final route: /project-ult/system
  requests:
    GET /api/project-ult/health   -> 200
    GET /api/project-ult/modules  -> 200
    GET /api/project-ult/profiles -> 200
    GET /api/project-ult/compat   -> 200
```

Observed UI state:

- System Map shows a read-only banner and quick links to available API-1/API-2
  workspaces.
- Cycle/Formal shows read-only context, manifest snapshot count, formal
  source status, snapshot id, wrapper/metadata, and payload sections.
- Market Overview, Pool, and Recommendations show artifact-backed source notes.
- Risk links to stock detail, graph, admin override, subsystem, and audit are
  either redirected to System Map or disabled in Project ULT mode.

Boundary checks:

- Browser console had no error or warning entries during the smoke.
- No unsupported `/api/subsystems/status`, `/api/admin/health`, `/api/graph/*`,
  `/api/audit/*`, or `/api/stocks/*` request was observed in Project ULT mode.
- No Project ULT command, run, freeze, release-freeze, or POST route was used.
- This is frontend/API smoke evidence only; existing verified compatibility
  matrix rows remain unchanged.
