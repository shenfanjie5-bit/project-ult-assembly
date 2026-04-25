# frontend-api API-4B Evidence Console Read-Only Smoke Evidence

Recorded: 2026-04-25T08:54:36Z

Scope:

- Record API-4B Evidence Console read-only frontend/backend smoke evidence.
- Confirm the FrontEnd Evidence Console consumes the existing API-4A backend
  GET endpoints and clamps over-limit URL query params before requesting the
  backend.
- Keep this evidence outside the verified compatibility matrix rows; no matrix
  `module_set` promotion or `verified_at` update is implied.

Commits under smoke:

- FrontEnd Evidence Console commit:
  `a13469304904ac564048482b62e108c253b87f53`
- frontend-api: `09a284ea56b47edad8407f01fa4b804c180c1df0`
- reasoner-runtime: `0ed380246a63ec71b8c667a8375f0390111f7e7d`
- audit-eval: `837bab7eeacf3c8c4f6c2ee7306c59519b9b5f94`
- orchestrator: `598259d234a29161698fae15cc3b9310d586664a`
- assembly report repo base: `ee10101`

Runtime:

- `frontend-api`: `http://127.0.0.1:8701`
- Frontend dev server: `http://127.0.0.1:1420`
- Frontend dev env:
  `VITE_PROJECT_ULT_API_BASE=http://127.0.0.1:8701`

Backend API-4A route checks:

```text
GET /api/project-ult/reasoner/providers
  status: 200
  source_status: available
  total: 2

GET /api/project-ult/reasoner/results?limit=1&cycle_id=CYCLE_20260424
  status: 200
  source_status: available
  total: 2

GET /api/project-ult/audit/CYCLE_20260424
  status: 200
  source_status: available
  snapshot_id: api4a_audit_cycle_20260424

GET /api/project-ult/replay/CYCLE_20260424
  status: 200
  source_status: available
  snapshot_id: api4a_replay_cycle_20260424

GET /api/project-ult/backtests?limit=1
  status: 200
  source_status: available
  total: 2

GET /api/project-ult/backtests/BT_API4A_001
  status: 200
  source_status: available
  backtest_id: BT_API4A_001

GET /api/project-ult/orchestrator/runs?limit=1&status=success
  status: 200
  source_status: available
  total: 1

GET /api/project-ult/orchestrator/runs/RUN_API4A_001
  status: 200
  source_status: available
  run_id: RUN_API4A_001
```

Frontend browser smoke:

```text
http://127.0.0.1:1420/project-ult/evidence?data_mode=projectUlt
  final route: /project-ult/evidence?data_mode=projectUlt
  title: AI 投研操作系统
  observed:
    Project ULT Evidence Console visible
    Reasoner Providers visible
    reasoner_primary_structured / openai / gpt-5.4 visible
    Reasoner Results visible
    reasoner_result_cycle_20260424_001 visible
    Audit Evidence visible
    api4a_audit_cycle_20260424 visible
    Replay Evidence visible
    api4a_replay_cycle_20260424 visible
    Backtests visible
    BT_API4A_001 visible
    Backtest Detail visible
    Orchestrator Runs visible
    RUN_API4A_001 visible
    Run Detail visible
    "422" not visible
    "Unprocessable" not visible
    "Failed to fetch" not visible

http://127.0.0.1:1420/project-ult/evidence?data_mode=projectUlt&reasoner_limit=9999&backtest_limit=9999&run_limit=9999&cycle_id=CYCLE_20260424&backtest_id=BT_API4A_001&run_id=RUN_API4A_001
  final route: /project-ult/evidence?data_mode=projectUlt&reasoner_limit=9999&backtest_limit=9999&run_limit=9999&cycle_id=CYCLE_20260424&backtest_id=BT_API4A_001&run_id=RUN_API4A_001
  title: AI 投研操作系统
  observed:
    Project ULT Evidence Console visible
    cycle_id input displayed CYCLE_20260424
    reasoner_limit input displayed 500
    backtest_limit input displayed 500
    run_limit input displayed 500
    backtest_id input displayed BT_API4A_001
    run_id input displayed RUN_API4A_001
    "422" not visible
    "Unprocessable" not visible
    "Failed to fetch" not visible
  backend clamped requests verified:
    GET /api/project-ult/reasoner/results?limit=500&cycle_id=CYCLE_20260424 -> 200
    GET /api/project-ult/backtests?limit=500 -> 200
    GET /api/project-ult/orchestrator/runs?limit=500 -> 200

http://127.0.0.1:1420/project-ult/system?data_mode=projectUlt
  final route: /project-ult/system?data_mode=projectUlt
  title: AI 投研操作系统
  observed:
    Project ULT System Map visible
    API-4A Evidence Console entry visible

Guarded projectUlt routes:
  http://127.0.0.1:1420/admin?data_mode=projectUlt
    final route: /project-ult/system
  http://127.0.0.1:1420/subsystems?data_mode=projectUlt
    final route: /project-ult/system
  http://127.0.0.1:1420/audit?data_mode=projectUlt
    final route: /project-ult/system
  http://127.0.0.1:1420/graph?data_mode=projectUlt
    final route: /project-ult/system
```

Read-only boundary:

- API-4B is frontend Evidence Console polish over API-4A read-only backend
  routes.
- The console consumes only API-4A `GET` endpoints.
- `frontend-api` OpenAPI inspection returned no Project ULT `POST`, `PUT`, or
  `DELETE` routes.
- No command, run, freeze, release-freeze, compat-run, e2e-run, min-cycle, or
  replay POST endpoint is present or used.
- No command/run/freeze UI path is introduced or exercised.

Matrix boundary:

- This report is API-4B read-only frontend/backend smoke evidence only.
- `compatibility-matrix.yaml` verified rows remain unchanged.
- `frontend-api` and API-4 evidence are not bound to the old verified
  compatibility baseline.
- Future promotion into verified matrix rows requires a separate fresh
  contract/smoke/e2e evidence run and matching `verified_at` update.
