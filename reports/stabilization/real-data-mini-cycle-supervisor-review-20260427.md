# Real-data Mini Cycle Supervisor Review - 2026-04-27

## Scope

This review closes the first real-data mini-cycle backend evidence batch. It
decides whether Project ULT may enter the P2 real L1-L8 dry run gate.

## Reviewed Commits

- data-platform: `e0835823d9abbcb5310d5ed03235f003dd5c13ec`
- assembly evidence: `e2674fa9eef5a6244d750576a9163edcef6a2976`
- orchestrator baseline inspected: `c004ee32666097ce67b431869a94b428852c59ad`
- audit-eval baseline inspected: `2f41580078c0b39c5315f7bb312785c26bc67ccf`

## Reviewed Evidence

- `assembly/reports/stabilization/real-data-mini-cycle-20260427.md`
- `assembly/reports/stabilization/real-data-mini-cycle-probe-20260427.json`
- `assembly/reports/stabilization/real-data-mini-cycle-artifacts/daily-refresh-real-probe-20260415.json`
- `assembly/reports/stabilization/real-data-mini-cycle-artifacts/orchestrator-min-cycle-report.json`
- `assembly/reports/stabilization/real-data-mini-cycle-artifacts/orchestrator-min-cycle/cycle_summary.json`

## Independent Review

Testing role independently re-ran the focused paths and reported no
P0/P1/P2/P3 findings.

Key confirmations:

- no fixture, mock, or assembly-only path was represented as real execution;
- `audit_eval_replay_entrypoint` is explicitly marked `fixture_only`;
- `orchestrator min-cycle` remains import/assembly-only and does not materialize
  real assets;
- data-platform probe is narrow and does not introduce API-6, sidecar, or
  command/run/freeze/release-freeze exposure;
- target commits do not include `.env`, venv/cache/tmp/build/dist/egg-info, or
  `PROJECT_REPORT.md`.

## Supervisor Reproduction

Commands re-run by the supervisor:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
.venv/bin/python -m pytest -q tests/integration/test_real_data_mini_cycle_probe.py
```

Result: pass, `2 passed`.

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
.venv/bin/python scripts/real_data_mini_cycle_probe.py \
  --dates 20260415 \
  --symbols 600519.SH,000001.SZ,000063.SZ \
  --artifact-dir /tmp/project-ult-supervisor-real-mini-cycle-review/artifacts \
  --json-report /tmp/project-ult-supervisor-real-mini-cycle-review/probe.json
```

Result: exit `2`, expected hard block. The reproduced report had
`real_cycle_runnable=false`, `mock_fallback_used=false`, and
`allow_p2_real_l1_l8_dry_run=false`.

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/orchestrator
.venv/bin/python -m pytest -q tests/cli/test_min_cycle.py tests/integration/test_daily_cycle_four_phase.py
```

Result: pass, `27 passed, 2 skipped`.

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/audit-eval
.venv/bin/python -m pytest -q tests/test_spike_replay.py
```

Result: pass, `5 passed`.

```bash
git diff --check
```

Run in data-platform, orchestrator, audit-eval, and assembly. Result: pass.

## Gate Decision

Do not enter P2 real L1-L8 dry run.

The batch is valid evidence, but it proves that the real-data mini cycle is
currently blocked by missing operator/runtime prerequisites:

- `DP_PG_DSN` / `DATABASE_URL` missing;
- `DP_TUSHARE_TOKEN` missing;
- `DP_RAW_ZONE_PATH`, `DP_ICEBERG_WAREHOUSE_PATH`, `DP_DUCKDB_PATH`, and
  `DP_ICEBERG_CATALOG_NAME` missing;
- no corpus-backed bridge exists for `daily_refresh` if the external corpus is
  the intended real data source;
- candidate freeze, formal publish manifest, manifest-pinned formal serving,
  and real audit/replay remain unproven in this environment.

## Next Batch

Before retrying the mini-cycle gate, assign a backend batch to provide one of:

1. a non-secret operator runtime profile with the required PG/Iceberg/Tushare
   environment values and bounded artifact directories; or
2. a scoped corpus-backed ingestion bridge if the mounted corpus is the intended
   real data source.

Only after a clean 1-3 trading-day mini cycle proves ingestion, dbt,
candidate freeze, Phase 0-3 execution, manifest publish, formal serving, and
audit/replay may the project enter P2 real L1-L8 dry run.
