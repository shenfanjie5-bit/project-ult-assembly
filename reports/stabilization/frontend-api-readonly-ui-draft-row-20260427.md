# Frontend API Readonly UI Draft Row Evidence

Recorded: 2026-04-27T05:14:53Z

Repo: `/Users/fanjie/Desktop/Cowork/project-ult/assembly`

Base commit before this change: `8423fc9be9865872307806cc255eaab7402253a5`

Implementation commit: see the commit that contains this evidence file and the final task handoff. A Git commit cannot embed its own final hash without changing that hash.

## Scope

- Added `profiles/lite-local-readonly-ui.yaml` as a read-only UI/frontend-api-inclusive variant of `lite-local`.
- Kept the base `lite-local` profile unchanged.
- Added `lite-local-readonly-ui` support to the core bundle manifests only: `postgres`, `neo4j`, and `dagster`.
- Added `lite-local-readonly-ui` to `supported_profiles` for the 13 modules enabled by the variant: base Lite 12 plus `frontend-api`.
- Did not add `lite-local-readonly-ui` support to `feature-store` or `stream-layer`.
- Added one draft compatibility matrix row for `lite-local-readonly-ui` with `module_set` equal to base Lite plus `frontend-api`.

## Promotion Status

- No promotion was run.
- `contract-suite --promote` was not run.
- Existing verified rows were not promoted, refreshed, or re-stamped.

## Verified Row Preservation

The historical verified matrix row identities remain:

- `("lite-local", [])`
- `("full-dev", [])`
- `("full-dev", ["minio"])`

Those rows remain `status: verified`, retain their existing `verified_at` values, and do not include `frontend-api` in `module_set`.

## Validation

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python -m pytest -q -p no:cacheprovider tests/registry tests/profiles tests/compat tests/smoke tests/e2e/test_runner.py tests/release/test_freezer.py
```

Result: passed. Output ended with `100%`; expected skips were present in the existing suite.

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python -m pytest -q -p no:cacheprovider tests/test_runtime_registry_resolution.py
```

Result: passed, `12 passed`.

Command:

```bash
git diff --check
```

Result: passed with no output.
