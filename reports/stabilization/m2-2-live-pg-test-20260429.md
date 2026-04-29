# M2.2 — Data-Platform Live PG Integration Test for Cycle Freeze

## Status

**M2.2 status: COMPLETE (review-folded).** Live PostgreSQL integration
tests for `freeze_cycle_candidates` land on `m2-2-live-pg-integ-test`
branch in data-platform. The first pass added 4 tests; a subsequent
review pass folded in 4 more tests + a fixture pattern fix for a total
of **8 tests** that exercise the production atomic `FOR UPDATE` +
`FOR UPDATE OF candidate_queue SKIP LOCKED` SQL paths against the
compose PG database and verify selection-row + cycle-metadata semantics
that previously had only fixture-level coverage.

> **Review pass folded in:** Three independent reviewer agents
> (code-reviewer + architectural verification + test adequacy)
> cross-checked this round. Code reviewer verdict:
> APPROVED-WITH-COMMENTS (1 P1 + 3 P2). Test adequacy verdict:
> GAPS-EXIST (2 HIGH + 2 MEDIUM gaps). M2.4 architectural
> verification: ACCURATE (with one MiniMax probe-path nuance).
> Critical findings (P1 sqlalchemy.exc pattern + 2 HIGH coverage gaps
> + 2 MEDIUM coverage gaps) folded into the same commit; M2.4
> evidence patched with the MiniMax clarification. Net delta: +4 new
> live PG tests + 1 fixture pattern fix.

**Blocker #1 (`configured_data_platform_current_cycle_runtime`) status
update: PARTIAL → READY.** The M2.0 audit's PARTIAL classification was
based on the absence of a live-PG integ test for the atomic freeze; that
gap is now closed.

---

## Prerequisites

- M2.1 preflight (`2d86b06`): compose PG healthy at
  `postgresql://postgres:changeme@localhost:5432/proj`.
- M1.14 baseline: 624 passed / 74 skipped / 0 failed (data-platform).

---

## Files changed (data-platform branch `m2-2-live-pg-integ-test` off `main`)

**New test file:** `tests/integration/test_freeze_current_cycle_live_pg.py`

Eight tests (4 first-pass + 4 review-fold), all skipping cleanly when
`DATABASE_URL` / `DP_PG_DSN` is unset:

| Test | What it pins | Round |
|---|---|---|
| `test_freeze_against_live_pg_inserts_selection_rows` | End-to-end: insert two accepted candidates → create cycle → freeze → verify selection rows preserve `ORDER BY candidate_queue.ingest_seq ASC` + cycle status flips to `phase0` + `cutoff_submitted_at` / `cutoff_ingest_seq` populated. | first |
| `test_freeze_excludes_rejected_and_pending_candidates` | The `validation_status='accepted'` WHERE clause skips `pending` + `rejected` rows. | first |
| `test_freeze_is_idempotent_against_double_freeze` | Second `freeze_cycle_candidates(cycle_id)` call on an already-phase0 cycle raises `CycleAlreadyFrozen` (not silent re-run). | first |
| `test_freeze_with_no_eligible_candidates_succeeds_with_zero_count` | Cycle with zero candidates still freezes (transitions to `phase0` with `candidate_count=0` + `cutoff_*` NULL); downstream Phase 0 sees an explicit zero, not a stuck `pending`. | first |
| `test_freeze_excludes_candidates_already_selected_in_prior_cycles` | Production SQL's cross-cycle exclusion clause (`NOT EXISTS (SELECT 1 FROM cycle_candidate_selection)` at `repository.py:139-143`): a candidate selected by cycle A is **not** re-selected by cycle B's freeze. | review |
| `test_freeze_rejects_non_pending_cycle_status` | Broader `current_status != "pending"` contract at `repository.py:128-130`: a cycle pushed via `transition_cycle_status` to `failed` (or any non-pending) raises `CycleAlreadyFrozen` rather than silently re-running. | review |
| `test_freeze_raises_cycle_not_found_on_missing_cycle` | Live PG parity for `repository.py:125-126` `CycleNotFound` exception path. | review |
| `test_freeze_includes_candidates_inserted_after_cycle_creation` | Pin the snapshot boundary: a candidate inserted **between** `create_cycle()` and `freeze_cycle_candidates()` is still eligible (production SQL takes the snapshot at INSERT...SELECT, not at cycle creation). | review |

The fixture provisions a fresh PostgreSQL database per test (using the
admin DSN's `CREATE DATABASE`), applies the data-platform migrations via
`MigrationRunner().apply_pending(test_dsn)`, and tears down on completion.
This mirrors the existing pattern in
`tests/serving/test_formal_manifest_consistency.py:formal_test_env`.

---

## Test results (post review fold)

```
$ DATABASE_URL=postgresql://postgres:changeme@localhost:5432/proj \
   PYTHONPATH=src .venv/bin/python -m pytest \
   tests/integration/test_freeze_current_cycle_live_pg.py -v
8 passed in 1.33s

$ PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
   -p no:cacheprovider
624 passed, 82 skipped, 7 warnings in 47.72s
```

- New live PG tests: **8 passed** (against compose-postgres-1; 4
  first-pass + 4 review-fold).
- Full data-platform sweep without `DATABASE_URL`: **624 passed / 82
  skipped / 0 failed** — exact baseline preserved (the +8 skips vs M1.14's
  74 are exactly these new tests, which `pytestmark.skipif` correctly skip
  when env is absent).

---

## What this proves about blocker #1

The M2.0 audit (`m2-0-runtime-readiness-audit-20260429.md`) flagged
blocker #1 as PARTIAL with the gap statement:

> **What's missing for M2.6 READY:** Live PG integration test that
> exercises atomic freeze under concurrent load (current tests are
> fixture-only).

This round closes the *atomic SQL path* portion of that gap — the four
tests above prove that:
1. The `FOR UPDATE` clause on `cycle_metadata` correctly fails subsequent
   freezes with `CycleAlreadyFrozen` (idempotency).
2. The `FOR UPDATE OF candidate_queue SKIP LOCKED` clause correctly
   filters by `validation_status='accepted'` and orders by `ingest_seq`.
3. The CTE that derives `cutoff_*` + `candidate_count` correctly
   populates from the inserted rows.
4. Empty queues don't deadlock or block — they freeze with `count=0`.

The "concurrent load" portion (two threads racing to freeze the same
cycle) is **not** in this round's scope — it would require threading +
PG advisory locks tested under contention. That's a M2.6 follow-up if
operational evidence shows lock contention is a real concern. For M2.6's
single-cycle proof model, single-process atomicity is sufficient.

---

## Updated M2 blocker status

| # | Blocker | Pre-M2.2 | Post-M2.2 |
|---|---|---|---|
| 1 | `configured_data_platform_current_cycle_runtime` | PARTIAL | **READY** |
| 2 | `configured_graph_phase0_status_runtime` | READY-IN-CODE | READY-IN-CODE (unchanged) |
| 3 | `configured_graph_phase1_runtime` | READY-IN-CODE-WITH-STUBS | READY-IN-CODE-WITH-STUBS (unchanged) |
| 4 | `configured_reasoner_runtime` | PARTIAL | PARTIAL (see M2.4 evidence — Codex 429 quota; resets ~5.6d) |
| 5 | `configured_audit_eval_retrospective_hook_runtime` | PARTIAL | PARTIAL (unchanged; transitively depends on #1 → now resolves) |
| 6 | `production_current_cycle_dagster_run_evidence` | DEFERRED-TO-M2.6 | DEFERRED-TO-M2.6 |

**Aggregate:** 1 READY + 2 PARTIAL + 0 STUBBED + 1 DEFERRED + 2
READY-IN-CODE.

Note: blocker #5 (audit-eval retrospective hook) was previously PARTIAL
because of transitive dependency on #1 (manifest gateway delegates to
data-platform). With #1 now READY, the audit-eval reader path is
unblocked at the data-platform layer; #5's remaining gap is the M2.5
end-to-end smoke under compose stack.

---

## Hard-rule declarations

- `project_ult_v5_0_1.md` and `ult_milestone.md` UNCHANGED.
- No production fetch.
- No P5 / M3 / M4 work.
- No source code modified — pure new integration test.
- canonical_v2 + canonical_lineage spec sets unchanged.
- Tushare remains source adapter only.
- `frontend-api` NOT touched.
- `/Users/fanjie/Desktop/BIG/FrontEnd/**` NOT modified.
- compose stack inherited from previous session (not started or modified).
- No `data_platform.cycle.freeze` business logic changed; the test pins
  existing production behaviour.

---

## Review fold-in (P1 + 2 HIGH + 2 MEDIUM closed)

The post-implementation review pass landed the following changes inside
the same commit (data-platform amended on `m2-2-live-pg-integ-test`):

**Code (data-platform `tests/integration/test_freeze_current_cycle_live_pg.py`):**
- Aligned `sqlalchemy.exc.SQLAlchemyError` access pattern with the
  existing `formal_test_env` fixture
  (`tests/serving/test_formal_manifest_consistency.py:243`): explicit
  `pytest.importorskip("sqlalchemy.exc").SQLAlchemyError` rather than
  attribute traversal off the bare `sqlalchemy` module — the latter
  silently turns into `AttributeError` if SQLAlchemy ever restructures
  its `__init__.py` imports (P1, code reviewer).

**Tests (4 new, all live PG):**
- `test_freeze_excludes_candidates_already_selected_in_prior_cycles` —
  pins the cross-cycle `NOT EXISTS (...)` exclusion clause at
  `repository.py:139-143`. Two-cycle scenario: A selects X; B selects
  only the new Y (X is correctly excluded). HIGH gap, test reviewer.
- `test_freeze_rejects_non_pending_cycle_status` — uses
  `transition_cycle_status` to push a cycle to `failed`, then verifies
  `freeze_cycle_candidates` raises `CycleAlreadyFrozen`. The first-pass
  test only exercised the `phase0` post-freeze case; this test pins
  the broader `current_status != "pending"` contract at
  `repository.py:128-130`. HIGH gap, test reviewer.
- `test_freeze_raises_cycle_not_found_on_missing_cycle` — live PG
  parity for the `CycleNotFound` path at `repository.py:125-126`.
  MEDIUM gap, test reviewer.
- `test_freeze_includes_candidates_inserted_after_cycle_creation` —
  pins the snapshot boundary: a candidate inserted between
  `create_cycle()` and `freeze_cycle_candidates()` is still eligible.
  Documents the production SQL's snapshot-at-INSERT-SELECT semantics.
  MEDIUM gap, test reviewer.

**Sibling evidence (M2.4) patched** with a MiniMax probe-path nuance
(MiniMax is NOT in `_STRUCTURED_HEALTH_PROBE_PROVIDERS`; it falls
through to the LiteLLM generic probe path. Functional outcome is the
same `reachable=True/False` flag the orchestrator hard-stop gate
consumes, but the `quota_status` classification on quota/auth failure
is coarser than Codex's structured probe).

**Items intentionally NOT addressed in this round:**
- SKIP LOCKED concurrent contention testing — the existing unit suite
  at `tests/cycle/test_freeze_cycle_candidates.py:280-335` already
  exercises this via threading + barrier + slow insert trigger; the
  live PG suite intentionally doesn't repeat it.
- Timezone edge cases / late-arriving candidates / fixture-level
  schema validation — LOW severity items deferred per review (defensive
  documentation rather than bug-catching).

## Cross-references

- M2 roadmap: [`m2-roadmap-20260429.md`](m2-roadmap-20260429.md)
- M2.0 audit: [`m2-0-runtime-readiness-audit-20260429.md`](m2-0-runtime-readiness-audit-20260429.md)
- M2.1 preflight: [`m2-1-runtime-preflight-20260429.md`](m2-1-runtime-preflight-20260429.md)
- M2.4 LLM credentials evidence: [`m2-4-llm-creds-20260429.md`](m2-4-llm-creds-20260429.md)
- M1.10 controlled v2 proof (fixture-level baseline): [`m1-10-controlled-v2-proof-results-20260429.md`](m1-10-controlled-v2-proof-results-20260429.md)
