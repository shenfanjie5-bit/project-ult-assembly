# Real-data mini-cycle runtime unblock evidence - 2026-04-27

## Scope

- Role: backend/data-platform Batch A.
- Goal: reduce operator/runtime blockers for the real-data mini-cycle without entering P2.
- Explicit non-goals honored: no P2, no P5 shadow-run, no API-6, no sidecar, no command/run/freeze/release-freeze write API exposure.
- Secret policy: no secret values printed or committed. `DP_PG_DSN`, `DATABASE_URL`, and `DP_TUSHARE_TOKEN` were reported only as set/missing/source type.

## Discovery

- data-platform has no tracked `docker-compose*.yml` or compose bootstrap. Existing PG-backed tests can create temporary databases only when `DATABASE_URL` is already available.
- `scripts/smoke_p1a.sh` and `scripts/smoke_p1c.sh` already create bounded raw/warehouse/duckdb/catalog paths, but both require `DP_PG_DSN`.
- Current shell env status before bootstrap: all required `DP_*` runtime keys missing; `DATABASE_URL` missing; external corpus root present.
- `assembly/.env` exists locally but contains none of the required mini-cycle `DP_*` keys.
- External corpus `/Volumes/dockcase2tb/database_all` has real `stock_basic`, `daily`, and `trade_cal` source directories. The selected symbols have daily rows through `20260331`; no `20260415` daily rows were found for the selected symbols.

## Changes

- data-platform commit: `4864e0db7d62641ccdca57f897c78ba63db1379d`
- Added `scripts/mini_cycle_runtime_bootstrap.py`:
  - creates bounded runtime dirs and catalog name;
  - can optionally create a temporary `dp_real_mini_cycle_*` PG database from an admin DSN env;
  - never writes `.env` and redacts DSN/token values.
- Added `scripts/corpus_backed_raw_zone_probe.py`:
  - explicit corpus-backed Raw Zone bridge/probe;
  - writes bounded parquet artifacts for `stock_basic`, `daily`, and `trade_cal`;
  - reports `live_tushare_token_used=false` and does not represent corpus data as live Tushare-token ingestion.

## Runtime profile

Command:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
.venv/bin/python scripts/mini_cycle_runtime_bootstrap.py \
  --base-dir /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/real-data-mini-cycle-runtime-unblock-artifacts/runtime \
  --profile-name batch-a-20260427 \
  --json-report /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/real-data-mini-cycle-runtime-unblock-artifacts/runtime-preflight.json \
  --print-json
```

Result: exit `2`, expected blocked preflight.

- Bounded runtime paths: created.
- Catalog name: `data_platform_real_mini_cycle_batch_a_20260427`.
- `DP_RAW_ZONE_PATH`, `DP_ICEBERG_WAREHOUSE_PATH`, `DP_DUCKDB_PATH`, `DP_ICEBERG_CATALOG_NAME`: generated.
- `DP_PG_DSN`: missing.
- `DP_TUSHARE_TOKEN`: missing.
- `DATABASE_URL`: missing.
- PG/Docker: not started; no repo compose file and no admin DSN were available.
- Full mini-cycle rerunnable now: no. Runtime-path blocker is reduced, but PG and live token blockers remain.

## Corpus bridge probe

Command:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
.venv/bin/python scripts/corpus_backed_raw_zone_probe.py \
  --corpus-root /Volumes/dockcase2tb/database_all \
  --raw-zone-path /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/real-data-mini-cycle-runtime-unblock-artifacts/raw \
  --iceberg-warehouse-path /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/real-data-mini-cycle-runtime-unblock-artifacts/warehouse \
  --dates 20260331 \
  --symbols 600519.SH,000001.SZ,000063.SZ \
  --json-report /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/real-data-mini-cycle-runtime-unblock-artifacts/corpus-bridge-raw-zone-probe-20260331.json \
  --print-json
```

Result: exit `0`.

- Mode: `corpus_backed_raw_zone_probe`.
- Live Tushare token used: `false`.
- Artifacts: 3 parquet files, 7 total rows.
- Raw Zone paths:
  - `reports/stabilization/real-data-mini-cycle-runtime-unblock-artifacts/raw/tushare/stock_basic/dt=20260331/`
  - `reports/stabilization/real-data-mini-cycle-runtime-unblock-artifacts/raw/tushare/daily/dt=20260331/`
  - `reports/stabilization/real-data-mini-cycle-runtime-unblock-artifacts/raw/tushare/trade_cal/dt=20260331/`

## Mini-cycle probe rerun

Command used the generated non-secret runtime paths and no PG/token:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
DP_RAW_ZONE_PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/real-data-mini-cycle-runtime-unblock-artifacts/runtime/batch_a_20260427/raw \
DP_ICEBERG_WAREHOUSE_PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/real-data-mini-cycle-runtime-unblock-artifacts/runtime/batch_a_20260427/warehouse \
DP_DUCKDB_PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/real-data-mini-cycle-runtime-unblock-artifacts/runtime/batch_a_20260427/duckdb/data_platform.duckdb \
DP_ICEBERG_CATALOG_NAME=data_platform_real_mini_cycle_batch_a_20260427 \
DP_ENV=test \
.venv/bin/python scripts/real_data_mini_cycle_probe.py \
  --dates 20260415 \
  --symbols 600519.SH,000001.SZ,000063.SZ \
  --artifact-dir /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/real-data-mini-cycle-runtime-unblock-artifacts/probe-artifacts \
  --json-report /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/real-data-mini-cycle-runtime-unblock-artifacts/real-data-mini-cycle-probe-runtime-paths.json \
  --print-json
```

Result: exit `2`, expected hard block.

- Runtime paths/catalog: `set`.
- `DP_PG_DSN`: missing.
- `DP_TUSHARE_TOKEN`: missing.
- `external_tushare_corpus_smoke`: OK.
- `tushare_token_raw_ingestion`: blocked, no mock fallback.
- `daily_refresh_dbt_canonical_real_path`: blocked by missing `DP_PG_DSN` and `DP_TUSHARE_TOKEN`.
- `audit_eval_replay_entrypoint`: OK, still `fixture_only`.
- `mock_fallback_used=false`, `allow_p2_real_l1_l8_dry_run=false`.

## Verification

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
.venv/bin/python -m pytest -q tests/scripts/test_mini_cycle_runtime_bootstrap.py tests/scripts/test_corpus_backed_raw_zone_probe.py tests/integration/test_real_data_mini_cycle_probe.py
```

Result: pass, `5 passed`.

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
git diff --check
```

Result: pass.

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
.venv/bin/python scripts/external_smoke_tushare_corpus.py
```

Result: pass, `6/6 checks passed`.

## Artifacts

- `reports/stabilization/real-data-mini-cycle-runtime-unblock-artifacts/runtime-preflight.json`
- `reports/stabilization/real-data-mini-cycle-runtime-unblock-artifacts/corpus-bridge-raw-zone-probe-20260331.json`
- `reports/stabilization/real-data-mini-cycle-runtime-unblock-artifacts/real-data-mini-cycle-probe-runtime-paths.json`
- `reports/stabilization/real-data-mini-cycle-runtime-unblock-artifacts/probe-artifacts/daily-refresh-real-probe-20260415.json`
- `reports/stabilization/real-data-mini-cycle-runtime-unblock-artifacts/raw/tushare/*/dt=20260331/`

## Gate decision

Do not enter P2.

The runtime-path blocker is partially removed by a reproducible non-secret bootstrap, and the corpus-backed Raw Zone bridge is proven for a bounded real corpus slice. The full real-data mini-cycle is still blocked because there is no `DP_PG_DSN` and no live `DP_TUSHARE_TOKEN`; the corpus bridge is intentionally separate from the live token path.

## Risks

- P0: none introduced in this batch.
- P1: no reachable PG DSN/admin DSN; daily refresh, cycle metadata, formal publish, and formal serving remain blocked.
- P2: live Tushare token path remains blocked; corpus bridge must not be promoted as live Tushare ingestion.
- P3: corpus selected symbols have daily data through `20260331`, not `20260415`; mini-cycle date selection must align with actual corpus availability or use live token.

## Next step

Provide either a non-secret operator runtime envelope with a reachable temporary PG/admin DSN plus live `DP_TUSHARE_TOKEN`, or decide that the mounted corpus is the intended real-data source and extend the corpus bridge into a bounded daily-refresh lane with explicit date coverage checks.
