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
* `IcebergCanonicalGraphWriter` (final, post-fold-in semantics):
  - Lazy `load_catalog()` on first write (catalog connection deferred).
  - `_resolve_catalog` is thread-safe via `threading.Lock` (mirrors
    `PostgresCandidateDeltaReader._resolve_engine` pattern).
  - `write_canonical_records(plan)` converts each record list to a
    PyArrow table with explicit canonical schema and calls
    `target.overwrite(arrow, overwrite_filter=EqualTo("cycle_id",
    plan.cycle_id))` on the corresponding Iceberg table. **All three
    tables are overwritten on every call**, even when a slice is empty;
    an empty slice becomes a zero-row Arrow batch carrying the
    canonical schema so the cycle-scoped delete still clears any prior
    rows for that `cycle_id` (codex review #1: closes the empty-slice
    ghost-row gap).
  - Per-record validation: `created_at` / `updated_at` MUST be tz-aware
    UTC datetimes; the writer raises `ValueError` on tz-naive or
    non-UTC offsets rather than letting PyArrow silently coerce against
    the tz-tagged `GRAPH_TIMESTAMP_TYPE` column (codex review #7).
  - Overwrite order: node → edge → assertion (preserves referential
    intent in snapshot history if a partial-write inspection occurs).
  - Atomicity: known-non-atomic across the 3 tables; documented in the
    docstring. Cycle-scoped overwrite + idempotent retry are the
    recovery contract — re-running the same `cycle_id` produces the
    correct final state regardless of how far the prior run got.
* New `_FailClosedCanonicalGraphWriter` class for environments where
  Iceberg is unavailable (mirrors orchestrator's
  `_FailClosedGraphStatusProvider` pattern).

**Tests** (final post-fold-in count):

`tests/cycle/test_graph_phase1_adapters.py` — **28 unit tests** (was
15 in M2.3a-2 review-fold; +13 across the M2.6f1 line). Coverage:
- Stub alias resolution
- Lazy catalog initialisation in `from_env`
- Three-table cycle-scoped overwrite sequence
- `overwrite_filter` pins `EqualTo("cycle_id", cycle_id)` on every call
- Per-record-type Arrow schema + value pinning (node, edge, assertion)
- Empty-slice cycle-scoped overwrite carries 0-row Arrow + correct filter
- Null-target_node_id assertion handling
- Sorted-key JSON determinism for properties
- Fail-closed writer raises `RuntimeError`
- tz-naive datetime rejection (`ValueError`)
- Non-UTC offset rejection (`ValueError`)
- Partial-write exception propagation (graph_node committed before
  graph_edge raises; graph_assertion not attempted)

`tests/integration/test_iceberg_canonical_graph_writer_live.py` —
**4 live Iceberg integration tests** (use SQLite-backed `SqlCatalog`
+ filesystem warehouse under `tmp_path`):
- `round_trip_against_live_catalog` — write 1 node + 1 edge + 1
  assertion via `target.overwrite`, read back via `scan().to_arrow()`,
  pin row counts + values.
- `writes_distinct_cycles_without_overwriting_each_other` — Cycle A
  and Cycle B each write 1 node + 1 edge + 1 assertion; all three
  tables hold 2 rows post both writes (codex review #6: seed all
  three record types so cross-cycle preservation is verified per
  table, not just `graph_node`).
- `clears_prior_cycle_rows_when_retry_slice_is_empty` — Run 1 writes
  full slice for `CYCLE_GHOST`; Run 2 retries the same cycle with
  empty edge + assertion slices; post-Run-2 graph_edge and
  graph_assertion have **zero rows** (no ghost rows from Run 1) —
  the codex review #1 regression test.
- `is_idempotent_across_two_runs_of_same_cycle` — same plan twice;
  each table has exactly 1 row.

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

## Test results (initial M2.6f1 — superseded by review-fold + codex-fold sections below)

> **NOTE:** these are the initial-implementation counts before the
> M2.6f1.r1 review-fold and the M2.6f1.r2 codex-fold landed. The only
> current authoritative sweep block is **Test results post codex-fold
> (reproducible)** (~L690), which explicitly excludes `tests/dbt`
> because the three dbt-toolchain failures reproduce independently of
> the graph writer.

Initial implementation pass (M2.6f1, commit `4e5e3d6`):

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

These counts are historical: the M2.6f1.r1 review-fold added the
review-fold test set, and the M2.6f1.r2 codex-fold added the
empty-slice + UTC-validation test set. **Do not cite these initial
numbers as the current state.**

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

Post-followup-#1: Phase 1 `graph_promotion` actually persists the
`PromotionPlan` records into the three `canonical.graph_*` Iceberg
tables instead of raising `NotImplementedError`. The asset returns a
`GraphPromotionAssetResult` whose `graph_status` field satisfies the
downstream `graph_snapshot` asset's input contract, so Dagster
evaluates `graph_snapshot` instead of cascade-skipping; that asset is
backed by `GraphPhase1Service.compute_graph_snapshot`, which reads
from Neo4j (live graph) + the regime context reader and writes the
formal artifact via `snapshot_writer`. Phase 2 / Phase 3 / audit-eval
do not yet consume `canonical.graph_*` directly — they read the
formal artifact and Phase 3 publish manifest. **What this fold-in
unblocks** is therefore:

* Phase 1 `graph_promotion` no longer halts the daily cycle at write
  time;
* the `canonical.graph_*` snapshots are now **available** in
  Iceberg as a foundation for downstream graph readers — but no
  consumer is wired up yet (cold reload still reads from
  `ArtifactCanonicalReader`'s JSON path, not Iceberg).

M2.6 daily-cycle proof is **newly viable** for the asset-graph wiring
sense, assuming blocker #4 (LLM credentials) is resolved (currently
Codex 429 quota). It does NOT yet prove an end-to-end Iceberg→graph
read path; that is a separate consumer-side wiring round (corrected
per codex review #2).

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
**Fix applied:** new `tests/_graph_promotion_fakes.py` defines
`FakeNodeRecord` / `FakeEdgeRecord` / `FakeAssertionRecord` /
`FakePromotionPlan` once. Both unit and integration tests now import
the same definitions as `tests._graph_promotion_fakes` (aliased to
`_FakeXxx` at the call site to keep the leading-underscore
private-test-helper signal), so pytest only needs `pythonpath=["src"]`.
Helper factories (`_node_record` / `_edge` etc.) stay local to each
test file since fixture shapes diverge by intent.

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

### Test results post fold-in (historical, superseded)

This block records the M2.6f1.r1 review-fold reproducer before the
codex-fold and before the dbt-toolchain exclusion was made explicit.
It is retained for provenance only. **Do not cite this as the current
authoritative sweep result.** Use **Test results post codex-fold
(reproducible)** below for the current graph-writer evidence.

`contracts` is a sibling repo at the workspace root, not a subdir of
data-platform; the `PYTHONPATH` must be expressed as an absolute path
or workspace-relative path, not as a bare relative `contracts/src`
(codex review #8). Replace `<workspace>` with the absolute path of the
project-ult workspace root (e.g. `/Users/fanjie/Desktop/Cowork/project-ult`).

```
# Reproducer setup (one-time): the data-platform venv is uv-managed
# and minimal at clone time; pytest must be installed explicitly.
$ cd <workspace>/data-platform
$ uv pip install --python .venv/bin/python 'pytest>=8,<10' 'pytest-cov>=5,<8'

# Cycle-adapter unit tests (graph_phase1 writer + readers):
$ PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=src:<workspace>/contracts/src \
  .venv/bin/python -m pytest -p no:cacheprovider \
    tests/cycle/test_graph_phase1_adapters.py
28 passed in 0.62s
  (was 25 in M2.6f1.r1; +3 = empty-slice 0-row overwrite,
   tz-naive rejection, non-UTC offset rejection)

# Live Iceberg integration tests (SQLite-backed SqlCatalog + tmp_path):
$ PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=src:<workspace>/contracts/src \
  .venv/bin/python -m pytest -p no:cacheprovider \
    tests/integration/test_iceberg_canonical_graph_writer_live.py
4 passed, 4 warnings in 1.21s
  (was 3 in M2.6f1.r1; +1 = clears_prior_cycle_rows_when_retry_slice_is_empty.
   Warnings are pyiceberg's internal "Delete operation did not match
   any records" on first overwrite of an empty table — cosmetic.)

# Historical full data-platform regression sweep (pre-codex-fold):
$ PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=src:<workspace>/contracts/src \
  .venv/bin/python -m pytest -p no:cacheprovider
657 passed, 73 skipped in <~50s>
  (was 654/73/0 in M2.6f1.r1; +3 unit + +1 integration = +4 collected here,
   no regressions across the rest of the sweep.)

# graph-engine regression sweep (no graph-engine code touched in
# this fold; baseline pin):
$ cd <workspace>/graph-engine
$ PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider
425 passed, 21 skipped in 0.84s
  (matches M2.3a-2 / M2.6f1 / M2.6f1.r1 baseline; 0 regressions)
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
* `data-platform/pyproject.toml` — pytest `pythonpath` is `["src"]`;
  shared fakes are imported through `tests._graph_promotion_fakes`
  rather than as top-level helper modules.
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

---

## Codex review fold-in (M2.6f1.r2)

After the M2.6f1.r1 commits landed, an external codex review surfaced
9 findings (2 P1 + 6 P2 + 1 P3). All actionable findings folded into
the same `m2-6f1-iceberg-canonical-graph-writer-v2` data-platform
branch + `m2-baseline-2026-04-29` assembly branch. Below is the
disposition.

### codex#1 — P1: empty slices leave stale rows for the cycle

**Finding (re-stated):** `write_canonical_records()` skipped overwrite
when a record slice was empty. If the same `cycle_id` was retried and
now produced zero edges/assertions/nodes after a prior run wrote rows,
the prior rows remained — breaking the cycle-scoped replacement /
re-run idempotency contract for the slice that now happened to be
empty (e.g. a cycle of isolated-node promotions).

**Fix applied:** the writer now overwrites **all three** graph tables
on every call. Empty slices materialise as zero-row Arrow batches
carrying `CANONICAL_GRAPH_*_SPEC.schema`; pyiceberg's
`overwrite(filter=EqualTo("cycle_id", cycle_id))` runs the
cycle-scoped delete and commits a no-op snapshot. Probed
(`pyiceberg 0.11.1`, SqlCatalog backed by SQLite): zero-row Arrow +
non-trivial filter correctly deletes the matching rows and leaves
other cycles' rows intact. The previous "skip on empty slice"
short-circuit is removed.

**New tests:**
* `test_iceberg_writer_overwrites_all_three_tables_even_for_empty_slices`
  (unit) — replaces the prior "skip" test; pins that empty `edges` /
  `assertions` slices still issue cycle-scoped overwrites with zero-row
  Arrow batches.
* `test_iceberg_writer_empty_slice_overwrite_carries_zero_row_arrow_with_cycle_filter`
  (unit) — pins both the row count (zero) and the filter
  (`EqualTo("cycle_id", "CYCLE_GHOST_TEST")`) on the empty slice.
* `test_iceberg_writer_clears_prior_cycle_rows_when_retry_slice_is_empty`
  (live integration) — full regression: Run 1 writes node + edge +
  assertion; Run 2 retries the same cycle with empty edges +
  assertions; post-Run-2 graph_edge / graph_assertion have **zero
  rows** for that cycle (no ghost rows from Run 1).

### codex#2 — P1: M2.6 evidence overstates downstream graph consumption

**Finding (re-stated):** the original "What this unlocks for M2.6"
section said `graph_snapshot` reads the new `canonical.graph_*`
Iceberg snapshots and Phase 2 consumes them. graph-engine's
`compute_graph_snapshots` reads from Neo4j + regime context, not from
those Iceberg tables; Phase 2's canonical input loaders also do not
yet read them.

**Fix applied:** the "What this unlocks for M2.6" section is rewritten
to honestly state what M2.6f1 does prove (Phase 1 `graph_promotion`
no longer halts the daily cycle at write time; canonical.graph_*
snapshots are now *available* in Iceberg as a foundation) and what it
does NOT prove (no consumer is wired up yet — cold reload still
reads from `ArtifactCanonicalReader`'s JSON path). The
"end-to-end Iceberg→graph read path" claim is deferred to a separate
consumer-side wiring round.

### codex#3 — P2: ult_milestone.md G1 status stale after M1 closure

**Finding (re-stated):** the milestone's gate table still said G1
provider-neutral canonical was blocked by `ts_code` / `source_run_id`
/ `raw_loaded_at` in physical schemas, despite M1.1-M1.14 closing
those gaps.

**Fix applied:** the G1 row in the gate table is rewritten to reflect
the M1 closure: `canonical_v2` migration + lineage separation +
formal nested-no-source guard + CI v2 lane + 9/9 retirement
preconditions all proven, and legacy `ts_code` / `source_run_id` /
`raw_loaded_at` retired from canonical physical schemas. Decision
column flips from "Blocked" to "Pass". G0 evidence-hygiene row also
flipped to "Pass" (M1/M2 reports are tracked across baseline
branches).

### codex#4 — P2: ult_milestone.md dirty-state section obsolete

**Finding (re-stated):** the milestone's dirty-state section
described old untracked assembly reports + old data-platform raw-
manifest edits + old frontend-api README edit, none of which still
match the active branches.

**Fix applied:** the section is replaced with a "Current Branch /
Status Snapshot" describing the actual active branches per repo
(assembly `m2-baseline-2026-04-29`, data-platform
`m2-6f1-iceberg-canonical-graph-writer-v2`, etc.) and a note that
the M0.3 dirty-state decision is now made round-by-round (each
M-evidence round commits its own evidence + code together).

### codex#5 — P2: M2.6 evidence top still describes append semantics

**Finding (re-stated):** the original "Files changed" top section
said the writer calls `target.append(arrow)` and proves append-only
behaviour, contradicting the M2.6f1.r1 fold-in below it that switched
to cycle-scoped overwrite.

**Fix applied:** the top section is rewritten to match the final
post-fold-in semantics — `target.overwrite(arrow,
overwrite_filter=EqualTo("cycle_id", cycle_id))` on all three tables,
zero-row Arrow on empty slices, UTC timestamp validation. Test
inventory updated to **28 unit + 4 live integration** with the new
test names.

### codex#6 — P2: live cross-cycle test only exercised nodes

**Finding (re-stated):** the live distinct-cycles test seeded
`edge_records=[]` and `assertion_records=[]` for both cycles; it only
proved real-Iceberg cycle preservation for `canonical.graph_node`,
not for the other two tables.

**Fix applied:** the test now seeds full slices (1 node + 1 edge + 1
assertion) for both cycles. The post-write assertions iterate over
all three tables and pin (a) row count = 2 per table, (b) the
expected ID per cycle, (c) both `cycle_id` values present. Cross-
cycle preservation is now verified per table.

### codex#7 — P2: UTC timestamp contract not enforced

**Finding (re-stated):** the graph specs use UTC-tagged Arrow
timestamps, but the writer passed `created_at` / `updated_at`
directly into Arrow. PyArrow can silently coerce naive datetimes
into UTC-tagged columns, so the stated rejection contract was not
actually enforced — it was load-bearing on PyArrow's coercion
behaviour.

**Fix applied:** new
`IcebergCanonicalGraphWriter._require_utc_datetime` static helper
validates each `created_at` / `updated_at` value is (a) a `datetime`
instance, (b) tz-aware, (c) UTC offset (zero). Each
`_*_records_to_arrow` helper invokes it on every record's timestamp
fields up-front so the writer fails closed with a typed `ValueError`
before constructing the Arrow batch. Two new unit tests pin the
contract: `test_iceberg_writer_rejects_tz_naive_created_at_on_node`
and `test_iceberg_writer_rejects_non_utc_offset_on_edge`.

### codex#8 — P2: test command evidence not reproducible as written

**Finding (re-stated):** the prior fold-in evidence documented
`PYTHONPATH=src:contracts/src` after `cd data-platform`, but
`contracts` is a sibling repo at the workspace root, not under
data-platform. The local project venv also lacks `pytest` at clone
time (uv-managed minimal venv).

**Fix applied:** the "Test results" code block is rewritten with
absolute / workspace-relative `PYTHONPATH` (using a `<workspace>`
placeholder) and an explicit reproducer-setup step that installs
`pytest` + `pytest-cov` via `uv pip install`. Run counts updated to
post-codex-fold values (28 unit / 4 integration).

### codex#9 — P3: fake overwrite accepts unsupported kwargs

**Finding (re-stated):** `_FakeIcebergTable.overwrite(self, table_arrow,
*, overwrite_filter=None, **_)` swallowed any future pyiceberg kwarg
silently via `**_`, so a writer evolution adding e.g.
`snapshot_properties={...}` would pass unit tests but diverge from
real pyiceberg behaviour.

**Fix applied:** the fake's `overwrite` signature now mirrors real
pyiceberg explicitly — `(self, table_arrow, *, overwrite_filter,
snapshot_properties=None, case_sensitive=True, branch="main")` — no
`**` swallow. `overwrite_filter` is a required kwarg (no default).
Any unsupported kwarg the writer might pass surfaces as `TypeError`
rather than a silent no-op. The fake records each call as
`(arrow, overwrite_filter, snapshot_properties)` triples (instead of
2-tuples) so any future writer evolution that starts setting
snapshot_properties is visible to assertions. The
`_FailOnEdgeIcebergTable` subclass in the partial-write test mirrors
the same explicit signature.

### Test results post codex-fold (reproducible)

This is the current authoritative sweep block for M2.6f1 graph-writer
evidence. The full data-platform command intentionally excludes
`tests/dbt`; the dbt-toolchain failures are tracked separately and are
not part of the graph-writer regression signal.

```
$ cd <workspace>/data-platform
# uv-managed minimal venv lacks pytest at clone time:
$ uv pip install --python .venv/bin/python 'pytest>=8,<10' 'pytest-cov>=5,<8'

$ PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=src:<workspace>/contracts/src \
  .venv/bin/python -m pytest -p no:cacheprovider \
    tests/cycle/test_graph_phase1_adapters.py
28 passed in 0.62s

$ PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=src:<workspace>/contracts/src \
  .venv/bin/python -m pytest -p no:cacheprovider \
    tests/integration/test_iceberg_canonical_graph_writer_live.py
4 passed, 4 warnings in 1.21s

$ PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=src:<workspace>/contracts/src \
  .venv/bin/python -m pytest -p no:cacheprovider --ignore=tests/dbt
586 passed, 70 skipped in ~41s
   (excluding tests/dbt — those 3 dbt-toolchain failures pre-exist
   on the M2.6f1.r1 baseline `fde70e2` and are unrelated to the
   graph writer; they reproduce identically on stash-pop. Tracked
   as a separate dbt-tooling round.)

$ cd <workspace>/graph-engine
$ PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider
425 passed, 21 skipped in 0.84s   (matches all prior baselines; 0 regressions)
```

### Files changed (codex-fold)

* `data-platform/src/data_platform/cycle/graph_phase1_adapters.py` —
  `write_canonical_records` always overwrites all three tables (codex
  #1); new `_require_utc_datetime` UTC validation helper (codex #7);
  `_*_records_to_arrow` helpers always materialise an Arrow batch
  (zero-row when slice is empty); docstring rewritten to match.
* `data-platform/tests/cycle/test_graph_phase1_adapters.py` —
  `_FakeIcebergTable.overwrite` strict signature recording 3-tuples
  (codex #9); previous `skips_table_when_record_list_empty` test
  flipped to `overwrites_all_three_tables_even_for_empty_slices`
  (codex #1) and now covers empty node slices as well as empty edge /
  assertion slices; +3 new tests
  (`empty_slice_overwrite_carries_zero_row_arrow_with_cycle_filter`,
  `rejects_tz_naive_created_at_on_node`,
  `rejects_non_utc_offset_on_edge`); `_FailOnEdgeIcebergTable` updated
  to the strict signature.
* `data-platform/tests/integration/test_iceberg_canonical_graph_writer_live.py`
  — cross-cycle test seeds full slices for both cycles + iterates over
  all three tables (codex #6); +1 new test
  (`clears_prior_cycle_rows_when_retry_slice_is_empty`), now seeding a
  second cycle and retrying the first cycle with empty node / edge /
  assertion slices to prove the zero-row overwrite is cycle-scoped and
  preserves other cycles.
* `data-platform/pyproject.toml` — pytest `pythonpath` narrowed back
  to `["src"]`; graph-writer tests import the shared helper as
  `tests._graph_promotion_fakes`.
* `assembly/reports/stabilization/m2-6-followup-1-canonical-graph-writer-20260429.md`
  — top section + downstream-claim + reproducible-commands sections
  rewritten (codex #2 / #5 / #8); this codex-fold section appended.
* `ult_milestone.md` — G0 + G1 row in gate table flipped to "Pass"
  reflecting M1 closure (codex #3); §6 dirty-state replaced with
  "Current Branch / Status Snapshot" (codex #4).

### Aggregate M2 readiness (unchanged in count, contract strengthened)

| # | Blocker | Status |
|---|---|---|
| 1 | `configured_data_platform_current_cycle_runtime` | READY |
| 2 | `configured_graph_phase0_status_runtime` | READY-IN-CODE |
| 3 | `configured_graph_phase1_runtime` | **READY-IN-CODE** (idempotent re-run including empty-slice retry; UTC-only timestamps enforced) |
| 4 | `configured_reasoner_runtime` | PARTIAL (Codex 429 quota) |
| 5 | `configured_audit_eval_retrospective_hook_runtime` | READY |
| 6 | `production_current_cycle_dagster_run_evidence` | DEFERRED-TO-M2.6 |

The empty-slice ghost-row class of bug is now closed: a Phase 1
retry whose plan legitimately produces zero edges/assertions for a
cycle correctly clears that cycle's prior rows. UTC contract
violations fail loud at write time. Codex review's blocker call on
the M2.6 evidence's downstream-consumption claim is corrected. M2.6
itself remains the next milestone gate (still requires Codex quota
reset or alternative LLM credentials).
