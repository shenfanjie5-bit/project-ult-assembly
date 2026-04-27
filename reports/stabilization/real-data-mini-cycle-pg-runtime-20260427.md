# Real-data mini-cycle PG/runtime evidence - 2026-04-27

## Scope

- Role: backend/data-platform PG/runtime worker, Batch B.
- Goal: unblock or clearly isolate PG/runtime for the real-data mini-cycle without entering P2.
- Secret policy: no secret values printed or committed. `DP_PG_DSN`, `DATABASE_URL`, `POSTGRES_PASSWORD`, and `DP_TUSHARE_TOKEN` are reported only as set/missing/source type.
- Local live token source: existing untracked `assembly/.env`; not committed.

## Discovery

- `psql`, `createdb`, `pg_isready`, Homebrew, Docker, and Colima are installed.
- `pg_isready` on the default local endpoint returned no response.
- Homebrew service discovery showed `postgresql@17 none`.
- Docker has a healthy `postgres:16` container, `compose-postgres-1`, mapped to `127.0.0.1:5432`.
- Docker container env has `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` set; values were not printed.
- Current shell env before sourcing local files:
  - `DATABASE_URL`: missing
  - `DP_PG_DSN`: missing
  - `DP_TUSHARE_TOKEN`: missing
- Local untracked `assembly/.env`:
  - `DP_TUSHARE_TOKEN`: set
  - `DATABASE_URL` / `DP_PG_DSN`: missing

## Runtime bootstrap

Command shape:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
DATABASE_URL=<set from local Docker PG env, value not printed> \
DP_TUSHARE_TOKEN=<set from untracked assembly/.env, value not printed> \
.venv/bin/python scripts/mini_cycle_runtime_bootstrap.py \
  --base-dir /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/real-data-mini-cycle-pg-runtime-artifacts/runtime \
  --profile-name batch-b-20260427-090300 \
  --json-report /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/real-data-mini-cycle-pg-runtime-artifacts/runtime-preflight.json \
  --create-pg-database \
  --admin-dsn-env DATABASE_URL \
  --print-json
```

Result: exit `0`.

- Temporary PG database created: `dp_real_mini_cycle_batch_b_20260427_090300`.
- `DP_PG_DSN`: obtained and used only in child process environment.
- Runtime profile ready: `true`.
- Generated catalog: `data_platform_real_mini_cycle_batch_b_20260427_090300`.
- Generated bounded paths:
  - `reports/stabilization/real-data-mini-cycle-pg-runtime-artifacts/runtime/batch_b_20260427_090300/raw`
  - `reports/stabilization/real-data-mini-cycle-pg-runtime-artifacts/runtime/batch_b_20260427_090300/warehouse`
  - `reports/stabilization/real-data-mini-cycle-pg-runtime-artifacts/runtime/batch_b_20260427_090300/duckdb/data_platform.duckdb`

Path note: `mini_cycle_runtime_bootstrap.py` normalizes profile names to safe
suffixes, so its preflight artifact records `batch_b_20260427_090300`. The
subsequent `daily_refresh` probe used an explicit shell work directory named
`batch-b-20260427-090300`. Both roots are evidence artifacts from the same
Batch B run; reruns should prefer the generated env values in
`runtime-preflight.json` unless intentionally overriding the runtime paths.

## PG-backed proof

Commands:

```bash
.venv/bin/python -m data_platform.ddl.runner --upgrade
.venv/bin/python scripts/init_iceberg_catalog.py
```

Results:

- Migrations applied: `0001`, `0002`, `0003`, `0004`, `0005`.
- Iceberg namespaces initialized: `canonical`, `formal`, `analytical`.

Additional PG-backed metadata probe:

- Created `CYCLE_20260427`.
- Transitioned through `phase0`, `phase1`, `phase2`, `phase3`.
- Published a formal manifest with 4 formal tables.
- Verified `get_publish_manifest`, `get_latest_publish_manifest`, and `get_publish_manifest_for_snapshot`.
- Result: `cycle_formal_metadata_ok`.

Focused PG-backed Iceberg/catalog test:

```bash
.venv/bin/python -m pytest -q \
  tests/scripts/test_mini_cycle_runtime_bootstrap.py \
  tests/integration/test_real_data_mini_cycle_probe.py \
  tests/serving/test_catalog.py \
  tests/spike/test_iceberg_write_chain.py
```

Result: `25 passed`.

## Mini-cycle probe

Command shape:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
DP_PG_DSN=<set in process env, value not printed> \
DP_TUSHARE_TOKEN=<set from untracked assembly/.env, value not printed> \
DP_RAW_ZONE_PATH=<bounded artifact path> \
DP_ICEBERG_WAREHOUSE_PATH=<bounded artifact path> \
DP_DUCKDB_PATH=<bounded artifact path> \
DP_ICEBERG_CATALOG_NAME=data_platform_real_mini_cycle_batch_b_20260427_090300 \
DP_ENV=test \
.venv/bin/python scripts/real_data_mini_cycle_probe.py \
  --dates 20260415 \
  --symbols 600519.SH,000001.SZ,000063.SZ \
  --artifact-dir /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/real-data-mini-cycle-pg-runtime-artifacts/probe-artifacts \
  --json-report /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/real-data-mini-cycle-pg-runtime-artifacts/real-data-mini-cycle-probe-pg-runtime.json \
  --print-json
```

Result: exit `2`.

Probe environment:

- `DP_PG_DSN`: set
- `DP_TUSHARE_TOKEN`: set
- `DP_RAW_ZONE_PATH`: set
- `DP_ICEBERG_WAREHOUSE_PATH`: set
- `DP_DUCKDB_PATH`: set
- `DP_ICEBERG_CATALOG_NAME`: set
- `DATABASE_URL`: set
- `dbt_executable`: set
- external corpus root: present

Probe checks:

- `external_tushare_corpus_available`: ok
- `tushare_token_raw_ingestion`: ok
- `daily_refresh_dbt_canonical_real_path`: failed
- `cycle_metadata_candidate_freeze`: unknown, not executed by this probe after daily refresh failure
- `formal_object_commit_publish_manifest`: unknown, not executed by this probe after daily refresh failure
- `formal_serving_manifest_snapshot_read`: unknown, not executed by this probe after daily refresh failure
- `audit_eval_replay_entrypoint`: ok, still `fixture_only`

Accurate failure point:

- `scripts/daily_refresh.sh --date 20260415 --select stock_basic,daily` reached `dbt_run`.
- `dbt_run` failed with exit `1`.
- Captured root exception tail: `mashumaro.exceptions.UnserializableField: Field "schema" of type Optional[str] in JSONObjectSchema is not serializable`.
- This is a dbt/mashumaro runtime compatibility failure in the current `.venv` (`python3.14`), not a PG DSN or token blocker.

## Artifacts

- `reports/stabilization/real-data-mini-cycle-pg-runtime-artifacts/runtime-preflight.json`
- `reports/stabilization/real-data-mini-cycle-pg-runtime-artifacts/runtime-env-status.txt`
- `reports/stabilization/real-data-mini-cycle-pg-runtime-artifacts/migrations.stdout.txt`
- `reports/stabilization/real-data-mini-cycle-pg-runtime-artifacts/init-catalog.stdout.txt`
- `reports/stabilization/real-data-mini-cycle-pg-runtime-artifacts/cycle-formal-metadata.stdout.txt`
- `reports/stabilization/real-data-mini-cycle-pg-runtime-artifacts/focused-pytest.stdout.txt`
- `reports/stabilization/real-data-mini-cycle-pg-runtime-artifacts/probe-artifacts/daily-refresh-real-probe-20260415.json`
- `reports/stabilization/real-data-mini-cycle-pg-runtime-artifacts/real-data-mini-cycle-probe-pg-runtime.json`

Secret scan:

- New artifact directory scanned for current `DP_TUSHARE_TOKEN`, `DP_PG_DSN`, `DATABASE_URL`, and `POSTGRES_PASSWORD` values.
- Result: pass.

## Verification

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
.venv/bin/python -m pytest -q \
  tests/scripts/test_mini_cycle_runtime_bootstrap.py \
  tests/integration/test_real_data_mini_cycle_probe.py \
  tests/serving/test_catalog.py \
  tests/spike/test_iceberg_write_chain.py
```

Result: `25 passed`.

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/assembly
python3 <secret-value-scan for real-data-mini-cycle-pg-runtime-artifacts>
```

Result: `secret_value_scan=pass`.

## Gate decision

Do not enter P2.

PG/runtime is no longer the blocker for this local environment: a safe `dp_real_mini_cycle_*` database was created, migrations ran, PG-backed Iceberg catalog initialized, Iceberg write-chain tests passed, and cycle/formal publish metadata was proven. The remaining blocker is the `daily_refresh` dbt runtime failure under the current Python/dbt/mashumaro environment.

## Risks

- P0: none introduced.
- P1: full mini-cycle cannot close until dbt runtime compatibility is fixed or rerun under a supported Python environment.
- P2: still closed; probe did not authorize P2 real L1-L8 dry run.
- P3: local Docker PG dependency is operator-local; repeatability requires either the same Docker PG envelope or an explicit admin DSN.

## Recommendation

Proceed to a Batch D mini-cycle close loop only after the dbt/mashumaro failure is fixed or a known-good Python runtime is selected. PG/runtime can be treated as provisionally unblocked for local reruns with the same safe temporary DB bootstrap.
