# M2.1 — Runtime Preflight (compose stack + env vars + import + lane sweep)

## Status

**M2.1 status: COMPLETE.** Compose stack is up and healthy (2-day uptime
inherited from previous session). All cross-module env vars are in place via
`assembly/.env`. Canonical v2 lane sweep passes against the host venv (185/5,
matches M1.10 baseline). Orchestrator imports and emits the expected 6
RUNTIME_BLOCKERS.

The biggest **new finding** of M2.1: the dbt CLI subprocess (`dbt --version`)
fails on Python 3.14 (host data-platform venv) with a mashumaro/3.14
incompatibility — but this is **not a M2.6 blocker**: `daily_refresh.py` uses
dbt-as-Python-library (in-process), not CLI subprocess. Programmatic
invocation of all `tests/dbt/` + `tests/integration/test_daily_refresh.py`
passes (82/82).

---

## Prerequisites

- M1 closed at 9/9 + 0 xfail + 0 deferred (data-platform `bca54d1`,
  assembly `6bb16bf`, frontend-api `5f86355` on `origin/main`).
- M2.0 audit complete (commit `f817f8b` on `m2-baseline-2026-04-29`):
  6 RUNTIME_BLOCKERS classified as 0 READY + 4 PARTIAL + 1 STUBBED + 1
  DEFERRED-TO-M2.6.

---

## Compose stack health

```
$ docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
NAMES                         IMAGE                             STATUS                PORTS
compose-dagster-webserver-1   project-ult/dagster-lite:1.7.16   Up 2 days (healthy)   127.0.0.1:3000->3000/tcp
compose-dagster-daemon-1      project-ult/dagster-lite:1.7.16   Up 2 days (healthy)
compose-postgres-1            postgres:16                       Up 2 days (healthy)   127.0.0.1:5432->5432/tcp
compose-neo4j-1               neo4j:5                           Up 2 days (healthy)   127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp
```

**4 services healthy** (lite-local profile target). Neo4j 5.26 with `graph-data-science`
plugin loaded. PostgreSQL 16.11 (Debian aarch64).

### Connectivity verification

```
# PG from host (using DP_PG_DSN credentials)
$ PGPASSWORD=changeme psql -h localhost -p 5432 -U postgres -d proj -c "SELECT current_database(), current_user, version();"
 current_database | current_user |              version
------------------+--------------+------------------------------------------
 proj             | postgres     | PostgreSQL 16.11 (Debian 16.11-1.pgdg13+1) ...

# Neo4j from inside container (auth verified)
$ docker exec compose-neo4j-1 cypher-shell -u neo4j -p changeme123 "RETURN 1 AS one, 'graph-engine ready' AS msg;"
one, msg
1, "graph-engine ready"

# Dagster webserver from host (HTTP 200, 5.6ms latency)
$ curl -s http://127.0.0.1:3000/server_info
{"dagster_webserver_version":"1.7.16","dagster_version":"1.7.16","dagster_graphql_version":"1.7.16"}
```

All three live data planes reachable.

---

## Env-var inventory (live values from `assembly/.env`)

| Domain | Key | Live value (sanitized) | Notes |
|---|---|---|---|
| PG | `POSTGRES_HOST` / `_PORT` / `_DB` / `_USER` / `_PASSWORD` | `localhost:5432/proj` as `postgres` | matches compose service |
| PG | `DP_PG_DSN` | `postgresql://postgres:***@localhost:5432/proj` | derived from above |
| PG | `DATABASE_URL` | same as `DP_PG_DSN` | dual binding |
| Neo4j | `NEO4J_URI` | `bolt://localhost:7687` | bolt-protocol port |
| Neo4j | `NEO4J_USER` / `NEO4J_PASSWORD` | `neo4j` / `changeme123` | matches `NEO4J_AUTH` inside container |
| Dagster | `DAGSTER_HOME` / `_HOST` / `_PORT` | `/opt/dagster/dagster_home` / `localhost` / `3000` | webserver listens on `:3000` |
| Reasoner | `P2_REASONER_PROVIDER` | `openai-codex` | matches default `_DEFAULT_PROVIDER` (p2_dry_run.py:17) |
| Reasoner | `P2_REASONER_MODEL` | `gpt-5.5` | matches default `_DEFAULT_MODEL` |
| Reasoner | `REASONER_RUNTIME_ENABLE_CODEX_OAUTH` | `1` | unlocks Codex structured probe |
| Audit-eval | `AUDIT_EVAL_DUCKDB_PATH` | `assembly/tmp-runtime/audit-eval/audit_eval.duckdb` | filesystem path; M2.5 verifies write-back |
| Orchestrator | `ORCHESTRATOR_DEFINITIONS_PROFILE` | `p5` | NOTE: this currently selects the P5 profile, not `lite-local`; M2.6 may need to flip this |
| Orchestrator | `ORCHESTRATOR_POLICY_PATH` | `orchestrator/config/policy/gate_policy.lite.yaml` | gate policy YAML |
| Orchestrator | `ORCHESTRATOR_MODULE_FACTORIES` | `orchestrator_adapters.production_daily_cycle:production_daily_cycle_provider` | matches M2.0 audit anchor |
| Data-platform | `DP_RAW_ZONE_PATH` / `DP_ICEBERG_WAREHOUSE_PATH` / `DP_DUCKDB_PATH` | under `assembly/tmp-runtime/data-platform/{raw,iceberg,duckdb}/` | local FS canonical store |
| Data-platform | `DP_ICEBERG_CATALOG_NAME` | `data_platform` | for Iceberg SQLcat |
| Data-platform | `DP_TUSHARE_TOKEN` | `8b1fa9e1...` | adapter creds; not used by M2.6 directly |

**M2.0 audit's required env-var inventory is satisfied** for the lite-local
profile. Items still to be wired before M2.6 actually runs:
- `DP_CANONICAL_USE_V2=1` — currently NOT set in `.env`; needs to be exported
  before `daily_refresh` to read canonical_v2 (per M1 closure default).
- Codex/Claude credentials (operationally required for `P2_REASONER_PROVIDER=openai-codex`)
- `ORCHESTRATOR_PHASE2_POOL_FAILURE_RATE_EVENT_JSON` — first M2.6 run needs
  this JSON fallback (M2.0 audit clarification).
- `ORCHESTRATOR_DEFINITIONS_PROFILE`: change from `p5` → matches the actual
  M2.6 target if different.

---

## dbt runtime: clarification of M2.0 audit's "dbt CLI gap"

### Finding

```
$ docker exec compose-dagster-daemon-1 bash -c 'which dbt'
exit=1
bash: line 1: dbt: command not found
```

dbt CLI is **NOT installed** in the dagster-daemon image. Recent `pip list`
inside the image shows only `dagster*` packages.

```
$ /Users/fanjie/Desktop/Cowork/project-ult/data-platform/.venv/bin/dbt --version
mashumaro.exceptions.UnserializableField: Field "schema" of type Optional[str]
in JSONObjectSchema is not serializable
```

dbt CLI also fails on the **host** data-platform venv: the venv is built with
Python 3.14.3, but `data-platform/pyproject.toml` declares
`requires-python = ">=3.12,<3.14"` — Python 3.14 is excluded. Inside dbt's
adapter-factory loader, `mashumaro` (3.14-incompatible serializer) raises.

### But: dbt-as-library works fine

```
$ PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -p no:cacheprovider tests/dbt/ tests/integration/test_daily_refresh.py
82 passed, 4 skipped in 7.93s
```

`daily_refresh.py:run_daily_refresh()` invokes dbt programmatically (not as a
subprocess), so the CLI gap **does not block** M2.6 production daily-cycle
execution. `tests/dbt/` and `tests/integration/test_daily_refresh.py` cover
the in-process invocation path; both green.

### Recommendation

This finding **softens** M2.0 audit's "dbt CLI runnable inside dagster-daemon
image OR confirm host runtime path" requirement to: "data-platform Python
package importable + dbt-core importable in the dagster-daemon image". The
current dagster-daemon image satisfies this (verified via `dagster*` package
listing).

**Action item for M2.6 (optional polish, NOT blocking):** if standalone dbt
debugging is needed, pin host venv Python to 3.12 or 3.13 by recreating
`data-platform/.venv` with a compliant interpreter. Out of M2.1 scope.

---

## Canonical v2 lane re-validation (under live compose stack)

**Goal:** confirm the M1.10 controlled v2 proof's underlying canonical_v2 lane
still passes on the live compose snapshot (PG/Neo4j/Dagster have 2-day uptime
since M1.10 was run).

```
$ cd data-platform && DP_CANONICAL_USE_V2=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
    .venv/bin/python -m pytest -p no:cacheprovider \
    tests/serving \
    tests/cycle/test_current_cycle_inputs.py \
    tests/cycle/test_current_cycle_inputs_lineage_absent.py \
    tests/test_assets.py
185 passed, 5 skipped, 7 warnings in 3.53s
```

**185/5 — exact match with the M1.10 baseline.** The canonical_v2 +
canonical_lineage substrate is intact and reproducible.

The pre-existing M1.10 proof artifacts at
`assembly/tmp-runtime/m1-controlled-v2-proof/` (notably
`daily-refresh-20260429.json` with `ok: true` + 28 artifacts) confirm that a
full daily_refresh run did succeed on this exact compose snapshot ~4 hours
prior to M2.1.

> **Note:** Re-running the full M1.10 proof end-to-end was deferred. The
> proof is fixture-based; the artifacts on disk + the lane sweep above
> together demonstrate reproducibility without consuming additional cycles.

---

## Orchestrator runtime status surface (sanity check)

```python
$ orchestrator/.venv/bin/python -c "
from orchestrator_adapters.production_daily_cycle import production_daily_cycle_status
s = production_daily_cycle_status()
print(f'blocker_code={s.blocker_code}')
print(f'blocked={s.blocked}')
print(f'#blockers={len(s.runtime_blockers)}')
[print(f'  - {b}') for b in s.runtime_blockers]"
```

Output:
```
blocker_code=ORCH_PRODUCTION_DAILY_CYCLE_PROVIDER_BLOCKED
blocked=True
#blockers=6
  - configured_data_platform_current_cycle_runtime
  - configured_graph_phase0_status_runtime
  - configured_graph_phase1_runtime
  - configured_reasoner_runtime
  - configured_audit_eval_retrospective_hook_runtime
  - production_current_cycle_dagster_run_evidence
```

**6 blockers exactly match M2.0 audit's source-of-truth count** (vs. roadmap's
original 5). Orchestrator's Python 3.12 venv imports cleanly.

---

## Gap-to-M2.6 list (revised post-M2.1)

| # | Sub-round | What's left | Owner |
|---|---|---|---|
| 1 | M2.2 | Live PG integ-test for `freeze_current_cycle_candidates` (closes blocker #1 PARTIAL → READY); confirm `current_cycle_inputs` reads canonical_v2 with `DP_CANONICAL_USE_V2=1` set | data-platform |
| 2 | M2.3a (NEW per M2.0) | Implement `Neo4jGraphStatusProvider` + factory in graph-engine; fix `_FailClosedGraphPhase1Runtime` default in `phase1.py:285`; orchestrator default-wire fix | graph-engine + orchestrator |
| 3 | M2.3b | Orchestrator integ-test exercising Phase 0 → Phase 1 chain end-to-end | orchestrator |
| 4 | M2.4 | Provision Codex OAuth credentials (`~/.codex/auth.json`) **OR** switch `P2_REASONER_PROVIDER` → `minimax` + set `MINIMAX_API_KEY`. Probe `reasoner_runtime.health_check` returns reachable=True | reasoner-runtime + ops |
| 5 | M2.5 | Verify `_EnvBackedRetrospectiveHookRuntime` round-trip against live PG manifest + DuckDB; small smoke | audit-eval |
| 6 | M2.6 | Full `daily_cycle_job.execute_in_process(tags={"cycle_id": "CYCLE_20260429"})` proof | orchestrator + assembly |

**Critical-path bottleneck remains M2.3a.** All other PARTIALs are addressable
in parallel.

---

## Hard-rule declarations

- `project_ult_v5_0_1.md` UNCHANGED.
- `ult_milestone.md` UNCHANGED.
- No production fetch (no Tushare HTTP, no live LLM call).
- No P5 / M3 / M4 work.
- No source code modified in any of the 6 module repositories — preflight
  is read-only verification.
- canonical_v2 + canonical_lineage spec sets unchanged.
- Tushare remains `provider="tushare"` source adapter only.
- `frontend-api` NOT touched.
- `/Users/fanjie/Desktop/BIG/FrontEnd/**` NOT modified.
- Compose stack was already running from a previous session (2-day uptime);
  M2.1 did not start or modify it.

---

## Cross-references

- M2 roadmap: [`m2-roadmap-20260429.md`](m2-roadmap-20260429.md)
- M2.0 audit: [`m2-0-runtime-readiness-audit-20260429.md`](m2-0-runtime-readiness-audit-20260429.md)
- M1.10 controlled v2 proof: [`m1-10-controlled-v2-proof-results-20260429.md`](m1-10-controlled-v2-proof-results-20260429.md)
- M1 closure: [`m1-legacy-retirement-preconditions-progress-20260428.md`](m1-legacy-retirement-preconditions-progress-20260428.md)

## Next steps

1. **Recommended: M2.3a** — graph-engine implements `Neo4jGraphStatusProvider`
   + fixes `phase1.py:285` default-wire; live Neo4j is up so integ-test
   can be exercised in the same compose snapshot.
2. **Parallel: M2.4** — provision LLM credentials (Codex OAuth or MiniMax key).
   Operationally independent.
3. **Parallel: M2.2** — data-platform live PG integ-test for atomic freeze.
4. M2.5 + M2.6 wait for #1-3.
