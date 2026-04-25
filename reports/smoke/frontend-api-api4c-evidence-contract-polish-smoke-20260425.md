# frontend-api API-4C Evidence Contract/Polish Smoke Evidence

Recorded: 2026-04-25T09:14:38Z

Scope:

- Record API-4C Evidence Console contract and frontend polish smoke evidence.
- Confirm the API-4C backend contract audit keeps the API-4A read-only route
  surface stable.
- Confirm the FrontEnd Evidence Console renders normal, clamped, and invalid
  deep-link states without blank pages.
- Keep this evidence outside the verified compatibility matrix rows; no matrix
  `module_set` promotion or `verified_at` update is implied.

Commits under smoke:

- frontend-api API-4C contract tests:
  `8f52c27b1d642570c911ebf2edcd228d4efb2c24`
- FrontEnd API-4C polish:
  `87f18245c95375f55d6584c6d9d295125b2e2934`
- reasoner-runtime API-4A artifacts:
  `0ed380246a63ec71b8c667a8375f0390111f7e7d`
- audit-eval API-4A artifacts:
  `837bab7eeacf3c8c4f6c2ee7306c59519b9b5f94`
- orchestrator API-4A artifacts:
  `598259d234a29161698fae15cc3b9310d586664a`
- assembly report repo base: `9557970`

Runtime:

- `frontend-api`: `http://127.0.0.1:8701`
- Frontend dev server: `http://127.0.0.1:1420`
- Frontend dev env:
  `VITE_PROJECT_ULT_API_BASE=http://127.0.0.1:8701`

Backend API-4C contract audit:

```text
OpenAPI:
  contains /api/project-ult/reasoner/providers
  contains /api/project-ult/reasoner/results
  contains /api/project-ult/audit/{cycle_id}
  contains /api/project-ult/replay/{cycle_id}
  contains /api/project-ult/backtests
  contains /api/project-ult/backtests/{backtest_id}
  contains /api/project-ult/orchestrator/runs
  contains /api/project-ult/orchestrator/runs/{run_id}

List query contract:
  /api/project-ult/reasoner/results limit maximum: 500
  /api/project-ult/backtests limit maximum: 500
  /api/project-ult/orchestrator/runs limit maximum: 500

Invalid query/id behavior:
  /api/project-ult/reasoner/results?cursor=bad
    error.code: PROJECT_ULT_CURSOR_INVALID
  /api/project-ult/orchestrator/runs?status=../secret
    error.code: PROJECT_ULT_STATUS_INVALID
  /api/project-ult/audit/bad%20cycle
    error.code: PROJECT_ULT_IDENTIFIER_INVALID

Source/error behavior:
  list missing source:
    status: 200
    source_status: unavailable
    items: []
    total: 0
  detail missing source:
    error.code: PROJECT_ULT_AUDIT_SOURCE_UNAVAILABLE
  detail not found:
    error.code: PROJECT_ULT_AUDIT_NOT_FOUND
  detail schema drift:
    error.code: PROJECT_ULT_AUDIT_ARTIFACT_SCHEMA_INVALID
  detail invalid JSON:
    error.code: PROJECT_ULT_AUDIT_ARTIFACT_SCHEMA_INVALID

Project ULT POST route introspection:
  []
```

Frontend API-4C polish smoke:

```text
http://127.0.0.1:1420/project-ult/evidence?data_mode=projectUlt
  final route: /project-ult/evidence?data_mode=projectUlt
  title: AI 投研操作系统
  observed after evidence data load:
    Project ULT Evidence Console visible
    reasoner_primary_structured visible
    reasoner_result_cycle_20260424_001 visible
    api4a_audit_cycle_20260424 visible
    api4a_replay_cycle_20260424 visible
    BT_API4A_001 visible
    RUN_API4A_001 visible
    "422" not visible
    "Failed to fetch" not visible

http://127.0.0.1:1420/project-ult/evidence?data_mode=projectUlt&reasoner_limit=9999&backtest_limit=9999&run_limit=9999&cycle_id=CYCLE_20260424&backtest_id=BT_API4A_001&run_id=RUN_API4A_001
  final route: /project-ult/evidence?data_mode=projectUlt&reasoner_limit=9999&backtest_limit=9999&run_limit=9999&cycle_id=CYCLE_20260424&backtest_id=BT_API4A_001&run_id=RUN_API4A_001
  title: AI 投研操作系统
  observed:
    Project ULT Evidence Console visible
    reasoner_limit input displayed 500
    backtest_limit input displayed 500
    run_limit input displayed 500
    reasoner_primary_structured visible
    "422" not visible
    "Unprocessable" not visible
    "Failed to fetch" not visible
  backend clamped requests verified:
    GET /api/project-ult/reasoner/results?limit=500&cycle_id=CYCLE_20260424 -> 200
    GET /api/project-ult/backtests?limit=500 -> 200
    GET /api/project-ult/orchestrator/runs?limit=500 -> 200

Invalid deep links:
  /project-ult/evidence?data_mode=projectUlt&reasoner_cursor=bad
    displayed error state with PROJECT_ULT_CURSOR_INVALID
    page was not blank
  /project-ult/evidence?data_mode=projectUlt&run_status=..%2Fsecret
    displayed error state with PROJECT_ULT_STATUS_INVALID
    page was not blank
  /project-ult/evidence?data_mode=projectUlt&cycle_id=bad%20cycle
    displayed error state with PROJECT_ULT_IDENTIFIER_INVALID
    page was not blank
  /project-ult/evidence?data_mode=projectUlt&backtest_id=bad%20backtest
    displayed error state with PROJECT_ULT_IDENTIFIER_INVALID
    page was not blank
  /project-ult/evidence?data_mode=projectUlt&run_id=bad%20run
    displayed error state with PROJECT_ULT_IDENTIFIER_INVALID
    page was not blank
```

System Map and guarded routes:

```text
http://127.0.0.1:1420/project-ult/system?data_mode=projectUlt
  final route: /project-ult/system?data_mode=projectUlt
  title: AI 投研操作系统
  observed:
    Project ULT System Map visible
    Project ULT read-only navigation includes the API-4A reasoner/audit/replay/
    backtest/orchestrator evidence entry

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

- API-4C is read-only backend contract audit plus frontend Evidence Console
  polish.
- The console consumes only API-4A `GET` endpoints.
- `frontend-api` route introspection returned no Project ULT `POST`, `PUT`, or
  `DELETE` routes.
- No command, run, freeze, release-freeze, compat-run, e2e-run, min-cycle, or
  replay POST endpoint is present or used.
- No command/run/freeze UI path is introduced or exercised.

Matrix boundary:

- This report is API-4C read-only contract/polish smoke evidence only.
- `compatibility-matrix.yaml` verified rows remain unchanged.
- `frontend-api` and API-4 evidence are not bound to the old verified
  compatibility baseline.
- Future promotion into verified matrix rows requires a separate fresh
  contract/smoke/e2e evidence run and matching `verified_at` update.
