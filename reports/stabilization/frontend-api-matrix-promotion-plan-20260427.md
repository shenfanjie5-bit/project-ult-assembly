# Frontend API Verified Matrix Promotion Plan

Recorded: 2026-04-27T04:38:34Z

Scope:

- Plan a future verified compatibility matrix promotion that includes
  `frontend-api`.
- Do not modify `compatibility-matrix.yaml` in this step.
- Do not promote or refresh old verified rows from prior evidence.
- Do not run release-freeze, command, run, compat-run, e2e-run, min-cycle, or
  sidecar auto-start work from this plan step.

Current facts:

```text
Current verified matrix rows:
  (lite-local, extra_bundles=[])
  (full-dev, extra_bundles=[])
  (full-dev, extra_bundles=[minio])

Current matrix row identity:
  (profile_id, sorted(extra_bundles))

Current profile enabled_modules:
  lite-local: does not include frontend-api
  full-dev: does not include frontend-api

Current registry:
  frontend-api is registered as a public read-only module and supports
  lite-local and full-dev.

Current matrix rows:
  no module_set contains frontend-api.
```

Why direct promotion is not safe:

- The existing verified rows are keyed by `(profile_id, extra_bundles)`.
- Adding a second `lite-local` or default `full-dev` row that differs only by
  `module_set` would collide with the selector and release-freeze identity.
- Updating the old rows in place would overwrite the historical evidence
  identity and recreate the stale-evidence problem that this stabilization pass
  explicitly avoided.
- Treating `frontend-api` as an `extra_bundles` value is also wrong: optional
  bundles are infrastructure slots, while `frontend-api` is a public module.

Promotion decision:

```text
Do not update existing verified rows.
Do not add duplicate matrix rows with the same (profile_id, extra_bundles).
Do not encode frontend-api as an extra_bundles value.
Use an explicit profile variant or a deliberate matrix schema/version upgrade.
```

Recommended path:

1. Add explicit read-only UI profile variants, for example:

   ```text
   lite-local-readonly-ui
   full-dev-readonly-ui
   ```

   Each variant should reuse the same service bundles as its base profile, but
   include `frontend-api` in `enabled_modules`.

2. Add draft matrix rows for those new profile ids:

   ```text
   profile_id: lite-local-readonly-ui
   module_set: base lite-local module_set + frontend-api
   status: draft
   required_tests:
     - contract-suite
     - smoke
     - min-cycle-e2e

   profile_id: full-dev-readonly-ui
   module_set: base full-dev module_set + frontend-api
   status: draft
   required_tests:
     - contract-suite
     - smoke
     - min-cycle-e2e
   ```

3. Update registry/profile consistency tests to expect the new profile ids and
   preserve the old three verified rows.

4. Run fresh evidence bound to the new matrix context. The required run order
   should be:

   ```bash
   cd /Users/fanjie/Desktop/Cowork/project-ult/assembly

   PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python -m assembly.cli.main \
     smoke \
     --profile lite-local-readonly-ui \
     --env-file .env \
     --reports-dir reports/smoke

   PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python -m assembly.cli.main \
     e2e \
     --profile lite-local-readonly-ui \
     --env-file .env \
     --reports-dir reports/e2e

   PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python -m assembly.cli.main \
     contract-suite \
     --profile lite-local-readonly-ui \
     --env-file .env \
     --reports-dir reports/contract \
     --promote
   ```

   Repeat the same sequence for `full-dev-readonly-ui` only if full-dev UI
   promotion is required immediately.

5. The promoted row must record fresh `verified_at` and the supporting
   contract/smoke/e2e run ids for the exact frontend-api-inclusive module set.

Required guardrails for implementation:

- Keep the old verified rows intact.
- Keep `frontend-api` read-only: no Project ULT POST/PUT/PATCH/DELETE routes.
- Do not introduce release-freeze, command, run, compat-run, e2e-run,
  min-cycle, replay POST, or graph simulate endpoints.
- Do not stage local `.env`, `.orchestrator`, venv, cache, tmp, build, dist,
  egg-info, dbt runtime state, or scratch report files.

Pre-promotion validation commands:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/assembly

PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python -m pytest -q -p no:cacheprovider \
  tests/registry \
  tests/compat \
  tests/smoke \
  tests/e2e/test_runner.py \
  tests/release/test_freezer.py

git diff --check
```

Promotion success criteria:

- New profile ids resolve and do not alter existing base profile semantics.
- Draft rows load without colliding with existing matrix row keys.
- Smoke and e2e records contain `compatibility_context` artifacts matching the
  exact draft row.
- `contract-suite --promote` refuses stale evidence and promotes only the new
  frontend-api-inclusive row.
- `frontend-api` remains outside the old verified rows.

Next step after this plan:

- Implement the profile variant and draft-row changes in assembly, then run the
  fresh promotion sequence above.
- Only after a clean promotion should the project proceed to a real-data mini
  cycle.
