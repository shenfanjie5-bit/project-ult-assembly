# P3 → P2 Graph Consumption Audit (C4)

**Task**: C4 — P3 → P2 Graph Consumption Audit (Project ULT v5.0.1 closure audit set)
**Date**: 2026-04-28
**Repos in scope**: graph-engine + main-core + orchestrator + assembly
**Plan reference**: `/Users/fanjie/.claude/plans/project-ult-v5-0-1-cosmic-milner.md` § C4
**Output report**: `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/p3-p2-graph-consumption-audit-20260428.md`
**Author note**: AUDIT ONLY. No source modifications. No git init. No commits. Tushare remains a `provider=tushare` adapter only.

---

## 1. Validation block

Interpreters used:
- `main-core/.venv/bin/python` — Python 3.14.3 (subrepo's own venv present; no fallback needed)
- `graph-engine/.venv/bin/python` — Python 3.14.3 (subrepo's own venv present; no fallback needed)

### 1.1 main-core same-cycle graph consumption fixture

```
cd main-core && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q tests/integration/test_graph_readonly_consumption.py 2>&1 | tail -10
```
Result: `.` (1 test PASSED — fixture-only same-cycle path through `FakeGraphEnginePort`).
Interpretation: this proves the L3 + L4 read-only consumption path is wired in code; it does NOT prove production same-cycle consumption (which is bounded by C1 RUNTIME_BLOCKERS) and it does NOT exercise the cross-cycle rejection branch (asserted only in the per-layer unit tests, not in this integration fixture).

### 1.2 Symbol presence — consumer call sites

```
cd project-ult && rg -n 'load_graph_features|load_graph_regime_context|read_graph_impact_snapshot|read_graph_regime_context' main-core/src main-core/tests reasoner-runtime/ 2>&1 | head -50
```
Result (truncated, full output observed during the run):
- Producer-side protocol: `main-core/src/main_core/common/protocols/graph.py:40` (`read_graph_impact_snapshot`), `:46` (`read_graph_regime_context`).
- Consumer entry points:
  - `main-core/src/main_core/l3_features/graph_adapter.py:16` — `def load_graph_features(...)`; `:26` calls `port.read_graph_impact_snapshot(cycle_id)`.
  - `main-core/src/main_core/l4_world_state/graph_adapter.py:13` — `def load_graph_regime_context(...)`; `:22` calls `port.read_graph_regime_context(cycle_id)`.
  - `main-core/src/main_core/l4_world_state/service.py:12,35` — wires `load_graph_regime_context` into `derive_world_state`.
  - `main-core/src/main_core/l3_features/builder.py:117` — wires `load_graph_features` into `build_feature_signal_bundles`.
- Tests (per-layer unit + integration):
  - `main-core/tests/l3_features/test_graph_adapter.py:121` — `test_load_graph_features_rejects_cycle_mismatch`.
  - `main-core/tests/l4_world_state/test_graph_adapter.py:114` — `test_load_graph_regime_context_rejects_cycle_mismatch`.
  - `main-core/tests/integration/test_graph_readonly_consumption.py:41,65` — `FakeGraphEnginePort.read_graph_impact_snapshot` / `read_graph_regime_context`.
  - Contract: `main-core/tests/protocols/test_graph_engine_contract.py:26,33`.
- `reasoner-runtime/`: ZERO hits for any of the four consumer/producer symbols. No graph adapter, no graph reader, no graph reference of any kind in `reasoner-runtime/reasoner_runtime/` source. (See L6 gap, §8.)

### 1.3 Symbol presence — producer side and orchestrator l1 asset

```
cd project-ult && rg -n 'graph_snapshot|graph_impact_snapshot' graph-engine/graph_engine/snapshots graph-engine/graph_engine/reload orchestrator/src/orchestrator_adapters/p2_dry_run.py 2>&1 | head -40
```
Key matches:
- `graph-engine/graph_engine/snapshots/__init__.py:5-7` — public exports `build_graph_impact_snapshot`, `build_graph_snapshot`, `compute_graph_snapshots`.
- `graph-engine/graph_engine/snapshots/artifact_writer.py:35-51` — `FormalArtifactSnapshotWriter.write_snapshots(...)` accepts `(graph_snapshot, impact_snapshot)`; persisted JSON path is `<artifact_root>/<namespace>/<artifact_kind>/<cycle_id>/<graph_snapshot_id>.json` (the cycle_id is the path partition; cycle_id is also stamped inside the payload at `:68` `cycle_id: graph_snapshot.cycle_id`).
- `graph-engine/graph_engine/reload/service.py:166-226` — `metrics_snapshot_from_graph_snapshot` re-derives `cycle_id`, `snapshot_id`, `node_count`, `edge_count` from the persisted snapshot (used by the Cold Reload reader).
- `orchestrator/src/orchestrator_adapters/p2_dry_run.py:682` — `def l1(context, graph_snapshot: str)`. The l1 Dagster asset takes `graph_snapshot: str` (a snapshot reference string), not the deserialised artifact; further occurrences at `:155, :388, :408, :453, :477, :691, :1335, :1348, :1373, :1386, :1414, :1426`. At `:1426` the dry-run wraps the reference into `graph_features={"graph_snapshot_ref": graph_snapshot}` rather than reading the snapshot back through `GraphEnginePort`.

### 1.4 graph-engine sanity test sweep

```
cd graph-engine && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q tests 2>&1 | tail -10
```
Result (full bar):
```
...........................................ssssssssssssssss............. [ 17%]
........................................................................ [ 34%]
..................s..................................................... [ 51%]
........................................................................ [ 69%]
........................................................................ [ 86%]
.........................................................                [100%]
```
All non-skipped graph-engine tests PASS; `s` markers are pre-existing skips (no new failures). Sanity-only — does not certify production graph promotion / propagation / reload end-to-end.

---

## 2. Producer (P3 Phase 1)

**File path verified**: `graph-engine/graph_engine/snapshots/` resolves; contents include `__init__.py`, `artifact_writer.py`, `generator.py`, `writer.py`.

**Snapshot writer**: `graph-engine/graph_engine/snapshots/artifact_writer.py`.
- Class `FormalArtifactSnapshotWriter` (line 13).
- `write_snapshots(graph_snapshot, impact_snapshot)` (lines 33–42) atomically writes a JSON payload.
- `cycle_id` stamping:
  - As path partition at line 49: `/ graph_snapshot.cycle_id /`.
  - Inside payload at line 68: `"cycle_id": graph_snapshot.cycle_id`.
  - Both `graph_snapshot.model_dump(mode="json")` (line 69) and `impact_snapshot.model_dump(mode="json")` (line 70) carry their own `cycle_id` field through the serialised model.
- Generation id encoded into snapshot id and surfaced at line 73 (`graph_generation_id`), supporting the Cold Reload code paths.

**Snapshot generation**: `graph-engine/graph_engine/snapshots/generator.py:45` `build_graph_snapshot(...)` and `:64` `build_graph_impact_snapshot(...)` produce the two artifacts; `compute_graph_snapshots` is exported from the package init for orchestrator wiring.

**Reload reader (Layer A → Cold Reload)**: `graph-engine/graph_engine/reload/artifact_reader.py:78` `class ArtifactCanonicalReader`; `:98` `def read_cold_reload_plan(self, snapshot_ref: str) -> ColdReloadPlan`. Resolves `file://`, `artifact://`, and bare path refs; validates `node_records` / `edge_records` / `assertion_records` counts against `expected_snapshot.node_count` / `edge_count` (`:405`–`:425`).

**Status — Producer**: CONFIRMED — graph-engine writes snapshot+impact JSON with cycle_id stamping in both the path partition (`artifact_writer.py:49`) and the payload body (`artifact_writer.py:68`), and the Cold Reload reader exists at `reload/artifact_reader.py:98`.

---

## 3. Consumer (P2 L3/L4)

**Both adapter file paths verified.**

### 3.1 L3 graph adapter — `main-core/src/main_core/l3_features/graph_adapter.py`

Cycle-id FAIL-CLOSED check (lines 26–32):

```python
records = list(port.read_graph_impact_snapshot(cycle_id))
matching_records: list[GraphImpactRecord] = []
for record in records:
    if str(record.cycle_id) != str(cycle_id):
        raise _GraphSnapshotError(
            "graph impact snapshot contains records from a different cycle"
        )
```

Behaviour: every record returned by `port.read_graph_impact_snapshot(cycle_id)` is checked against the requested `cycle_id`; a single mismatch raises `GraphSnapshotError`. Duplicate-record check at lines 38–41.

Wiring point: `main-core/src/main_core/l3_features/builder.py:117` calls `load_graph_features(cycle_id, entity_id, graph_engine_port)` inside `build_feature_signal_bundles`, attaching the result as `bundle.graph_features` for downstream consumers (notably L6 — see §8).

### 3.2 L4 graph adapter — `main-core/src/main_core/l4_world_state/graph_adapter.py`

Cycle-id FAIL-CLOSED check (lines 22–28):

```python
context = port.read_graph_regime_context(cycle_id)
if context is None:
    return {}
if str(context.cycle_id) != str(cycle_id):
    raise GraphSnapshotError(
        "graph regime context contains records from a different cycle"
    )
```

Wiring point: `main-core/src/main_core/l4_world_state/service.py:12,35` consumes `load_graph_regime_context(...)` inside `derive_world_state`.

**Status — Consumer**: CONFIRMED — both adapters fail-closed on cycle_id mismatch in code, wired through their respective L3 / L4 entry points.

---

## 4. Same-cycle consumption inside fixture

**Path verified**: `main-core/tests/integration/test_graph_readonly_consumption.py` (179 lines, single test function `test_previous_world_state_feeds_readonly_graph_context_into_l3_and_l4`).

The fixture:
- Constructs `FakeGraphEnginePort` (lines 34–78) implementing both `read_graph_impact_snapshot` and `read_graph_regime_context`, returning records stamped with the requested `cycle_id`.
- Invokes `build_feature_signal_bundles(current_cycle_id, ..., graph_engine_port=graph_port)` (lines 135–139).
- Invokes `derive_world_state(..., graph_engine_port=graph_port)` (lines 152–165).
- Asserts `graph_port.impact_calls == [current_cycle_id]` and `graph_port.regime_calls == [current_cycle_id]` (lines 177–178), proving both adapters were called with the matching cycle.
- Asserts the bundle's `graph_features` equals the snapshot payload (lines 142–149) and the world-state policy saw the regime context attached (lines 169–176).

Validation §1.1 shows this test PASSES today.

**Status — same-cycle fixture**: CONFIRMED (fixture-only; not promoted beyond fixture-level).

---

## 5. Cross-cycle rejection

**Code-level cross-cycle rejection**: PRESENT.
- `main-core/src/main_core/l3_features/graph_adapter.py:29-32` raises `GraphSnapshotError` on mismatch.
- `main-core/src/main_core/l4_world_state/graph_adapter.py:25-28` raises `GraphSnapshotError` on mismatch.

**Per-layer unit tests for the rejection path**: PRESENT.
- `main-core/tests/l3_features/test_graph_adapter.py:121` — `test_load_graph_features_rejects_cycle_mismatch`.
- `main-core/tests/l4_world_state/test_graph_adapter.py:114` — `test_load_graph_regime_context_rejects_cycle_mismatch`.

**Integration-level cross-cycle rejection**: NOT PRESENT.
- `rg -n 'rejects_cycle' main-core/tests/integration/test_graph_readonly_consumption.py` returned zero hits.
- The integration fixture exercises only the matching-cycle path; no assertion proves that L3 + L4 chained rejection propagates upward through `build_feature_signal_bundles` / `derive_world_state` end-to-end.

**Status — cross-cycle rejection**: PARTIAL. Adapters fail-closed in code (`l3_features/graph_adapter.py:29-32`, `l4_world_state/graph_adapter.py:25-28`) and per-layer unit tests assert the rejection (`tests/l3_features/test_graph_adapter.py:121`, `tests/l4_world_state/test_graph_adapter.py:114`). The existing integration fixture (`tests/integration/test_graph_readonly_consumption.py`) does NOT exercise the rejection path; per-cycle isolation across the chained L3+L4 path is therefore not asserted at integration level. Per the plan's labelling rules, this is PARTIAL, not CONFIRMED.

---

## 6. Production same-cycle consumption

The orchestrator `daily_cycle_job` Phase-2 `l1` Dagster asset is defined at `orchestrator/src/orchestrator_adapters/p2_dry_run.py:682`:

```python
@dagster.asset(name=PHASE2_STAGE_KEYS[0], group_name=PHASE2_GROUP_NAME)
def l1(context, graph_snapshot: str):
    ...
    return input_provider.load_current_cycle_inputs(
        cycle_id=cycle_id,
        graph_snapshot=graph_snapshot,
    )
```

The asset accepts `graph_snapshot: str` — i.e. a reference string, not a deserialised `GraphSnapshot`. Downstream of l1, the dry-run path at `:1426` packages it as `graph_features={"graph_snapshot_ref": graph_snapshot}` rather than reading the snapshot back through `GraphEnginePort`. Production same-cycle consumption requires real `GraphEnginePort` wiring inside `configured_graph_phase1_runtime` and the asset graph to honour the graph reference end-to-end.

Per C1 (`assembly/reports/stabilization/production-daily-cycle-gap-audit-20260428.md`, §"The 6 RUNTIME_BLOCKERS"), the relevant fail-closed runtime providers gating this path are:
- `configured_graph_phase0_status_runtime`
- `configured_graph_phase1_runtime`
- `configured_reasoner_runtime`
- `configured_data_platform_current_cycle_runtime`
- `configured_audit_eval_retrospective_hook_runtime`
- `production_current_cycle_dagster_run_evidence`

Until those six blockers are closed, `daily_cycle_job.execute_in_process(tags={"cycle_id": ...})` cannot prove same-cycle graph consumption end-to-end with real engines.

**Status — production same-cycle consumption**: PARTIAL — bounded by the 6 RUNTIME_BLOCKERS in C1. NOT upgraded beyond PARTIAL. See C1 report for blocker detail.

---

## 7. (intentionally merged into §6 above)

---

## 8. L6 (reasoner) gap

**Searched paths** (per the plan):
- `main-core/src/main_core/l6_alpha/` — listing: `__init__.py`, `_README.md`, `ab_runner.py`, `fallback.py`, `multi_agent_analyzer.py`, `reasoner_port.py`, `service.py`, `single_prompt_analyzer.py`, `stubs.py`.
- `reasoner-runtime/` — Python tree under `reasoner-runtime/reasoner_runtime/`: `__init__.py`, `_contracts.py`, `callbacks/`, `config/`, `core/`, `health/`, `providers/`, `public.py`, `replay/`, `scrub/`, `structured/`.
- `orchestrator/src/orchestrator_adapters/p2_dry_run.py` — reasoner-call sites at `:218` (`P2ReasonerGateway` adapter), `:280` (`from main_core.l6_alpha.reasoner_port import AlphaReasonerResponse`), `:723-747` (Dagster `l6` asset).

**Search results**:
- `rg -n 'GraphEnginePort|graph_engine_port' main-core/src/main_core/l6_alpha/ reasoner-runtime/reasoner_runtime/` returned ZERO matches.
- `rg -n 'graph' reasoner-runtime/reasoner_runtime/` returned ZERO matches; the only hit anywhere under `reasoner-runtime/` is `reasoner-runtime/tests/boundary/test_red_lines.py:157: "graph_engine"` — a boundary red-line listing graph_engine as a banned import direction, NOT a consumer wiring.
- `rg -n 'graph' main-core/src/main_core/l6_alpha/` returned a single hit: `multi_agent_analyzer.py:117 "graph_features": _plain_value(context.feature_bundle.graph_features)`. That is, L6 reads `graph_features` only as a passthrough field of the feature bundle that L3 already populated; L6 itself does NOT call `port.read_graph_impact_snapshot` or `port.read_graph_regime_context`.
- The Dagster `l6` asset at `p2_dry_run.py:723-747` constructs `AlphaAnalysisContext(feature_bundle=bundles_by_entity[...], world_state=l4, similar_cases=[])` — `similar_cases=[]` is hard-coded; no graph adapter is invoked at the L6 stage.

**Interpretation**: L6 receives graph-derived data exclusively through the indirection `feature_bundle.graph_features`, which is populated by L3 via the `GraphEnginePort` chain. L6 does NOT have its own graph adapter; the reasoner-runtime project intentionally has no graph dependency (boundary test enforces this). This is consistent with the L4 / L5 / L6 boundary documented in `main-core/CLAUDE.md` (L5/L6/L7 only read `world_state_snapshot`, do not directly consume graph). However, the plan defines L6 graph consumption status as "GAP unless code search proves an explicit graph adapter exists."

**Status — L6 graph consumption**: CONFIRMED gap. No explicit L6 graph adapter exists in `main-core/src/main_core/l6_alpha/`, and `reasoner-runtime/` has no graph references at all. Per the plan's L6 status rule (CONFIRMED gap if no explicit graph adapter is found), this is reported as a CONFIRMED gap. Whether L6 *should* have its own graph adapter is an architecture decision (tension between the plan's "L6 graph consumption is a gap" framing and `main-core/CLAUDE.md`'s "L5/L6/L7 read-only consume world_state_snapshot" boundary); resolving that decision is outside the scope of this audit.

---

## 9. What would close the gaps (PLAN ONLY)

Per the plan, this section enumerates the work that would close each gap. NO implementation is performed in this round.

### 9.1 Cross-cycle rejection at integration level
Add ONE assertion to `main-core/tests/integration/test_graph_readonly_consumption.py` that wraps `build_feature_signal_bundles(..., graph_engine_port=graph_port)` with a graph port whose returned `GraphImpactRecord.cycle_id` does not match the requested `cycle_id`, and asserts `pytest.raises(GraphSnapshotError)`. Repeat for the L4 path. This proves chained rejection through the integration layer, not just per-adapter unit tests.
- Estimated diff: one new test function (~25 lines), no source-code changes.
- Risk: low; relies on the existing `GraphSnapshotError` plumbing.
- NOT executed in this audit.

### 9.2 L6 graph adapter wiring
Location enumeration only. If the architecture decision moves toward L6 having its own graph adapter (rather than relying on L3-populated `feature_bundle.graph_features`), the wiring would land in:
- New module: `main-core/src/main_core/l6_alpha/graph_adapter.py` (mirroring `l3_features/graph_adapter.py` and `l4_world_state/graph_adapter.py` shape).
- Caller change: `main-core/src/main_core/l6_alpha/single_prompt_analyzer.py` and/or `multi_agent_analyzer.py:106` `build_multi_agent_input_payload` to invoke the adapter and inject the result alongside `graph_features`.
- Orchestrator wiring: `orchestrator/src/orchestrator_adapters/p2_dry_run.py:723` `l6` Dagster asset to receive a `GraphEnginePort` resource and pass it into `AlphaAnalysisContext` (today `similar_cases=[]` is hard-coded, no graph port is plumbed).
- Boundary impact: `reasoner-runtime/tests/boundary/test_red_lines.py:157` lists `graph_engine` as a banned import direction for `reasoner-runtime`, so any graph access by the alpha analyzer would have to remain inside `main-core` and pass scalar/serialised data into `reasoner-runtime`, not import-graph dependencies.
- NOT implemented; locations enumerated for plan continuity.

### 9.3 Resolve C1 RUNTIME_BLOCKERS
Production same-cycle consumption upgrade from PARTIAL to CONFIRMED requires the six RUNTIME_BLOCKERS enumerated in `assembly/reports/stabilization/production-daily-cycle-gap-audit-20260428.md` to be closed and `daily_cycle_job.execute_in_process(tags={"cycle_id": ...})` to run end-to-end with real engines. This is a precondition; this audit does not promise an outcome.

---

## 10. Findings tally

| # | Area | Status | Evidence |
|---|------|--------|----------|
| 1 | Producer (graph-engine snapshot+impact JSON, cycle_id stamping) | CONFIRMED | `graph-engine/graph_engine/snapshots/artifact_writer.py:35-51, :49, :68` |
| 2 | Cold Reload reader (Layer A canonical artifact reader) | CONFIRMED | `graph-engine/graph_engine/reload/artifact_reader.py:78, :98` |
| 3 | L3 consumer fail-closed on cycle mismatch (code) | CONFIRMED | `main-core/src/main_core/l3_features/graph_adapter.py:26-32` |
| 4 | L4 consumer fail-closed on cycle mismatch (code) | CONFIRMED | `main-core/src/main_core/l4_world_state/graph_adapter.py:22-28` |
| 5 | L3 wiring into builder | CONFIRMED | `main-core/src/main_core/l3_features/builder.py:117` |
| 6 | L4 wiring into derive_world_state | CONFIRMED | `main-core/src/main_core/l4_world_state/service.py:12,35` |
| 7 | Per-layer unit tests for cross-cycle rejection | CONFIRMED | `main-core/tests/l3_features/test_graph_adapter.py:121`; `main-core/tests/l4_world_state/test_graph_adapter.py:114` |
| 8 | Same-cycle consumption inside integration fixture | CONFIRMED (fixture-only) | `main-core/tests/integration/test_graph_readonly_consumption.py` (single test, 179 lines) |
| 9 | Cross-cycle rejection at integration level | PARTIAL | Code present (§3) + per-layer unit tests (§5); fixture lacks the assertion |
| 10 | Production same-cycle graph consumption | PARTIAL | `orchestrator/src/orchestrator_adapters/p2_dry_run.py:682` `graph_snapshot: str` is a reference; bounded by 6 C1 RUNTIME_BLOCKERS |
| 11 | L6 graph adapter (explicit) | CONFIRMED gap | No `GraphEnginePort` usage in `main-core/src/main_core/l6_alpha/` or `reasoner-runtime/reasoner_runtime/`; only passthrough at `main-core/src/main_core/l6_alpha/multi_agent_analyzer.py:117` |
| 12 | reasoner-runtime banned-graph boundary | CONFIRMED | `reasoner-runtime/tests/boundary/test_red_lines.py:157` keeps `graph_engine` on the banned import list |
| 13 | graph-engine sanity test sweep | CONFIRMED | All non-skipped tests pass (§1.4) — sanity only, NOT production proof |

Tally: **9 CONFIRMED, 2 PARTIAL, 2 CONFIRMED-gap (also CONFIRMED in the sense of "the absence is verified"), 0 INFERRED.**

For the handoff format, treating CONFIRMED gap as a CONFIRMED finding of an absence: **11 CONFIRMED, 2 PARTIAL, 0 INFERRED.**

---

## 11. Outstanding risks

- Production same-cycle graph consumption is gated on six independent runtime providers (per C1). Any one of them remaining stubbed keeps this gap open.
- The integration fixture does not exercise the cross-cycle rejection path; if a future change weakens the per-adapter cycle check, only the per-layer unit tests would catch it — not the chained integration scenario.
- L6 graph access today is implicit (passthrough of `feature_bundle.graph_features` produced by L3). The architecture decision on whether L6 should have its own `GraphEnginePort` adapter is unresolved; `main-core/CLAUDE.md` says L5/L6/L7 should only consume `world_state_snapshot` (i.e. NOT a direct graph port), which is in tension with the plan's framing that L6 graph consumption is a gap until a dedicated adapter exists. The plan's labelling rule (CONFIRMED gap absent an explicit adapter) is applied as instructed; the architectural reconciliation is out of scope.
- `orchestrator/src/orchestrator_adapters/p2_dry_run.py:682` accepts `graph_snapshot: str` and the dry-run wraps it as a `graph_snapshot_ref` (line 1426). Production wiring will need to round-trip the reference through `GraphEnginePort.read_*` calls inside main-core — this is currently only proven via `FakeGraphEnginePort` in the fixture.
- `reasoner-runtime` has zero graph references; any future "L6 graph context" injection must remain on the `main-core` side of the boundary (red-line at `reasoner-runtime/tests/boundary/test_red_lines.py:157`).
- The `main-core/.venv` and `graph-engine/.venv` interpreters are both Python 3.14.3 — non-LTS. If future stabilization moves to a 3.12 LTS line, the tests must be re-run there.

---

## 12. Per-task handoff block

```
Task: C4
Repo(s): graph-engine + main-core + orchestrator + assembly
Output report: /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/p3-p2-graph-consumption-audit-20260428.md
Validation commands:
  1) cd main-core && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q tests/integration/test_graph_readonly_consumption.py 2>&1 | tail -10
  2) cd project-ult && rg -n 'load_graph_features|load_graph_regime_context|read_graph_impact_snapshot|read_graph_regime_context' main-core/src main-core/tests reasoner-runtime/ 2>&1 | head -50
  3) cd project-ult && rg -n 'graph_snapshot|graph_impact_snapshot' graph-engine/graph_engine/snapshots graph-engine/graph_engine/reload orchestrator/src/orchestrator_adapters/p2_dry_run.py 2>&1 | head -40
  4) cd graph-engine && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q tests 2>&1 | tail -10
Validation results:
  1) PASS — 1 test passed (fixture-only same-cycle path; tail showed `.` and `[100%]`)
  2) PASS — symbols present in expected files; reasoner-runtime/ has zero hits (consistent with CONFIRMED L6 gap)
  3) PASS — producer artifacts at graph-engine/snapshots, Cold Reload at graph-engine/reload, p2_dry_run l1 takes graph_snapshot:str at line 682
  4) PASS — all non-skipped graph-engine tests passed (sanity only; not production proof)
Per-subrepo git state:
  graph-engine:  rev-parse HEAD = fc4e083e1328333f0320fa7c0afa96d0b0dd6b37; status = clean; push status = main tracks origin/main (no audit edits attempted); interpreter = graph-engine/.venv/bin/python (Python 3.14.3)
  main-core:     rev-parse HEAD = efaa4f62027401ee85d1a20095ab4f7ff29e6994; status = clean; push status = main tracks origin/main (no audit edits attempted); interpreter = main-core/.venv/bin/python (Python 3.14.3)
  orchestrator:  rev-parse HEAD = 6a4c42c687fb6e7be4a792a8b3a5b9681b0a254f; status = clean; push status = main tracks origin/main (no audit edits attempted)
  assembly:      rev-parse HEAD = a7f19c5994f807b2cf32eb2f45ef48f6fe23095f; status = untracked: reports/stabilization/frontend-raw-route-alignment-fix-20260428.md, reports/stabilization/production-daily-cycle-gap-audit-20260428.md, reports/stabilization/project-ult-v5-0-1-supervisor-review-20260428.md, reports/stabilization/raw-manifest-source-interface-hardening-20260428.md, AND (after this audit) reports/stabilization/p3-p2-graph-consumption-audit-20260428.md; push status = main tracks origin/main (NOT pushed; audit-only)
Dirty files: assembly/reports/stabilization/p3-p2-graph-consumption-audit-20260428.md (this report, untracked); plus the four pre-existing untracked reports listed above (untouched by this task)
Findings: 11 CONFIRMED (incl. 2 CONFIRMED gap-presence findings), 2 PARTIAL, 0 INFERRED
Outstanding risks:
  - Production same-cycle consumption gated on the 6 C1 RUNTIME_BLOCKERS
  - Integration fixture lacks cross-cycle rejection assertion
  - L6 graph access is implicit (passthrough); architecture decision pending
  - p2_dry_run l1 accepts graph_snapshot as a string ref; production must round-trip via GraphEnginePort
  - Both main-core/.venv and graph-engine/.venv are Python 3.14.3 (non-LTS)
Declaration: I did not mark any PARTIAL or PREFLIGHT finding as PASS. I did not commit any forbidden files. Tushare remains a provider=tushare adapter only. I did not run `git init`. I did not push without approval.
```
