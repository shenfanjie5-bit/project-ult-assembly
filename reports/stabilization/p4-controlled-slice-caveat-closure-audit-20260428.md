# P4 Controlled Slice Caveat Closure Audit — 2026-04-28

## Task header

- Task: C5 — P4 Controlled Slice Caveat Closure Audit
- Repos in scope: subsystem-sdk + entity-registry + subsystem-news + subsystem-announcement + data-platform + assembly
- Output: `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/p4-controlled-slice-caveat-closure-audit-20260428.md`
- Date: 2026-04-28
- Audit mode: read-only inventory; no source changes, no commits, no `git init`, no new news/Polymarket production hookups, no SDK / graph-engine / new test code.

This report distinguishes between symbol-presence and runtime evidence.
Test passes recorded below confirm package import, in-process repository
contracts, and SDK adapter behaviour. They DO NOT prove the controlled
slice runs end-to-end against a live PostgreSQL container, nor that Ex-3
candidates are consumed downstream by graph-engine, reasoner-runtime, or
frontend-api in the same cycle.

---

## 1. Per-subrepo git topology probe

| Subrepo | toplevel | HEAD | branch | `git status -s` |
|---------|----------|------|--------|------------------|
| subsystem-sdk | `/Users/fanjie/Desktop/Cowork/project-ult/subsystem-sdk` | `5f131237df9101bde0a41293df151f6f9ea47fe7` | main | clean |
| entity-registry | `/Users/fanjie/Desktop/Cowork/project-ult/entity-registry` | `a38944533a2aae2191ee07e699156453a5bf708d` | main | clean |
| subsystem-news | `/Users/fanjie/Desktop/Cowork/project-ult/subsystem-news` | `c27f044ebb97646fe583dfa5e1a737f62903f647` | main | clean |
| subsystem-announcement | `/Users/fanjie/Desktop/Cowork/project-ult/subsystem-announcement` | `36555beb69ce565ee9a8d2b0f926a01158c32335` | main | clean |
| data-platform | `/Users/fanjie/Desktop/Cowork/project-ult/data-platform` | `330f6b4d82a96d36c8fd150cc1a0a432d7c6cb9c` | main | ` M src/data_platform/raw/writer.py` / ` M tests/raw/test_writer.py` |
| assembly | `/Users/fanjie/Desktop/Cowork/project-ult/assembly` | `a7f19c5994f807b2cf32eb2f45ef48f6fe23095f` | main | 4 untracked stabilization reports (incl. this one being created) |

Push status: not pushed by this audit; no commits created.
Dirty files: data-platform `src/data_platform/raw/writer.py` and
`tests/raw/test_writer.py` are out-of-scope for C5 (raw zone hardening,
not the candidate_queue bridge); assembly has 4 untracked reports under
`reports/stabilization/`. Audit performs no edits to either subrepo's
source tree.

---

## 2. Validation block (commands + verbatim results)

### 2.1 Symbol presence: subsystem_submit_queue / candidate_queue / CANDIDATE_QUEUE_TABLE

```
cd /Users/fanjie/Desktop/Cowork/project-ult && rg -n 'subsystem_submit_queue|candidate_queue|CANDIDATE_QUEUE_TABLE' subsystem-sdk/ data-platform/src 2>&1 | head -60
```

Verbatim result (key matches; full output had ~50 lines, truncated to
the load-bearing ones):

```
data-platform/src/data_platform/queue/validation.py:51:                "candidate payload_type does not match candidate_queue payload_type: "
data-platform/src/data_platform/queue/validation.py:65:    """Validated producer envelope ready for candidate_queue insertion."""
data-platform/src/data_platform/ddl/migrations/0004_cycle_candidate_selection.sql:5:    candidate_id BIGINT NOT NULL REFERENCES data_platform.candidate_queue(id),
data-platform/src/data_platform/queue/repository.py:12:    CANDIDATE_QUEUE_TABLE,
data-platform/src/data_platform/queue/repository.py:32:INSERT INTO {CANDIDATE_QUEUE_TABLE} (
data-platform/src/data_platform/queue/repository.py:50:FOR UPDATE SKIP LOCKED
data-platform/src/data_platform/queue/repository.py:53:UPDATE {CANDIDATE_QUEUE_TABLE}
data-platform/src/data_platform/queue/api.py:11:    """Validate and insert one producer Ex payload into candidate_queue."""
data-platform/src/data_platform/ddl/migrations/0002_candidate_queue.sql:40:CREATE TABLE IF NOT EXISTS data_platform.candidate_queue (
data-platform/src/data_platform/queue/__init__.py:5:    CANDIDATE_QUEUE_TABLE,
data-platform/src/data_platform/queue/models.py:14:CANDIDATE_QUEUE_TABLE: Final[str] = "data_platform.candidate_queue"
data-platform/src/data_platform/queue/worker.py:102:        description="Validate pending data_platform.candidate_queue rows once.",
data-platform/src/data_platform/cycle/repository.py:20:from data_platform.queue.models import CANDIDATE_QUEUE_TABLE
data-platform/src/data_platform/cycle/repository.py:136:                    SELECT candidate_queue.id AS candidate_id
data-platform/src/data_platform/cycle/repository.py:145:                    FOR UPDATE OF candidate_queue SKIP LOCKED
data-platform/src/data_platform/cycle/repository.py:165:                      ON candidate_queue.id = inserted.candidate_id
data-platform/src/data_platform/cycle/freeze.py:10:    """Freeze accepted candidate_queue rows for one cycle."""
data-platform/src/data_platform/cycle/current_selection.py:493:                        JOIN data_platform.candidate_queue AS candidate_queue
data-platform/src/data_platform/smoke/p1c.py:376:                        FROM data_platform.candidate_queue
subsystem-sdk/subsystem_sdk/backends/lite_pg.py:13:_DEFAULT_QUEUE_TABLE = "subsystem_submit_queue"
subsystem-sdk/tests/backends/test_lite_pg_heartbeat_backend.py:80:        queue_table="subsystem_submit_queue",
subsystem-sdk/tests/backends/test_lite_pg_backend.py:163:        queue_table='subsystem_submit_queue; drop table "contracts"',
subsystem-sdk/tests/integration/test_p4_core_vertical_slice.py:93:            queue_table="subsystem_submit_queue",
subsystem-sdk/tests/submit/test_backend_receipt_normalization.py:69:                "pg_table": "subsystem_submit_queue",
```

Key fact: `subsystem_submit_queue` appears ONLY in
`subsystem-sdk/subsystem_sdk/backends/lite_pg.py` and that subrepo's
own tests. `candidate_queue` and `CANDIDATE_QUEUE_TABLE` appear ONLY
in data-platform code. The two namespaces never co-occur in any
production module.

### 2.2 PG atomic locking predicate in cycle / queue

```
cd /Users/fanjie/Desktop/Cowork/project-ult && rg -n 'FOR UPDATE|SKIP LOCKED' data-platform/src/data_platform/cycle data-platform/src/data_platform/queue 2>&1 | head -30
```

Verbatim:

```
data-platform/src/data_platform/queue/repository.py:50:FOR UPDATE SKIP LOCKED
data-platform/src/data_platform/cycle/repository.py:104:        Eligible candidate rows are locked with SKIP LOCKED so concurrent freezes
data-platform/src/data_platform/cycle/repository.py:120:                FOR UPDATE
data-platform/src/data_platform/cycle/repository.py:145:                    FOR UPDATE OF candidate_queue SKIP LOCKED
data-platform/src/data_platform/cycle/repository.py:336:                    FOR UPDATE
data-platform/src/data_platform/cycle/manifest.py:145:                    FOR UPDATE
```

The `FOR UPDATE OF candidate_queue SKIP LOCKED` predicate exists at
`data-platform/src/data_platform/cycle/repository.py:145`, and the
`cycle_metadata` row is `FOR UPDATE`-locked at line 120 before the
freeze CTE runs.

### 2.3 Bridge code search: submit_queue ↔ candidate_queue

```
cd /Users/fanjie/Desktop/Cowork/project-ult && rg -n 'submit_queue.*candidate_queue|candidate_queue.*submit_queue' subsystem-sdk/ data-platform/src 2>&1 | head -20
```

Verbatim result: **no output** — pattern does not match in either
subrepo's source tree.

This is a load-bearing finding: there is NO module that mentions both
table names in a single file or transfer flow.

### 2.4 subsystem-sdk pytest

```
cd /Users/fanjie/Desktop/Cowork/project-ult/subsystem-sdk && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q tests 2>&1 | tail -10
```

Verbatim tail:

```
=========================== short test summary info ============================
ERROR tests/regression/test_with_shared_fixtures.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
```

The collection error is `ModuleNotFoundError: No module named
'audit_eval_fixtures'` at
`subsystem-sdk/tests/regression/test_with_shared_fixtures.py:37`. This
is a cross-repo fixture-share test that requires `audit-eval` on
PYTHONPATH and is not relevant to the C5 candidate-queue bridge audit.

A re-run that ignores this single file confirms the rest of the SDK
suite passes:

```
cd /Users/fanjie/Desktop/Cowork/project-ult/subsystem-sdk && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests --ignore=tests/regression/test_with_shared_fixtures.py 2>&1 | tail -1
```

```
426 passed, 4 skipped in 0.38s
```

Interpreter: `subsystem-sdk/.venv/bin/python` →
`/Users/fanjie/.local/share/uv/python/cpython-3.12-macos-aarch64-none/bin/python3.12`
(Python 3.12.12).

### 2.5 data-platform queue + cycle pytest

```
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -p no:cacheprovider -q tests/queue tests/cycle 2>&1 | tail -15
```

Verbatim summary:

```
81 passed, 54 skipped in 0.42s
```

The 54 skipped tests are the live-PG suites — every test that requires
`DATABASE_URL` or `DP_PG_DSN` calls `pytest.skip(...)` when neither env
var is set. Examples (cited at file+line):

- `data-platform/tests/cycle/test_freeze_cycle_candidates.py:340-342` —
  freeze tests skip without `DATABASE_URL`/`DP_PG_DSN`.
- `data-platform/tests/queue/test_candidate_queue_schema.py:45-47` —
  schema/DDL tests skip without `DATABASE_URL`/`DP_PG_DSN`.
- `data-platform/tests/queue/test_worker.py:231-234` — worker tests
  skip without `DATABASE_URL`/`DP_PG_DSN`.
- `data-platform/tests/cycle/test_publish_manifest.py:485-487` —
  manifest tests skip without `DATABASE_URL`/`DP_PG_DSN`.
- `data-platform/tests/cycle/test_current_selection.py:302-304` —
  current-cycle wrapper tests skip without `DATABASE_URL`/`DP_PG_DSN`.

Interpreter: `data-platform/.venv/bin/python` → `python3.14` (Python
3.14.3). NOTE: data-platform's interpreter is 3.14.3, not the 3.12
shared by other subrepos; this is per data-platform's own venv layout.

`tests/queue/` and `tests/cycle/` both exist (confirmed by `ls
data-platform/tests/`).

---

## 3. Current controlled-slice scope

### 3.1 subsystem-sdk → `subsystem_submit_queue` (PG, adapter-only) — **CONFIRMED partial**

The PgSubmitBackend writes to `subsystem_submit_queue` via parameterised
INSERT.

- File: `subsystem-sdk/subsystem_sdk/backends/lite_pg.py:13` —
  `_DEFAULT_QUEUE_TABLE = "subsystem_submit_queue"`.
- File: `subsystem-sdk/subsystem_sdk/backends/lite_pg.py:53-70` —
  `submit(payload)` connects, inserts, commits, returns
  `transport_ref=str(queue_id)`.
- File: `subsystem-sdk/subsystem_sdk/backends/lite_pg.py:85-95` —
  `_execute_insert` issues `insert into <quoted_queue_table> (payload)
  values (%s) returning id`.
- File: `subsystem-sdk/subsystem_sdk/backends/lite_pg.py:114-124` —
  `_quote_identifier_path` validates a simple or schema-qualified PG
  identifier.

Live-PG state per code evidence:
- The adapter accepts a `connection_factory` callable; in tests
  (`tests/integration/test_p4_core_vertical_slice.py:93`,
  `tests/backends/test_lite_pg_backend.py:163`,
  `tests/backends/test_lite_pg_heartbeat_backend.py:80`) the factory is
  injected with a recording / fake connection. No subsystem-sdk test
  here was observed exercising a live PostgreSQL container.
- The prior controlled-slice report
  (`assembly/reports/stabilization/p4-controlled-live-bridge-20260428.md`,
  lines 78-79) explicitly states: "The PG proof is SDK adapter/pre-
  dispatch coverage with an injected connection factory. It does not
  exercise a live PostgreSQL server." This audit confirms that
  statement still holds.

Status: **CONFIRMED that the SDK writes to `subsystem_submit_queue`
via injected connection factory; CONFIRMED that no live-PG SDK test
exists in this audit's evidence set.**

### 3.2 `subsystem_submit_queue` → `candidate_queue` bridge — **INFERRED (gap)**

This is the load-bearing finding. The bridge is **not present in
repository code**.

Evidence pattern A — the regex `submit_queue.*candidate_queue|
candidate_queue.*submit_queue` matches NOTHING across `subsystem-sdk/`
and `data-platform/src` (validation §2.3).

Evidence pattern B — `subsystem_submit_queue` has no DDL anywhere in
the project:

- `data-platform/src/data_platform/ddl/migrations/` contains:
  `0001_init.sql`, `0002_candidate_queue.sql`,
  `0003_cycle_metadata.sql`, `0004_cycle_candidate_selection.sql`,
  `0005_cycle_publish_manifest.sql` — none mention
  `subsystem_submit_queue`.
- A repo-wide `rg 'subsystem_submit_queue'` confirms references are
  confined to `subsystem-sdk/subsystem_sdk/backends/lite_pg.py` and
  that subrepo's own tests.

Evidence pattern C — the data-platform candidate_queue write path is
direct, NOT a transfer from subsystem_submit_queue:

- `data-platform/src/data_platform/queue/api.py:10-18` —
  `submit_candidate(payload: ExPayload) -> CandidateQueueItem` directly
  validates the envelope and inserts into `candidate_queue` via
  `CandidateRepository.insert_candidate(envelope)`.
- `data-platform/src/data_platform/queue/repository.py:31-43` —
  `_INSERT_CANDIDATE_SQL` writes directly to `CANDIDATE_QUEUE_TABLE`
  (`data_platform.candidate_queue`).
- `data-platform/src/data_platform/queue/worker.py:35-94` —
  `validate_pending_candidates` reads from `candidate_queue` (via
  `repository.fetch_pending_for_update`, which uses
  `_FETCH_PENDING_FOR_UPDATE_SQL` against `CANDIDATE_QUEUE_TABLE`,
  repository.py:44-51) and updates the row's `validation_status`. It
  does NOT read from `subsystem_submit_queue`.

These are TWO distinct write paths into TWO distinct tables, with no
in-repo code that moves rows from `subsystem_submit_queue` into
`candidate_queue`.

Status per the user-defined labelling rule:
> "INFERRED if no transfer code exists in repo and the bridge is
> described only in docs/reports — absence IS a finding."

**Status: INFERRED (gap).** The bridge is described in the prior
controlled-slice reports
(`p4-core-subsystem-vertical-slice-20260428.md`,
`p4-controlled-live-bridge-20260428.md`) at the design-intent level
but no transfer code (writer / consumer / sweeper / Dagster op) exists
in either subsystem-sdk or data-platform that reads
`subsystem_submit_queue` rows and inserts equivalent rows into
`data_platform.candidate_queue`. Absence is the finding.

Plausible interpretations consistent with code (each NEEDS
confirmation by the user — this audit does NOT promote any of them):
1. The SDK's `subsystem_submit_queue` is an SDK-internal staging table
   only, and the eventual production wiring will replace it with a
   direct Layer B HTTP/RPC submit that lands in `candidate_queue`.
2. The bridge is intended to be a future Dagster op or background
   worker not yet committed.
3. The Lite mode is intended to short-circuit by having producers call
   `data_platform.queue.api.submit_candidate(...)` directly, with
   `subsystem_submit_queue` retained only as the SDK adapter's raw
   transport target during pre-Layer-B scaffolding.

The audit makes no claim about which interpretation is correct; it
only records that the bridge code is absent.

### 3.3 data-platform `candidate_queue` operations — **CONFIRMED**

- DDL: `data-platform/src/data_platform/ddl/migrations/0002_candidate_queue.sql:40` — `CREATE TABLE IF NOT EXISTS data_platform.candidate_queue (...)`; constraints at lines 49-51 (unique `ingest_seq`, jsonb-typed payload, payload excludes ingest metadata).
- Models: `data-platform/src/data_platform/queue/models.py:14` —
  `CANDIDATE_QUEUE_TABLE: Final[str] = "data_platform.candidate_queue"`.
- Insert path: `data-platform/src/data_platform/queue/repository.py:31-43,82-108` — `CandidateRepository.insert_candidate(envelope)` performs a transactional INSERT...RETURNING and maps via `_row_to_candidate_queue_item`.
- Pending-fetch path: `data-platform/src/data_platform/queue/repository.py:44-51,115-142` — `fetch_pending_for_update(limit, connection)` issues `SELECT ... FOR UPDATE SKIP LOCKED` against `CANDIDATE_QUEUE_TABLE`.
- Validation update path: `data-platform/src/data_platform/queue/repository.py:52-59,144-180` — `mark_validation_result(...)` updates `validation_status` only when the row is still `pending`.
- Public API: `data-platform/src/data_platform/queue/api.py:10-18` — `submit_candidate(payload)` is the producer-facing entry point.
- Worker: `data-platform/src/data_platform/queue/worker.py:35-94` — `validate_pending_candidates(limit, *, validator)` runs one synchronous pass inside a single `repository.begin()` transaction; rejection branch (line 61) marks `rejected`, success branch (line 77) marks `accepted`; the `try/except Exception` block at lines 69-76 logs and re-raises so transient validator failures roll back the transaction and leave rows pending.

Status: **CONFIRMED** — the in-process repository contract is fully
present. Live-PG runtime evidence is bounded by §3.5 (54 skipped
tests).

### 3.4 `cycle/freeze.py` PG atomic semantics — **CONFIRMED**

- File: `data-platform/src/data_platform/cycle/freeze.py:9-18` — `freeze_cycle_candidates(cycle_id)` opens a single transaction via `repository.begin()` and delegates to `freeze_selection`.
- Lock predicate (verified from code, not inference):
  - File: `data-platform/src/data_platform/cycle/repository.py:111-124` — first reads `cycle_metadata` row `FOR UPDATE` (line 120) and rejects unknown / already-frozen cycles.
  - File: `data-platform/src/data_platform/cycle/repository.py:132-191` — single CTE: `locked_candidates` selects accepted-and-not-yet-selected rows from `candidate_queue` with `FOR UPDATE OF candidate_queue SKIP LOCKED` (line 145); `inserted` writes into `cycle_candidate_selection`; `stats` derives cutoff/count from inserted; the final `UPDATE ... cycle_metadata` sets `selection_frozen_at = now()`, `status = 'phase0'`, and returns the metadata row.
  - The transaction-level docstring at `repository.py:99-108` explicitly states the freeze boundary semantic: under PostgreSQL READ COMMITTED, the `INSERT...SELECT` statement snapshot is the cutoff; later-accepted candidates wait for a future cycle.

Status: **CONFIRMED in code**. Live-PG runtime evidence is bounded by
§3.5 — `data-platform/tests/cycle/test_freeze_cycle_candidates.py:340-
342` skips when `DATABASE_URL`/`DP_PG_DSN` is absent, so the audit
recorded zero freeze tests actually executed against a live PG
instance during this run.

### 3.5 Ex-0 / Ex-1 / Ex-2 / Ex-3 schema status — **CONFIRMED**

- File: `data-platform/src/data_platform/queue/models.py:11` —
  `CandidatePayloadType: TypeAlias = Literal["Ex-0", "Ex-1", "Ex-2",
  "Ex-3"]` (matches the four Ex types per subsystem-sdk's CLAUDE.md).
- File: `data-platform/src/data_platform/queue/models.py:18-20` —
  `_CANDIDATE_PAYLOAD_TYPES: Final[frozenset[str]] = frozenset(("Ex-0",
  "Ex-1", "Ex-2", "Ex-3"))`.
- File: `data-platform/src/data_platform/queue/models.py:24` —
  `_FORBIDDEN_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset(
  ("submitted_at", "ingest_seq"))` (mirrors subsystem-sdk producer-
  owned-fields rule).
- subsystem-news supports `Ex-1`, `Ex-2`, `Ex-3`; Ex-0 is provided by
  subsystem-sdk's heartbeat client (per
  `subsystem-news/src/subsystem_news/public.py:75` — `_SUPPORTED_EX_TYPES
  = ("Ex-1", "Ex-2", "Ex-3")` — confirmed by reading the public entry
  per the C5 scope rule).
- subsystem-announcement public entry exists at
  `subsystem-announcement/src/subsystem_announcement/public.py:1-40`
  with the same five module-level singletons; Ex types not enumerated
  at the public entry (they live in the runtime modules — internals not
  read per scope).
- entity-registry public entry at
  `entity-registry/src/entity_registry/public.py:60-70,99-106` exposes
  `resolve_mention`, `lookup_alias`, `batch_resolve` for the Ex-2/Ex-3
  preflight ref check (per CLAUDE.md the registry does NOT auto-mint
  canonical IDs).

Status: **CONFIRMED** — all four Ex schema codes are first-class in
the candidate_queue layer's payload-type alias and frozenset, and
producer subsystems support the Ex types claimed in the prior
controlled-slice report (Ex-1/Ex-2/Ex-3 for news + announcement; Ex-0
for SDK heartbeat).

---

## 4. Gaps to production P4

### 4.1 SDK → canonical candidate_queue (explicit bridge status)

**Status: INFERRED (gap).** Per §3.2, no in-repo code transfers rows
from `subsystem_submit_queue` (SDK adapter target) to
`data_platform.candidate_queue` (data-platform target). The two write
paths are independent. Whatever Layer B production wiring finally
lives in (Lite-mode worker / Full-mode Kafka topic / direct API
submit), it does not exist in either subsystem-sdk or data-platform's
source tree on the current HEADs (§1).

### 4.2 Live PG freeze status

**Status: PARTIAL.** The cycle freeze logic exists in code with a
verified `FOR UPDATE OF candidate_queue SKIP LOCKED` predicate
(§3.4). The 81 in-process tests pass. The 54 PG-dependent freeze /
queue / manifest / worker / current-selection tests skip without
`DATABASE_URL`/`DP_PG_DSN` (§2.5 cited skip sites). No live-PG smoke
run was executed during this audit, and no env vars were set to
attempt one. The lite-local compose file at
`assembly/compose/lite-local.yaml:1-16` does spin up a PostgreSQL 16
service, so the infrastructure scaffold for a live PG smoke exists,
but no audit-time wiring connects the data-platform pytest run to it.

### 4.3 Ex-3 same-cycle entry into graph / reasoner / frontend

**Status: PARTIAL → INFERRED (depending on consumer).**

- **graph-engine consumption — INFERRED (gap)**: graph-engine's
  `CandidateGraphDelta` symbol exists at
  `graph-engine/graph_engine/__init__.py:6,21,74,127`, and
  `promote_graph_deltas` is wired in `phase1.py:12,156`, but no
  in-repo path was located that ingests `data_platform.candidate_queue`
  rows of `payload_type='Ex-3'` directly into graph-engine's promotion
  pipeline within the same cycle. The connection has to flow through
  the freeze → cycle_candidate_selection → graph-engine wiring and the
  audit observed only the CTE side (cycle/repository.py:132-191), not
  a graph-engine reader of cycle_candidate_selection's Ex-3-typed
  rows.
- **reasoner-runtime semantic consumption — INFERRED (gap)**:
  `orchestrator/src/orchestrator_adapters/p2_dry_run.py` defines a
  reasoner gateway (`P2ReasonerGateway` Protocol at line 167,
  `DefaultReasonerRuntimeGateway` at line 217, calls into
  `reasoner_runtime.health_check / generate_structured_with_replay` at
  lines 238 / 345). These payloads are world-state / alpha decisions
  (`WorldStateDeltaDecision` at line 250, `AlphaReasonerResponse` at
  line 280), not direct Ex-3 candidate ingestion.
  **Existing symbol-level reader (CONFIRMED, not Ex-3 semantic)**: an
  in-repo helper at `orchestrator/src/orchestrator_adapters/p2_dry_run.py:1227`
  (`_load_frozen_candidate_symbols(cycle_id)`) already reads
  `data_platform.cycle_candidate_selection JOIN data_platform.candidate_queue`
  for the current cycle and feeds the P2 L1 input chain. It projects
  each row down to `candidate_id / ts_code (or entity_id) /
  submitted_by` only (lines 1237-1275); it does NOT decode the
  `payload_type='Ex-3'` semantic body, does NOT pass an Ex-3 graph
  delta payload to the reasoner, and therefore does NOT close
  reasoner-runtime Ex-3 semantic consumption. **An Ex-3 semantic
  reader does not exist in repo** — the semantic seam would attach at
  `p2_dry_run.py:217-345` (gateway) and would parallel or extend
  `_load_frozen_candidate_symbols` to surface Ex-3 payload content.
- **frontend-api consumption — INFERRED (gap)**: a `rg` against
  `frontend-api/src` for `Ex-3|graph_delta|GraphDelta|ex_3` produced
  no matches; the routes folder contains `cycle.py`, `graph.py`,
  `entity_data.py`, `operations.py`, `system.py`, but none was found
  that surfaces Ex-3-derived signals as a read-only response. The
  closest would be `routes/graph.py` — that is where an Ex-3-derived
  read-only route would attach. No such route exists today.

The prior P4 controlled-live-bridge report
(`p4-controlled-live-bridge-20260428.md:80-91`) is consistent with
this finding: it explicitly states the bridge "is a controlled
scaffold over local read-only projection input shapes. It does not
call graph-engine Phase 1, reasoner-runtime live LLM, frontend-api
HTTP routes, external news, or Polymarket." That report is labelled
PARTIAL and this audit does **not** upgrade it.

---

## 5. What would close each gap (PLAN — do NOT execute)

The actions below are PROPOSALS. Each describes the seam, the
location, and the shape of work; none are executed and none are
implementation directives for this round.

### 5.1 Live PG smoke test scaffold

- Compose target: `assembly/compose/lite-local.yaml:1-16` already
  defines a PostgreSQL 16 service with a healthcheck.
- Required env: `DP_PG_DSN` (per `data_platform/queue/repository.py:189-205` `_resolve_dsn`) or `DATABASE_URL` (per the
  test skip predicate at `tests/cycle/test_freeze_cycle_candidates.py:340-342`).
- Required setup: run the migrations in
  `data-platform/src/data_platform/ddl/migrations/0001_init.sql` →
  `0005_cycle_publish_manifest.sql` against the compose-managed PG.
- Test scaffold flow (described, not coded):
  1. `docker compose -f assembly/compose/lite-local.yaml up -d
     postgres`.
  2. Apply the 5 migration files in order.
  3. Set `DP_PG_DSN=postgresql://<...>` for both the SDK Pg adapter
     and the data-platform pytest run.
  4. Re-run `pytest -p no:cacheprovider tests/queue tests/cycle` —
     the 54 currently-skipped tests would execute.
  5. Independently exercise SDK `submit()` via PgSubmitBackend with
     the live DSN to confirm `subsystem_submit_queue` rows materialise
     (this would also expose the §3.2 INFERRED bridge gap when the
     `candidate_queue` is then queried and found empty).
- Audit-time outcome: this scaffold was NOT executed; the report
  records what would have to be wired.

### 5.2 Ex-3 → graph-engine bridge test scaffold

- Producer side: an Ex-3 payload writes to
  `data_platform.candidate_queue` via
  `data_platform.queue.api.submit_candidate(...)` (queue/api.py:10-18).
- Cycle-freeze side: `cycle/repository.py:132-191` writes the
  candidate_id into `cycle_candidate_selection` (DDL at
  `data-platform/src/data_platform/ddl/migrations/0004_cycle_candidate_selection.sql:5`).
- Consumer side (gap): a graph-engine adapter would have to read
  `cycle_candidate_selection` joined with
  `candidate_queue WHERE payload_type='Ex-3'` and feed those payloads
  into `promote_graph_deltas`
  (`graph-engine/graph_engine/__init__.py:21`,
  `graph-engine/graph_engine/providers/phase1.py:156`).
- Test scaffold flow (described): an integration test would create a
  cycle, submit one Ex-1 / Ex-2 / Ex-3 payload set, freeze the cycle,
  invoke the graph-engine adapter, and assert the
  `CandidateGraphDelta` is registered against the live snapshot — all
  inside one PG-backed transaction or a connected sequence.
- Out of scope for this audit: implementing that adapter (would change
  graph-engine source) and writing the integration test (would add new
  test code).

### 5.3 Ex-3 → reasoner bridge: identify the seam

- Seam in repo:
  `orchestrator/src/orchestrator_adapters/p2_dry_run.py:167-188`
  defines `P2ReasonerGateway` Protocol (`health_check`, world-state
  delta call, alpha analysis call); `DefaultReasonerRuntimeGateway` at
  `p2_dry_run.py:217-373` is the production adapter that wraps
  `reasoner_runtime.health_check` (line 238) and
  `reasoner_runtime.generate_structured_with_replay` (line 345).
- Existing symbol-level reader: `_load_frozen_candidate_symbols` at
  `p2_dry_run.py:1227` already executes the
  `cycle_candidate_selection JOIN candidate_queue` query for the
  current cycle but projects only `candidate_id / ts_code (or
  entity_id) / submitted_by`. The Ex-3 semantic payload sits
  untouched in the unpacked `candidate_queue.payload` (line 1239) but
  is not propagated to the reasoner gateway.
- Where Ex-3 semantic content would attach: a new payload-shaping
  helper (parallel to or extending `_load_frozen_candidate_symbols`)
  would filter `WHERE payload_type='Ex-3'`, decode the JSON body, and
  pass it as part of the `world_state_delta_request` /
  `alpha_request` context built by the reasoner gateway
  (`p2_dry_run.py:217-345`). The exact attach point depends on whether
  Ex-3 deltas should inform L4 world-state or L6 alpha (or both); per
  CLAUDE.md (subsystem-news §19), Ex-3 is the "high-threshold"
  candidate graph delta and must NOT be derived from co-occurrence /
  sentiment alone, so the reasoner needs to treat them as anchored
  graph hypotheses, not raw text.
- This audit identifies the seam location only; it does not propose
  the payload schema or change the gateway.

### 5.4 Ex-3 → frontend bridge: identify the read-only route

- The relevant route file would be
  `frontend-api/src/frontend_api/routes/graph.py` (since Ex-3 is graph
  delta material). A `rg` showed no Ex-3 / `graph_delta` reference in
  any of the existing 5 route files (`cycle.py`, `entity_data.py`,
  `graph.py`, `operations.py`, `system.py`).
- The proposed shape: a read-only `GET` route that reads
  `cycle_candidate_selection` joined with
  `candidate_queue WHERE payload_type='Ex-3'` for a given cycle and
  returns a sanitized projection (no provider lineage / no
  ingest_metadata) for the frontend to display the Ex-3-derived
  signals from a same-cycle execution.
- The C3 hardening plan (formal-serving no-source-leak) is the
  governance gate for this route — any new public-facing column would
  have to pass the prefix-token + lineage-pattern checks proposed in
  C3 before promotion. This audit does not implement the route; it
  identifies the file and the shape.

---

## 6. Findings tally

- **CONFIRMED** (code evidence read end-to-end at file+line): 4
  - 3.1 SDK → subsystem_submit_queue adapter (with the explicit
    "adapter-only, no live PG" caveat)
  - 3.3 data-platform candidate_queue operations
  - 3.4 cycle/freeze.py PG atomic semantics with verified lock
    predicate
  - 3.5 Ex-0/1/2/3 schema status across queue models + producer public
    entries
- **PARTIAL** (some evidence + clear gap): 1
  - 4.2 Live PG freeze: in-process tests pass, 54 PG-dependent tests
    skip, no live-PG smoke executed
- **INFERRED** (no in-repo evidence; absence is the finding): 4
  - 3.2 / 4.1 subsystem_submit_queue → candidate_queue bridge (no
    transfer code in either subrepo)
  - 4.3 Ex-3 → graph-engine same-cycle consumption (no reader of
    cycle_candidate_selection × payload_type='Ex-3' located)
  - 4.3 Ex-3 → reasoner-runtime same-cycle consumption (seam exists at
    `p2_dry_run.py:217-345` but no Ex-3 reader)
  - 4.3 Ex-3 → frontend-api same-cycle read-only surfacing (no
    matching route in `frontend-api/src/frontend_api/routes/`)

The prior reports
`p4-controlled-live-bridge-20260428.md` (PARTIAL) and
`p4-core-subsystem-vertical-slice-20260428.md` (PASS for the
controlled subset only) remain **NOT upgraded** by this audit.

---

## 7. Outstanding risks

- **Bridge ambiguity**: the SDK's `subsystem_submit_queue` table has
  no DDL in the data-platform migration set and no transfer code
  anywhere; whether it is meant to be replaced by direct
  `submit_candidate(...)` calls, by a future Dagster sweep op, or by
  the Full-mode Kafka path, is undocumented in code. This is the
  highest-priority closure target before the slice can be called
  production-ready.
- **Live-PG runtime evidence is zero**: 54 skipped tests in this
  audit's data-platform run; the SDK adapter uses an injected
  connection factory in every test; no docker compose was started
  during this audit. The atomic-freeze claim relies on code reading
  alone, not on observed concurrent-cycle behaviour.
- **Same-cycle Ex-3 downstream consumption is unconnected**: graph-
  engine's `promote_graph_deltas` exists, the reasoner gateway exists,
  and frontend-api routes exist, but no in-repo seam reads Ex-3
  candidates from `cycle_candidate_selection`. This bounds C4's P3 →
  P2 graph-consumption claim and bounds C1's RUNTIME_BLOCKERS
  resolution (the audit-eval / reasoner / graph-status providers all
  default fail-closed today).
- **subsystem-sdk pytest collection error**: a non-fatal cross-repo
  fixture import error
  (`tests/regression/test_with_shared_fixtures.py:37` — missing
  `audit_eval_fixtures` module) blocks `pytest tests` from completing
  cleanly. Out of scope for C5 but flagged for C1/C4 follow-up.
- **Interpreter divergence**: data-platform ships Python 3.14.3 in
  `.venv/`; subsystem-sdk ships Python 3.12.12. Cross-repo wheel
  compatibility is not in this audit's scope but should be confirmed
  before any combined live-PG smoke is wired.
- **Dirty data-platform working tree**: `src/data_platform/raw/writer.py`
  and `tests/raw/test_writer.py` are modified outside this audit's
  scope (raw zone, not candidate_queue bridge). No edits performed
  here.

---

## 8. Per-task handoff block

```
Task: C5
Repo(s): subsystem-sdk + entity-registry + subsystem-news + subsystem-announcement + data-platform + assembly
Output report: /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/p4-controlled-slice-caveat-closure-audit-20260428.md
Validation commands:
  rg -n 'subsystem_submit_queue|candidate_queue|CANDIDATE_QUEUE_TABLE' subsystem-sdk/ data-platform/src
  rg -n 'FOR UPDATE|SKIP LOCKED' data-platform/src/data_platform/cycle data-platform/src/data_platform/queue
  rg -n 'submit_queue.*candidate_queue|candidate_queue.*submit_queue' subsystem-sdk/ data-platform/src
  cd subsystem-sdk && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q tests
  cd data-platform && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -p no:cacheprovider -q tests/queue tests/cycle
Validation results:
  rg #1 (queue symbols): SDK references subsystem_submit_queue only inside subsystem-sdk; data-platform references candidate_queue only inside data-platform; no co-mention.
  rg #2 (FOR UPDATE / SKIP LOCKED): present at queue/repository.py:50, cycle/repository.py:104,120,145,336, cycle/manifest.py:145.
  rg #3 (bridge co-mention regex): no matches — bridge code absent in repo (load-bearing finding).
  pytest subsystem-sdk: 1 collection error (audit_eval_fixtures module not on PYTHONPATH); ignoring that file: 426 passed, 4 skipped.
  pytest data-platform queue+cycle: 81 passed, 54 skipped (skips are live-PG tests requiring DATABASE_URL/DP_PG_DSN).
Per-subrepo git state:
  subsystem-sdk:           rev-parse HEAD = 5f131237df9101bde0a41293df151f6f9ea47fe7; status = clean; push = not pushed (no commit by audit); interpreter = subsystem-sdk/.venv/bin/python (cpython 3.12.12)
  entity-registry:         rev-parse HEAD = a38944533a2aae2191ee07e699156453a5bf708d; status = clean; push = not pushed (no commit by audit)
  subsystem-news:          rev-parse HEAD = c27f044ebb97646fe583dfa5e1a737f62903f647; status = clean; push = not pushed (no commit by audit)
  subsystem-announcement:  rev-parse HEAD = 36555beb69ce565ee9a8d2b0f926a01158c32335; status = clean; push = not pushed (no commit by audit)
  data-platform:           rev-parse HEAD = 330f6b4d82a96d36c8fd150cc1a0a432d7c6cb9c; status =  M src/data_platform/raw/writer.py /  M tests/raw/test_writer.py (out of scope, not edited by audit); push = not pushed (no commit by audit); interpreter = data-platform/.venv/bin/python (cpython 3.14.3)
  assembly:                rev-parse HEAD = a7f19c5994f807b2cf32eb2f45ef48f6fe23095f; status = 4 untracked stabilization reports under reports/stabilization/ (incl. this one); push = not pushed (no commit by audit)
Dirty files:
  data-platform/src/data_platform/raw/writer.py (pre-existing, out of scope, untouched)
  data-platform/tests/raw/test_writer.py (pre-existing, out of scope, untouched)
  assembly/reports/stabilization/frontend-raw-route-alignment-fix-20260428.md (untracked, pre-existing)
  assembly/reports/stabilization/production-daily-cycle-gap-audit-20260428.md (untracked, pre-existing)
  assembly/reports/stabilization/project-ult-v5-0-1-supervisor-review-20260428.md (untracked, pre-existing)
  assembly/reports/stabilization/raw-manifest-source-interface-hardening-20260428.md (untracked, pre-existing)
  assembly/reports/stabilization/p4-controlled-slice-caveat-closure-audit-20260428.md (NEW — this audit's output)
Findings: 4 CONFIRMED, 1 PARTIAL, 4 INFERRED
Outstanding risks:
  - subsystem_submit_queue → candidate_queue bridge code is absent in repo; absence is the finding (highest priority before P5).
  - Live-PG runtime evidence is zero this round (54 skipped tests; no compose started).
  - Same-cycle Ex-3 downstream consumption (graph-engine / reasoner / frontend) is INFERRED gap on all three; bounds C4 P3→P2 claim and C1 RUNTIME_BLOCKERS resolution.
  - subsystem-sdk pytest collection error from missing audit_eval_fixtures (out of scope for C5; flagged for C1/C4 follow-up).
  - Interpreter divergence (subsystem-sdk 3.12.12 vs data-platform 3.14.3) needs verification before any combined live-PG smoke.
Declaration: I did not mark any PARTIAL or PREFLIGHT finding as PASS. I did not commit any forbidden files. Tushare remains a provider=tushare adapter only. I did not run `git init`. I did not push without approval.
```
