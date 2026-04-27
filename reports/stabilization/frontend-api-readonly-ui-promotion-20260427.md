# Frontend API Readonly UI Promotion Evidence

Recorded: 2026-04-27T05:34:25Z

Repo: `/Users/fanjie/Desktop/Cowork/project-ult/assembly`

Scope:

- Promote only `profile_id=lite-local-readonly-ui`.
- Preserve the existing verified rows:
  - `(lite-local, extra_bundles=[])`
  - `(full-dev, extra_bundles=[])`
  - `(full-dev, extra_bundles=[minio])`
- Do not run API-6, sidecar, command/run/freeze/release-freeze write APIs, or
  any frontend write surface.

Base commits reviewed before this promotion:

- assembly: `df1fdbbef70279c65bd3b806d3a275f47798c619`
- assembly draft row: `3ede58faf667e68ab0a26d6ede67fd2cec427f31`
- frontend-api smoke blocker fix: `68414ed8423caf51f192a9c1a00c36ddaf19ab93`

The final assembly commit hash is reported in the promotion handoff/final
response because a file cannot embed the hash of the commit that contains it.

## Service Bootstrap

Initial smoke found the Lite stack down:

```text
failed  smoke-lite-local-readonly-ui-20260427T053021535634Z  failing=dagster-daemon,dagster-webserver,neo4j,postgres
```

Bootstrap command used to start the real Lite stack:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python -m assembly.cli.main \
  bootstrap \
  --profile lite-local-readonly-ui \
  --env-file .env \
  --out reports/bootstrap
```

The compose startup stage passed and all four services became healthy. The
bootstrap command then failed during public smoke validation because several
existing sibling smoke hooks return a `details` field and some legacy hooks only
recognize the base `lite-local` profile id. Assembly was updated to accept
`SmokeResult.details`, normalize legacy smoke dictionaries, and retry only
`*-readonly-ui` smoke hooks with their base profile id when the hook explicitly
returns `unknown profile_id`.

## Fresh Evidence

Smoke:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python -m assembly.cli.main \
  smoke \
  --profile lite-local-readonly-ui \
  --env-file .env \
  --reports-dir reports/smoke
```

Result:

```text
success  smoke-lite-local-readonly-ui-20260427T053402181740Z  failing=
```

Report path:

- `reports/smoke/smoke-lite-local-readonly-ui-20260427T053402181740Z.json`

E2E:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python -m assembly.cli.main \
  e2e \
  --profile lite-local-readonly-ui \
  --env-file .env \
  --reports-dir reports/e2e
```

Result:

```text
success  e2e-lite-local-readonly-ui-20260427T053406092429Z  failing=
```

Report paths:

- `reports/e2e/e2e-lite-local-readonly-ui-20260427T053406092429Z.json`
- `reports/e2e/e2e-lite-local-readonly-ui-20260427T053406092429Z/`
- e2e contract preflight:
  `reports/contract/contract-lite-local-readonly-ui-20260427T053406120916Z.json`

Contract suite pre-promotion:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python -m assembly.cli.main \
  contract-suite \
  --profile lite-local-readonly-ui \
  --env-file .env \
  --reports-dir reports/contract
```

Result:

```text
success  contract-lite-local-readonly-ui-20260427T053413006335Z  failing=
```

Report path:

- `reports/contract/contract-lite-local-readonly-ui-20260427T053413006335Z.json`

Compatibility context checked for smoke, e2e, and contract:

```text
profile_id: lite-local-readonly-ui
extra_bundles: ""
matrix_version: 0.1.0
contract_version: v0.1.3
module_set_digest: e0c5a07e5efa60548db16118f0ac6bb11135285ef03f9ce2cbd552c4e93135af
matrix_digest: 44cb246986a99a43d38c3c3d1c8bd08e1579ffc99677a4d2d2eda4e879f776df
```

All three fresh run records carried exactly one matching
`compatibility_context` artifact.

## Promotion

Promotion command:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python -m assembly.cli.main \
  contract-suite \
  --profile lite-local-readonly-ui \
  --env-file .env \
  --reports-dir reports/contract \
  --promote
```

Result:

```text
success  contract-lite-local-readonly-ui-20260427T053424928510Z  failing=
```

Promotion report path:

- `reports/contract/contract-lite-local-readonly-ui-20260427T053424928510Z.json`

Promoted row:

```text
profile_id: lite-local-readonly-ui
extra_bundles: []
status: verified
verified_at: 2026-04-27T05:34:25.425611Z
```

Promotion supporting run records:

- `contract-lite-local-readonly-ui-20260427T053424928510Z`
- `smoke-lite-local-readonly-ui-20260427T053402181740Z`
- `e2e-lite-local-readonly-ui-20260427T053406092429Z`

## Preservation Check

Existing verified rows after promotion:

```text
lite-local [] verified 2026-04-24T05:24:14Z
full-dev [] verified 2026-04-24T05:24:14Z
full-dev [minio] verified 2026-04-24T06:51:23Z
```

The matrix diff is limited to the `lite-local-readonly-ui` row status,
comment, and `verified_at`; old verified rows' module sets, status, and
verified timestamps were preserved.

## Verification

Targeted compatibility tests run after the smoke normalization fix:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python -m pytest -q -p no:cacheprovider \
  tests/contracts/test_models.py \
  tests/smoke/test_runner.py
```

Result:

```text
29 passed
```

Required final verification commands:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python -m pytest -q -p no:cacheprovider \
  tests/registry \
  tests/compat \
  tests/smoke \
  tests/e2e/test_runner.py \
  tests/release/test_freezer.py

git diff --check
```

Results are recorded in the final handoff after execution.

Final result:

```text
passed (exit 0; existing expected skips/warnings only)
```

`git diff --check` result:

```text
passed
```
