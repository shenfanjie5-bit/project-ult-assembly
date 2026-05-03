# M4 Bridge Live PostgreSQL Proof - 2026-05-03

This report closes the live PostgreSQL evidence portion of M4.3 and M4.4 for
the production bridge. It reuses the running `compose-postgres-1` PostgreSQL 16
service and only touches the two isolated proof databases listed below.

## Environment

- PostgreSQL container: `compose-postgres-1`
- Host endpoint: `localhost:5432`
- User: `postgres`
- P1c smoke database: `dp_p1c_smoke_m4bridge`
- M4.4 proof database: `m4_bridge_proof_20260503`
- DSN policy: redacted in reports; password is read from `assembly/.env` only

Both proof databases were rebuilt before execution with `dropdb --if-exists`
and `createdb`.

## M4.3 Queue/Freeze Smoke

Command shape:

```bash
cd data-platform
DP_ENV=test \
DP_SMOKE_P1C_CONFIRM_DESTRUCTIVE=1 \
DP_ICEBERG_CATALOG_NAME=data_platform_p1c_smoke_m4bridge \
DP_SMOKE_WORK_DIR=/tmp/data-platform-p1c-smoke-m4bridge \
DP_RAW_ZONE_PATH=/tmp/data-platform-p1c-smoke-m4bridge/raw \
DP_ICEBERG_WAREHOUSE_PATH=/tmp/data-platform-p1c-smoke-m4bridge/warehouse \
DP_DUCKDB_PATH=/tmp/data-platform-p1c-smoke-m4bridge/data_platform.duckdb \
DP_PG_DSN='postgresql://postgres:<redacted>@localhost:5432/dp_p1c_smoke_m4bridge' \
make smoke-p1c
```

Result:

- Status: passed, non-skipped
- Output marker: `P1c smoke OK`
- Cycle: `CYCLE_20260503`
- Submitted candidates: 3
- Accepted candidates: 3
- Frozen `cycle_candidate_selection` rows: 3
- `cycle_metadata` rows: 1

The first invocation failed at the script guard before migrations or writes
because inherited raw paths were outside `DP_SMOKE_WORK_DIR`. The successful run
explicitly pinned raw, warehouse, and DuckDB paths inside the smoke work dir.

## M4.4 Ex-3 Graph Bridge Proof

Command shape:

```bash
cd assembly
DP_PG_DSN='postgresql://postgres:<redacted>@localhost:5432/m4_bridge_proof_20260503' \
.venv-py312/bin/python scripts/m4_ex3_queue_promotion_proof.py \
  --database-url "$DP_PG_DSN" \
  --trade-date 20260503 \
  --out reports/stabilization/m4-ex3-queue-promotion-proof-20260503.json
```

Evidence file:

- `reports/stabilization/m4-ex3-queue-promotion-proof-20260503.json`

Result summary:

- Status: `passed`
- Applied migrations: `0001`, `0002`, `0003`, `0004`, `0005`
- Candidate id: `1`
- Candidate ingest seq: `1`
- Candidate validation status: `accepted`
- Cycle id: `CYCLE_20260503`
- Selection ref: `cycle_candidate_selection:CYCLE_20260503`
- Frozen candidate count: `1`
- Reader delta count: `1`
- Promotion plan delta count: `1`
- Edge count: `1`
- Writer called: `true`
- Skipped live prerequisites: none

The proof establishes:

```text
candidate_queue Ex-3
  -> validate_pending_candidates
  -> freeze_cycle_candidates / cycle_candidate_selection
  -> PostgresCandidateDeltaReader
  -> CandidateGraphDelta
  -> graph_engine.promote_graph_deltas(sync_to_live_graph=False)
  -> PromotionPlan edge output
```

## Closeout

M4.3 and M4.4 are no longer blocked by missing PostgreSQL evidence in this
local environment. Remaining M4 follow-up should not expand into holdings work
until the bridge changes and evidence are reviewed as one diff.
