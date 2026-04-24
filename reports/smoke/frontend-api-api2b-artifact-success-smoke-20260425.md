# frontend-api API-2B Artifact-Backed Success Smoke Evidence

Recorded: 2026-04-24T17:35:05Z

Scope:

- Verify `frontend-api` can serve API-2A read-only cycle, manifest, formal
  object, and legacy latest routes from committed `data-platform`
  `artifacts/frontend-api/` JSON read models.
- Verify the existing frontend can render real 200 success-state data, not only
  the previous no-source/error-envelope state.
- Keep this evidence outside the verified compatibility matrix rows; no matrix
  `module_set` promotion is implied.

Commits under smoke:

- data-platform: `d56efd5e1c76912369ba20c824f3f6ae76ba53c8`
- frontend-api: `18f527630a5c69136cba1f4ee648ce13d7a4d476`
- Frontend: `b09f579c7986b298557b52b09bed6ee0850a71d6`
- assembly report repo base: `b1a5026f`

Artifact source:

```text
data-platform/artifacts/frontend-api/cycles.json
data-platform/artifacts/frontend-api/manifests/latest.json
data-platform/artifacts/frontend-api/formal/world_state_snapshot/latest.json
data-platform/artifacts/frontend-api/formal/official_alpha_pool/latest.json
data-platform/artifacts/frontend-api/formal/recommendation_snapshot/latest.json
```

Endpoint checks:

```text
GET /api/project-ult/health                         -> 200 healthy
GET /api/project-ult/cycles                         -> 200 source_status=available, total=1
GET /api/project-ult/cycles/CYCLE_20260424          -> 200 status=published
GET /api/project-ult/manifests/latest               -> 200 keyed formal_table_snapshots object
GET /api/project-ult/formal/world_state_snapshot    -> 200 FormalObjectResponse root fields + payload
GET /api/project-ult/formal/official_alpha_pool     -> 200 FormalObjectResponse root fields + payload
GET /api/project-ult/formal/recommendation_snapshot -> 200 FormalObjectResponse root fields + payload
GET /api/world-state/latest                         -> 200 raw world-state payload root
GET /api/pool/latest                                -> 200 raw pool payload root
GET /api/recommendations/latest                     -> 200 raw recommendations payload root
```

Automated checks:

```text
frontend-api tests/test_cycle_routes.py             -> 5 passed
frontend-api full suite                             -> 26 passed
data-platform tests/contract/test_frontend_api_artifacts.py -> 4 passed
data-platform targeted public/cycle/artifact tests  -> 29 passed, 12 skipped
Project ULT POST route introspection                -> []
```

Browser check:

```text
http://127.0.0.1:5173/project-ult/cycles?data_mode=projectUlt
  - rendered Cycle / Formal page
  - showed Cycle Source available and total 1
  - showed CYCLE_20260424, status published, cycle_date 2026-04-24
  - rendered manifest snapshot table with keyed rows:
    world_state_snapshot, official_alpha_pool, recommendation_snapshot
  - rendered formal root metadata and payload for world_state_snapshot
  - console had only React DevTools info
```

Boundary checks:

- No Project ULT command, run, freeze, release-freeze, or POST route was used.
- Legacy latest routes return raw domain payload roots, not wrappers.
- `frontend-api` still reads `data-platform` through artifact/public read
  sources only; no assembly verified matrix rows were modified.
