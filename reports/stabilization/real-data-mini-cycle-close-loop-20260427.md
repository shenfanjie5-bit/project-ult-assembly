# Real Data Mini-Cycle Close Loop - 2026-04-27

## Scope

- Date: `20260415`
- Requested symbols: `600519.SH`, `000001.SZ`
- Actual `daily_refresh` scope: dataset-bounded only. `daily_refresh.sh --select stock_basic,daily` does not apply a symbol filter, so raw `daily` ingestion was broader than the requested two-symbol probe scope.
- Runtime: local untracked `assembly/.env` supplied the live Tushare token and compose PostgreSQL credentials. No token or DSN is recorded in this report.

## Runtime

- Temporary PostgreSQL database: `dp_real_mini_cycle_20260427_batch_d_091540`
- Runtime root: `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/tmp/real-data-mini-cycle-close-loop-20260427/20260427_batch_d_091540`
- Artifact directory: `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/real-data-mini-cycle-close-loop-20260427-artifacts`
- Python runtime: `/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python`
- dbt runtime: `/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/dbt`
- Environment status artifact: `real-data-mini-cycle-close-loop-20260427-artifacts/runtime-env-status.json`

## Commands

```bash
source /Users/fanjie/Desktop/Cowork/project-ult/assembly/.env
export PYTHON=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python
export DP_DBT_EXECUTABLE=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/dbt
export DP_RAW_ZONE_PATH=/Users/fanjie/Desktop/Cowork/project-ult/data-platform/tmp/real-data-mini-cycle-close-loop-20260427/20260427_batch_d_091540/raw
export DP_ICEBERG_WAREHOUSE_PATH=/Users/fanjie/Desktop/Cowork/project-ult/data-platform/tmp/real-data-mini-cycle-close-loop-20260427/20260427_batch_d_091540/warehouse
export DP_DUCKDB_PATH=/Users/fanjie/Desktop/Cowork/project-ult/data-platform/tmp/real-data-mini-cycle-close-loop-20260427/20260427_batch_d_091540/duckdb/data_platform.duckdb
export DP_ICEBERG_CATALOG_NAME=data_platform_real_mini_cycle_close_loop_20260427
# DP_PG_DSN and DP_TUSHARE_TOKEN were set in-process only and are intentionally omitted.

bash scripts/daily_refresh.sh \
  --date 20260415 \
  --select stock_basic,daily \
  --json-report /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/real-data-mini-cycle-close-loop-20260427-artifacts/daily-refresh-20260415.json
```

Follow-up Python probes used existing `data_platform.cycle`, `data_platform.serving.catalog`, and `data_platform.serving.formal` APIs to create/freeze the cycle, write minimal formal snapshots, publish the manifest, and read `latest`, `by_id`, and `by_snapshot`.

## Daily Refresh Evidence

- Result: PASS
- Steps: `adapter`, `dbt_run`, `dbt_test`, `canonical`, `raw_health` all `ok`
- Raw row counts:
  - `stock_basic`: 5,510 rows
  - `daily`: 5,494 rows
- Canonical write:
  - `canonical.stock_basic`: 5,510 rows, snapshot `2303340538722692231`
  - `canonical.canonical_marts`: skipped because only `stock_basic,daily` datasets were selected
- Evidence: `real-data-mini-cycle-close-loop-20260427-artifacts/daily-refresh-20260415.json`

## Cycle And Formal Evidence

- Cycle ID: `CYCLE_20260415`
- Final cycle status: `published`
- Candidate freeze:
  - `candidate_count`: 0
  - `selection_row_count`: 0
  - `selection_frozen_at`: set
  - Empty-candidate semantics are explicit: no accepted candidates existed in this temporary DB, and no candidates were fabricated.
- Formal content: synthetic/minimal formal object rows, written only to prove the publish/serving path.
- Manifest snapshot IDs:
  - `formal.world_state_snapshot`: `1145325163516225717`
  - `formal.official_alpha_pool`: `3767228895954008953`
  - `formal.alpha_result_snapshot`: `424165751233285843`
  - `formal.recommendation_snapshot`: `6320750134102262127`
- Metadata migrations applied: `0001`, `0002`, `0003`, `0004`, `0005`
- Evidence: `real-data-mini-cycle-close-loop-20260427-artifacts/cycle-formal-serving-summary.json`

## Manifest-Pinned Serving

`get_formal_latest("recommendation_snapshot")`, `get_formal_by_id("CYCLE_20260415", "recommendation_snapshot")`, and `get_formal_by_snapshot(6320750134102262127, "recommendation_snapshot")` all returned:

- `cycle_id`: `CYCLE_20260415`
- `snapshot_id`: `6320750134102262127`
- `row_count`: 1
- payload marker: `content_kind=synthetic_minimal_formal_object`

This proves serving read through the published manifest snapshot rather than relying on a direct formal head read.

## Audit/Replay Status

- `audit-eval/scripts/spike_replay.py` ran successfully against its fixture cycle `cycle_20260410`.
- Status: PASS for fixture replay entrypoint.
- Real-cycle binding: gap/blocker. The inspected `audit-eval` replay path is fixture-backed through `FixtureManifestGateway` and `FixtureFormalSnapshotGateway`; no real `data-platform` cycle manifest/formal snapshot gateway is wired yet.
- Evidence: `real-data-mini-cycle-close-loop-20260427-artifacts/audit-eval-status.json`

## Gate Recommendation

P1 mini-cycle close-loop is clean enough to start P2 planning with a scoped caveat:

- Green: live Tushare ingestion, dbt run/test, canonical write, cycle create/freeze, explicit empty-candidate handling, formal snapshot commit, publish manifest, and manifest-pinned serving are proven in one temporary real-data runtime.
- Caveat: formal object business content is synthetic/minimal.
- Blocker for claiming full real audit/replay close-loop: `audit-eval` is still fixture-only for replay gateway binding.

