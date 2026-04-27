# Real-data mini-cycle dbt runtime evidence - 2026-04-27

## Scope

- Role: backend/data-platform dbt runtime fix worker.
- Goal: unblock the `daily_refresh` dbt runtime failure without entering P2.
- Secret policy: no token, DSN, password, or `.env` value printed or committed. Local untracked `assembly/.env` was used only as process env for PG/Tushare inputs.

## Discovery

- `data-platform/.venv` is Python `3.14.3`.
- Current failing dbt stack in `data-platform/.venv`:
  - `dbt-core 1.11.8`
  - `dbt-duckdb 1.10.1`
  - `dbt-adapters 1.22.10`
  - `dbt-common 1.37.3`
  - `mashumaro 3.14`
- `pyproject.toml` previously allowed `requires-python = ">=3.12"` while repo tooling targets Python 3.12.
- Reproduced direct import/runtime failure:
  - command: `.venv/bin/dbt --version`
  - result: exit `1`
  - root exception: `mashumaro.exceptions.UnserializableField: Field "schema" of type Optional[str] in JSONObjectSchema is not serializable`
- Existing compatible local runtime:
  - `assembly/.venv-py312` is Python `3.12.12`
  - dbt stack: `dbt-core 1.9.8`, `dbt-duckdb 1.10.1`, `mashumaro 3.14`
  - `dbt --version` succeeds there.

## Fix

Data-platform changes:

- Restricted package runtime to `>=3.12,<3.14` to stop silently bootstrapping the dbt path on Python 3.14.
- Updated `scripts/dbt.sh` to honor explicit `DP_DBT_EXECUTABLE`/`DBT_BIN`, then prefer repo-local `.venv-py312` / `.venv-py313`, then PATH, then legacy `.venv`.
- Updated `daily_refresh._run_dbt_command()` to resolve the same compatible dbt executable and pass it to the wrapper as `DP_DBT_EXECUTABLE`.
- Updated `scripts/daily_refresh.sh` to prefer `.venv-py312` / `.venv-py313` Python runtimes when present.
- Added wrapper regression coverage for explicit compatible dbt executable selection.
- Added `.venv-py312/` and `.venv-py313/` to `.gitignore`.

No dbt step was mocked or skipped.

## Validation

Focused tests:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
.venv/bin/python -m pytest tests/dbt/test_dbt_wrapper.py tests/integration/test_daily_refresh.py -q
```

Result: `10 passed, 1 skipped`.

Whitespace check:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
git diff --check
```

Result: pass.

Real `daily_refresh` dbt/canonical path:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
DP_PG_DSN=<set to temporary dp_real_mini_cycle_* database> \
DP_TUSHARE_TOKEN=<set from local untracked assembly/.env> \
DP_RAW_ZONE_PATH=<bounded temp raw path> \
DP_ICEBERG_WAREHOUSE_PATH=<bounded temp warehouse path> \
DP_DUCKDB_PATH=<bounded temp DuckDB path> \
DP_ICEBERG_CATALOG_NAME=<bounded temp catalog> \
DP_DBT_EXECUTABLE=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/dbt \
PYTHON=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python \
./scripts/daily_refresh.sh --date 20260415 --select stock_basic,daily \
  --json-report <artifact>
```

Result: exit `0`, `Daily refresh OK`.

Report summary:

- JSON report: `reports/stabilization/real-data-mini-cycle-dbt-runtime-artifacts/daily-refresh-stock-basic-daily-20260415.json`
- `ok`: `true`
- `adapter`: ok, live mode, 2 raw artifacts written.
- `dbt_run`: ok, return code `0`.
- `dbt_test`: ok, return code `0`.
- `canonical`: ok, wrote selected canonical stock_basic path and intentionally skipped full marts because this run selected a subset.
- `raw_health`: ok, 2 artifacts checked.
- Temporary database was dropped after validation.

## Gate decision

`daily_refresh_dbt_canonical_real_path` is no longer blocked by the Python 3.14 dbt/mashumaro runtime failure when a Python 3.12 dbt runtime is selected.

Do not enter P2 from this evidence.

## Risks

- P0: none introduced.
- P1: dbt runtime blocker is cleared for the local close-loop path; repeatability requires a Python 3.12/3.13 dbt runtime or explicit `DP_DBT_EXECUTABLE`.
- P2: still closed; this is not an L1-L8 real dry-run approval.
- P3: current validation uses operator-local Docker PG and untracked local token env; CI should use the documented env contract rather than checked-in secrets.

## Recommendation

Proceed to Batch D mini-cycle close loop with the compatible dbt runtime selected explicitly or via repo-local `.venv-py312`.
