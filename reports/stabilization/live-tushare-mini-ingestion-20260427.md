# Live Tushare mini ingestion evidence - 2026-04-27

## Scope

- Role: backend/data-platform Batch C live Tushare ingestion worker.
- Goal: reusable, auditable bounded live Tushare Raw Zone probe for the real-data mini-cycle close loop.
- Explicit non-goals honored: no P2, no corpus/mock data represented as live, no PostgreSQL/dbt/canonical execution.
- Secret handling: `DP_TUSHARE_TOKEN` was loaded from local untracked `assembly/.env`; token value was not printed or committed.

## Discovery

- `data_platform.adapters.tushare.adapter.TushareAdapter._fetch()` passes caller params through to Tushare after validating configured date params, and overwrites `fields` with the declared schema fields.
- `daily` can be bounded by `ts_code` plus `trade_date`; the new probe issues one request per requested symbol for a single date.
- `trade_cal` has no symbol dimension; it is bounded with `start_date=end_date=<date>`.
- `stock_basic` is static and has no date or `ts_code` request filter in the current adapter/Tushare API usage. The probe supports it explicitly with `list_status=L`, marks it as not symbol-filterable upstream, and writes only requested symbols after fetch. It was not included in the live smoke below to keep this run small.
- `daily_refresh` supports selected assets/datasets via `--select`, but it has no symbol filter and still proceeds into PG/dbt/canonical steps. I did not widen `daily_refresh`; the new entry is a narrow Raw Zone probe.

## Data-platform change

- Added `scripts/live_tushare_bounded_raw_probe.py`.
- Supported datasets: `daily`, `trade_cal`, `stock_basic`.
- Defaults: `daily,trade_cal`, date `20260415`, symbols `600519.SH,000001.SZ`.
- Report guarantees:
  - includes `live_tushare_token_used=true` when token-backed live probe ran;
  - records request scope, row counts, artifact paths, manifest paths, and bounded strategy;
  - does not emit token values.

## Live smoke

Command:

```bash
set -euo pipefail
ARTIFACT_ROOT=/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/live-tushare-mini-ingestion-artifacts
rm -rf "$ARTIFACT_ROOT"
mkdir -p "$ARTIFACT_ROOT/raw" "$ARTIFACT_ROOT/warehouse"
set -a
source /Users/fanjie/Desktop/Cowork/project-ult/assembly/.env
set +a
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src:/Users/fanjie/Desktop/Cowork/project-ult/data-platform \
  /Users/fanjie/Desktop/Cowork/project-ult/data-platform/.venv/bin/python \
  /Users/fanjie/Desktop/Cowork/project-ult/data-platform/scripts/live_tushare_bounded_raw_probe.py \
  --date 20260415 \
  --symbols 600519.SH,000001.SZ \
  --datasets daily,trade_cal \
  --raw-zone-path "$ARTIFACT_ROOT/raw" \
  --iceberg-warehouse-path "$ARTIFACT_ROOT/warehouse" \
  --json-report "$ARTIFACT_ROOT/live-tushare-bounded-raw-probe-20260415.json" \
  --print-json
```

Result: exit `0`.

- `live_tushare_token_used=true`
- Scope:
  - date: `20260415`
  - symbols: `600519.SH`, `000001.SZ`
  - datasets: `daily`, `trade_cal`
- `daily`:
  - bounded strategy: per-symbol `ts_code` plus single `trade_date`
  - requests: `2`
  - upstream rows: `2`
  - written rows: `2`
  - artifact: `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/live-tushare-mini-ingestion-artifacts/raw/tushare/daily/dt=20260415/a8ef0d4d-b89e-4ca2-8249-3030aa4b094b.parquet`
  - manifest: `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/live-tushare-mini-ingestion-artifacts/raw/tushare/daily/dt=20260415/_manifest.json`
- `trade_cal`:
  - bounded strategy: single-day `start_date=end_date`; no symbol dimension
  - requests: `1`
  - upstream rows: `1`
  - written rows: `1`
  - artifact: `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/live-tushare-mini-ingestion-artifacts/raw/tushare/trade_cal/dt=20260415/774c86fa-b70b-4157-b3ed-c40f80887cca.parquet`
  - manifest: `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/live-tushare-mini-ingestion-artifacts/raw/tushare/trade_cal/dt=20260415/_manifest.json`
- JSON report: `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/live-tushare-mini-ingestion-artifacts/live-tushare-bounded-raw-probe-20260415.json`

## Verification

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
.venv/bin/python -m pytest tests/scripts/test_live_tushare_bounded_raw_probe.py tests/integration/test_real_data_mini_cycle_probe.py
```

Result: pass, `5 passed`.

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
.venv/bin/ruff check scripts/live_tushare_bounded_raw_probe.py tests/scripts/test_live_tushare_bounded_raw_probe.py
```

Result: pass, `All checks passed!`.

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
git diff --check
```

Result: pass.

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/assembly
git diff --check
```

Result: pass.

## Can connect to daily_refresh/dbt

- Raw Zone layout is compatible with existing dbt sources: `raw/tushare/<dataset>/dt=YYYYMMDD/*.parquet` with `_manifest.json`.
- The probe itself does not call dbt or canonical writers and does not require PG.
- Once `DP_PG_DSN` and runtime paths are available, the full close-loop should rerun through `daily_refresh` or a PG-backed mini-cycle command.
- Current gap: `daily_refresh` cannot preserve symbol bounds, so a full `daily_refresh --select daily,trade_cal,stock_basic` may call broader upstream scopes than this probe.

## Gate decision

Do not enter P2.

- P0: none introduced.
- P1: live bounded Raw Zone ingestion for `daily` and `trade_cal` is proven. After the later PG/runtime batch, the remaining full mini-cycle blocker is the `daily_refresh` dbt/mashumaro runtime failure, not `DP_PG_DSN`.
- P2: remains closed; no L1-L8 real dry-run approval from this evidence.
- P3: `stock_basic` is supported by the probe but upstream symbol filtering is not available; use it only with explicit awareness of the active-list API call and post-fetch output bound.
