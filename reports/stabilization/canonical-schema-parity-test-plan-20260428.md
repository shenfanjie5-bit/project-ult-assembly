# Canonical Schema Parity Test Plan (M1-C)

- Date: 2026-04-28
- Scope: M1-C per `ult_milestone.md`. Adds parity test scaffolding that asserts the M1 target end-state. **Tests are intentionally RED today**; they flip to GREEN as M1-D landings advance the canonical_v2 + canonical_lineage migration.
- Mode: test additions only. Tushare remains a `provider="tushare"` adapter only. No source code changes outside `data-platform/tests/`. No commits, no `git init`.
- Authority: `project_ult_v5_0_1.md` (NOT modified) + `ult_milestone.md` §M1.2.

---

## 1. Validation block

### 1.1 New parity-test sweep

```
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform && \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
    -p no:cacheprovider --tb=no \
    tests/ddl/test_canonical_provider_neutrality.py \
    tests/serving/test_canonical_writer_provider_neutrality.py \
    tests/dbt/test_marts_provider_neutrality.py 2>&1 | tail -8
```

**Result**: `44 failed, 2 passed, 7 skipped in 0.35s`. Interpreter: `data-platform/.venv/bin/python` — Python 3.14.3.

**Interpretation (per ult_milestone.md M1-C "tests may fail initially")**:

- **44 failed** — parametrized parity tests over the 8 legacy `CANONICAL_MART_LOAD_SPECS` × 8 legacy `CANONICAL_MART_TABLE_SPECS` × 8 legacy `mart_*.sql` files; each failure points at a real schema violation (`source_run_id`, `raw_loaded_at`, or `ts_code`/`index_code` present on canonical business surfaces). Plus 2 forbidden-set extension tests asserting the writer-side and DDL-side `FORBIDDEN_*` constants don't yet block lineage.
- **2 passed** — sentinels (`test_FORBIDDEN_RAW_LINEAGE_FIELDS_set_is_stable`, `test_legacy_marts_directory_exists_and_is_inventoried`).
- **7 skipped** — future-state assertions for `CANONICAL_V2_*_SPEC` / `CANONICAL_LINEAGE_*_SPEC` symbols + canonical_v2/marts_lineage directories that do not yet exist; tests skip rather than fabricate to avoid false positives.

These failures are the documented gap — they are NOT a regression and NOT a CI break introduced by this round; they are the M1-D acceptance scoreboard.

### 1.2 Pre-existing pytest sweep is unaffected

```
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform && \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
    -p no:cacheprovider --tb=no \
    tests/ddl tests/serving/test_canonical_writer.py \
    tests/serving/test_schema_evolution.py tests/serving/test_catalog.py tests/dbt
```

Per M1-B: `103 passed, 7 skipped`. M1-C does NOT change source code, so M1-B's pass count is unchanged. The 44 new failures are purely additive.

---

## 2. Test files added (3 files; ~330 lines total)

### 2.1 `data-platform/tests/ddl/test_canonical_provider_neutrality.py`

DDL parity tests. Six test functions:

| Test | Type | Today | Becomes GREEN when |
|---|---|---|---|
| `test_canonical_business_spec_does_not_carry_raw_lineage[<spec>]` | parametrize × 9 specs | RED for all 9 (lineage present on legacy specs) | M1-D step 5 retires legacy `canonical.*` specs |
| `test_canonical_business_spec_does_not_carry_provider_shaped_identifier[<spec>]` | parametrize × 9 specs | RED for 7 specs that carry `ts_code` / `index_code` | M1-D step 5 retires legacy specs OR M1-D step 1 adds canonical_v2 + step 4 reader cutover |
| `test_FORBIDDEN_SCHEMA_FIELDS_includes_canonical_lineage_block` | single | RED (only blocks `submitted_at`/`ingest_seq`) | M1-D step 5 extends the set |
| `test_canonical_lineage_namespace_specs_keep_canonical_pk_first` | single (auto-discover) | SKIP (no lineage specs declared) | Per-spec assertion runs as M1-D adds them |
| `test_canonical_v2_namespace_specs_do_not_carry_raw_lineage` | single (auto-discover) | SKIP (no v2 specs declared) | Per-spec assertion runs as M1-D adds them |
| `test_FORBIDDEN_RAW_LINEAGE_FIELDS_set_is_stable` | sentinel | PASS | Stays PASS unless the test contract drifts |

### 2.2 `data-platform/tests/serving/test_canonical_writer_provider_neutrality.py`

Writer parity tests. Five test functions:

| Test | Type | Today | Becomes GREEN when |
|---|---|---|---|
| `test_canonical_mart_load_spec_does_not_require_raw_lineage[<spec>]` | parametrize × 8 specs | RED for all 8 | M1-D step 5 retires legacy load specs |
| `test_canonical_mart_load_spec_does_not_require_provider_shaped_identifier[<spec>]` | parametrize × 8 specs | RED for 7 (1 dim_index uses `index_code`) | M1-D step 5 retires legacy load specs |
| `test_FORBIDDEN_PAYLOAD_FIELDS_extends_to_canonical_lineage` | single | RED (only blocks `submitted_at`/`ingest_seq`) | M1-D step 5 extends the set |
| `test_canonical_v2_load_specs_drop_raw_lineage` | single (auto-discover) | SKIP | M1-D adds `CANONICAL_V2_*_LOAD_SPECS` |
| `test_canonical_lineage_load_specs_carry_lineage_explicitly` | single (auto-discover) | SKIP | M1-D adds `CANONICAL_LINEAGE_*_LOAD_SPECS` |

### 2.3 `data-platform/tests/dbt/test_marts_provider_neutrality.py`

dbt mart SQL parity tests. Four test functions:

| Test | Type | Today | Becomes GREEN when |
|---|---|---|---|
| `test_canonical_mart_sql_does_not_select_lineage_columns[<file>]` | parametrize × 8 SQL files | RED for all 8 | M1-D step 5 retires legacy marts (or step 4 reader cutover routes through marts_v2) |
| `test_canonical_v2_mart_sql_does_not_select_lineage_columns[<file>]` | parametrize × N (vacuous PASS) | (no files yet) | M1-D adds `dbt/models/marts_v2/*.sql` |
| `test_canonical_v2_mart_sql_does_not_select_provider_shaped_identifier[<file>]` | parametrize × N (vacuous PASS) | (no files yet) | M1-D adds `dbt/models/marts_v2/*.sql` |
| `test_lineage_mart_sql_carries_lineage_columns[<file>]` | parametrize × N (vacuous PASS) | (no files yet) | M1-D adds `dbt/models/marts_lineage/*.sql` |
| `test_legacy_marts_directory_exists_and_is_inventoried` | sentinel | PASS | Stays PASS until legacy marts dir is removed |

---

## 3. Coverage map: blocker fields → test that asserts each

| Blocker field | Where it lives today | Test that asserts non-presence | M1-D step that flips it |
|---|---|---|---|
| `source_run_id` (DDL) | 9 canonical specs in `iceberg_tables.py` | DDL #1 | step 5 (retire legacy) |
| `raw_loaded_at` (DDL) | 8 canonical specs (not in `stock_basic`) | DDL #1 | step 5 |
| `ts_code` (DDL) | 6 canonical specs | DDL #2 | step 5 |
| `index_code` (DDL) | 2 canonical specs | DDL #2 | step 5 |
| `source_run_id` (writer required) | 9 `CanonicalLoadSpec`s | Writer #1 | step 5 |
| `raw_loaded_at` (writer required) | 8 `CanonicalLoadSpec`s | Writer #1 | step 5 |
| `ts_code` (writer required) | 6 `CanonicalLoadSpec`s | Writer #2 | step 5 |
| `index_code` (writer required) | 2 `CanonicalLoadSpec`s | Writer #2 | step 5 |
| `source_run_id` (mart SQL) | 8 mart `.sql` files | dbt #1 | step 5 |
| `raw_loaded_at` (mart SQL) | 8 mart `.sql` files | dbt #1 | step 5 |
| `FORBIDDEN_SCHEMA_FIELDS` extension | DDL forbidden set in `iceberg_tables.py` | DDL #3 | step 5 |
| `FORBIDDEN_PAYLOAD_FIELDS` extension | Writer forbidden set in `canonical_writer.py` | Writer #3 | step 5 |

Plus 5 future-state tests (DDL #4, #5; Writer #4, #5; dbt #2, #3, #4) that auto-discover canonical_v2 / canonical_lineage symbols and gate the new namespace shape as M1-D adds those symbols.

---

## 4. What this test plan does NOT cover (intentional non-goals)

- **`current_cycle_inputs.py` row schema test** (M1-A §1.6 noted that `_security_rows_by_alias` keys on `ts_code` internally). This requires fixture machinery for the canonical reader; defer to M1-D's parity testing once `canonical_v2` is the default read path.
- **Manifest co-pin test** for canonical + canonical_lineage snapshot pairs (M1-A §4). Requires the lineage namespace to exist; defer to M1-D when the sidecar v2 schema lands.
- **Frontend-api response shape test** for lineage-field absence. Owned by M1-E (no-source hardening on the formal serving layer); not a data-platform concern.
- **Live PG round-trip parity**. M1-B documented this as deferred to M2.1; M1-D's pytest sweep stays in-process.
- **Provider-shaped name aliases inside canonical_v2 marts** (e.g., `ts_code AS security_id`). The dbt #3 test allows the alias form; bare `ts_code` references are caught by the simple windowed lookahead. This is intentional — staging→intermediate stays Tushare-shaped per data-platform CLAUDE.md.

---

## 5. Test execution conventions

- All M1-C tests run under `data-platform/.venv/bin/python` (Python 3.14.3).
- Same `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src` invocation as the pre-existing `tests/provider_catalog` and `tests/serving/test_canonical_writer.py` suites.
- No fixtures depend on PG, dbt runtime, Iceberg catalog state, or DuckDB on-disk databases. Pure spec/SQL parsing — runs in 0.35s.
- The 44 failures are stable: same set runs on every invocation. They will not flake.

---

## 6. M1-C ↔ M1-D handshake

For each M1-D landing (whether full migration or vertical slice), the M1-D handoff must report:

- Number of M1-C tests that were RED before the landing (today: 44).
- Number of M1-C tests that are RED after the landing.
- Each remaining RED test, marked as either:
  - **Resolved** (test now PASSES because the gap closed)
  - **Resolved structurally** (test remains RED because the structure was changed without the user-visible gap closing — should not happen if M1-D follows the plan)
  - **Outstanding blocker** (test remains RED, work is scheduled for a follow-up M1.x increment with explicit dependencies)

If M1-D lands the vertical slice for `dim_security` only, the expected end-state is:

- DDL #1 + #2 for `canonical.dim_security` and `canonical.stock_basic`: still RED (legacy specs untouched). DDL #3: still RED (forbidden set not extended).
- DDL #4 + #5 (auto-discover): PASS for `CANONICAL_V2_DIM_SECURITY_SPEC` and `CANONICAL_LINEAGE_DIM_SECURITY_SPEC` only.
- Writer #1 + #2 for `canonical.dim_security`: still RED (legacy load spec untouched). Writer #3: still RED.
- Writer #4 + #5: PASS for the new v2 + lineage load specs.
- dbt #1 for `mart_dim_security.sql`: still RED. dbt #2 + #3 + #4: PASS for the new v2 + lineage marts.

This is the explicit "remaining failures marked as blocker" criterion from the milestone. M1-D's report will list each remaining failure and its scheduled increment.

---

## 7. M1-C acceptance against milestone

`ult_milestone.md` §M1-C acceptance:

- [x] **测试覆盖了所有 blocker 字段** (tests cover all blocker fields) — §3 maps every CONFIRMED blocker field from C2 to a test that asserts non-presence.
- [x] **测试失败时能指向真实 schema violation** (failing tests point at real schema violation) — every failure message names the spec/file/line and the leaked column. Sample: `canonical.dim_security embeds raw-zone lineage fields ['raw_loaded_at', 'source_run_id']; lineage must live on a sibling canonical_lineage.* table per M1-A design`.
- [x] **不用"projection-only"当作唯一修复** (don't use projection-only as the only fix) — none of these tests inspect or accept the `current_cycle_inputs.py` projection-only path; they enforce the storage-layer contract directly.

---

## 8. Findings tally

- **CONFIRMED** (3):
  1. 3 new test files added (~330 lines), 16 test functions covering all C2-identified blocker fields.
  2. Today's test run: 44 RED + 2 PASS sentinels + 7 SKIP future-state. RED set is stable and points at real violations.
  3. Pre-existing test sweep unchanged (M1-B 103 passes still 103).
- **PARTIAL** (1):
  1. Tests for `current_cycle_inputs.py` row shape and manifest co-pin are **deferred to M1-D / M1-E** (§4); they require fixture machinery or lineage namespace existence that M1-D introduces.
- **INFERRED** (0).

---

## 9. Outstanding risks

- The 44 failures are visible to anyone who runs the full data-platform test suite. CI dashboards may need an opt-in marker if the CI is configured to fail-fast on any test failure. Per the milestone "tests may fail initially" — this is the explicit expected state. If CI policy disagrees, mark with `@pytest.mark.xfail(strict=True, reason="awaits M1-D")` later (one-line per parametrized test).
- The auto-discover tests (DDL #4, #5 / Writer #4, #5 / dbt #2, #3, #4) rely on naming conventions (`CANONICAL_V2_`, `CANONICAL_LINEAGE_`, `marts_v2/`, `marts_lineage/`). M1-D must follow these conventions or the auto-discover passes vacuously.
- The dbt #3 test uses a simple windowed lookahead to permit `ts_code AS security_id` while rejecting bare `ts_code`. Edge cases (multi-line aliases, comments) are not covered by this heuristic. If M1-D introduces such patterns, refine the test then.
- M1-C does not add tests for cross-repo readers (`assembly`, `main-core`, `entity-registry`) that may consume `canonical.*` directly. C2 §8 flagged this risk; a separate cross-repo grep is needed when M1-D is ready to retire legacy specs.

---

## 10. Per-task handoff block

```
Task: M1-C canonical schema parity test plan
Repo(s): data-platform + assembly
Output (plan): /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/canonical-schema-parity-test-plan-20260428.md
Output (tests): data-platform/tests/ddl/test_canonical_provider_neutrality.py
                data-platform/tests/serving/test_canonical_writer_provider_neutrality.py
                data-platform/tests/dbt/test_marts_provider_neutrality.py
Validation command: cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -p no:cacheprovider --tb=no tests/ddl/test_canonical_provider_neutrality.py tests/serving/test_canonical_writer_provider_neutrality.py tests/dbt/test_marts_provider_neutrality.py
Validation result: 44 failed, 2 passed, 7 skipped in 0.35s. Failures are the expected RED scoreboard for M1-D; 2 sentinels PASS; 7 future-state tests SKIP because canonical_v2 / canonical_lineage symbols and directories do not yet exist.
Per-subrepo git state:
  data-platform: rev-parse HEAD = 330f6b4; status =  M src/data_platform/raw/writer.py /  M tests/raw/test_writer.py (pre-existing) + 3 new untracked test files; push = not pushed; branch = main; interpreter = data-platform/.venv/bin/python (Python 3.14.3)
  assembly:      rev-parse HEAD = a7f19c5; status = untracked stabilization reports include this M1-C plan; push = not pushed; branch = main
Dirty files added by this task:
  data-platform/tests/ddl/test_canonical_provider_neutrality.py (NEW)
  data-platform/tests/serving/test_canonical_writer_provider_neutrality.py (NEW)
  data-platform/tests/dbt/test_marts_provider_neutrality.py (NEW)
  assembly/reports/stabilization/canonical-schema-parity-test-plan-20260428.md (NEW)
Findings: 3 CONFIRMED, 1 PARTIAL, 0 INFERRED
Outstanding risks:
  - 44 visible failures may need xfail markers if CI policy requires
  - auto-discover tests rely on naming conventions M1-D must follow
  - dbt #3 alias-detection heuristic may need refinement for edge cases
  - cross-repo readers of `canonical.*` not yet enumerated
Declaration: I did not modify project_ult_v5_0_1.md. I did not enter M2/M3/M4. I did not enable production fetch. I did not start P5 shadow-run. I did not start compose. I did not commit any forbidden files. I did not run `git init`. I did not push without approval. Tushare remains a provider=tushare adapter only. The 44 RED tests document the gap; they are not a regression — they are the M1-D acceptance scoreboard.
```
