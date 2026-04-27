# Runtime Environment Preflight - 2026-04-28

## Status

PASS for the scoped runtime preflight. This is redacted evidence only; it is
not a production daily-cycle pass certificate and not P5 readiness.

## Command

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/assembly
.venv-py312/bin/python scripts/production_daily_cycle_proof.py \
  --preflight-only \
  --run-current-selection-tests
```

Result:

```text
RUNTIME_PREFLIGHT_PASS /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/p1-p2-production-daily-cycle-proof-artifacts/20260427T193251Z/production-daily-cycle-proof.json
```

## Redacted Environment

The artifact records presence only, with no token, password, DSN, OAuth, or API
key values.

| Runtime input | Status |
| --- | --- |
| `DP_TUSHARE_TOKEN` | set |
| `DP_PG_DSN` | set |
| `DATABASE_URL` | set |
| `NEO4J_URI` | set |
| `NEO4J_USER` | set |
| `NEO4J_PASSWORD` | set |
| `P2_REASONER_PROVIDER` | set |
| `P2_REASONER_MODEL` | set |
| `REASONER_RUNTIME_ENABLE_CODEX_OAUTH` | set |
| `AUDIT_EVAL_DUCKDB_PATH` | set |
| `ORCHESTRATOR_POLICY_PATH` | set |
| `ORCHESTRATOR_MODULE_FACTORIES` | set |
| `OPENAI_API_KEY` | missing |

`OPENAI_API_KEY` is not required for this Codex preflight path because the
configured provider is `openai-codex` with Codex OAuth enabled.

## Passed Checks

| Check | Result |
| --- | --- |
| Assembly/runtime imports | PASS: data-platform current selection, daily refresh, orchestrator production provider, audit-eval audit storage, and reasoner-runtime imported. |
| PostgreSQL connect | PASS: `SELECT 1` succeeded through the configured DSN; DSN value redacted. |
| data-platform current selection tests | PASS: `tests/cycle/test_current_selection.py -q -rs` returned code 0 with `.......... [100%]`. |
| Codex reasoner health | PASS: provider `openai-codex`, model `gpt-5.5`, reachable true, quota `ok`. |
| audit DuckDB write/read | PASS: managed DuckDB audit/replay bundle write and repository readback succeeded. |

## Artifact

- `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/p1-p2-production-daily-cycle-proof-artifacts/20260427T193251Z/production-daily-cycle-proof.json`
- `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/p1-p2-production-daily-cycle-proof-artifacts/20260427T193251Z/data-platform-current-selection-tests.stdout.txt`
- `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/p1-p2-production-daily-cycle-proof-artifacts/20260427T193251Z/data-platform-current-selection-tests.stderr.txt`

## Non-Claims

- This does not run live Tushare refresh, candidate freeze, or full Dagster
  `daily_cycle_job`.
- This does not start P5.
- This does not add sidecar, frontend write APIs, API-6, news, or Polymarket
  production flow.
- Provider wiring and full Dagster proof remain tracked in the production
  daily-cycle proof report.
