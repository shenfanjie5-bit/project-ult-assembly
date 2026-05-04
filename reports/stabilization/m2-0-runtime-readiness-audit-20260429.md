# M2.0 — Production Daily-Cycle Runtime Readiness Audit (2026-04-29)

## Status

**M2.0 audit status: COMPLETE.** Read-only audit of the 6 RUNTIME_BLOCKERS declared in
`orchestrator/src/orchestrator_adapters/production_daily_cycle.py:46-53`,
covering 4 cross-module repositories (data-platform / graph-engine /
reasoner-runtime / audit-eval).

This is the **ground-truth readiness snapshot** that gates which M2 sub-rounds
need real implementation work vs. just wiring/configuration. It does **not**
modify any module source — only this evidence file and a small fact-correction
to the M2 roadmap.

> Note: `production_daily_cycle_status().blocked` remains `True`
> (`production_daily_cycle.py:399`) until M2.6 passes end-to-end. The "AUDIT
> COMPLETE" status here means the readiness snapshot is recorded, not that
> the production daily-cycle is unblocked.

> **2026-04-29 review pass:** This document was independently cross-checked by
> 3 reviewer agents; their findings were folded into this version. Notable
> verdict shifts: blocker #3 and #5 downgraded from READY → PARTIAL after
> reviewers found hidden fail-closed defaults / fallback paths the first-pass
> audit missed.

---

## Prerequisites

- M1 closed at 9/9 + 0 xfail + 0 deferred (data-platform main `bca54d1`,
  assembly main `6bb16bf`, frontend-api main `5f86355` pushed to origin).
- `assembly/reports/stabilization/m2-roadmap-20260429.md` written with 6
  sub-rounds (M2.0–M2.6).

---

## Roadmap fact correction

`m2-roadmap-20260429.md` line 42 declared **"5 RUNTIME_BLOCKERS"**.
The source-of-truth tuple in
`orchestrator/src/orchestrator_adapters/production_daily_cycle.py:46-53`
has **6 entries**:

```python
RUNTIME_BLOCKERS: Final[tuple[str, ...]] = (
    "configured_data_platform_current_cycle_runtime",        # ← roadmap missed
    "configured_graph_phase0_status_runtime",
    "configured_graph_phase1_runtime",
    "configured_reasoner_runtime",
    "configured_audit_eval_retrospective_hook_runtime",
    "production_current_cycle_dagster_run_evidence",
)
```

This audit corrects the count to 6. The M2 roadmap file is patched in
parallel (separate diff) to match.

---

## Per-Blocker Status Table

| # | Blocker | Owner Module | **Status** | Critical Path |
|---|---|---|---|---|
| 1 | `configured_data_platform_current_cycle_runtime` | data-platform | **PARTIAL** | Live PG integration test gap |
| 2 | `configured_graph_phase0_status_runtime` | graph-engine | **STUBBED** | **No Neo4jGraphStatusProvider exists — implementation work needed** |
| 3 | `configured_graph_phase1_runtime` | graph-engine | **PARTIAL** | Impl exists, but orchestrator's default wiring substitutes `_FailClosedGraphPhase1Runtime` (phase1.py:285) |
| 4 | `configured_reasoner_runtime` | reasoner-runtime | **PARTIAL** | Graceful-degradation health probe + env-gated Codex/Claude credentials needed |
| 5 | `configured_audit_eval_retrospective_hook_runtime` | audit-eval | **PARTIAL** | Audit-eval side structurally complete, but operationally inherits #1 (live PG manifest read) |
| 6 | `production_current_cycle_dagster_run_evidence` | orchestrator + assembly | **DEFERRED-TO-M2.6** | Artifact produced by the M2.6 proof itself; cannot be wired before the cycle runs |

**Aggregate readiness: 0 READY + 4 PARTIAL + 1 STUBBED + 1 DEFERRED.**

The single STUBBED blocker (#2) remains the **critical-path bottleneck for M2.6**.
PARTIAL blockers (#1, #3, #4, #5) are runnable under M2.1 preflight with
documented gaps each addressed in their own sub-round.

---

## Blocker-by-Blocker Detail

### #1. `configured_data_platform_current_cycle_runtime` — PARTIAL

**Owner:** data-platform

**Source evidence:**
- `data-platform/src/data_platform/cycle/current_selection.py:163` — `CurrentCycleReadinessProvider` class (real impl)
- `data-platform/src/data_platform/cycle/current_selection.py:428` — `freeze_current_cycle_candidates()` (real impl)
- `data-platform/src/data_platform/cycle/repository.py:104,120,145` — actual `FOR UPDATE` + `FOR UPDATE OF candidate_queue SKIP LOCKED` SQL (review pass corrected this from `current_selection.py`)
- `orchestrator/src/orchestrator_adapters/production_daily_cycle.py:188-194` — hardcoded resource injection
- `orchestrator/src/orchestrator_adapters/production_daily_cycle.py:125-142` — `candidate_freeze` asset calls `freeze_current_cycle_candidates()`

**What's wired:**
- Atomic PG transactions: `FOR UPDATE` on cycle metadata + `FOR UPDATE OF candidate_queue SKIP LOCKED` in production code (`repository.py:120, 145`), not fixtures.
- `current_cycle_inputs()` (in `data_platform/cycle/current_cycle_inputs.py`, separate module from current_selection) honors `DP_CANONICAL_USE_V2=1` and reads `canonical_v2.*` (canonical_datasets.py:143).
- M1 closure proved fixture-level write→read closure under `DP_CANONICAL_USE_V2=1`
  (M1.10 controlled v2 proof).

**What's missing for M2.6 READY:**
- Live PG integration test that exercises atomic freeze under concurrent load
  (current tests are fixture-only).
- M2.1 preflight will run a dry compose-PG smoke; that closes the gap without
  source changes.

**Required env vars:**
- `DP_PG_DSN` — live PostgreSQL connection string
- `DP_CANONICAL_USE_V2=1` — required to read canonical_v2 (default off)
- `DP_CURRENT_CYCLE_SYMBOLS` — optional, defaults to `("600519.SH", "000001.SZ")`

---

### #2. `configured_graph_phase0_status_runtime` — STUBBED ⚠️ critical

**Owner:** graph-engine

**Source evidence:**
- `orchestrator/src/orchestrator_adapters/production_daily_cycle.py:290-295` — `_FailClosedGraphStatusProvider` raises `RuntimeError`
- `orchestrator/src/orchestrator_adapters/production_daily_cycle.py:190` — default uses fail-closed stub when no override passed
- `orchestrator/src/orchestrator_adapters/production_daily_cycle.py:73-78` — `GraphStatusProvider` Protocol defined (interface only)

**What's NOT wired in graph-engine:**
- No class in `graph-engine/graph_engine/` implements `GraphStatusProvider` Protocol's `get_graph_status(candidate_freeze, cycle_id)` method.
- `graph-engine/graph_engine/status/store.py:41-55` has `PostgreSQLStatusStore`
  (graph status row storage) but it does not satisfy the orchestrator's Phase 0
  Protocol shape.
- `graph-engine/graph_engine/status/manager.py` has `GraphStatusManager` (state-machine)
  but is also not a Phase 0 asset provider.

**What's missing for M2.6 READY:**
1. Implement `Neo4jGraphStatusProvider` (or analogous) in graph-engine that
   queries live Neo4j for graph readiness and returns a structured status
   matching the orchestrator's `GraphStatusProvider` Protocol.
2. Add a public factory (e.g., `graph_engine.providers.build_graph_phase0_status_provider`)
   so orchestrator can wire it into `ProductionPhase0Provider(graph_status_provider=…)`.
3. Live Neo4j integration test in graph-engine proving readiness check.
4. Wire the override into orchestrator `production_daily_cycle_provider()`
   factory or via env-driven module factory.

**Required env vars:**
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`
  (graph-engine/graph_engine/config.py:29-32)

**Estimated effort:** 2-3 dedicated rounds (review pass revised this upward
from "1 round"). The work decomposes into:
1. Implement `Neo4jGraphStatusProvider` class against live Neo4j
2. Add `build_graph_phase0_status_provider()` factory in `graph_engine.providers`
3. Wire orchestrator `_default_graph_phase0_status_provider()` to use it
4. Live Neo4j integration test in graph-engine
5. Orchestrator-side integration test wiring through `ProductionPhase0Provider`

---

### #3. `configured_graph_phase1_runtime` — PARTIAL

**Owner:** graph-engine

> **Review pass downgraded this from READY → PARTIAL.** The first-pass audit
> missed a hidden fail-closed default at `phase1.py:285`. The implementation
> exists in graph-engine, but orchestrator's default wiring does NOT pass it.

**Source evidence:**
- `graph-engine/graph_engine/providers/phase1.py:291-303` — `build_graph_phase1_provider(runtime=None, ...)` factory; the `runtime` parameter is OPTIONAL.
- `graph-engine/graph_engine/providers/phase1.py:285` — `runtime = self.runtime or _FailClosedGraphPhase1Runtime()` — **hidden fail-closed default when no runtime is passed**.
- `graph-engine/graph_engine/providers/phase1.py:247-277` — defines `graph_promotion` + `graph_snapshot` assets (real)
- `graph-engine/tests/integration/test_live_closure.py:94-212` — live Neo4j test requires `NEO4J_PASSWORD` env (test is skipped without credentials).
- `orchestrator/src/orchestrator_adapters/production_daily_cycle.py:413-416` — calls `build_graph_phase1_provider()` **with no `runtime` argument** → falls through to fail-closed default at execution time.

**What's wired (when runtime passed explicitly):**
- `runtime.promote_graph()` + `runtime.compute_graph_snapshot()` against live Neo4j
- Cold reload validation
- Recent commits (`fc4e083` "test: prove graph live closure with GDS",
  `78019a7` "harden graph phase1 artifact proof", `14c32f2` "add graph phase1 provider assets")
  prove active hardening

**What's missing for M2.6 READY:**
1. **Default-wiring fix**: either (a) graph-engine's `build_graph_phase1_provider()` should default to a real `GraphPhase1Service` instead of `_FailClosedGraphPhase1Runtime` when Neo4j env is set, OR (b) `_default_graph_phase1_provider()` in `production_daily_cycle.py:413-416` should construct and pass a real runtime.
2. **NEO4J_PASSWORD-gated test caveat**: the live integration test `test_live_closure.py` is skipped without `NEO4J_PASSWORD`; M2.1 preflight must provision Neo4j credentials to actually exercise this path.
3. Orchestrator-level integration test exercising Phase 0 → Phase 1 chain end-to-end (likely M2.3b).

**Required env vars:**
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`
- `CANONICAL_READER_ARTIFACT_PATH` (for artifact-backed snapshot reader path)

---

### #4. `configured_reasoner_runtime` — PARTIAL

**Owner:** reasoner-runtime

**Source evidence:**
- `reasoner-runtime/reasoner_runtime/health/checker.py:33-65` — `health_check` entry point
- `reasoner-runtime/reasoner_runtime/health/checker.py:68-105` — `probe_provider` (LiteLLM completion with real HTTP)
- `reasoner-runtime/reasoner_runtime/health/checker.py:108-153` — structured probe for Codex / Claude Code
- `reasoner-runtime/reasoner_runtime/providers/client.py:59-90` — `build_client` with Codex / Claude Code env-flag gating
- `reasoner-runtime/reasoner_runtime/replay/models.py:19-25` — `ReplayBundle` 5-field invariant
  (`sanitized_input`, `input_hash`, `raw_output`, `parsed_result`, `output_hash`)
- `reasoner-runtime/reasoner_runtime/replay/builder.py:27-45` — `build_replay_bundle()` SHA-256 hashing
- `reasoner-runtime/reasoner_runtime/scrub/handler.py:75-80` — `scrub_input()` PII boundary
- `orchestrator/src/orchestrator_adapters/p2_dry_run.py:217-243` — `DefaultReasonerRuntimeGateway` wraps reasoner_runtime API

**What's wired:**
- Real LiteLLM-backed health probe (issues a real HTTP completion to verify provider reachability).
- Codex + Claude Code structured probes (`025db5b reasoner: support codex structured health`).
- **Graceful-degradation health-check** (review-pass correction): probes catch exceptions and return `reachable=False` in `HealthCheckReport`, NOT a hard `raise ProviderConfigError`. This is operationally fine — orchestrator sees `reachable=False` and fails the cycle — but the audit's earlier "fail-closed raise" wording was inaccurate.
- PII scrub before any LLM call boundary.
- Replay 5-field invariant enforced (Pydantic `extra="forbid"`).
- `_DEFAULT_PROVIDER = "openai-codex"` + `_DEFAULT_MODEL = "gpt-5.5"`
  (`p2_dry_run.py:17-18`); these are only used if `P2_REASONER_PROVIDER` /
  `P2_REASONER_MODEL` envs are unset. **`P2_REASONER_PROVIDER` is therefore
  not strictly required as an env var (it has a default), but valid
  Codex/Claude/MiniMax credentials must be provisioned regardless.**

**What's missing for M2.6 READY:**
1. Production env must set `REASONER_RUNTIME_ENABLE_CODEX_OAUTH=1` (or
   `REASONER_RUNTIME_ENABLE_CLAUDE_CODE_CLI=1`) — currently flags-off blocks
   the structured probe.
2. Valid Codex OAuth credentials at `~/.codex/auth.json` (or `CODEX_AUTH_PATH`)
   — credential lifecycle is fail-closed (M2 spec compliant); operator must
   provision them.
3. Generic LiteLLM probe path has only token-count heartbeat (1 max_token);
   not gating, but operationally weaker than structured probe.

**Required env vars:**
- `P2_REASONER_PROVIDER` (e.g., `openai-codex`, `claude-code`, `minimax`)
- `P2_REASONER_MODEL` (e.g., `gpt-5.5`)
- `REASONER_RUNTIME_ENABLE_CODEX_OAUTH=1` (to unlock Codex structured probe)
- `REASONER_RUNTIME_ENABLE_CLAUDE_CODE_CLI=1` (to unlock Claude Code probe)
- `CODEX_AUTH_PATH` (optional; default `~/.codex/auth.json`)
- `CLAUDE_BINARY_PATH` (optional; default `claude` in `PATH`)
- Provider-specific keys via LiteLLM (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
  `MINIMAX_API_KEY`)

**Why not READY:** All code paths exist, but the runtime is
configuration-blocked: it fails closed under default env, which is correct
for safety but means M2.6 can't run unattended without operator credential
setup.

---

### #5. `configured_audit_eval_retrospective_hook_runtime` — PARTIAL

**Owner:** audit-eval

> **Review pass downgraded this from READY → PARTIAL.** The audit-eval side is
> structurally complete, but it operationally inherits blocker #1's PARTIAL
> status: the manifest gateway delegates to `data_platform.cycle.get_publish_manifest`,
> which only returns real PG data when blocker #1 is itself live.

**Source evidence:**
- `audit-eval/src/audit_eval/retro/hook.py:197-293` — `run_real_retrospective_hook` (full production impl with provenance + manifest validation)
- `audit-eval/src/audit_eval/audit/storage.py:230-331` — `DuckDBReplayRepository` (durable read-only DuckDB queries)
- `audit-eval/src/audit_eval/audit/storage.py:106-228` — `ManagedDuckDBFormalAuditStorageAdapter` (atomic transaction writes)
- `audit-eval/src/audit_eval/audit/storage.py:402-434` — `_ensure_managed_tables` creates `audit_eval.audit_records` + `audit_eval.replay_records`
- `audit-eval/src/audit_eval/audit/real_cycle.py:96-130` — `DataPlatformManifestGateway` constructor injection point; line 120-129 falls through to `from data_platform.cycle import get_publish_manifest` only when no override is supplied. Production wiring (production_daily_cycle.py:340) constructs `DataPlatformManifestGateway()` with no override → real PG path is taken.
- `audit-eval/tests/test_retro_hook.py:329-360` — `test_real_retrospective_hook_durable_duckdb_query_succeeds` integration test (real DuckDB file, roundtrip)
- `orchestrator/src/orchestrator_adapters/production_daily_cycle.py:298-343` — `_EnvBackedRetrospectiveHookRuntime` wires it all

**What's wired:**
- Real DuckDB durable persistence with retry-safe append-only writes.
- Real data-platform manifest gateway in production wiring (constructor injection used only by tests).
- Provenance validation rejects forbidden markers ("smoke", "fixture", "historical").
- Audit/replay 5-field replay contract persists in `payload_json`.
- Manifest binding required (`require_manifest_gateway=True`).
- Recent commits (`a038ce1` provenance hardening, `13cff87` durable manifest
  lookup, `fd6ac28` real retrospective hook, `d1cf19b` managed DuckDB) prove
  maturity.

**What's missing for M2.6 READY:**
- Transitive dependency on blocker #1: `DataPlatformManifestGateway.load()` only
  returns real published-cycle data when `data_platform.cycle.get_publish_manifest`
  is hitting live PG. Once blocker #1 reaches READY (via M2.2), blocker #5
  follows.
- M2.5 sub-round verifies the end-to-end DuckDB write→read path under compose
  stack with a real cycle manifest.

**Required env vars:**
- `AUDIT_EVAL_DUCKDB_PATH` — required; absolute path to DuckDB file (orchestrator fails closed if unset)
- `AUDIT_EVAL_AUDIT_TABLE_ENV` — optional; default `audit_eval.audit_records`
- `AUDIT_EVAL_REPLAY_TABLE_ENV` — optional; default `audit_eval.replay_records`

---

### #6. `production_current_cycle_dagster_run_evidence` — DEFERRED-TO-M2.6

This blocker has **no provider class** and **no factory**. It is the artifact
produced by the M2.6 proof itself: a captured Dagster run id, persisted
manifest, replay rows, and retrospective hook result emitted by a real
`daily_cycle_job.execute_in_process()` invocation.

**It cannot be "wired" before M2.6**. Once blockers 1–5 are at READY-or-PARTIAL
*and* M2.1 preflight passes, M2.6 produces this evidence on its first successful
end-to-end run. (The audit's earlier "N/A" classification was retained as a tuple
member for `production_daily_cycle_status().runtime_blockers` so that M2.6 can
clear it; it is not removable from the tuple.)

---

## Cross-Module Env-Var Inventory (for M2.1 preflight)

Consolidated list — every env var the production daily-cycle runtime needs:

### Data-platform
| Var | Required? | Description |
|---|---|---|
| `DP_PG_DSN` | yes | PostgreSQL connection string |
| `DP_CANONICAL_USE_V2` | yes (`=1`) | Read canonical_v2 instead of legacy canonical |
| `DP_CURRENT_CYCLE_SYMBOLS` | optional | Defaults to `("600519.SH", "000001.SZ")` |

### Graph-engine
| Var | Required? | Description |
|---|---|---|
| `NEO4J_URI` | yes | Neo4j connection URI |
| `NEO4J_USER` | yes | Neo4j auth user |
| `NEO4J_PASSWORD` | yes | Neo4j auth password |
| `NEO4J_DATABASE` | yes | Neo4j database name |
| `CANONICAL_READER_ARTIFACT_PATH` | optional | Artifact-backed snapshot reader |

### Reasoner-runtime
| Var | Required? | Description |
|---|---|---|
| `P2_REASONER_PROVIDER` | optional (has default) | Default `openai-codex` (`p2_dry_run.py:17`); set to override |
| `P2_REASONER_MODEL` | optional (has default) | Default `gpt-5.5` (`p2_dry_run.py:18`); set to override |
| `P2_REASONER_HEALTH_TIMEOUT_S` | optional | Default 30s; raise for slower providers |
| `REASONER_RUNTIME_ENABLE_CODEX_OAUTH` | conditional (`=1` if Codex) | Unlocks Codex structured probe |
| `REASONER_RUNTIME_ENABLE_CLAUDE_CODE_CLI` | conditional (`=1` if Claude Code) | Unlocks Claude Code probe |
| `CODEX_AUTH_PATH` | optional | Default `~/.codex/auth.json` |
| `CLAUDE_BINARY_PATH` | optional | Default `claude` in `PATH` |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `MINIMAX_API_KEY` | conditional | Per provider; **required operationally even if `P2_REASONER_PROVIDER` is unset** (default is `openai-codex` → still needs Codex creds) |

### Audit-eval
| Var | Required? | Description |
|---|---|---|
| `AUDIT_EVAL_DUCKDB_PATH` | yes | Absolute path to DuckDB file |
| `AUDIT_EVAL_AUDIT_TABLE_ENV` | optional | Default `audit_eval.audit_records` |
| `AUDIT_EVAL_REPLAY_TABLE_ENV` | optional | Default `audit_eval.replay_records` |

### Orchestrator (Phase 2 + cycle binding)
| Var | Required? | Description |
|---|---|---|
| `ORCHESTRATOR_PHASE2_POOL_FAILURE_RATE_METRIC_ARTIFACT` | conditional | Persisted P2 metric artifact path; **only used after the first cycle has produced one**. First M2.6 run must use the JSON fallback below. |
| `ORCHESTRATOR_PHASE2_POOL_FAILURE_RATE_EVENT_JSON` | conditional (first run) | JSON fallback for non-production / first-cycle runs. M2.1 preflight cannot produce a real metric artifact (it is preflight only); first M2.6 run sources from this env or inline JSON. |
| `ORCHESTRATOR_POLICY_PATH` | yes | Gate policy YAML/TOML path |
| `ORCHESTRATOR_DEFINITIONS_PROFILE` | yes | Dagster definitions profile selector (e.g., `lite-local`, `full-dev`) |
| `ORCHESTRATOR_MODULE_FACTORIES` | yes | Module factory registration list (must include `production_daily_cycle:production_daily_cycle_provider`) |
| `ORCHESTRATOR_DBT_PROJECT_DIR` | yes | dbt project root path for Phase 0 dbt CLI invocation |
| `DAGSTER_HOME` | yes | Dagster instance home for run/event log persistence |
| Dagster run tag `cycle_id` | yes | Must be set per `daily_cycle_job.execute_in_process(tags=…)` |

---

## Gap-to-M2.1 List

What must happen before M2.1 (runtime preflight) can execute:

1. **Compose stack ready**: `lite-local.yaml` running with PG + Neo4j + dagster-daemon + dagster-webserver, all healthy.
2. **All required env vars set** (see inventory above) with at least non-fake placeholders for Codex/Claude (M2.1 can use `MINIMAX_API_KEY` if Codex/Claude not yet provisioned, since the `P2_REASONER_PROVIDER` choice gates which credentials are needed). If keeping default `P2_REASONER_PROVIDER=openai-codex`, Codex creds are still required.
3. **DuckDB file path provisioned** at `AUDIT_EVAL_DUCKDB_PATH`.
4. **Phase 2 pool metric flow** decided: M2.1 cannot produce a valid `ORCHESTRATOR_PHASE2_POOL_FAILURE_RATE_METRIC_ARTIFACT` (preflight only). First M2.6 run must instead supply `ORCHESTRATOR_PHASE2_POOL_FAILURE_RATE_EVENT_JSON` inline as the non-production fallback. Subsequent cycles can read the artifact persisted by an earlier successful run.
5. **DBT project path** provisioned at `ORCHESTRATOR_DBT_PROJECT_DIR` (Phase 0 dbt CLI invocation requires this).

Nothing in the gap list requires *source code changes* before M2.1.

---

## Sub-Round Sequencing Recommendation

Based on the audit, the original M2 roadmap order needs **one critical
adjustment**: insert a **M2.3a** sub-round to unblock the STUBBED Phase 0
graph status provider before the Phase 0 → Phase 1 chain can even start.

**Recommended sequence (revised after review pass):**

1. **M2.1** — runtime preflight (compose stack + env vars). Blockers 1, 4, 5
   become testable here. **No source changes**.
2. **M2.3a** (NEW, replaces part of M2.3) — graph-engine implements
   `Neo4jGraphStatusProvider` + factory + orchestrator default-wire fix +
   live Neo4j integration test. Also fix Phase 1 default fail-closed wiring
   (`phase1.py:285`). **Must land before M2.6.** Estimated 2-3 rounds.
3. **M2.3b** — orchestrator integration test exercising Phase 0 → Phase 1
   chain end-to-end (uses M2.3a output).
4. **M2.2** — data-platform live PG integration test (closes blocker 1's
   PARTIAL gap). Can run in parallel with M2.3a.
5. **M2.4** — reasoner-runtime credential provisioning + production env
   pre-flight (closes blocker 4's PARTIAL gap; mostly ops, not code). **Can
   start in parallel with M2.3a, not after** — credential work is independent
   ops and often slow.
6. **M2.5** — audit-eval end-to-end DuckDB path verification under compose
   stack with real cycle manifest (closes blocker 5's transitive PARTIAL gap
   once M2.2 lands). Likely a P1 integration test, not a full round of code
   work.
7. **M2.6** — full Dagster job proof. Produces blocker 6 artifact.

**Parallel opportunities (similar to M1.12 + M1.13 pattern):**
- M2.2 + M2.3a + M2.4 can run as separate worktrees off `m2-baseline-2026-04-29`.
- M2.5 depends on M2.2 + M2.3a + M2.4 closures.
- M2.6 depends on all of M2.1–M2.5.

---

## Hard-rule declarations

- `project_ult_v5_0_1.md` UNCHANGED.
- `ult_milestone.md` UNCHANGED.
- No production fetch (no Tushare HTTP, no live LLM call).
- No P5 / M3 / M4 work.
- No compose stack started in M2.0 (deferred to M2.1).
- No source code modified in any of the 6 module repositories — only
  evidence file written and roadmap fact-corrected.
- canonical_v2 + canonical_lineage spec sets unchanged from M1 closure.
- Tushare remains `provider="tushare"` source adapter only.
- `frontend-api` NOT touched.
- `/Users/fanjie/Desktop/BIG/FrontEnd/**` NOT modified.

---

## Cross-references

- M2 roadmap (parent planning doc, fact-corrected in same diff): [`m2-roadmap-20260429.md`](m2-roadmap-20260429.md)
- M1 closure final state: [`m1-legacy-retirement-preconditions-progress-20260428.md`](m1-legacy-retirement-preconditions-progress-20260428.md)
- M1.14 cleanup proof: [`m1-14-cleanup-proof-20260429.md`](m1-14-cleanup-proof-20260429.md)
- M1.10 controlled v2 proof results (forerunner of blocker 1 PARTIAL): [`m1-10-controlled-v2-proof-results-20260429.md`](m1-10-controlled-v2-proof-results-20260429.md)
- Production daily-cycle gap audit (Apr 28 baseline): [`production-daily-cycle-gap-audit-20260428.md`](production-daily-cycle-gap-audit-20260428.md)

## Next steps

1. Patch `m2-roadmap-20260429.md` 5→6 blocker count (already landed in same commit).
2. **Decision point for user:**
   - Proceed to **M2.1 runtime preflight** (compose stack + env vars), since
     4 PARTIAL + 1 STUBBED + 1 DEFERRED means M2.1 is unblocked even with #2
     STUBBED. M2.1's output informs whether to start M2.3a in parallel.
   - Or proceed directly to **M2.3a** (graph-engine impl + default-wire fixes),
     since it's the only true critical-path blocker.
   - Recommendation: **M2.1 first**. M2.3a needs compose-Neo4j to be running
     for its integration test anyway, and M2.1 sets that up.

## Review-pass findings folded in (2026-04-29 second pass)

This document was independently cross-checked by 3 reviewer agents after the
first-pass audit. Key catches folded into this version:

- **Blocker #3 downgraded READY → PARTIAL**: hidden `_FailClosedGraphPhase1Runtime`
  default at `graph-engine/graph_engine/providers/phase1.py:285` (orchestrator's
  `_default_graph_phase1_provider()` calls `build_graph_phase1_provider()`
  with no runtime arg, so the fail-closed branch wins).
- **Blocker #5 downgraded READY → PARTIAL**: transitive dependency on #1 — the
  manifest gateway delegates to data-platform's `get_publish_manifest`, which
  is only live when blocker #1 is itself live.
- **Blocker #4 wording corrected**: health probe is graceful-degradation
  (`reachable=False`), not hard `raise ProviderConfigError`.
- **Blocker #1 file paths corrected**: FOR UPDATE/SKIP LOCKED actually live in
  `repository.py:120,145`, not `current_selection.py`. `DP_CANONICAL_USE_V2`
  consumer is `current_cycle_inputs.py`, not `current_selection.py`.
- **Blocker #6 reclassified**: "N/A" → "DEFERRED-TO-M2.6" for clarity.
- **M2.3a effort revised upward** from 1 round to 2-3 rounds (impl + factory +
  default-wire fix + live integ test + orchestrator integ test).
- **M2.4 sequencing**: should parallelize with M2.3a (credential ops are
  independent), not run after.
- **Env-var inventory additions**: `ORCHESTRATOR_DBT_PROJECT_DIR`,
  `P2_REASONER_HEALTH_TIMEOUT_S`, `DAGSTER_HOME`, profile examples for
  `ORCHESTRATOR_DEFINITIONS_PROFILE`.
- **Phase 2 metric artifact flow clarified**: M2.1 cannot produce a real
  artifact (preflight only); first M2.6 run must use the JSON fallback.
- **`P2_REASONER_PROVIDER` correction**: technically optional (has default
  `openai-codex`); credentials are the actually-required item.
