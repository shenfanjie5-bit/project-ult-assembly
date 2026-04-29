# M2.6 Follow-up #1 — Real `IcebergCanonicalGraphWriter`

## Status

**M2.6 followup #1 status: COMPLETE.** Replaces the M2.3a-2
`StubCanonicalGraphWriter` (which raised `NotImplementedError` at
`graph_promotion` asset evaluation time) with a real Iceberg-backed
writer that persists `PromotionPlan.{node,edge,assertion}_records` into
three new `canonical.graph_*` Iceberg tables.

**Phase 1 graph_promotion asset is now functionally complete.** The
M2.3a-1 review identified the canonical write-back stub as the M2.6
critical-path blocker; this round closes that gap.

**Blocker #3 status update: READY-IN-CODE-WITH-STUBS → READY-IN-CODE.**
The Phase 1 stub-writer is replaced by a real implementation; the
remaining "stub" at `PlaceholderRegimeContextReader` is a propagation
multiplier policy decision (M2.6 followup #2), not a write-side
correctness gap.

---

## Prerequisites

- M2.3a-2 completed (`d271bae`/`32438a4` graph-engine,
  `1655488`/`cfeeb2f` data-platform): cross-module env factory wiring
  for Phase 1 in place; only the canonical writer was a stub.
- M2.5 verified blocker #5 round-trip end-to-end against live PG.

---

## Files changed

### data-platform (branch `m2-6f1-iceberg-canonical-graph-writer-v2`, off `m2-3a-2-phase1-adapters`)

**Modified:** `src/data_platform/ddl/iceberg_tables.py`

* New TableSpec triple in the `canonical` namespace:
  - `CANONICAL_GRAPH_NODE_SPEC` — `(node_id, canonical_entity_id, label, properties_json, cycle_id, created_at, updated_at)`
  - `CANONICAL_GRAPH_EDGE_SPEC` — `(edge_id, source_node_id, target_node_id, relationship_type, properties_json, weight, cycle_id, created_at, updated_at)`
  - `CANONICAL_GRAPH_ASSERTION_SPEC` — `(assertion_id, source_node_id, target_node_id, assertion_type, evidence_json, confidence, cycle_id, created_at)`
* Aggregated as `CANONICAL_GRAPH_PROMOTION_TABLE_SPECS` and added to
  `DEFAULT_TABLE_SPECS` (between entity_alias and canonical_v2 specs)
  so the Iceberg DDL runner creates them automatically.
* Schema fits the `_forbidden_schema_fields_for(canonical)` guard
  (no `submitted_at` / `ingest_seq` / `source_run_id` / `raw_loaded_at`).
* `properties` / `evidence` dicts serialise to JSON strings (Iceberg/
  PyArrow has no native arbitrary-key struct type).

**Modified:** `src/data_platform/cycle/graph_phase1_adapters.py`

* Replaced `StubCanonicalGraphWriter` with real
  `IcebergCanonicalGraphWriter` class. Backwards-compat alias
  `StubCanonicalGraphWriter = IcebergCanonicalGraphWriter` retained so
  any existing imports continue to work.
* `IcebergCanonicalGraphWriter`:
  - Lazy `load_catalog()` on first write (catalog connection deferred).
  - `_resolve_catalog` is thread-safe via `threading.Lock` (mirrors
    `PostgresCandidateDeltaReader._resolve_engine` pattern).
  - `write_canonical_records(plan)` converts each record list to a
    PyArrow table with explicit schema and calls `target.append(arrow)`
    on the corresponding Iceberg table.
  - Empty record lists short-circuit (no empty append).
  - Append order: node → edge → assertion (preserves referential
    intent in snapshot history if a partial-write inspection occurs).
  - Atomicity: known-non-atomic across the 3 tables; documented in the
    docstring. Phase 1's idempotent re-run pattern recovers from
    partial-write failures.
* New `_FailClosedCanonicalGraphWriter` class for environments where
  Iceberg is unavailable (mirrors orchestrator's
  `_FailClosedGraphStatusProvider` pattern).

**New tests:** `tests/cycle/test_graph_phase1_adapters.py` — 23 unit
tests now (was 15 in M2.3a-2 review-fold). +8 new tests covering:
- Stub alias resolution
- Lazy catalog initialisation in `from_env`
- Three-table append sequence
- Per-record-type Arrow schema + value pinning (node, edge, assertion)
- Empty-record-list short-circuit
- Null-target_node_id assertion handling
- Sorted-key JSON determinism for properties
- Fail-closed writer raises `RuntimeError`

**New tests:** `tests/integration/test_iceberg_canonical_graph_writer_live.py`
— 2 live Iceberg integration tests (use SQLite-backed `SqlCatalog` +
filesystem warehouse under `tmp_path`):
- `test_iceberg_canonical_graph_writer_round_trip_against_live_catalog`
  — write 1 node + 1 edge + 1 assertion via `target.append`, read back
  via `target.scan().to_arrow()`, pin row counts + values.
- `test_iceberg_writer_appends_across_two_cycles` — proves the writer
  is append-only (cycle B's row coexists with cycle A's row, no
  overwrite).

**Updated tests:** `tests/ddl/test_iceberg_tables.py` — adds the 3 new
graph specs to the `test_ensure_tables_is_idempotent` expected table
list.

### graph-engine (branch `m2-6f1-real-canonical-writer`, off `m2-3a-2-phase1-runtime-from-env`)

**Modified:** `graph_engine/providers/phase1.py`

* `build_graph_phase1_runtime_from_env` now imports
  `IcebergCanonicalGraphWriter` from data-platform (instead of the
  stub) and constructs it via `from_env()`. The lazy-import block is
  consolidated; the typed exception wrap remains.
* Docstring updated to reference the real writer.

**Updated tests:** `tests/unit/test_phase1_from_env.py` — fake module
injected via `sys.modules` monkeypatch now provides
`IcebergCanonicalGraphWriter` (matching the new import name); call-site
trace renamed accordingly.

### assembly (`m2-baseline-2026-04-29`)

**New file:** this evidence document.

---

## Test results

```
$ cd data-platform
$ PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:contracts/src .venv/bin/python -m pytest \
   -p no:cacheprovider tests/cycle/test_graph_phase1_adapters.py
23 passed in 0.45s

$ PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
   -p no:cacheprovider tests/integration/test_iceberg_canonical_graph_writer_live.py
2 passed in 1.02s

$ PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
   -p no:cacheprovider --ignore=tests/cycle/test_graph_phase1_adapters.py
626 passed, 74 skipped, 7 warnings in 47.44s

$ cd graph-engine
$ PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider
425 passed, 21 skipped, 0 failed
```

- data-platform unit tests on the new module: **23 passed** (was 15
  in M2.3a-2 review-fold).
- data-platform live Iceberg integ tests: **2 passed** (covers SQLite-
  backed catalog round-trip + 2-cycle append semantics).
- data-platform full sweep (excl. new test): **626 passed / 74 skipped
  / 0 failed** (was 624/74/0 in M1.14 baseline; +2 = 2 new live Iceberg
  tests; **0 regressions**).
- graph-engine full sweep: **425 passed / 21 skipped / 0 failed**
  (matches M2.3a-2 review-fold baseline; **0 regressions**).

---

## Updated M2 blocker status

| # | Blocker | Pre-followup-#1 | Post-followup-#1 |
|---|---|---|---|
| 1 | `configured_data_platform_current_cycle_runtime` | READY | READY (unchanged) |
| 2 | `configured_graph_phase0_status_runtime` | READY-IN-CODE | READY-IN-CODE (unchanged) |
| 3 | `configured_graph_phase1_runtime` | READY-IN-CODE-WITH-STUBS | **READY-IN-CODE** |
| 4 | `configured_reasoner_runtime` | PARTIAL (Codex 429 quota) | PARTIAL (unchanged) |
| 5 | `configured_audit_eval_retrospective_hook_runtime` | READY | READY (unchanged) |
| 6 | `production_current_cycle_dagster_run_evidence` | DEFERRED-TO-M2.6 | DEFERRED-TO-M2.6 |

**Aggregate:** 2 READY + 1 PARTIAL + 0 STUBBED + 1 DEFERRED + 2
READY-IN-CODE.

The remaining "stub" in Phase 1 is `PlaceholderRegimeContextReader`
(neutral 1.0 multipliers). That is a propagation policy choice (regime
→ multiplier business mapping) tracked as M2.6 followup #2; it does
NOT block Phase 1 graph_promotion or graph_snapshot from running
end-to-end, since neutral 1.0 multipliers preserve the existing
graph-engine test contract (cf. `StaticRegimeReader`).

---

## What this unlocks for M2.6

Pre-followup-#1: invoking `daily_cycle_job.execute_in_process(...)`
would have halted at the Phase 1 `graph_promotion` asset's call to
`canonical_writer.write_canonical_records(plan)` with
`NotImplementedError`. Phase 2 / Phase 3 / Audit-eval would then
cascade-skip per Dagster's upstream-failure semantics, and M2.6's
"15 asset materialisations" exit criterion would not be reachable.

Post-followup-#1: Phase 1 graph_promotion produces real
`canonical.graph_*` Iceberg snapshots; Phase 1 graph_snapshot reads
those snapshots; Phase 2 (canonical input loaders) consumes them; the
chain proceeds through Phase 3 + audit-eval. M2.6 daily-cycle proof is
**newly viable** assuming blocker #4 (LLM credentials) is resolved
(currently Codex 429 quota).

---

## Hard-rule declarations

- `project_ult_v5_0_1.md` and `ult_milestone.md` UNCHANGED.
- No P5 / M3 / M4 work.
- No production fetch.
- canonical_v2 + canonical_lineage spec sets unchanged (this round
  adds 3 specs to `canonical` namespace, not to v2 or lineage).
- Tushare remains source adapter only.
- `frontend-api` NOT touched.
- `/Users/fanjie/Desktop/BIG/FrontEnd/**` NOT modified.
- compose stack inherited; not started or modified.
- data-platform CLAUDE.md respected: data-platform OWNs canonical
  storage; the writer adheres to that ownership boundary. graph-engine
  produces records; data-platform persists them. No cross-module
  business-logic leakage.
- graph-engine CLAUDE.md respected: graph-engine does not reverse-
  import data-platform internals (only public adapter classes via the
  lazy-import in `phase1.py`).

---

## Cross-references

- M2 roadmap: [`m2-roadmap-20260429.md`](m2-roadmap-20260429.md)
- M2.0 audit (blocker #3 stub identification): [`m2-0-runtime-readiness-audit-20260429.md`](m2-0-runtime-readiness-audit-20260429.md)
- M2.3a-1 review (architectural-drift critique that flagged Phase 1
  stub-writer + identified follow-up #1):
  [`m2-3a-1-impl-20260429.md`](m2-3a-1-impl-20260429.md)
- M2.3a-2 (where StubCanonicalGraphWriter landed as the typed Protocol-
  satisfying placeholder): [`m2-3a-2-impl-20260429.md`](m2-3a-2-impl-20260429.md)
- M2.5 (sibling round closing blocker #5): [`m2-5-audit-eval-roundtrip-20260429.md`](m2-5-audit-eval-roundtrip-20260429.md)

## Recommended next round

| Option | Scope | Effort | Unlocks |
|---|---|---|---|
| **review** M2.6 followup #1 | reviewer agents | 5-10 min | catches design / coverage gaps before lock-in |
| M2.6 followup #2 — real `WorldStateRegimeContextReader` | main-core regime → multipliers business mapping (needs PM decision) | 0.5-1 round (post-decision) | tightens propagation correctness (functional but not blocking) |
| Wait for Codex quota reset (~5.6d) → run **M2.6** | full daily-cycle one-shot proof | 1 round | M2 closure + P5 unblock |

`m2-baseline-2026-04-29` continues to accumulate evidence; M2 is now
**1 PARTIAL away from full code-side readiness** (blocker #4 is
operationally limited by Codex quota).

---

## Post-review fold-in (M2.6f1.r1)

After the initial M2.6 followup #1 commits landed, **3 reviewer agents**
(python-reviewer / database-reviewer / code-reviewer) ran in parallel
and surfaced 3 P1 + 5 P2 findings. All actionable findings folded into
the same `m2-6f1-iceberg-canonical-graph-writer-v2` branch (data-
platform). Below is the disposition.

### P1-A — Append-only writer with no idempotency enforcement

**Reviewer:** database-reviewer
**Risk:** Phase 1 retry after a partial failure would duplicate node /
edge / assertion rows; no read-side filter enforcement either.
**Fix applied:** writer switched from
`target.append(arrow)` to
`target.overwrite(arrow, overwrite_filter=EqualTo("cycle_id", plan.cycle_id))`.
Re-running the same cycle's plan now atomically replaces the prior
cycle's slice rather than accumulating duplicates. Cross-cycle writes
still accumulate (verified by the renamed
`test_iceberg_writer_writes_distinct_cycles_without_overwriting_each_other`).
**API probe:** confirmed `pyiceberg 0.11.1` `overwrite()` with row-
filter works on `SqlCatalog` (probe in
`assembly/tmp-runtime/m2-6f1-r1/probe_overwrite_filter.py`-equivalent
script run pre-implementation; result: row-level idempotency works as
expected, with a pyiceberg internal UserWarning on the first overwrite
of an empty table — cosmetic only).
**New tests:**
* `test_iceberg_writer_overwrite_filter_pins_cycle_id` (unit) —
  asserts the overwrite filter is `EqualTo("cycle_id", cycle_id)` with
  the plan's exact `cycle_id` value, on each of the 3 tables.
* `test_iceberg_writer_is_idempotent_across_two_runs_of_same_cycle`
  (live integration) — writes the same plan twice, asserts each table
  has exactly 1 row after both writes.

### P1-B — Timestamp tz-naive on graph specs

**Reviewer:** database-reviewer
**Risk:** PyArrow accepts tz-aware datetimes into a tz-naive
`pa.timestamp("us")` field via silent coercion in current versions;
stricter PyArrow versions or a PostgreSQL-backed Iceberg catalog
enforcing `timestamptz` would reject. Live integration test fixtures
were already passing tz-aware datetimes — drift was latent.
**Fix applied:** new `GRAPH_TIMESTAMP_TYPE = pa.timestamp("us", tz="UTC")`
in `iceberg_tables.py`, applied to the 3 graph specs only. Existing
`TIMESTAMP_TYPE` (tz-naive) unchanged for `canonical_entity` /
`entity_alias` / `canonical_v2.*` / `canonical_lineage.*` to avoid a
catalog-wide migration; harmonising the entire family is a separate
`canonical-timestamp-tz` round.
**Test side:** unit test `_now()` updated to return
`datetime(..., tzinfo=timezone.utc)` to match the new schema (was
tz-naive — the drift the reviewer flagged).

### P1-C — Writer inline schema duplicated `TableSpec`

**Reviewer:** database-reviewer
**Risk:** Two sources of truth — if `TableSpec` evolves a column, the
writer's inline `pa.schema(...)` would silently drift and only fail
at append time against the already-created Iceberg table.
**Fix applied:** all three `_node_records_to_arrow` /
`_edge_records_to_arrow` / `_assertion_records_to_arrow` helpers now
import the corresponding `CANONICAL_GRAPH_*_SPEC` and reference
`spec.schema` directly. Lazy import keeps module-load behaviour
unchanged.

### P2-1 — `StubCanonicalGraphWriter` exported via `__all__`

**Reviewers:** python-reviewer + database-reviewer + code-reviewer
(unanimous)
**Risk:** A name containing "Stub" that resolves to the production
`IcebergCanonicalGraphWriter` is misleading via `from module import *`.
**Fix applied:** removed from `__all__`. The module-level alias is
retained for direct-name imports (M2.3a-2 callers), with a comment
pointing new code at `IcebergCanonicalGraphWriter` /
`_FailClosedCanonicalGraphWriter`.

### P2-2 — Bare `list` type hints on writer helpers

**Reviewer:** python-reviewer
**Fix applied:** `records: list` → `records: list[Any]` on all three
`_*_records_to_arrow` helpers (specific record types live in
graph-engine and would create a reverse-import; `Any` is the correct
boundary placeholder per the data-platform CLAUDE.md ownership rules).

### P2-3 — No test for partial-write exception propagation

**Reviewers:** code-reviewer + database-reviewer
**Fix applied:** new
`test_iceberg_writer_partial_write_exception_propagates_after_first_table`
unit test injects a catalog whose graph_edge `overwrite()` raises;
asserts the exception propagates, asserts graph_node was already
overwritten before the failure, asserts graph_assertion was not
attempted. This pins the recovery contract: the cycle-scoped overwrite
on retry replaces the partial state cleanly.

### P2-4 — Duplicate fake dataclass definitions across unit + integration

**Reviewer:** python-reviewer
**Risk:** Already drifted: integration test passed `tzinfo=UTC`, unit
test passed naive datetime — a real bug surface.
**Fix applied:** new `tests/_graph_promotion_fakes.py` (added `tests`
to `pythonpath` in `pyproject.toml`) defines `FakeNodeRecord` /
`FakeEdgeRecord` / `FakeAssertionRecord` / `FakePromotionPlan` once.
Both unit and integration tests now import the same definitions
(aliased to `_FakeXxx` at the call site to keep the leading-underscore
private-test-helper signal). Helper factories (`_node_record` /
`_edge` etc.) stay local to each test file since fixture shapes
diverge by intent.

### P2-5 — `partition_by=["cycle_id"]` on graph specs

**Reviewer:** database-reviewer
**Probe result:** `_identity_partition_spec` calls
`pyiceberg.io.pyarrow.pyarrow_to_schema()` which raises
`"Parquet file does not have field-ids and the Iceberg table does not
have 'schema.name-mapping.default' defined"` on a `pa.schema(...)`-built
PyArrow schema — same constraint that already deferred
`partition_by=["trade_date"]` on `canonical_v2.fact_*` (cf.
`iceberg_tables.py` L301-304).
**Fix applied:** `partition_by=None` retained on all 3 graph specs;
inline NOTE comments on each spec explicitly cite the deferral cause
and reference the `canonical_v2.fact_*` precedent. A future
`canonical-partition-strategy` round can add field-id mapping for the
whole canonical family in one pass; the scan-side cost is acceptable
at M2.6 daily-cycle volumes (one cycle's rows per scan).

### Test results post fold-in

```
$ cd data-platform
$ PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:contracts/src .venv/bin/python -m pytest \
   -p no:cacheprovider tests/cycle/test_graph_phase1_adapters.py
25 passed in 0.50s   (was 23 — added overwrite_filter_pins_cycle_id +
                      partial_write_exception_propagates_after_first_table)

$ PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:contracts/src .venv/bin/python -m pytest \
   -p no:cacheprovider tests/integration/test_iceberg_canonical_graph_writer_live.py
3 passed, 3 warnings in 0.62s   (was 2 — added is_idempotent_across_two_runs_of_same_cycle;
                                 the warnings are pyiceberg's internal
                                 "Delete operation did not match any records" on
                                 first overwrite of an empty table — cosmetic)

$ PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:contracts/src .venv/bin/python -m pytest \
   -p no:cacheprovider
654 passed, 73 skipped, 10 warnings in 46.33s   (was 626/74/0;
                                                 +28 = 25 cycle adapters + 3 live
                                                 integration tests now collected
                                                 here, **0 regressions**)

$ cd graph-engine
$ PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider
425 passed, 21 skipped in 0.84s   (matches M2.3a-2 / M2.6f1 baseline; **0 regressions**)
```

### Files changed (post-fold-in)

* `data-platform/src/data_platform/cycle/graph_phase1_adapters.py` —
  `IcebergCanonicalGraphWriter.write_canonical_records` switched to
  cycle-scoped `target.overwrite(...)`; `_*_records_to_arrow` helpers
  reference `CANONICAL_GRAPH_*_SPEC.schema`; bare-`list` hints fixed;
  `__all__` no longer exports `StubCanonicalGraphWriter`.
* `data-platform/src/data_platform/ddl/iceberg_tables.py` — new
  `GRAPH_TIMESTAMP_TYPE = pa.timestamp("us", tz="UTC")` applied to 3
  graph specs; `partition_by` deferral notes added.
* `data-platform/tests/_graph_promotion_fakes.py` — new shared module
  hosting `FakeNodeRecord` / `FakeEdgeRecord` / `FakeAssertionRecord` /
  `FakePromotionPlan` for both unit + integration test suites.
* `data-platform/tests/cycle/test_graph_phase1_adapters.py` —
  `_FakeIcebergTable.overwrite()` records `(arrow, filter)` pairs;
  `_now()` returns tz-aware datetime; 7 existing writer assertions
  switched from `appended` to `overwritten`; +2 new tests
  (`overwrite_filter_pins_cycle_id`,
  `partial_write_exception_propagates_after_first_table`); imports
  shared fakes.
* `data-platform/tests/integration/test_iceberg_canonical_graph_writer_live.py`
  — renamed `appends_across_two_cycles` →
  `writes_distinct_cycles_without_overwriting_each_other` (semantics
  clarified); +1 new test
  `is_idempotent_across_two_runs_of_same_cycle`; imports shared fakes.
* `data-platform/pyproject.toml` — `pythonpath` extended to
  `["src", "tests"]` to enable the shared fakes module.
* `assembly/reports/stabilization/m2-6-followup-1-canonical-graph-writer-20260429.md`
  — this Post-review fold-in section.

### Reviewer false-alarm dispositions (deep-verified, no fix needed)

* python-reviewer P1: `target_node_id` not explicitly `nullable=True`
  in the assertion spec/writer. Verified PyArrow `pa.field()` defaults
  to `nullable=True`, the test for null target_node_id passes, and the
  schema contract validator (`_schema_field_contract`) compares
  nullable flags symmetrically. code-reviewer self-retracted the same
  finding upon further inspection. **Disposition:** P2 polish at most
  (explicitness only); not folded.
* code-reviewer expressed asymmetry concern about
  `_FailClosedCanonicalGraphWriter` being private (no `__all__` entry)
  while the `StubCanonicalGraphWriter` alias was public. The fold-in
  removes `StubCanonicalGraphWriter` from `__all__`, resolving the
  asymmetry by demoting the alias rather than promoting the
  fail-closed class. The fail-closed class remains the explicit
  fail-closed surface; orchestrator can construct it via the typed
  exception path in `phase1.py`.

### Aggregate M2 readiness (unchanged from M2.6f1 pre-fold)

| # | Blocker | Status |
|---|---|---|
| 1 | `configured_data_platform_current_cycle_runtime` | READY |
| 2 | `configured_graph_phase0_status_runtime` | READY-IN-CODE |
| 3 | `configured_graph_phase1_runtime` | **READY-IN-CODE** (now with idempotent re-run + tz-aware timestamps) |
| 4 | `configured_reasoner_runtime` | PARTIAL (Codex 429 quota) |
| 5 | `configured_audit_eval_retrospective_hook_runtime` | READY |
| 6 | `production_current_cycle_dagster_run_evidence` | DEFERRED-TO-M2.6 |

The Phase 1 graph_promotion asset's write semantics are now harder to
break: a re-run produces the same final state as a single run, and
catalog-side timezone enforcement is satisfied. M2.6 readiness is
unchanged in the count, **strengthened in the contract**.
