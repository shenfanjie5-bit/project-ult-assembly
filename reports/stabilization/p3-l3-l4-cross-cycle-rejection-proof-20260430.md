# M3.1 — L3/L4 cross-cycle integration rejection proof

## Status

**M3.1 status: COMPLETE.** Closes the C4-audit-flagged integration coverage
gap: the per-layer unit tests pin `GraphSnapshotError` on a single-call
cycle-id mismatch, but the integration suite previously only exercised
the same-cycle happy path. Three new integration tests now exercise the
fail-closed cross-cycle rejection branch end-to-end through
`build_feature_signal_bundles` (L3) and `derive_world_state` (L4).

---

## Prerequisites

- C4 audit (`assembly/reports/stabilization/p3-p2-graph-consumption-audit-20260428.md`)
  identified the gap: "this proves the L3 + L4 read-only consumption
  path is wired in code; it does NOT prove production same-cycle
  consumption (which is bounded by C1 RUNTIME_BLOCKERS) **and it does
  NOT exercise the cross-cycle rejection branch** (asserted only in
  the per-layer unit tests, not in this integration fixture)."
- Existing per-layer unit tests already pin the rejection at the
  adapter level:
  - `main-core/tests/l3_features/test_graph_adapter.py:121` —
    `test_load_graph_features_rejects_cycle_mismatch`
  - `main-core/tests/l4_world_state/test_graph_adapter.py:114` —
    `test_load_graph_regime_context_rejects_cycle_mismatch`
- Existing happy-path integration test:
  `test_previous_world_state_feeds_readonly_graph_context_into_l3_and_l4`
  in the same file.

---

## Files changed

### main-core (branch `m2-3a-2-regime-reader`)

**Modified:** `tests/integration/test_graph_readonly_consumption.py` —
+147 LOC. Adds:

1. `GraphSnapshotError` import.
2. New `FakeDriftedGraphEnginePort` dataclass: returns graph artifacts
   whose `cycle_id` deliberately differs from the requested
   `cycle_id`. Configurable via `drift_impact` / `drift_regime`
   booleans so a test can drift only one of the two read paths.
3. New helper `_entity_with_market_bar` to compose the minimal
   data-platform fixture for the rejection tests.
4. **3 new integration tests:**
   - `test_l3_build_feature_bundles_fails_closed_on_cross_cycle_graph_impact`
     — drifts the impact snapshot's `cycle_id`; calls
     `build_feature_signal_bundles`; asserts `GraphSnapshotError` is
     raised AND the regime read was never attempted (proving L3
     halts before L4).
   - `test_l4_derive_world_state_fails_closed_on_cross_cycle_graph_regime`
     — drifts only the regime context (impact OK); calls
     `build_feature_signal_bundles` (succeeds), then
     `derive_world_state`; asserts L4 raises `GraphSnapshotError`
     AND the world-state policy was never consulted (proving the
     reject halts before any downstream world-state computation).
   - `test_cross_cycle_rejection_stops_before_l4_graph_read`
     — drifts both paths; asserts the L3 raise prevents the L4 graph
     regime read from being attempted. This is an integration-layer
     ordering proof, not a wrapper-level world-state emission proof.

### assembly (branch `m2-baseline-2026-04-29`)

**New file:** this evidence document.

---

## Test results

```
$ cd <workspace>/main-core
$ PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
    tests/integration/test_graph_readonly_consumption.py -v
4 passed in 0.13s
  (was 1 — added L3 cross-cycle rejection, L4 cross-cycle rejection,
   and L3-stops-before-L4-read coverage)

$ PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider
379 passed, 3 skipped in 0.26s
  (full main-core sweep: 0 regressions)

$ .venv/bin/python -m ruff check tests/integration/test_graph_readonly_consumption.py
All checks passed!
```

---

## What this unlocks for M3 / G3

### G3 gate — "Same-cycle graph consumption" — readiness contribution

| Aspect | Status |
|---|---|
| L3 fail-closed on cross-cycle (per-layer unit) | Was: Pass | Now: Pass (unchanged) |
| L4 fail-closed on cross-cycle (per-layer unit) | Was: Pass | Now: Pass (unchanged) |
| L3 fail-closed on cross-cycle (integration) | Was: **Missing** | Now: **Pass** (new) |
| L4 fail-closed on cross-cycle (integration) | Was: **Missing** | Now: **Pass** (new) |
| L3 rejection stops before L4 graph read | Was: **Missing** | Now: **Pass** (new) |
| Production same-cycle consumption proof | Blocked on M2.6 + production GraphEnginePort/orchestrator wiring | Unchanged |

M3.1 closes the integration-coverage gap that the C4 audit explicitly
identified. M3.3 (production same-cycle proof) remains blocked on
M2.6 plus production GraphEnginePort/orchestrator wiring; M3.1 just
narrows the "could-the-fail-closed-guard-survive-the-real-call-stack"
question that M3.3 would otherwise have to answer from scratch.

### What M3.1 does NOT prove

* It does NOT prove production same-cycle consumption (M3.3 territory;
  needs `daily_cycle_job` execution + real Iceberg/Neo4j +
  production GraphEnginePort/orchestrator wiring).
* It does NOT exercise a real `GraphEnginePort` implementation —
  only the protocol contract via `FakeDriftedGraphEnginePort`. The
  real `Neo4jGraphSnapshotPort` (or equivalent) reading from Iceberg
  graph snapshots is a separate integration step (depends on M2.6 +
  production GraphEnginePort/orchestrator wiring; M3.2 only covers
  the bounded GraphSnapshot round-trip preflight).
* It does NOT exercise the L4 → L5 / L6 chain. Today main-core's L5+
  do not consume graph context directly (per main-core/CLAUDE.md
  L4 is the shared state surface; L5+ read `world_state_snapshot`),
  so a cross-cycle drift in graph context surfaces in L4 and never
  reaches L5+. This is the documented design, not a gap.

---

## Updated M3 task status

| # | Task | Pre-M3.1 | Post-M3.1 |
|---|---|---|---|
| M3.1 | L3/L4 cross-cycle integration rejection test | (P2, not started) | **PASS** |
| M3.2 | Graph snapshot ref round-trip preflight | P1, blocked on M2.3 (now READY-IN-CODE) | Ready to start |
| M3.3 | Production same-cycle graph consumption proof | P1, blocked on M2.6 + M3.2 | Blocked on M2.6 + production GraphEnginePort/orchestrator wiring |
| M3.4 | Graph impact consumption decision | P2, blocked on M3.2 | Blocked (PM decision) |
| M3.5 | L6 graph context architecture decision | P2, blocked on C4 (closed) | Blocked (PM decision) |

The next progressable M3 round is **M3.2 (Graph snapshot ref round-trip
preflight)** — bounded run, exercises a real produced graph snapshot
ref through L3/L4 consumers; does not require the full daily-cycle
proof that M3.3 needs.

---

## Hard-rule declarations

- `project_ult_v5_0_1.md` UNCHANGED.
- `ult_milestone.md` UNCHANGED in this round (M3.1 closes a gap, does
  not move a gate decision).
- No P5 / M3.2 / M3.3 work in this round.
- No production fetch.
- No source-code changes — pure new test + new evidence.
- Tushare remains source adapter only.
- `frontend-api` NOT touched.
- `/Users/fanjie/Desktop/BIG/FrontEnd/**` NOT modified.
- compose stack inherited; not started or modified.
- main-core CLAUDE.md respected: rejection guards live in
  `l3_features/graph_adapter.py:29` and `l4_world_state/graph_adapter.py:25`,
  consistent with L3/L4 ownership of cross-cycle integrity for
  feature/world-state inputs. Test does not import or modify
  graph-engine internals (uses only the public `GraphEnginePort`
  protocol via the `FakeDriftedGraphEnginePort` fake).
- graph-engine CLAUDE.md respected: no graph-engine code touched.

---

## Cross-references

- C4 audit (gap identification): [`p3-p2-graph-consumption-audit-20260428.md`](p3-p2-graph-consumption-audit-20260428.md)
- M2.6 followup #1 (Phase 1 graph_promotion writer): [`m2-6-followup-1-canonical-graph-writer-20260429.md`](m2-6-followup-1-canonical-graph-writer-20260429.md)
- Per-layer unit tests:
  - `main-core/tests/l3_features/test_graph_adapter.py::test_load_graph_features_rejects_cycle_mismatch`
  - `main-core/tests/l4_world_state/test_graph_adapter.py::test_load_graph_regime_context_rejects_cycle_mismatch`
- Production guards (call sites):
  - `main-core/src/main_core/l3_features/graph_adapter.py:26-32`
  - `main-core/src/main_core/l4_world_state/graph_adapter.py:22-28`

## Recommended next round

| Option | Scope | Effort | Unlocks |
|---|---|---|---|
| **review** M3.1 | reviewer agents + codex CLI | 5-10 min | catches design / coverage gaps |
| M3.2 — Graph snapshot ref round-trip preflight | graph-engine + orchestrator + main-core; bounded run with real produced snapshot | 1 round | sets up M3.3 (production same-cycle proof) |
| M4.7 — Docling/LlamaIndex offline preflight | subsystem-announcement + subsystem-news; offline parse 10-20 docs | 0.5-1 round | independent track, P2, not on daily-cycle critical path |

`m2-baseline-2026-04-29` continues to accumulate evidence; M3.1 is the
first M3 round to land.
