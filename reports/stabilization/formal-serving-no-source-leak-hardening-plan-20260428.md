# Formal Serving No-Source-Leak Hardening Plan

- **Task**: C3 (Project ULT v5.0.1 closure audit)
- **Date**: 2026-04-28
- **Repos**: data-platform + frontend-api + assembly
- **Mode**: PLAN-ONLY — no source code changes, no test code added, no commits, no `git init`. Tushare remains a `provider=tushare` adapter only. No business route changes; no new write API; no raw debug routes enabled.
- **Approved plan**: `/Users/fanjie/.claude/plans/project-ult-v5-0-1-cosmic-milner.md` §C3.

---

## 1. Validation block

All four validation commands were executed verbatim from the C3 task instruction.

### 1.1 data-platform — provider catalog no-source-leak test

```
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform && \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
    -p no:cacheprovider -q tests/provider_catalog/test_no_source_leak.py 2>&1 | tail -5
```

Result (exact tail-5 output):

```
..                                                                       [100%]
2 passed in 0.02s
```

Interpreter: `data-platform/.venv/bin/python` → Python 3.14.3.

Interpretation: PASS — the two prefix-token tests
(`test_curated_marts_do_not_expose_provider_specific_contracts`,
`test_formal_serving_registry_is_provider_neutral`) hold against the **current
prefix-only token list** (`tushare_`, `stg_tushare_`, `doc_api`,
`source('tushare'`). PASS does **not** prove the wider scope discussed below;
it confirms only that today's narrow detection still matches.

### 1.2 frontend-api — no-source-leak test

```
cd /Users/fanjie/Desktop/Cowork/project-ult/frontend-api && \
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q \
    tests/test_no_source_leak.py 2>&1 | tail -5
```

`frontend-api/.venv/` does not contain a Python interpreter (only `.gitignore` +
`bin/` directory; no `python` executable). Per the C3 instruction I fell back
to the assembly venv:

```
cd /Users/fanjie/Desktop/Cowork/project-ult/frontend-api && \
  PYTHONDONTWRITEBYTECODE=1 ../assembly/.venv-py312/bin/python -m pytest \
    -p no:cacheprovider -q tests/test_no_source_leak.py 2>&1 | tail -5
```

Result (exact tail-5 output):

```
....                                                                     [100%]
4 passed in 0.17s
```

Interpreter: `assembly/.venv-py312/bin/python` → Python 3.12.12 (fallback;
recorded as deviation from the documented `.venv/bin/python`).

Interpretation: PASS — the four frontend tests
(`test_business_readonly_surfaces_do_not_depend_on_tushare_source_contracts`,
`test_default_readonly_surface_does_not_mount_raw_debug_routes`,
`test_public_contract_excludes_raw_debug_routes`,
`test_data_platform_public_api_fallback_is_disabled_by_default`) confirm:
prefix tokens absent across 9 enumerated business surfaces; raw debug routes
are not mounted by default; `data-platform` public API fallback is disabled.

### 1.3 Repo-wide prefix-token grep (line count)

```
cd /Users/fanjie/Desktop/Cowork/project-ult && \
  rg -n 'tushare_|stg_tushare_|doc_api' \
    data-platform/src/data_platform/dbt/models/marts \
    data-platform/src/data_platform/serving \
    frontend-api/src/frontend_api 2>&1 | wc -l
```

Result: `0`.

Interpretation: zero hits — no prefix-token leaks in marts, formal serving, or
frontend-api source. Consistent with §1.1 and §1.2 PASS.

### 1.4 Repo-wide lineage-field grep (line count)

```
cd /Users/fanjie/Desktop/Cowork/project-ult && \
  rg -n 'source_run_id|raw_loaded_at' \
    data-platform/src/data_platform/serving \
    frontend-api/src/frontend_api 2>&1 | wc -l
```

Result: `17`.

All 17 hits are inside
`data-platform/src/data_platform/serving/canonical_writer.py` (lines 136, 169,
170, 183, 184, 204, 205, 250, 251, 267, 268, 313, 314, 335, 336, 356, 357 —
each one is either `"source_run_id",` or `"raw_loaded_at",` inside a
`CanonicalLoadSpec.required_columns` tuple). Zero hits in
`frontend-api/src/frontend_api`. The presence of these 17 lineage-field
references at the canonical writer is exactly the leak surface the wider
detection scope must cover; today's tests cannot see them because the token
list is prefix-only.

---

## 2. Current detection scope (CONFIRMED)

### 2.1 data-platform prefix-token test

`data-platform/tests/provider_catalog/test_no_source_leak.py` defines:

- L13 `FORBIDDEN_BUSINESS_TOKENS = ("doc_api", "tushare_", "stg_tushare_", "source('tushare'")`.
- L8 `MARTS_DIR = PROJECT_ROOT / "src" / "data_platform" / "dbt" / "models" / "marts"`.
- L9–L12 `FORMAL_SERVING_MODULES = (data_platform/serving/formal.py,
  data_platform/formal_registry.py)`.

Two assertions:

- L16–L28 `test_curated_marts_do_not_expose_provider_specific_contracts` —
  every `*.sql` under `marts/` must not contain any forbidden token; also
  forbids direct `ref('stg_…` references.
- L31–L39 `test_formal_serving_registry_is_provider_neutral` — both formal
  serving modules must not contain any forbidden token.

CONFIRMED scope: **prefix-only token search** over **two folders / two files**.
No lineage field detection. No regex / pattern detection. No JSON-shape
detection.

### 2.2 frontend-api prefix-token test

`frontend-api/tests/test_no_source_leak.py` defines:

- L21 `FORBIDDEN_SOURCE_TOKENS = ("stg_tushare_", "doc_api", "tushare_")`.
- L22–L25 `FORBIDDEN_DEFAULT_ROUTE_TOKENS = ("/api/project-ult/data/raw/{source}",
  "/api/project-ult/debug/data/raw/{source}")`.
- L11–L20 `BUSINESS_SURFACE_FILES` (9 entries):
  - `src/frontend_api/public.py`
  - `src/frontend_api/routes/entity_data.py`
  - `src/frontend_api/routes/cycle.py`
  - `src/frontend_api/routes/graph.py`
  - `src/frontend_api/routes/operations.py`
  - `src/frontend_api/adapters/data_platform_adapter.py`
  - `src/frontend_api/adapters/graph_adapter.py`
  - `src/frontend_api/adapters/operations_adapter.py`
  - (8 distinct files; the test header still calls it "9 business surfaces" —
    the actual Python tuple length is 8. This is a **fact-of-the-code**
    discrepancy worth recording; it does NOT change PASS status.)

Four assertions:

- L28–L36 — surface files must not contain prefix tokens.
- L39–L44 — default app from `create_app(FrontendApiSettings(project_root=tmp_path))`
  must not mount `/api/project-ult/data/raw/{source}` or
  `/api/project-ult/debug/data/raw/{source}`.
- L47–L53 — `public.py` text must not contain those route paths.
- L56–L65 — `FrontendApiSettings.allow_data_platform_public_api_fallback is
  False`; `DataPlatformReadAdapter._load_public_callable(...)` returns the
  "fallback disabled" sentinel.

CONFIRMED scope: **prefix-only token search** + **route-shape ban-list** +
**fallback-flag default**. No body/payload schema test. No lineage field
detection.

### 2.3 Canonical writer payload guard

`data-platform/src/data_platform/serving/canonical_writer.py`:

- L34 `FORBIDDEN_PAYLOAD_FIELDS = frozenset({"submitted_at", "ingest_seq"})`.
- L74–L81 — `CanonicalLoadSpec.__post_init__` rejects any spec whose
  `required_columns` lower-cases to a forbidden field.
- L562–L572 `_validate_no_forbidden_payload_fields` — same check at write time
  against the materialised PyArrow schema.

CONFIRMED block-list at the canonical writer boundary: only `submitted_at` and
`ingest_seq` (per data-platform CLAUDE.md "BAN" rule for ingest metadata).
`source_run_id` and `raw_loaded_at` are **explicitly required columns** in 9 of
9 enumerated specs (L136, L169–170, L183–184, L204–205, L250–251, L267–268,
L313–314, L335–336, L356–357), so they pass the writer's own check by design.

### 2.4 Frontend boundary surface (read-only)

Read confirms the four route modules behave as documented:

- `routes/entity_data.py` L16, L53–L60 — `debug_router` defines
  `/api/project-ult/debug/data/raw/{source}`. `__init__.py`/wiring keeps it
  off the default app (per §1.2 `test_default_readonly_surface_does_not_mount_raw_debug_routes`).
- `routes/cycle.py` L18–L86 — `/api/project-ult/cycles*`,
  `/api/project-ult/formal/{object_type}[/{cycle_id}]`,
  `/api/project-ult/manifests/latest`, plus three `/api/world-state|pool|recommendations/latest`
  legacy compat routes that all delegate to `_adapter(request).get_formal_object(...)`.
- `routes/graph.py` L15–L55 — `/api/project-ult/graph/{subgraph,paths,impact}`.
- `routes/operations.py` L20–L96 — reasoner / audit / replay / backtests /
  orchestrator runs.
- `routes/system.py` L16–L45 — `/api/project-ult/{health,modules,profiles,compat}`.

Returned models are `*Response` Pydantic schemas defined under
`frontend_api/schemas/*.py` and the legacy compat route returns
`FormalObject.payload` directly — that payload is a PyArrow table from
`data_platform.serving.formal.get_formal_latest(...)` which reads the
manifest-pinned canonical Iceberg snapshot **including** the `source_run_id`
and `raw_loaded_at` columns required by `canonical_writer.py`.

---

## 3. Coverage gaps (CONFIRMED)

### 3.1 Lineage fields are undetected at every boundary

- `source_run_id` and `raw_loaded_at` appear 17 times in
  `data-platform/src/data_platform/serving/canonical_writer.py` (§1.4) — all
  inside `required_columns` of `CanonicalLoadSpec`s.
- Neither `data-platform/tests/provider_catalog/test_no_source_leak.py`
  (§2.1) nor `frontend-api/tests/test_no_source_leak.py` (§2.2) lists those
  field names in their forbidden token sets.
- Therefore a row leaving `serving/formal.py` (which calls
  `serving_reader.read_iceberg_snapshot(...)` and returns the PyArrow table
  unchanged on L162–L167) will carry `source_run_id` / `raw_loaded_at` columns
  through to any consumer that materialises it — including the
  `frontend-api` legacy compat route `routes/cycle.py` L66–L82 which forwards
  `FormalObject.payload` verbatim. **This leak is undetected today.**

CONFIRMED: lineage-field leakage is not blocked by any current test, and
`canonical_writer.py` `FORBIDDEN_PAYLOAD_FIELDS` does not include them.

### 3.2 `ts_code` is legitimate at canonical, ambiguous at the API edge

- `data-platform/src/data_platform/cycle/current_cycle_inputs.py` L89, L97,
  L392, L405 — `ts_code` is referenced in column lists and row mappings; it
  is the canonical key column today.
- `data-platform/src/data_platform/serving/canonical_writer.py` L128, L143,
  L191, L213, L259, L275, L319, L342 — `ts_code` is the join key in 8 of 9
  `CanonicalLoadSpec`s.
- C2 already labels the broader `ts_code → security_id` rename as a
  CONFIRMED provider-neutral alignment gap (see
  `canonical-physical-schema-alignment-audit-20260428.md`). No-source-leak
  tests cannot help here without a coordinated schema migration; treating
  `ts_code` as a leak today would break legitimate canonical reads.

CONFIRMED: `ts_code` is provider-name-of-truth at canonical; ambiguous (but
not currently a "leak" by definition) at the FE boundary. Detection cannot
move ahead of C2.

### 3.3 No pattern-based detection

- The two test files (§2.1, §2.2) hardcode literal tokens — they cannot match
  `source_*`, `raw_*`, `*_provider`, or any other pattern that future
  providers might introduce.
- A new provider added by name (e.g., `wind_`, `eastmoney_`, `iwencai_`) would
  require a code-change to the test before its leakage is caught.

CONFIRMED: detection is **enumeration-based**; expansion is manual. There is
no defense-in-depth against unknown future provider tokens.

### 3.4 No schema-level test on `current_cycle_inputs()`

- `current_cycle_inputs.py` is positioned (per the approved C2 plan) as a
  "lineage-stripped temporary mitigation" — it drops `source_run_id` and
  `raw_loaded_at` but still surfaces `ts_code`, `trade_date`, `freq`, `close`,
  etc.
- No test asserts the stripped row schema today. If a future change re-adds
  `source_run_id` / `raw_loaded_at` to the projection, no test fails.

CONFIRMED: no boundary schema contract; the mitigation is implicit, not
asserted.

### 3.5 Documented surface count discrepancy

- §2.2 `BUSINESS_SURFACE_FILES` enumerates 8 paths; the supervisor / approved
  plan refer to "9 business surfaces". This may be a tally drift (e.g.,
  `routes/system.py` was historically listed but is not in the test today).
  PARTIAL — fact-of-the-code discrepancy; not a security gap, just an
  inventory drift the team should reconcile when they next touch this test.

---

## 4. Recommended additions (PLAN ONLY — DO NOT IMPLEMENT)

This task adds **zero** test code. The user reserves the right to opt in to
**one** pattern-based assertion in
`frontend-api/tests/test_no_source_leak.py` later. The four items below are
the recommended scope for a future round, in priority order.

### 4.1 Pattern test for `FORBIDDEN_RESPONSE_FIELDS` at the FE response boundary

**Where it would go**: `frontend-api/tests/test_no_source_leak.py`, as a new
test alongside existing `test_business_readonly_surfaces_do_not_depend_on_tushare_source_contracts`.

**Sketch (illustrative — DO NOT add)**:

```python
FORBIDDEN_RESPONSE_FIELDS = frozenset({
    "source_run_id", "raw_loaded_at",
    # candidate patterns (matched as substrings or via a name-set):
    "submitted_at", "ingest_seq",
})
# For each Pydantic *Response model under frontend_api/schemas/, walk the
# field tree (model.model_fields recursively) and assert no field name is
# in FORBIDDEN_RESPONSE_FIELDS. Cover entity_data.py / cycle.py / graph.py /
# operations.py / system.py response models.
```

**Why**: today `FormalObjectResponse.payload` (`schemas/cycle.py`) and the
legacy `_legacy_payload(...)` path (`routes/cycle.py` L81–L82) forward the
PyArrow row dict from `serving.formal.FormalObject.payload` without
field-name filtering. A pattern test on the response shape catches
lineage-field leakage **at the FE boundary** even when the canonical layer
keeps those columns (which it does, by design, until C2's lineage-separation
migration completes).

**Constraint**: assert by **field name**, not by row data — the test must not
require live data fixtures. The model walker should be added once and then
extended as new response schemas land.

### 4.2 Boundary schema test for `current_cycle_inputs()` row shape

**Where it would go**: a new module under
`data-platform/tests/cycle/test_current_cycle_inputs_lineage_absent.py` (does
not exist today; would be added in a future round, not this one).

**Sketch (illustrative — DO NOT add)**:

```python
# Call current_cycle_inputs(...) with a small synthetic fixture and assert
# that the returned row schema names do NOT include {"source_run_id",
# "raw_loaded_at"}. Allow ts_code until C2's rename lands; once lands, switch
# to {"security_id"}.
```

**Why**: pins the temporary mitigation contract. Without it, a future commit
can silently re-introduce lineage fields into the projection and the only
visible failure surface is the FE response-shape test (§4.1) — which depends
on the FE side staying correct. Defense in depth.

**Constraint**: data-platform CLAUDE.md forbids defining business judgement
in this repo, but a row-schema assertion is purely structural.

### 4.3 Token list expansion — lineage-suffix patterns

**Where it would go**: extend
`data-platform/tests/provider_catalog/test_no_source_leak.py` L13
`FORBIDDEN_BUSINESS_TOKENS` and `frontend-api/tests/test_no_source_leak.py`
L21 `FORBIDDEN_SOURCE_TOKENS` with the agreed pattern set.

**Sketch (illustrative — DO NOT add)**:

```python
# data-platform side: keep prefix tokens; ADD a SEPARATE suffix-pattern
# pass (regex or fnmatch) over the same files. Suggested patterns:
#   r'(?<!_)source_run_id(?!\w)'
#   r'(?<!_)raw_loaded_at(?!\w)'
#   r'(?<!\w)provider_[a-z]+(?!\w)'
# but EXCLUDE matches inside canonical_writer.py CanonicalLoadSpec
# required_columns until C2 migration removes them — otherwise the test
# becomes a false-positive generator.
```

**Why**: defense against unknown future providers AND against lineage-field
copies that bypass the prefix list.

**Constraint**: must coordinate with §4.4 — the pattern set is meaningless if
canonical writer still requires lineage columns.

### 4.4 Canonical writer `FORBIDDEN_PAYLOAD_FIELDS` extension (gated by C2)

**Where it would go**:
`data-platform/src/data_platform/serving/canonical_writer.py` L34.

**Sketch (illustrative — DO NOT add)**:

```python
# After C2's lineage-separation migration moves source_run_id/raw_loaded_at
# into a sibling raw_lineage table, extend the frozenset:
FORBIDDEN_PAYLOAD_FIELDS = frozenset({
    "submitted_at", "ingest_seq",
    "source_run_id", "raw_loaded_at",
})
# Drop these columns from every CanonicalLoadSpec.required_columns at
# L136–L357.
```

**Why**: closes the leak at its source. Today the canonical layer is the
**producer** of these columns; until that producer stops requiring them, no
downstream block can be enforced without breaking legitimate canonical reads.

**HARD GATING**: must NOT precede the C2 lineage-separation migration. The C2
report explicitly labels the current canonical schema retention of
`source_run_id` / `raw_loaded_at` as a CONFIRMED provider-neutral alignment
gap; closing it here in isolation would break canonical writes.

---

## 5. Priority ladder

| Tier | Item | Boundary | Gating |
|------|------|----------|--------|
| **High** | §4.4 — extend `FORBIDDEN_PAYLOAD_FIELDS` to include `source_run_id` / `raw_loaded_at`, drop them from `CanonicalLoadSpec`s | canonical → formal storage | gated on C2 lineage-separation migration |
| **High** | §4.2 — boundary schema test on `current_cycle_inputs()` row shape | data-platform internal projection | independent (works today as the temp mitigation contract) |
| **Medium** | §4.1 — pattern test for `FORBIDDEN_RESPONSE_FIELDS` over `frontend_api/schemas/*Response` models | frontend-api response shape | independent; user-opt-in for ONE assertion in this file |
| **Medium** | §4.3 — token-list expansion with regex pattern set (excluding canonical_writer.py until §4.4 lands) | source-text scan | gated on §4.4 (otherwise false positives) |
| **Low** | Raw debug routes — already disabled by default per §1.2 tests; no further action | frontend-api FastAPI router | none — already enforced |
| **Low** | §3.5 — reconcile "9 business surfaces" naming vs the 8-entry tuple | docs/test header | trivial; bundle with the next intentional edit |

---

## 6. Findings tally

- **CONFIRMED**: 6
  - §2.1 data-platform prefix-only scope
  - §2.2 frontend-api prefix-only scope (4 assertions)
  - §2.3 canonical writer block-list = `{submitted_at, ingest_seq}` only
  - §3.1 lineage fields undetected at every boundary
  - §3.3 no pattern-based detection
  - §3.4 no schema-level test on `current_cycle_inputs()`
- **PARTIAL**: 2
  - §3.2 `ts_code` legitimate-but-ambiguous (cannot move without C2)
  - §3.5 surface-count documentation discrepancy (8 vs 9)
- **INFERRED**: 0

(Total: 8 findings, 0 INFERRED, no PARTIAL/PREFLIGHT promoted to PASS.)

---

## 7. Outstanding risks

- **R1** — Canonical writer requires `source_run_id` / `raw_loaded_at` in 9 of
  9 mart specs; until C2's lineage-separation migration ships, every
  manifest-pinned formal read carries those columns into anyone who
  materialises the PyArrow table. The legacy compat routes in
  `routes/cycle.py` L66–L82 forward `FormalObject.payload` directly — this is
  the thinnest leak path today.
- **R2** — `frontend-api/.venv/` lacks a Python interpreter, so this audit
  used `assembly/.venv-py312/bin/python` (Python 3.12.12) as the documented
  fallback. CI/automation that depends on the per-subrepo venv contract will
  diverge from this audit.
- **R3** — The `BUSINESS_SURFACE_FILES` tuple lists 8 entries while the
  approved plan and prior reports say "9 business surfaces". Either a surface
  was dropped (e.g., `routes/system.py` is **not** in the tuple) or the
  documented count is stale.
- **R4** — Pattern-based expansion (§4.3) cannot be enabled in isolation; the
  canonical writer still requires lineage columns by design (§3.1) so any
  pattern hit inside `canonical_writer.py` is a false positive until §4.4
  lands.
- **R5** — `current_cycle_inputs()` is a lineage-stripped temporary mitigation
  per the approved C2 plan, but no test pins that contract today (§3.4). A
  silent regression would only surface at the FE response shape — which is
  itself currently undefended (§3.1).
- **R6** — `data-platform/.venv` runs Python 3.14.3 while the assembly fallback
  runs Python 3.12.12. Any future test addition under §4.1–§4.3 must
  cross-version cleanly (Pydantic / typing details).

---

## 8. Per-task handoff block

```
Task: C3
Repo(s): data-platform + frontend-api + assembly
Output report: /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/formal-serving-no-source-leak-hardening-plan-20260428.md
Validation commands:
  1. cd data-platform && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -p no:cacheprovider -q tests/provider_catalog/test_no_source_leak.py 2>&1 | tail -5
  2. cd frontend-api && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_no_source_leak.py 2>&1 | tail -5
     (frontend-api/.venv lacks an interpreter; fell back to assembly/.venv-py312/bin/python)
  3. cd project-ult && rg -n 'tushare_|stg_tushare_|doc_api' data-platform/src/data_platform/dbt/models/marts data-platform/src/data_platform/serving frontend-api/src/frontend_api 2>&1 | wc -l
  4. cd project-ult && rg -n 'source_run_id|raw_loaded_at' data-platform/src/data_platform/serving frontend-api/src/frontend_api 2>&1 | wc -l
Validation results:
  1. PASS (2 passed in 0.02s)
  2. PASS (4 passed in 0.17s; ran via assembly/.venv-py312/bin/python — fallback recorded)
  3. PASS — count = 0 (no prefix-token leaks in marts / serving / frontend_api)
  4. PARTIAL — count = 17, all in data-platform/src/data_platform/serving/canonical_writer.py CanonicalLoadSpec.required_columns; this is the producer of the leak surface, not itself a "leak" today
Per-subrepo git state:
  data-platform: rev-parse HEAD = 330f6b4d82a96d36c8fd150cc1a0a432d7c6cb9c
                status = " M src/data_platform/raw/writer.py\n M tests/raw/test_writer.py"
                push status = up-to-date with @{u} (0 commits ahead); branch = main; not pushed by this task
                interpreter = .venv/bin/python (Python 3.14.3)
  frontend-api:  rev-parse HEAD = 0c24fad51deabd3b1031dc1315b8d98294392b49
                status = " M README.md"
                push status = up-to-date with @{u} (0 commits ahead); branch = main; not pushed by this task
                interpreter = ../assembly/.venv-py312/bin/python (Python 3.12.12) — fallback because frontend-api/.venv has no python executable
  assembly:      rev-parse HEAD = a7f19c5994f807b2cf32eb2f45ef48f6fe23095f
                status = "?? reports/stabilization/frontend-raw-route-alignment-fix-20260428.md\n?? reports/stabilization/production-daily-cycle-gap-audit-20260428.md\n?? reports/stabilization/project-ult-v5-0-1-supervisor-review-20260428.md\n?? reports/stabilization/raw-manifest-source-interface-hardening-20260428.md" (this task additionally adds formal-serving-no-source-leak-hardening-plan-20260428.md as untracked)
                push status = up-to-date with @{u} (0 commits ahead); branch = main; not pushed by this task
Dirty files:
  data-platform: src/data_platform/raw/writer.py, tests/raw/test_writer.py (pre-existing; not touched by this task)
  frontend-api:  README.md (pre-existing; not touched by this task)
  assembly:      4 prior untracked reports + this task's new report (untracked, not committed)
Findings: 6 CONFIRMED, 2 PARTIAL, 0 INFERRED
Outstanding risks:
  - Canonical writer still requires source_run_id / raw_loaded_at in 9/9 mart specs; legacy compat FE routes forward FormalObject.payload verbatim
  - frontend-api/.venv has no python interpreter; audit used assembly fallback
  - "9 business surfaces" documentation vs 8-entry BUSINESS_SURFACE_FILES tuple
  - §4.3 pattern expansion cannot enable in isolation; gated on §4.4 (which is gated on C2)
  - current_cycle_inputs() temp-mitigation contract not asserted by any test today
  - Python 3.14.3 vs 3.12.12 cross-version compatibility for any future test addition
Declaration: I did not mark any PARTIAL or PREFLIGHT finding as PASS. I did not add any test code. I did not commit any forbidden files. Tushare remains a provider=tushare adapter only. I did not run `git init`. I did not push without approval.
```
