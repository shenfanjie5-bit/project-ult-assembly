# P2 Durable Real-Data Codex Dry-Run Closure - 2026-04-27

## Scope

This evidence closes the P2 durable real-data Codex dry-run gate for the current
Lite MVP path. It proves that a current-cycle Tushare input can drive L1-L8,
call the real `openai-codex` reasoner-runtime provider, durably persist
audit/replay records, publish real formal snapshots, and read L8 back through
manifest-bound serving.

News and alternative information sources are intentionally out of scope for
this gate. Phase 0/1 graph readiness is isolated by the closure runner so this
evidence focuses on the P2 L1-L8 data/reasoner/formal/audit path.

## Final Artifact

- JSON report:
  `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/p2-durable-real-data-codex-dry-run-artifacts/20260427T113854Z/p2-durable-real-data-codex-dry-run.json`
- Daily refresh report:
  `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/p2-durable-real-data-codex-dry-run-artifacts/20260427T113854Z/daily-refresh.json`
- Status: `passed`

## Current-Cycle Input

- `cycle_id`: `CYCLE_20260415`
- Trade date: `2026-04-15`
- Symbols: `600519.SH`, `000001.SZ`
- Candidate freeze: 2 candidates, IDs `1`, `2`, validation accepted `2`, rejected `0`
- Source: `data-platform:tushare-staging:frozen-candidates`
- Input tables: `main.stg_daily`, `main.stg_stock_basic`
- P2 input row count: `2`
- Raw source run IDs:
  - `daily`: `6ad9262c-93d6-4c8b-a4fa-c7d3df8c4aae`
  - `stock_basic`: `c2c7404a-a2fd-4eb8-a7e5-1b85bcca433c`
- Raw loaded timestamps:
  - `2026-04-27 11:38:57.407511`
  - `2026-04-27 11:38:59.194504`
- Tushare raw refresh:
  - `stock_basic`: `5510` rows
  - `daily`: `5494` rows

The final artifact records these fields under `dry_run.input_evidence`; it no
longer falls back to `legacy-test-input`, and L8 receives this evidence through
the `l3` asset input rather than a process-local side channel.

## Codex Reasoner Runtime

- Provider: `openai-codex`
- Model: `gpt-5.5`
- Provider health check: passed inside Dagster `llm_health_check`
- LLM call count: `3`
- LLM layers: `L4`, `L6`, `L6`
- No historical recommendation fallback was used; L8 is produced from the
  current Dagster run's L4/L6/L7 outputs.

## Formal Publish And Serving

- Manifest ref: `data-platform://cycle_publish_manifest/CYCLE_20260415`
- Formal snapshot IDs:
  - `world_state_snapshot`: `248279888129827474`
  - `official_alpha_pool`: `5543285357420142155`
  - `alpha_result_snapshot`: `3512795879910086449`
  - `recommendation_snapshot`: `7061880570766269445`
- Manifest-bound serving readback:
  - `get_formal_by_id(CYCLE_20260415, recommendation_snapshot)` returned snapshot `7061880570766269445`, row count `1`
  - `get_formal_by_snapshot(7061880570766269445, recommendation_snapshot)` returned cycle `CYCLE_20260415`, row count `1`

## Audit And Replay

- Persisted `AuditRecord` IDs: `5`
- Persisted `ReplayRecord` IDs: `5`
- Durable query by ID: all 5 audit IDs and all 5 replay IDs were queried back
- Replay readback:
  - Object ref: `recommendation_snapshot`
  - Manifest snapshot keys: `alpha_result_snapshot`, `official_alpha_pool`, `recommendation_snapshot`, `world_state_snapshot`
  - Historical formal object keys: `alpha_result_snapshot`, `official_alpha_pool`, `recommendation_snapshot`, `world_state_snapshot`

## Negative Gates

- No LLM availability: hard-stop before L8/publish.
- Audit persistence failure: no manifest publish.
- Missing L4/L6/L7/L8 provenance: rejected.
- `smoke`, `fixture`, or `historical` audit/replay IDs: rejected.
- Persisted audit/replay IDs must exactly match the provenance IDs used for
  `cycle_publish_manifest()`.

## Commands

Real closure:

```bash
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/orchestrator/src:/Users/fanjie/Desktop/Cowork/project-ult/main-core/src:/Users/fanjie/Desktop/Cowork/project-ult/reasoner-runtime:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src:/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src:/Users/fanjie/Desktop/Cowork/project-ult/audit-eval/src \
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/scripts/p2_durable_real_data_codex_dry_run.py \
--date 20260415 --symbols 600519.SH,000001.SZ
```

Result: passed.

Regression tests:

```bash
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/orchestrator/src:/Users/fanjie/Desktop/Cowork/project-ult/main-core/src:/Users/fanjie/Desktop/Cowork/project-ult/reasoner-runtime:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src:/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src:/Users/fanjie/Desktop/Cowork/project-ult/audit-eval/src \
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python \
-m pytest /Users/fanjie/Desktop/Cowork/project-ult/orchestrator/tests/integration/test_p2_dry_run_handoff.py -q -rs
```

Result: `6 passed`.

```bash
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/audit-eval/src \
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python \
-m pytest /Users/fanjie/Desktop/Cowork/project-ult/audit-eval/tests/test_audit_writer.py /Users/fanjie/Desktop/Cowork/project-ult/audit-eval/tests/test_replay_storage_integration.py -q
```

Result: `29 passed`.

```bash
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/reasoner-runtime:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python \
-m pytest /Users/fanjie/Desktop/Cowork/project-ult/reasoner-runtime/tests/unit/test_codex_client.py /Users/fanjie/Desktop/Cowork/project-ult/reasoner-runtime/tests/unit/test_health.py -q
```

Result: `41 passed`.

```bash
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src \
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python \
-m pytest /Users/fanjie/Desktop/Cowork/project-ult/data-platform/tests/cycle/test_publish_manifest.py /Users/fanjie/Desktop/Cowork/project-ult/data-platform/tests/serving/test_formal.py /Users/fanjie/Desktop/Cowork/project-ult/data-platform/tests/serving/test_formal_manifest_consistency.py -q -rs
```

Result: `35 passed, 20 skipped`; skipped cases require direct
`DATABASE_URL`/`DP_PG_DSN` in the test environment. The real closure command
used a temporary PostgreSQL database derived from local `POSTGRES_*` settings.

## Residual Notes

- The closure runner uses isolated Phase 0/1 providers so this is not a graph
  performance or full Phase 0/1 production readiness proof.
- The formal path uses real data-platform writers, manifest publication, and
  manifest-bound serving.
- Secrets are not written to the JSON artifact; DSN and token status are
  redacted to set/missing indicators.
