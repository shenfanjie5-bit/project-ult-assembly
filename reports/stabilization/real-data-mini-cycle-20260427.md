# Real-data mini cycle evidence - 2026-04-27

## Scope

- Cycle type: real-data mini-cycle backend evidence batch.
- Dates: `20260415` only. The requested 1-3 trading-day range was kept to one day because real PG/Iceberg/Tushare credentials are not present in this operator environment.
- Symbols: `600519.SH`, `000001.SZ`, `000063.SZ`.
- Mock/fixture policy: no mock fallback was used or represented as real. Audit replay fixture coverage is explicitly labeled fixture-only.

## Environment prerequisites

Checked without printing secret values:

- `DP_PG_DSN`: missing
- `DATABASE_URL`: missing
- `DP_TUSHARE_TOKEN`: missing
- `DP_RAW_ZONE_PATH`: missing
- `DP_ICEBERG_WAREHOUSE_PATH`: missing
- `DP_DUCKDB_PATH`: missing
- `DP_ICEBERG_CATALOG_NAME`: missing
- dbt executable: present in data-platform `.venv`
- external Tushare corpus root `/Volumes/dockcase2tb/database_all`: present

## Repo commits used

- data-platform: `e0835823d9abbcb5310d5ed03235f003dd5c13ec`
- orchestrator: `c004ee32666097ce67b431869a94b428852c59ad`
- audit-eval: `2f41580078c0b39c5315f7bb312785c26bc67ccf`
- assembly base while writing evidence: `7bf86b46b0d919b5a04bc81d5f45119074aa97dc`

## Commands and results

### data-platform focused test

Command:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
.venv/bin/python -m pytest -q tests/integration/test_real_data_mini_cycle_probe.py
```

Result: pass, `2 passed`.

### real-data probe batch

Command:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
.venv/bin/python scripts/real_data_mini_cycle_probe.py \
  --dates 20260415 \
  --symbols 600519.SH,000001.SZ,000063.SZ \
  --artifact-dir /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/real-data-mini-cycle-artifacts \
  --json-report /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/real-data-mini-cycle-probe-20260427.json \
  --print-json
```

Result: exit `2`, expected blocked real-cycle status. Key evidence:

- `external_tushare_corpus_smoke`: OK, 6/6 checks passed against `/Volumes/dockcase2tb/database_all`.
- `tushare_token_raw_ingestion_probe`: failed with `DP_TUSHARE_TOKEN is required for the Tushare adapter`; treated as hard block, no mock fallback.
- `daily_refresh_real_probe`: failed in `config` with `DP_PG_DSN is required for the PostgreSQL-backed Iceberg catalog`.
- `audit_eval_fixture_replay_probe`: OK, but `fixture_only`; no real cycle manifest gateway was found for data-platform formal snapshots.

Artifacts:

- `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/real-data-mini-cycle-probe-20260427.json`
- `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/real-data-mini-cycle-artifacts/daily-refresh-real-probe-20260415.json`

### orchestrator min-cycle probe

Command:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/orchestrator
.venv/bin/python -m orchestrator.cli.main min-cycle \
  --profile lite-local \
  --fixture /Users/fanjie/Desktop/Cowork/project-ult/assembly/src/assembly/tests/e2e/fixtures/minimal_cycle/manifest.yaml \
  --run-artifacts-dir /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/real-data-mini-cycle-artifacts/orchestrator-min-cycle \
  --report /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/real-data-mini-cycle-artifacts/orchestrator-min-cycle-report.json
```

Result: exit `0`. The report status is `success`, and the runtime artifact records:

- `produced_by`: `orchestrator.cli.min_cycle`
- `real_phase_execution`: `true`
- `assembled_job_names`: `["daily_cycle_job"]`
- `assembly_error`: `null`

Interpretation: this proves Dagster Phase 0-3 job assembly/import works. It does not prove real asset materialization, PG/Iceberg writes, or formal publish execution; `min_cycle.py` explicitly does not call materialize.

Artifacts:

- `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/real-data-mini-cycle-artifacts/orchestrator-min-cycle-report.json`
- `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/real-data-mini-cycle-artifacts/orchestrator-min-cycle/cycle_summary.json`

### orchestrator focused tests

Command:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/orchestrator
.venv/bin/python -m pytest -q tests/cli/test_min_cycle.py tests/integration/test_daily_cycle_four_phase.py
```

Result: pass, `27 passed, 2 skipped`.

### audit-eval focused tests

Command:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/audit-eval
.venv/bin/python -m pytest -q tests/test_spike_replay.py
```

Result: pass, `5 passed`.

### whitespace checks

Commands:

```bash
git diff --check
```

Run in data-platform, orchestrator, audit-eval, and assembly.

Result: all passed.

## Chain status

- Tushare/raw ingestion: blocked for token-backed real adapter because `DP_TUSHARE_TOKEN` is missing. External corpus is present and passes smoke, but existing `daily_refresh` has no corpus-backed raw ingestion bridge; corpus presence was not represented as a completed raw ingest.
- dbt/staging/intermediate/marts: blocked by missing `DP_PG_DSN` and missing DP runtime paths before the real daily refresh can enter dbt/canonical. The selected real probe did not reach dbt.
- candidate freeze / `cycle_metadata` / `cycle_candidate_selection`: blocked by missing PG environment. Existing code has tested APIs, but no real cycle row was created in this batch.
- Phase 0-3 orchestration path: assembly probe succeeds and assembles `daily_cycle_job`; real asset execution/materialization is not proven.
- formal object commit + `publish_manifest`: blocked by missing PG/Iceberg real cycle and formal table snapshots.
- formal serving by manifest snapshot: blocked by missing published manifest and formal snapshots in the real environment.
- audit/replay: fixture replay entrypoint works; no real cycle gateway wired to data-platform manifest-pinned formal snapshots was verified.

## Remaining gaps

- Provide a non-secret operator environment with `DP_PG_DSN`, `DP_TUSHARE_TOKEN`, `DP_RAW_ZONE_PATH`, `DP_ICEBERG_WAREHOUSE_PATH`, `DP_DUCKDB_PATH`, and `DP_ICEBERG_CATALOG_NAME`.
- Add or choose a real corpus-backed ingestion bridge if the intended real source is the external corpus rather than live Tushare token calls.
- Add a small-scope real close-loop entry that can keep symbols/dates bounded while still proving staging, intermediate, marts, cycle freeze, formal commit, publish manifest, formal serving, and audit/replay.
- Wire audit-eval replay to data-platform published cycle manifests/formal snapshots for real cycle replay; current replay proof is fixture-only.

## P2 recommendation

Do not enter P2 real L1-L8 dry run from this evidence batch. The corpus availability is encouraging, but the real token/PG/Iceberg runtime is blocked, and the orchestrator result is assembly-only rather than real asset execution.
