# frontend-api API-1 Public Smoke Evidence

Recorded: 2026-04-25 Asia/Shanghai

Scope:

- Register `frontend-api` as a Project ULT module in assembly.
- Verify standard public entrypoints:
  - `frontend_api.public:health_probe`
  - `frontend_api.public:smoke_hook`
  - `frontend_api.public:init_hook`
  - `frontend_api.public:version_declaration`
  - `frontend_api.public:cli`
- Verify API-1 remains read-only for System/Assembly endpoints.

Commands:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/frontend-api
.venv/bin/python -m pytest

cd /Users/fanjie/Desktop/Cowork/project-ult/assembly
.venv-py312/bin/python -m pytest tests/registry tests/profiles/test_lite_local_artifacts.py tests/registry/test_loader.py tests/registry/test_exporter.py tests/cli/test_main.py::test_export_registry_writes_runtime_artifacts
.venv-py312/bin/python -m pytest tests/compat tests/health tests/smoke
.venv-py312/bin/python -m pytest
.venv-py312/bin/python - <<'PY'
import json
from frontend_api import public
print(json.dumps(public.health_probe.check(timeout_sec=1.0), indent=2, sort_keys=True))
print(json.dumps(public.smoke_hook.run(profile_id="lite-local"), indent=2, sort_keys=True))
print(json.dumps(public.version_declaration.declare(), indent=2, sort_keys=True))
PY
```

Results:

- `frontend-api` tests: `11 passed`
- assembly registry/profile/export targeted tests: `74 passed`
- assembly compat/health/smoke targeted tests: `40 passed, 1 skipped`
- assembly full suite: `316 passed, 4 skipped`
- `frontend_api.public.health_probe.check(timeout_sec=1.0)`:
  - `module_id`: `frontend-api`
  - `status`: `healthy`
  - `module_count`: `15`
  - `profile_count`: `2`
  - `compatibility_row_count`: `3`
- `frontend_api.public.smoke_hook.run(profile_id="lite-local")`:
  - `module_id`: `frontend-api`
  - `hook_name`: `frontend-api.api1-readonly-smoke`
  - `passed`: `true`
  - `failure_reason`: `null`
- `frontend_api.public.version_declaration.declare()`:
  - `module_id`: `frontend-api`
  - `module_version`: `0.1.0`
  - `contract_version`: `v0.1.3`
  - `compatible_contract_range`: `>=0.1.0,<0.2.0`

Boundary checks:

- No Project ULT command endpoints are registered by `frontend-api`.
- No release-freeze endpoint or workflow is exposed by `frontend-api`.
- `frontend_api.public` does not import assembly.
- `frontend-api` reads assembly registry/profile/compat artifacts only through
  its read-only adapter.
- This is registry/public-smoke evidence only. `frontend-api` is intentionally
  kept out of the existing verified compatibility matrix rows until fresh
  contract/smoke/e2e evidence exists for a matrix identity that includes it.
