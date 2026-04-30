# M3.2 — Graph snapshot ref round-trip preflight

## Status

**M3.2 status: COMPLETE (preflight scope).** Closes the M3.2 milestone
criterion: P2 / main-core consumes an **actually produced** graph
snapshot ref in a bounded run, not a fixture-only fake. Four new
integration tests in main-core wire graph-engine's
`FormalArtifactSnapshotWriter` + `ArtifactCanonicalReader` through a
test-only `_ArtifactBackedGraphEnginePort` adapter into main-core's L3
+ L4 consumers, and verify the snapshot's identity (cycle_id +
graph_snapshot_id) and payload round-trip end-to-end.

This is **preflight**, not the full M3.3 production same-cycle proof:
no live PG, no live Neo4j, no Dagster job execution. M3.3 remains the
end-to-end production proof and depends on M2.6 (Codex quota).

---

## Prerequisites

- M2.3 (graph Phase 0/1 runtime wiring) — **READY-IN-CODE** as of
  M2.3a-2 / M2.6f1.r1+r2. graph-engine's `FormalArtifactSnapshotWriter`
  + `ArtifactCanonicalReader` are the artefacts produced by M2.3 path
  that M3.2 verifies round-trip cleanly.
- M3.1 (L3/L4 cross-cycle integration rejection test) — **PASS** as of
  the same-day commit. M3.1 closed the rejection-branch coverage gap;
  M3.2 closes the production-snapshot-consumption coverage gap.
- C4 audit (`assembly/reports/stabilization/p3-p2-graph-consumption-audit-20260428.md`)
  identified both gaps. M3.1 + M3.2 close them in succession.

---

## Files changed

### main-core (branch `m2-3a-2-regime-reader`)

**New file:** `tests/integration/test_graph_snapshot_round_trip_preflight.py`
— +400 LOC. Three-phase preflight + a belt-and-braces unicode-safe
cycle-id round-trip test:

1. **Phase 1 — `test_graph_snapshot_artifact_round_trips_via_writer_and_reader`**
   — pure graph-engine boundary check: `FormalArtifactSnapshotWriter`
   writes a real `(GraphSnapshot, GraphImpactSnapshot)` pair to
   `tmp_path`; `ArtifactCanonicalReader.read_cold_reload_plan` reads
   back a `ColdReloadPlan` whose `expected_snapshot.snapshot_id`
   matches the original `graph_snapshot_id`, and whose
   `node_records` / `edge_records` counts match `node_count` /
   `edge_count`. Proves the write/read shapes agree.

2. **Phase 2 — `test_main_core_l3_consumes_artifact_backed_graph_impact_records`**
   — wires the artifact-backed `GraphEnginePort` through main-core's
   `build_feature_signal_bundles`. Verifies:
   - the produced snapshot's `graph_snapshot_id` appears in
     `bundle.graph_features["snapshot_id"]` (proving L3 read the
     **real** ref, not a synthetic value);
   - the round-trip marker `"from-artifact-reader"` appears in
     `bundle.graph_features["features"]`, proving records flowed
     through the reader rather than a bypassed in-memory shortcut;
   - `graph_port.impact_calls == [cycle_id]` (called exactly once
     with the requested cycle id).

3. **Phase 3 — `test_main_core_l4_consumes_artifact_backed_graph_regime_context`**
   — same artifact, same adapter; routes through main-core's
   `derive_world_state`. Verifies:
   - `policy.seen_inputs[0].graph_impact["snapshot_id"]` matches the
     produced `graph_snapshot_id`;
   - `regime_context["node_count"]` / `"edge_count"` round-trip from
     the original snapshot;
   - `graph_port.regime_calls == [cycle_id]`.

4. **Belt-and-braces — `test_round_trip_preserves_cycle_id_under_unicode_safe_ref`**
   — exercises a non-trivial-but-spec-compliant `cycle_id` (e.g.
   `"cycle-m3-2-2026-04-30T12-00Z"`) to catch a regression where the
   writer or reader silently coerces / truncates the cycle id.

### Test-only adapter

`_ArtifactBackedGraphEnginePort` (in the test file) is a small
adapter that satisfies main-core's `GraphEnginePort` protocol by
sourcing records from the cold-reload plan's `node_records`. It is
**local to the test** — not a production adapter — but its shape
mirrors what a future production adapter would do (read records from a
persisted artifact, reshape into `GraphImpactRecord` /
`GraphRegimeContext`).

### graph-engine

No source-code changes. The test consumes graph-engine's **public**
entry points only: `FormalArtifactSnapshotWriter` and
`ArtifactCanonicalReader` from `graph_engine.snapshots` /
`graph_engine.reload`.

### orchestrator

No source-code changes in this round. M3.2's code-side wiring would be
a follow-up: extend `orchestrator/p2_dry_run.py` to use a
production `GraphEnginePort` impl backed by the same writer/reader
chain. Today that file just shuttles the snapshot ref string into
`graph_features={"graph_snapshot_ref": ...}` without consuming the
actual records — the consumer-side wiring is M3.3 territory (and
needs the production GraphEnginePort to be designed first).

### assembly (branch `m2-baseline-2026-04-29`)

**New file:** this evidence document.

---

## Test results

```
$ cd <workspace>/main-core
$ PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
    tests/integration/test_graph_snapshot_round_trip_preflight.py -v
4 passed in 0.12s

$ PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider
383 passed, 3 skipped in 0.29s
  (full main-core sweep: was 379/3/0 pre-M3.2; +4 = 4 new round-trip tests
   collected here; **0 regressions**)

$ .venv/bin/python -m ruff check tests/integration/test_graph_snapshot_round_trip_preflight.py
All checks passed!
```

---

## Schema discoveries (lessons learned for future preflights)

`graph-engine`'s `ArtifactCanonicalReader` enforces strict
"live-metric-shaped" properties on the `GraphSnapshot` it reads back.
Future tests / production adapters writing to the artifact format must
include the following keys in each node's `properties` map:

| Object | Required keys |
|---|---|
| Node | `node_id`, `label`, `canonical_entity_id` (when `entity` set), `properties_json`, `created_at`, `updated_at` |
| Edge | `edge_id`, `source_node_id`, `target_node_id`, `relationship_type`, `properties_json`, `weight`, `created_at`, `updated_at` |

`properties_json` is the source-of-truth for the decoded
`GraphEdgeRecord.properties` / `GraphNodeRecord.properties` map
(`_canonical_properties` returns `json.loads(properties_json)` when
present, otherwise filters `live_properties` by reserved keys). This
means evidence_refs on propagatable edges MUST be embedded inside the
JSON-encoded `properties_json` string, not as a sibling top-level
property — that catches a future production adapter writing
evidence_refs as a top-level property and finding the cold-reload
reader reject the artifact at runtime.

This is documented inline in the test fixture builder
(`_build_graph_snapshot_pair`).

---

## What this unlocks for M3 / G3

### G3 gate — "Same-cycle graph consumption" — readiness contribution

| Aspect | Pre-M3.2 | Post-M3.2 |
|---|---|---|
| L3 fail-closed on cross-cycle (integration) | M3.1 PASS | M3.1 PASS (unchanged) |
| L4 fail-closed on cross-cycle (integration) | M3.1 PASS | M3.1 PASS (unchanged) |
| Snapshot writer/reader round-trip (graph-engine) | covered by `test_live_closure.py` | unchanged |
| **Cross-module write→read→consume round-trip** | **MISSING** | **PASS (preflight)** |
| Snapshot ID + counts round-trip end-to-end | MISSING | PASS |
| Production same-cycle consumption proof | Blocked on M2.6 | Blocked on M2.6 (unchanged) |

M3.2 closes the cross-module preflight gap. M3.3 (production same-
cycle proof through the full daily_cycle_job) remains the blocking
prerequisite for the full G3 gate; M3.2 narrows the
"could-the-cross-module-snapshot-consumption-actually-work" question
that M3.3 would otherwise need to answer from scratch.

### What M3.2 does NOT prove

* It does NOT prove production same-cycle consumption (M3.3
  territory; needs `daily_cycle_job` execution + real Iceberg/Neo4j +
  Codex quota for the LLM legs).
* It does NOT exercise a real production `GraphEnginePort` impl.
  None exists yet — main-core's L3 / L4 still use
  `FakeGraphEnginePort` in tests. The test introduces a local
  `_ArtifactBackedGraphEnginePort` that mirrors what a future
  production adapter would do, but production wiring is deferred.
* It does NOT exercise the orchestrator `p2_dry_run.py` graph
  hand-off path. That file currently shuttles the snapshot ref as a
  string without consuming actual records; M3.3 will revisit when the
  production GraphEnginePort impl lands.
* It does NOT exercise the L4 → L5 / L6 chain. Per main-core/CLAUDE.md
  L5+ read `world_state_snapshot`, not graph context directly — so
  the L4 round-trip is the natural endpoint for graph data.

---

## Updated M3 task status

| # | Task | Pre-M3.2 | Post-M3.2 |
|---|---|---|---|
| M3.1 | L3/L4 cross-cycle integration rejection test | PASS | PASS |
| M3.2 | Graph snapshot ref round-trip preflight | (P1, ready to start) | **PASS (preflight)** |
| M3.3 | Production same-cycle graph consumption proof | P1, blocked on M2.6 + M3.2 | **Blocked on M2.6 only** (Codex quota) |
| M3.4 | Graph impact consumption decision | P2, blocked (PM decision) | Blocked (PM decision) |
| M3.5 | L6 graph context architecture decision | P2, blocked (PM decision) | Blocked (PM decision) |

The next progressable round depends on M2.6 (Codex quota reset). In
the meantime, **M4.7 (Docling/LlamaIndex offline preflight)** is an
independent P2 round that can progress without M2.6.

---

## Hard-rule declarations

- `project_ult_v5_0_1.md` UNCHANGED.
- `ult_milestone.md` UNCHANGED in this round (M3.2 closes a
  preflight criterion; no gate decision change).
- No P5 / M3.3 / M3.4 / M3.5 work in this round.
- No production fetch.
- No production source-code changes — pure new test + new evidence.
- Tushare remains source adapter only.
- `frontend-api` NOT touched.
- `/Users/fanjie/Desktop/BIG/FrontEnd/**` NOT modified.
- compose stack inherited; not started or modified.
- main-core CLAUDE.md respected: the test wires graph-engine **public**
  writer + reader entry points only; the `_ArtifactBackedGraphEnginePort`
  is local to the test, not in `main_core/*` source code. No
  graph-engine internal symbols touched.
- graph-engine CLAUDE.md respected: graph-engine is consumed as a
  read-only sibling repo via lazy `sys.path` insertion. No
  graph-engine code modified.
- orchestrator CLAUDE.md respected: orchestrator is NOT touched in
  this round. The `p2_dry_run.py` graph hand-off path is documented
  as a future consumer when the production `GraphEnginePort` impl
  lands.

---

## Cross-references

- C4 audit (gap identification): [`p3-p2-graph-consumption-audit-20260428.md`](p3-p2-graph-consumption-audit-20260428.md)
- M3.1 (L3/L4 cross-cycle rejection): [`p3-l3-l4-cross-cycle-rejection-proof-20260430.md`](p3-l3-l4-cross-cycle-rejection-proof-20260430.md)
- M2.6 followup #1 (Phase 1 graph_promotion writer): [`m2-6-followup-1-canonical-graph-writer-20260429.md`](m2-6-followup-1-canonical-graph-writer-20260429.md)
- graph-engine boundary entry points:
  - `graph_engine.snapshots.FormalArtifactSnapshotWriter`
  - `graph_engine.reload.ArtifactCanonicalReader.read_cold_reload_plan`
- main-core consumer entry points:
  - `main_core.l3_features.build_feature_signal_bundles`
  - `main_core.l4_world_state.derive_world_state`

## Recommended next round

| Option | Scope | Effort | Unlocks |
|---|---|---|---|
| **review** M3.2 | reviewer agents + codex CLI | 5-10 min | catches design / coverage gaps |
| M4.7 — Docling/LlamaIndex offline preflight | subsystem-announcement + subsystem-news; offline parse 10-20 docs | 0.5-1 round | independent track, P2, not on daily-cycle critical path |
| Wait for Codex quota reset (~5d) → M2.6 + M3.3 | full daily-cycle + production same-cycle proof | 1-2 rounds + wait | M2 closure + G2/G3 unblock |

`m2-baseline-2026-04-29` continues to accumulate evidence; M3.2 is the
second M3 round to land on the same day as M3.1.
