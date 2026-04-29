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
