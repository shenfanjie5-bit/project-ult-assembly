# M2.6 Full Production Daily-Cycle Proof Attempt - 2026-05-01

## Verdict

**BLOCKED. M2.6 is not passed.**

The current run reached the production Dagster proof path, but failed in Phase 0 `graph_status` before the full `daily_cycle_job` could complete. The active blocker is a PostgreSQL DSN compatibility issue between the assembly proof runner and graph-engine status store:

- assembly proof runtime sets `DATABASE_URL` to a SQLAlchemy-style URL: `postgresql+psycopg://...`
- graph-engine `PostgreSQLStatusStore` passes `DATABASE_URL` directly to `psycopg.connect(...)`
- psycopg rejects that URL form with `ProgrammingError: missing "=" after ... in connection info string`

This is a focused M2.6 blocker. It is not a reasoner quota blocker, not an M2.6f1 graph-writer blocker, and not a P5 readiness result.

## v5.0.1 Alignment

`project_ult_v5_0_1.md` remains unchanged and authoritative.

This attempt stayed inside the Lite P1-P5 stack:

- no Kafka, Flink, Temporal, Milvus, Grafana, Superset, or Feast introduced;
- Layer A/Iceberg remains canonical truth;
- Neo4j remains a hot mirror and status target, not truth;
- Phase 0 was validation/status only and did not write graph deltas;
- Phase 1 graph write-back is still the next stage after Phase 0 status passes;
- P5/shadow-run did not start.

Relevant v5.0.1 constraints checked during this run:

- `project_ult_v5_0_1.md:166-178`: Phase 0 validates graph status; Phase 1 writes graph deltas and snapshots.
- `project_ult_v5_0_1.md:1243-1264`: P5 depends on P1 + P2 + P3 + P4 and must not start here.
- `project_ult_v5_0_1.md:1319-1344`: P1 precedes P2/P3/P4; P5 comes only after P1-P4 readiness; P6/P11 Full components are later.

## Branch And Head Snapshot

| Repo | Branch | Head | Status at preflight start |
|---|---|---:|---|
| `data-platform` | `m2-6f1-iceberg-canonical-graph-writer-v2` | `8374504` | clean |
| `main-core` | `m2-3a-2-regime-reader` | `3def30a` | clean |
| `graph-engine` | `m2-6f1-real-canonical-writer` | `9d616af` | clean |
| `orchestrator` | `m2-3a-2-phase1-wiring` | `0ccae67` | clean |
| `audit-eval` | `m2-5-live-pg-roundtrip` | `a7d05b7` | clean |
| `reasoner-runtime` | `main` | `025db5b` | clean |
| `assembly` | `m2-baseline-2026-04-29` | `1581967` | clean before new proof artifacts |

## Targeted Regression Checks

These operator checks were run before the full proof attempt. They are recorded here as pre-run sanity context, not as gate-pass evidence; only the assembly runner's current-selection stdout/stderr was persisted by the proof script in the artifact directories below.

| Repo | Command scope | Result |
|---|---|---|
| `data-platform` | `tests/cycle/test_graph_phase1_adapters.py`, `tests/integration/test_iceberg_canonical_graph_writer_live.py`, `tests/ddl/test_iceberg_tables.py`, `tests/cycle/test_current_selection.py` with `PYTHONPATH=src:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src` | passed; 2 current-cycle PG wrapper tests skipped because no `DATABASE_URL`/`DP_PG_DSN` was set in this repo-local run |
| `main-core` | graph regime reader, readonly consumption, and snapshot round-trip preflight integration tests | `14 passed` |
| `graph-engine` | Phase 0 status provider, Phase 1 provider/from-env, and live closure suites | passed; 2 environment-gated tests skipped (`dagster` import unavailable, `NEO4J_PASSWORD` unset) |
| `reasoner-runtime` | health, provider routing, scrub/replay, direct-import/contract guard suites | passed |
| `orchestrator` | production daily-cycle provider and Phase 1 graph provider wiring integration suites | passed; 6 dbt-CLI-gated tests skipped in orchestrator-local environment |

The assembly runner also executed the current-selection focused suite during each proof run and persisted stdout/stderr under the artifact directories below.

## Commands And Artifacts

All commands were run from:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/assembly
```

### Runtime Preflight

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python \
  scripts/production_daily_cycle_proof.py \
  --preflight-only \
  --run-current-selection-tests
```

Result:

- verdict: `RUNTIME_PREFLIGHT_PASS`
- artifact: `reports/stabilization/p1-p2-production-daily-cycle-proof-artifacts/20260430T175320Z/production-daily-cycle-proof.json`
- imports: passed
- PostgreSQL connection: passed
- audit DuckDB write/read: passed
- data-platform current selection tests: passed
- Codex reasoner health: passed, provider `openai-codex`, model `gpt-5.5`, quota status `ok`

### Full Proof Attempt 1

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python \
  scripts/production_daily_cycle_proof.py \
  --run-dagster \
  --run-current-selection-tests
```

Result:

- verdict: `BLOCKED`
- artifact: `reports/stabilization/p1-p2-production-daily-cycle-proof-artifacts/20260430T175346Z/production-daily-cycle-proof.json`
- blocker: Dagster `DbtCliResource` resolved `dbt` from `PATH`, but `dbt` was not on the shell `PATH`
- evidence detail: `Value error, The dbt executable 'dbt' does not exist`

This was a command-environment blocker, not a product blocker. The next attempt added the assembly venv bin directory to `PATH`.

### Full Proof Attempt 2

```bash
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python \
  scripts/production_daily_cycle_proof.py \
  --run-dagster \
  --run-current-selection-tests
```

Result:

- verdict: `BLOCKED`
- artifact: `reports/stabilization/p1-p2-production-daily-cycle-proof-artifacts/20260430T175454Z/production-daily-cycle-proof.json`
- Codex reasoner health: passed, provider `openai-codex`, model `gpt-5.5`, quota status `ok`
- isolated PostgreSQL bootstrap: passed
- data-platform migrations: passed, versions `0001` through `0005`
- Tushare refresh: passed with real data (`mock=false`)
- daily-refresh dbt run/test/canonical/raw_health: passed
- candidate seed: passed, 2 accepted and 0 rejected
- current cycle selection: passed, `CYCLE_20260415`, symbols `600519.SH` and `000001.SZ`
- terminal output showed Dagster entered the job and advanced through:
  - `candidate_freeze`
  - `dbt_phase0_assets`
  - `phase0_readiness_ping`
- Dagster failed at:
  - `graph_status`

The failure message persisted in the artifact:

```text
psycopg.ProgrammingError: missing "=" after "<redacted>" in connection info string
```

The corresponding blocker list:

```text
production provider status is missing
missing "=" after "<redacted>" in connection info string
```

The structured proof JSON for this failed path does not persist Dagster materialization event records. Therefore the intermediate Dagster steps above are treated as console-observed progress only, not as Phase 0 PASS evidence.

## Phase Status

| Area | Status | Evidence |
|---|---|---|
| Runtime preflight | PASS | `20260430T175320Z/production-daily-cycle-proof.json` |
| Reasoner health/quota | PASS | `quota_status: ok` in all three proof JSON files |
| Data-platform refresh and current selection | PASS | `20260430T175454Z/daily-refresh.json` plus current-selection stdout |
| Dagster job bootstrap | CONSOLE-OBSERVED ONLY | second full attempt entered Dagster execution, but no structured Dagster event artifact was persisted |
| Phase 0 candidate freeze | CONSOLE-OBSERVED ONLY | terminal output showed progress before blocker; not credited as proof-backed PASS |
| Phase 0 dbt assets | CONSOLE-OBSERVED ONLY | terminal output showed progress before blocker; `orchestrator-dbt-compile.stdout.txt` is a compile artifact, not a persisted Dagster materialization event log |
| Phase 0 readiness ping | CONSOLE-OBSERVED ONLY | terminal output showed progress before blocker; not credited as proof-backed PASS |
| Phase 0 graph status | BLOCKED | graph-engine status readback fails while processing the SQLAlchemy-style `DATABASE_URL` through psycopg |
| Phase 1 graph write-back | NOT REACHED | blocked in Phase 0 |
| Phase 2 reasoner | NOT REACHED | blocked in Phase 0 |
| Phase 3 formal outputs/publish manifest | NOT REACHED | blocked in Phase 0 |
| Audit/replay/retrospective hook | NOT REACHED | blocked in Phase 0 |

## Blocker Classification

Primary blocker class: **graph status provider / PostgreSQL DSN compatibility**.

Why this is the active blocker:

- The first full attempt exposed a reproducible command-environment issue (`dbt` missing from `PATH`).
- Adding `assembly/.venv-py312/bin` to `PATH` allowed Dagster and dbt Phase 0 assets to run.
- The second full attempt then failed inside graph-engine Phase 0 status readback.
- The failure occurs before Phase 1, Phase 2, Phase 3, and audit completion.
- The reasoner health probe passed and quota was `ok`, so provider quota is not the current blocker.

Recommended next repair round:

1. Pick one DSN compatibility fix:
   - preferred: normalize SQLAlchemy-style `postgresql+psycopg://...` URLs before graph-engine passes them to `psycopg.connect(...)`;
   - alternative: have the assembly proof runner pass a psycopg-native `DATABASE_URL` while preserving the SQLAlchemy-style DSN for `DP_PG_DSN`.
2. Add a unit test proving graph-engine status store accepts the same DSN shape used by the assembly proof runner.
3. Add graph-status initialization evidence for the isolated proof database:
   - either seed/create a ready `neo4j_graph_status` row in the proof setup path; or
   - run against a PostgreSQL database that already hosts a ready `neo4j_graph_status` row; or
   - prove the intended cold-reload path initializes the row before `graph_status` is consumed.
4. Rerun the full proof command with `assembly/.venv-py312/bin` on `PATH`.
5. Persist a Dagster event/materialization log or equivalent structured artifact for the next full proof attempt.
6. Do not claim M2.6 pass until `daily_cycle_job.execute_in_process(...)` succeeds and all Phase 0-3 + audit criteria are captured.

## Explicit Non-Claims

- This does not pass M2.6.
- This does not start or pass P5.
- This does not prove M3.3 production same-cycle graph snapshot consumption.
- This does not prove P4/M4 bridge readiness.
- This does not change `project_ult_v5_0_1.md`.
- This does not change production source code.
