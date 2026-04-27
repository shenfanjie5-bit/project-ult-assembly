# Tushare Live Token Smoke - 2026-04-27

## Scope

This evidence records a narrow live Tushare adapter smoke after the operator
provided `DP_TUSHARE_TOKEN` locally. It does not approve P2 or the full
real-data mini-cycle.

## Secret Handling

- `DP_TUSHARE_TOKEN`: set in local untracked `assembly/.env`.
- Token value was not printed into command output or committed evidence.
- `assembly/.env` remains untracked and must not be committed.

## Runtime Status

Checked without printing secret values:

- `DP_TUSHARE_TOKEN`: set in `assembly/.env`
- `DP_PG_DSN`: missing
- `DATABASE_URL`: missing
- `DP_RAW_ZONE_PATH`: missing
- `DP_ICEBERG_WAREHOUSE_PATH`: missing
- `DP_DUCKDB_PATH`: missing
- `DP_ICEBERG_CATALOG_NAME`: missing

## Live Tushare Adapter Smoke

Command:

```bash
rm -rf /tmp/project-ult-live-tushare-token-probe
mkdir -p /tmp/project-ult-live-tushare-token-probe/raw \
  /tmp/project-ult-live-tushare-token-probe/warehouse
bash -lc '
  set -a
  source /Users/fanjie/Desktop/Cowork/project-ult/assembly/.env
  set +a
  export DP_RAW_ZONE_PATH=/tmp/project-ult-live-tushare-token-probe/raw
  export DP_ICEBERG_WAREHOUSE_PATH=/tmp/project-ult-live-tushare-token-probe/warehouse
  cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
  .venv/bin/python -m data_platform.adapters.tushare.adapter \
    --asset tushare_stock_basic \
    --date 20260415
'
```

Result: exit `0`.

Raw Zone manifest summary:

- source: `tushare`
- dataset: `stock_basic`
- partition date: `2026-04-15`
- artifact count: `1`
- row count: `5510`
- artifact path: `/tmp/project-ult-live-tushare-token-probe/raw/tushare/stock_basic/dt=20260415/5604bc93-e254-48a3-8393-a6c17b1d31d7.parquet`

## Gate Decision

Do not enter P2.

The live Tushare token path is now smoke-proven for `stock_basic`, but the full
mini-cycle still requires a reachable `DP_PG_DSN` or `DATABASE_URL` plus bounded
runtime paths before daily refresh, dbt, cycle metadata, formal publish,
manifest-pinned formal serving, and audit/replay can be proven.

## Blueprint Alignment

This remains aligned with `project_ult_v5_0_1.md`:

- P1 owns Tushare adapter and 40 API/staging coverage.
- P1 requires PG-backed Iceberg catalog and PostgreSQL runtime state.
- P2 depends on P1 real data outputs.
- P5 shadow-run remains out of scope until P1-P4 prerequisites are ready.
