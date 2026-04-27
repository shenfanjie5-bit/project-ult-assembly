# Real-data Mini Cycle Runtime Unblock Supervisor Review - 2026-04-27

## Scope

This review closes backend Batch A for reducing real-data mini-cycle runtime
blockers. It does not approve P2 real L1-L8 dry run.

## Reviewed Commits

- data-platform: `4864e0db7d62641ccdca57f897c78ba63db1379d`
- assembly evidence: `d9fe04d52089cc0fa93170f9180ffacbfe17f7e1`

## Reviewed Evidence

- `assembly/reports/stabilization/real-data-mini-cycle-runtime-unblock-20260427.md`
- `assembly/reports/stabilization/real-data-mini-cycle-runtime-unblock-artifacts/runtime-preflight.json`
- `assembly/reports/stabilization/real-data-mini-cycle-runtime-unblock-artifacts/corpus-bridge-raw-zone-probe-20260331.json`
- `assembly/reports/stabilization/real-data-mini-cycle-runtime-unblock-artifacts/real-data-mini-cycle-probe-runtime-paths.json`
- committed bounded Raw Zone artifacts under
  `assembly/reports/stabilization/real-data-mini-cycle-runtime-unblock-artifacts/raw/tushare/`

## Supervisor Checks

Reviewed changes:

- `data-platform/scripts/mini_cycle_runtime_bootstrap.py`
- `data-platform/scripts/corpus_backed_raw_zone_probe.py`
- `data-platform/tests/scripts/test_mini_cycle_runtime_bootstrap.py`
- `data-platform/tests/scripts/test_corpus_backed_raw_zone_probe.py`

The data-platform commit only adds scripts and tests. The assembly commit only
adds evidence markdown and evidence artifacts. No API-6, sidecar, or
command/run/freeze/release-freeze exposure was added.

## Commands Re-run

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
.venv/bin/python -m pytest -q \
  tests/scripts/test_mini_cycle_runtime_bootstrap.py \
  tests/scripts/test_corpus_backed_raw_zone_probe.py \
  tests/integration/test_real_data_mini_cycle_probe.py
```

Result: pass, `5 passed`.

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
.venv/bin/python scripts/mini_cycle_runtime_bootstrap.py \
  --base-dir /tmp/project-ult-runtime-unblock-review/runtime \
  --profile-name supervisor-review \
  --json-report /tmp/project-ult-runtime-unblock-review/runtime-preflight.json
```

Result: exit `2`, expected blocked preflight. It generated bounded
raw/warehouse/duckdb/catalog values, did not write `.env`, did not print
secrets, and still reported `DP_PG_DSN` and `DP_TUSHARE_TOKEN` missing.

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
.venv/bin/python scripts/corpus_backed_raw_zone_probe.py \
  --corpus-root /Volumes/dockcase2tb/database_all \
  --raw-zone-path /tmp/project-ult-corpus-bridge-review/raw \
  --iceberg-warehouse-path /tmp/project-ult-corpus-bridge-review/warehouse \
  --dates 20260331 \
  --symbols 600519.SH,000001.SZ,000063.SZ \
  --json-report /tmp/project-ult-corpus-bridge-review/corpus-probe.json
```

Result: pass. The probe produced three bounded Raw Zone artifacts:
`stock_basic`, `daily`, and `trade_cal`, with 7 total rows. The report explicitly
sets `mode=corpus_backed_raw_zone_probe` and `live_tushare_token_used=false`.

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
.venv/bin/python scripts/external_smoke_tushare_corpus.py
```

Result: pass, `6/6 checks passed`.

```bash
git diff --check
```

Run in data-platform and assembly. Result: pass.

## Independent Review

Testing role independently re-ran the focused paths and reported no
P0/P1/P2/P3 findings.

Key confirmations:

- runtime path/catalog blockers were narrowed;
- `DP_PG_DSN` and live `DP_TUSHARE_TOKEN` still block the full mini-cycle;
- the corpus bridge is not presented as live token ingestion;
- no forbidden files or secret values were committed;
- P2 remains blocked.

## Gate Decision

Do not enter P2.

Batch A is valid progress, but it does not yet prove the full real-data
mini-cycle. Current state:

- `DP_RAW_ZONE_PATH`, `DP_ICEBERG_WAREHOUSE_PATH`, `DP_DUCKDB_PATH`, and
  `DP_ICEBERG_CATALOG_NAME` can now be generated in a reproducible bounded
  runtime profile;
- mounted corpus data can be shaped into bounded Raw Zone artifacts for
  `20260331` and selected A-share symbols;
- `DP_PG_DSN` is still missing, so daily refresh, cycle metadata, formal publish
  manifest, and formal serving remain blocked;
- live `DP_TUSHARE_TOKEN` is still missing, so live Tushare ingestion remains
  hard-blocked;
- corpus data availability currently aligns with `20260331`, not the earlier
  `20260415` probe date.

## Next Backend Batch

Continue backend-first. Pick one path explicitly:

1. **Operator runtime path**: provide a temporary PG/admin DSN and live
   `DP_TUSHARE_TOKEN`, then use the new bootstrap profile to rerun the full
   mini-cycle probe and daily refresh path.
2. **Corpus-as-source path**: decide that the mounted corpus is the intended
   real data source for the mini-cycle, then extend the corpus bridge into a
   bounded daily-refresh lane with explicit date coverage checks and downstream
   dbt/cycle/formal/audit evidence.

Until one of those paths proves ingestion, dbt, candidate freeze, Phase 0-3,
manifest publish, formal serving, and audit/replay, P2 remains closed.
