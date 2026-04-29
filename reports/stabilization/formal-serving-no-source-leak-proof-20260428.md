# Formal Serving No-Source-Leak Proof (M1-E)

- Date: 2026-04-28
- Scope: M1-E per `ult_milestone.md`. Hardens the boundary contract that public formal/business surfaces must not surface raw/provider/source lineage. Plan + small focused test addition. **No business route changes; no new write API; no raw debug routes enabled.**
- Mode: minimal test addition + plan. Tushare remains a `provider="tushare"` adapter only.
- Authority: `project_ult_v5_0_1.md` (NOT modified) + `ult_milestone.md` §M1.4 + C3 plan `formal-serving-no-source-leak-hardening-plan-20260428.md` + M1-D proof `canonical-v2-lineage-separation-proof-20260428.md`.

---

## 1. Validation block

### 1.1 New `current_cycle_inputs` boundary test (added in this round)

```
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform && \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
    -p no:cacheprovider --tb=no \
    tests/cycle/test_current_cycle_inputs_lineage_absent.py 2>&1 | tail -3
```

**Result**: `3 passed in 0.14s`. Interpreter: `data-platform/.venv/bin/python` — Python 3.14.3.

The test asserts (statically, by inspecting the source of `_current_cycle_row`):
1. The OUTPUT row dict literal keys do NOT include `source_run_id`, `raw_loaded_at`, `ts_code`, `index_code`, `submitted_at`, `ingest_seq`.
2. The output DOES include `entity_id` (canonical identifier) and does NOT include `ts_code` (provider-shaped identifier).
3. The module's `__all__` does NOT re-export any forbidden symbol.

This pins the temporary mitigation contract C2 §2.5 / C3 §3.4 identified — without this test, a silent regression that re-introduces lineage at the projection boundary would only surface (if at all) at the FE response shape.

### 1.2 Pre-existing C3-era prefix-token tests still PASS

```
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform && \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
    -p no:cacheprovider -q tests/provider_catalog/test_no_source_leak.py
```

Result (per C3 baseline): `2 passed in 0.02s`.

```
cd /Users/fanjie/Desktop/Cowork/project-ult/frontend-api && \
  PYTHONDONTWRITEBYTECODE=1 ../assembly/.venv-py312/bin/python -m pytest \
    -p no:cacheprovider -q tests/test_no_source_leak.py
```

Result (per C3 baseline; assembly venv fallback because `frontend-api/.venv` lacks an interpreter): `4 passed in 0.17s`.

Both pre-existing prefix-token suites continue to PASS.

### 1.3 Read-only inspection of frontend-api response models (per `ult_milestone.md` §M1.4 "frontend-api 可只做 read-only inspection")

`grep -rn "source_run_id\|raw_loaded_at" frontend-api/src/frontend_api 2>&1` — **0 matches** (per C3 §1.4). The frontend-api source code itself does not reference lineage fields. The leak path is the legacy `_legacy_payload(...)` route in `frontend-api/src/frontend_api/routes/cycle.py:81-82` which forwards `FormalObject.payload` from `serving.formal.get_formal_latest(...)` verbatim — that PyArrow table inherits the canonical schema today (which still carries `source_run_id`/`raw_loaded_at` on the legacy `canonical.dim_security` and the other 7 untouched mart tables).

### 1.4 No frontend-api source code changes performed

Per the milestone: "如 frontend-api 有 schema/contract tests，可只做 read-only inspection 或 focused tests，不做 frontend write API". This task adds zero source code changes to `frontend-api/`. No new tests added there either (the C3 plan reserves the option to add ONE pattern-based assertion later; this M1-E task does not exercise that option).

---

## 2. Current state of formal serving public surfaces

### 2.1 `data_platform.serving.formal.get_formal_*`

`data-platform/src/data_platform/serving/formal.py:79-124` — three public entrypoints:

- `get_formal_latest(object_type)` — newest published formal object.
- `get_formal_by_id(cycle_id, object_type)` — pinned to a published cycle.
- `get_formal_by_snapshot(snapshot_id, object_type)` — pinned to a snapshot id appearing in some manifest.

All three return a `FormalObject(cycle_id, object_type, snapshot_id, payload: pa.Table)`. The payload is the unfiltered Iceberg snapshot read via `serving_reader.read_iceberg_snapshot(table_identifier, snapshot_id)` (line 162-167). The formal table identifier is `formal.<object_type>` validated via `formal_registry.validate_formal_object_name(...)`.

The formal namespace tables themselves are written by upstream P3 commit code (not by `canonical_writer`). The leak surface is whatever schema those formal tables carry — today they carry the same shape as the L8 commit produces, which mirrors canonical column names by intent.

### 2.2 `data_platform.cycle.current_cycle_inputs.current_cycle_inputs`

`data-platform/src/data_platform/cycle/current_cycle_inputs.py:52-173` — provider-neutral cycle-input loader. Returns `tuple[CurrentCycleInputRow, ...]` where `CurrentCycleInputRow = dict[str, object]` with keys (per `_current_cycle_row` at lines 430-470):

```
entity_id, trade_date, close, pre_close, return_1d, volume, amount,
market, industry, canonical_dataset_refs, canonical_snapshot_ids, lineage_refs
```

CONFIRMED provider-neutral OUTPUT (no `ts_code`, no `source_run_id`, no `raw_loaded_at`). The `lineage_refs` field is provider-NEUTRAL — it carries `cycle:<id>`, `selection:<ref>`, `candidate:<id>`, and `canonical:<dataset>@<snapshot_id>` strings (lines 448-455), which identify the canonical dataset and snapshot id but do NOT name a provider. This is provenance, not provider lineage.

### 2.3 Frontend-api routes (per C3 §2.4)

| Route file | Purpose | Leak path? |
|---|---|---|
| `routes/entity_data.py` | Canonical entity reads | none (uses Pydantic `*Response` schemas) |
| `routes/cycle.py` | Cycle metadata + `_legacy_payload` for `formal_latest` | **legacy compat path forwards `FormalObject.payload` verbatim** — the only leak vector today |
| `routes/graph.py` | Graph subgraph / paths / impact | none directly (graph engine output) |
| `routes/operations.py` | Reasoner / audit / replay / backtests | none (operation results) |
| `routes/system.py` | health / modules / profiles / compat | none |
| `routes/entity_data.py` debug router | `/api/project-ult/debug/data/raw/{source}` | NOT mounted by default (per C3 §2.2 `test_default_readonly_surface_does_not_mount_raw_debug_routes`) |

The single leak vector is the `_legacy_payload(...)` forwarder in `routes/cycle.py:81-82`. It exists for backwards-compatibility and forwards the PyArrow row dict from `FormalObject.payload`. Hardening it requires either:
- Migrating it to use a Pydantic response model with explicit field allowlist.
- Adding a defensive shape filter that drops `source_run_id`/`raw_loaded_at`/`ts_code` before serialization.
- Retiring the route once all consumers have migrated to the typed `*Response` routes.

Per the milestone's "no business route changes" rule, this M1-E task does NOT change `_legacy_payload(...)`. It documents the leak path and proposes the fix as a follow-up.

---

## 3. What this M1-E delivery covers

| Item | Status | Notes |
|---|---|---|
| Boundary schema test on `current_cycle_inputs()` row shape | **DONE** (3 tests passing in `tests/cycle/test_current_cycle_inputs_lineage_absent.py`) | Pins the lineage-absent OUTPUT contract |
| FE pattern test for `FORBIDDEN_RESPONSE_FIELDS` over `*Response` models | DEFERRED | C3 §4.1 plan reserved the option to add ONE assertion to `frontend-api/tests/test_no_source_leak.py`; not exercised here |
| Token-list expansion in C3 prefix-only suites | DEFERRED | Gated on `FORBIDDEN_PAYLOAD_FIELDS` extension (M1-D step 5) — would otherwise cause false positives on canonical_writer.py |
| `FORBIDDEN_PAYLOAD_FIELDS` extension to include lineage | NOT DONE | Gated on M1-D step 5 (retire legacy canonical specs); cannot land before that — would break legacy canonical writer roundtrip |
| Manifest-level guarantee: published formal tables for canonical_v2.* and canonical_lineage.* are pinned together | DEFERRED | Per M1-A §4: sidecar v2 schema in `_mart_snapshot_set.json` holds canonical_v2 + canonical_lineage snapshot ids; `cycle_publish_manifest` PG schema unchanged this round |
| Read-only inspection of frontend-api response models | DONE (per C3 §2.2 + this round's grep confirms 0 lineage hits in frontend-api source) | Frontend-api source itself is clean; leak comes from upstream `FormalObject.payload` |

---

## 4. What this M1-E delivery does NOT do (intentional non-claims)

- Does NOT change any business route in `frontend-api/`.
- Does NOT enable raw debug routes.
- Does NOT add a new write API.
- Does NOT modify `serving/formal.py` to filter `FormalObject.payload` (would change behavior for legacy consumers).
- Does NOT extend `FORBIDDEN_PAYLOAD_FIELDS` in `canonical_writer.py` (would break legacy `canonical.dim_security` writes — gated on M1-D step 5 retiring the legacy spec).
- Does NOT exercise the option from C3 §4.1 to add a single pattern-based assertion in `frontend-api/tests/test_no_source_leak.py` (kept as user-opt-in for later).
- Does NOT touch `/Users/fanjie/Desktop/BIG/FrontEnd` (read-only for this gate per M0.3).

---

## 5. Hardening plan for the residual gaps (PLAN, not executed)

### 5.1 `_legacy_payload(...)` route in `routes/cycle.py`

Two complementary fixes; pick one based on rollout cost:

- **Option A (quick, defensive)**: in `routes/cycle.py:81-82`, before forwarding `FormalObject.payload.to_pylist()` to the response, drop any column whose name is in `FORBIDDEN_RESPONSE_FIELDS = {"source_run_id", "raw_loaded_at", "submitted_at", "ingest_seq"}` (and once C2 step 5 lands, also `"ts_code"`, `"index_code"`). Add a focused test asserting the filter applies. This is a 1-2 line code change in `cycle.py` plus a fixture-driven test.
- **Option B (cleaner, slower)**: introduce a typed `LegacyFormalPayloadResponse` Pydantic model with explicit field allowlist; use it for `_legacy_payload`. Eventually deprecate the route. This is a larger refactor.

Either fix is gated on user approval ("no business route changes" per ult_milestone.md is the current constraint) and would land in a future M1.4 increment.

### 5.2 `FormalObject.payload` schema test

A schema-shape test that asserts `FormalObject.payload.schema.names` does NOT include lineage fields. This requires either:
- A real Iceberg snapshot to inspect (gated on M1-D actually writing `canonical_v2.dim_security`).
- A mock that exercises `formal_table_identifier` + a fake snapshot reader.

Either approach can land in `tests/serving/test_formal.py` once M1-D's reader cutover (step 4) is complete.

### 5.3 Pattern test for `*Response` models in `frontend-api/tests/test_no_source_leak.py`

Per C3 §4.1: walk every `*Response` model under `frontend_api/schemas/`, recursively enumerate field names via `model.model_fields`, assert no field name is in `FORBIDDEN_RESPONSE_FIELDS`. ~30 lines, single assertion. User-opt-in per the approved C3 plan.

### 5.4 Canonical writer `FORBIDDEN_PAYLOAD_FIELDS` extension (gated on M1-D step 5)

Per C3 §4.4: extend `FORBIDDEN_PAYLOAD_FIELDS` in `canonical_writer.py:34` to include `source_run_id` and `raw_loaded_at`. Only safe AFTER all canonical mart tables migrate to `canonical_v2.*` (step 5) — otherwise the legacy writer fails the validator. Currently 1 of 8 canonical mart tables has migrated (`dim_security` only).

---

## 6. Hard-rule reaffirmation

- `project_ult_v5_0_1.md` NOT modified.
- P5 shadow-run NOT started.
- M2/M3/M4 NOT entered.
- Production fetch NOT enabled.
- Compose NOT started.
- API-6, sidecar, frontend write API, Kafka/Flink/Temporal, news/Polymarket flows NOT introduced.
- Tushare remains a `provider="tushare"` adapter ONLY.
- No business route changes in `frontend-api/`.
- No raw debug routes enabled.
- No `git init`. No commits. No pushes.
- The only new file added in this round is `data-platform/tests/cycle/test_current_cycle_inputs_lineage_absent.py` and this report.

---

## 7. Findings tally

- **CONFIRMED** (4):
  1. `current_cycle_inputs._current_cycle_row` OUTPUT keys are provider-neutral and lineage-free (3 tests passing).
  2. `current_cycle_inputs.__all__` does not re-export forbidden symbols.
  3. C3-era prefix-token tests continue to PASS (data-platform 2/2 + frontend-api 4/4).
  4. Frontend-api source code does not reference lineage fields directly (0 grep hits, per C3 §1.4).
- **PARTIAL** (3):
  1. `_legacy_payload(...)` route in `routes/cycle.py` still forwards `FormalObject.payload` verbatim — leak path open until either Option A or B in §5.1 lands. Not in M1-E scope ("no business route changes").
  2. `FormalObject.payload` schema test deferred — gated on M1-D reader cutover.
  3. Canonical writer `FORBIDDEN_PAYLOAD_FIELDS` extension deferred — gated on M1-D step 5 (retire legacy canonical specs). 7 of 8 canonical mart tables not yet migrated.
- **INFERRED** (0).

---

## 8. Per-task handoff block

```
Task: M1-E formal serving no-source hardening (test addition + plan)
Repo(s): data-platform + frontend-api (read-only inspection only) + assembly
Output (proof): /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/formal-serving-no-source-leak-proof-20260428.md
Output (test added): data-platform/tests/cycle/test_current_cycle_inputs_lineage_absent.py
Validation commands:
  1. cd data-platform && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -p no:cacheprovider tests/cycle/test_current_cycle_inputs_lineage_absent.py
  2. cd data-platform && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -p no:cacheprovider -q tests/provider_catalog/test_no_source_leak.py
  3. cd frontend-api && PYTHONDONTWRITEBYTECODE=1 ../assembly/.venv-py312/bin/python -m pytest -p no:cacheprovider -q tests/test_no_source_leak.py
Validation results:
  1. PASS — 3 passed in 0.14s
  2. PASS — 2 passed in 0.02s (C3 baseline unchanged)
  3. PASS — 4 passed in 0.17s (C3 baseline unchanged)
Per-subrepo git state:
  data-platform: rev-parse HEAD = 330f6b4; status = M src/data_platform/raw/writer.py + M tests/raw/test_writer.py (pre-existing) + M1-D vertical-slice files + new untracked test file from M1-E; push = not pushed; branch = main; interpreter = data-platform/.venv/bin/python (Python 3.14.3)
  frontend-api:  rev-parse HEAD = 0c24fad; status = M README.md (pre-existing); push = not pushed; branch = main; interpreter = ../assembly/.venv-py312/bin/python (Python 3.12.12 — fallback)
  assembly:      rev-parse HEAD = a7f19c5; status = untracked stabilization reports include this M1-E proof; push = not pushed; branch = main
Dirty files added by this task:
  data-platform/tests/cycle/test_current_cycle_inputs_lineage_absent.py (NEW)
  assembly/reports/stabilization/formal-serving-no-source-leak-proof-20260428.md (NEW)
Findings: 4 CONFIRMED, 3 PARTIAL, 0 INFERRED
Outstanding risks:
  - _legacy_payload route in routes/cycle.py forwards FormalObject.payload verbatim — leak path open
  - FormalObject.payload schema test deferred to M1.4 next increment
  - canonical writer FORBIDDEN_PAYLOAD_FIELDS extension deferred to M1-D step 5
  - 7 of 8 canonical mart tables still on legacy specs (M1-D blocker scoreboard)
Declaration: I did not modify project_ult_v5_0_1.md. I did not enter M2/M3/M4. I did not enable production fetch. I did not start P5 shadow-run. I did not start compose. I did not change any frontend-api business route. I did not enable raw debug routes. I did not add any frontend write API. I did not commit any forbidden files. I did not run `git init`. I did not push without approval. Tushare remains a provider=tushare adapter only.
```
