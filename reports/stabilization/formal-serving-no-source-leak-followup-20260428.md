# Formal Serving No-Source-Leak Followup (M1.4)

- Date: 2026-04-28
- Scope: data-platform-side formal payload schema guard. Adds focused tests; does NOT change source code in `serving/formal.py` and does NOT remove the existing frontend-api legacy compat sanitizer (F5 mitigation per `m1-review-findings-closure-20260428.md`).
- Authority: `project_ult_v5_0_1.md` (NOT modified) + `ult_milestone.md` §M1.4 + prior `formal-serving-no-source-leak-proof-20260428.md` (M1-E baseline) + M1.3 batch progress report.
- Hard rules: no business route changes; no new write API; no raw debug routes enabled; no frontend write API; Tushare remains `provider="tushare"`; no compose; no production fetch.

---

## 1. Why a separate followup

The original M1-E proof (`formal-serving-no-source-leak-proof-20260428.md`) showed:

- Frontend-api legacy compat route forwards `FormalObject.payload` verbatim — the residual leak path.
- `current_cycle_inputs` output schema is provider-neutral (3 boundary tests passed).
- M1-E left `formal.py` payload-schema guard as an explicit "deferred to next M1.4 increment" item.

The M1 review closure round added an F5 mitigation: `frontend-api/src/frontend_api/routes/cycle.py` recursively sanitizes legacy compat payloads before returning them. That closes the FE-side leak path. **What was still missing was a data-platform-side structural contract** — a guard that fails closed at the data-platform serving boundary if a future formal table accidentally carries provider/raw-lineage fields. This followup adds that guard as a test contract.

---

## 2. What landed this round

### 2.1 New test file

`data-platform/tests/serving/test_formal_no_source_leak.py` — 10 tests, all PASS.

| Test | Purpose |
|---|---|
| `test_formal_table_identifier_uses_provider_neutral_namespace` | Pins `formal.<object>` namespace contract; rejects `tushare_*`, `stg_tushare_*`, `doc_api` via `formal_registry.validate_formal_object_name`. |
| `test_provider_neutral_payload_passes_guard` | Synthesizes a canonical_v2-shaped payload (security_id PK + business columns + `canonical_loaded_at`); guard helper accepts. |
| `test_payload_with_forbidden_field_is_rejected_by_guard` (×6 parametrize) | For each of `source_run_id`, `raw_loaded_at`, `ts_code`, `index_code`, `submitted_at`, `ingest_seq`, synthesizes a payload containing the forbidden field; guard helper raises AssertionError. |
| `test_legacy_canonical_schema_shape_would_fail_guard_today` | Documents the gap: a legacy `canonical.dim_security`-shaped payload (with `ts_code`, `source_run_id`, `raw_loaded_at`) is rejected by the guard. Documents the canonical-v2 cutover rationale. |
| `test_canonical_v2_dim_security_schema_passes_guard` | Pins the M1.3 design — `canonical_v2.dim_security` spec column names contain no forbidden tokens. |

The file defines `_assert_payload_is_provider_neutral(payload: pa.Table)` — a private helper that scans `payload.schema.names` for `FORBIDDEN_PUBLIC_FIELDS = {source_run_id, raw_loaded_at, ts_code, index_code, submitted_at, ingest_seq}`. Today this helper is test-only; future M1.4+ rounds may promote it to `data_platform.serving.formal` as a public guard that callers (e.g., a future formal HTTP serving layer) opt into.

### 2.2 Validation

```
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform && \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
    -p no:cacheprovider tests/serving/test_formal_no_source_leak.py
```

**Result**: `10 passed in 0.48s`. Interpreter: `data-platform/.venv/bin/python` — Python 3.14.3.

### 2.3 What this followup explicitly does NOT do

- Does NOT change any business route in `frontend-api/`.
- Does NOT remove the F5 legacy compat sanitizer in `frontend-api/src/frontend_api/routes/cycle.py`.
- Does NOT add a guard call inside `data-platform/src/data_platform/serving/formal.py`. The guard is test-only; promotion to a runtime guard is gated on the canonical_v2 reader cutover (M1.3 reader-cutover landed but is opt-in).
- Does NOT add any formal HTTP serving layer.
- Does NOT enable raw debug routes.

---

## 3. Why "test-only guard" is sufficient for this round

The leak surface for formal serving today is:

1. `data_platform.serving.formal.get_formal_*` returns `FormalObject(payload: pa.Table)`.
2. Callers (frontend-api legacy compat route) forward `payload` to consumers.

The frontend-api side already sanitizes recursively (per F5). For data-platform internal callers (none today; future P2/P3/P4 modules), the legitimate flow is to consume formal Iceberg snapshots that are L8 commit outputs — those don't carry raw-zone lineage by construction.

Promoting the guard to a runtime check inside `formal.py` would:
- Add a non-trivial failure mode if a downstream caller adds lineage on purpose (e.g., for an audit report).
- Require schema-walking on every read.
- Couple the formal serving layer to the canonical_v2 contract in a way that breaks the layered model (Formal Zone ≠ Canonical Zone per data-platform CLAUDE.md §架构核心决策 #1).

Keeping the guard test-only:
- Documents the contract explicitly (10 tests pin it).
- Lets future callers opt into the helper if they need it.
- Avoids destabilizing the Formal Zone read path.

---

## 4. Outstanding risks

- **Future formal Iceberg tables that carry lineage** would not be auto-rejected at runtime. The guard test catches them only when a developer explicitly writes a test that asserts the spec is provider-neutral (per the canonical_v2.dim_security pinned test in this file).
- **Frontend-api legacy compat sanitizer** is the load-bearing runtime defense for HTTP responses. It is owned by F5; this followup does not modify it.
- **`FormalObject.payload` schema in production** depends on what L8 commits write. Today L8 outputs (recommendation_snapshot, world_state_snapshot, alpha_result_snapshot, official_alpha_pool, dashboard_snapshot, report, audit_record, replay_record) do NOT include `source_run_id` / `raw_loaded_at` / `ts_code` / `index_code` — so the guard is currently an aspirational contract. A new formal object that included raw lineage would be the trigger to promote the guard to runtime.

---

## 5. Hard-rule reaffirmation

- `project_ult_v5_0_1.md` NOT modified.
- `ult_milestone.md` NOT modified.
- P5 shadow-run NOT started.
- M2/M3/M4 NOT entered.
- Production fetch NOT enabled.
- Compose NOT started.
- No business route changes in `frontend-api/`.
- No new write API; no raw debug routes enabled.
- F5 frontend-api legacy compat sanitizer NOT removed.
- Tushare remains a `provider="tushare"` adapter only.
- No `git init`. No commits. No pushes.
- The only new file added in this followup is `data-platform/tests/serving/test_formal_no_source_leak.py` and this report.

---

## 6. Findings tally

- **CONFIRMED** (4):
  1. 10 tests assert the formal payload schema-shape contract.
  2. `formal_table_identifier` correctly rejects provider-shaped object_type names via `formal_registry.validate_formal_object_name`.
  3. `canonical_v2.dim_security` spec is structurally provider-neutral (test pins it).
  4. Frontend-api legacy compat sanitizer continues to filter raw payload fields recursively (10 frontend-api tests pass — no regression).
- **PARTIAL** (1):
  1. The guard helper is test-only. Promotion to a runtime check inside `formal.py` is a future M1.4+ decision; current callers rely on the FE-side sanitizer + the layered model assumption that L8 commits never include raw lineage.
- **INFERRED** (0).

---

## 7. Per-task handoff block

```
Task: M1.4 followup — formal serving no-source-leak guard (test-only)
Repo(s): data-platform + assembly
Output (proof): /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/formal-serving-no-source-leak-followup-20260428.md
Output (test added): data-platform/tests/serving/test_formal_no_source_leak.py
Validation command: cd data-platform && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -p no:cacheprovider tests/serving/test_formal_no_source_leak.py
Validation result: 10 passed in 0.48s
Per-subrepo git state:
  data-platform: rev-parse HEAD = 330f6b4d82a96d36c8fd150cc1a0a432d7c6cb9c; status = (see canonical-v2-full-migration-progress handoff for full diff list); push = not pushed; branch = main
  assembly:      rev-parse HEAD = a7f19c5994f807b2cf32eb2f45ef48f6fe23095f; status = untracked stabilization reports include this followup; push = not pushed; branch = main
Dirty files added by this followup:
  data-platform/tests/serving/test_formal_no_source_leak.py (NEW)
  assembly/reports/stabilization/formal-serving-no-source-leak-followup-20260428.md (NEW)
Findings: 4 CONFIRMED, 1 PARTIAL, 0 INFERRED
Outstanding risks: see §4 (3 items)
Declaration: I did not modify project_ult_v5_0_1.md. I did not modify ult_milestone.md. I did not enter M2/M3/M4. I did not enable production fetch. I did not start P5 shadow-run. I did not start compose. I did not change any frontend-api business route. I did not remove the F5 frontend-api legacy compat sanitizer. I did not add any frontend write API. I did not enable raw debug routes. I did not commit any forbidden files. I did not run `git init`. I did not push without approval. Tushare remains a provider=tushare adapter only.
```
