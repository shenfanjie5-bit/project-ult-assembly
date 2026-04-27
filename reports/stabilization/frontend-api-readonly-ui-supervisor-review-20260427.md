# Frontend API Readonly UI Supervisor Review

Recorded: 2026-04-27T05:24:30Z

Scope:

- Review the first frontend-api verified matrix promotion preparation batch.
- Confirm the new `lite-local-readonly-ui` compatibility context is draft-only.
- Record the supervisor-discovered frontend-api smoke blocker and its fix.
- Do not promote any compatibility matrix row in this step.

## Commits Reviewed

- assembly: `3ede58faf667e68ab0a26d6ede67fd2cec427f31`
  - Added `profiles/lite-local-readonly-ui.yaml`.
  - Added one draft `lite-local-readonly-ui` compatibility matrix row.
  - Preserved the historical verified matrix rows:
    - `("lite-local", [])`
    - `("full-dev", [])`
    - `("full-dev", ["minio"])`
- frontend-api: `68414ed8423caf51f192a9c1a00c36ddaf19ab93`
  - Fixed public smoke so a pre-promotion draft default compatibility row is acceptable.
  - Kept health strict: `lite-local-readonly-ui` health remains degraded until verified.
  - Expanded the read-only route guard to reject Project ULT `POST`, `PUT`,
    `PATCH`, and `DELETE` routes.

## Matrix Review

The assembly draft row is:

```text
profile_id: lite-local-readonly-ui
extra_bundles: []
status: draft
verified_at: null
module_set: base lite-local module_set + frontend-api
```

The draft row does not include `feature-store` or `stream-layer`.
`frontend-api` is not encoded as an `extra_bundles` value.

The existing verified rows retain their prior `verified_at` values and do not
include `frontend-api` in `module_set`.

## Supervisor Finding And Resolution

Supervisor review found a P1 promotion blocker after the assembly commit:

```text
frontend_api.public.smoke_hook.run(profile_id="lite-local-readonly-ui")
```

returned:

```text
passed: False
failure_reason: health returned degraded: active profile has no verified compat row
```

This would have blocked the required fresh smoke evidence for a draft matrix
context. The frontend-api follow-up commit `68414ed8423caf51f192a9c1a00c36ddaf19ab93`
resolved the blocker by making public smoke validate readable assembly
artifacts plus a default compatibility row with status `draft` or `verified`,
without weakening the health endpoint.

## Independent Review

Assembly independent review result:

- Passed.
- One P3 note: the assembly evidence file explains why it cannot embed its own
  final commit hash directly. This is non-blocking because this supervisor
  review records the reviewed commit hash.

frontend-api independent review result:

- Passed.
- No P0/P1/P2/P3 findings.
- Confirmed no new write routes, sidecar, release-freeze, command/run,
  e2e-run, min-cycle, replay POST, or graph simulate endpoint.

## Validation Commands

assembly worker/test reviewer ran:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/assembly
PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python -m pytest -q -p no:cacheprovider \
  tests/registry \
  tests/profiles \
  tests/compat \
  tests/smoke \
  tests/e2e/test_runner.py \
  tests/release/test_freezer.py

PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_runtime_registry_resolution.py

git diff --check
```

Results:

- Main assembly suite passed with existing expected skips/warnings.
- Runtime registry resolution passed: `12 passed`.
- `git diff --check` passed.

frontend-api worker/test reviewer and supervisor ran:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/frontend-api
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q

PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
import os
from pathlib import Path
os.environ["PROJECT_ULT_ROOT"] = str(Path("/Users/fanjie/Desktop/Cowork/project-ult"))
from frontend_api import public
for profile in ["lite-local", "lite-local-readonly-ui"]:
    print(profile, public.smoke_hook.run(profile_id=profile))
os.environ["PROJECT_ULT_PROFILE"] = "lite-local-readonly-ui"
health = public.health_probe.check(timeout_sec=1.0)
print("health", health["status"], health["message"])
PY

git diff --check
```

Results:

- frontend-api tests passed: `58 passed`.
- `lite-local` public smoke passed.
- `lite-local-readonly-ui` public smoke passed.
- `lite-local-readonly-ui` health remained degraded with
  `active profile has no verified compat row`.
- `git diff --check` passed.

## Gate Status

First batch status: passed after frontend-api smoke blocker fix.

Promotion status:

- No compatibility matrix promotion was run.
- `contract-suite --promote` was not run.
- The next gate is fresh smoke/e2e/contract evidence for the exact
  `lite-local-readonly-ui` draft matrix context, followed by promotion only for
  that new frontend-api-inclusive context.
