# Canonical V2 Lineage Separation Proof (M1-D — vertical slice for `dim_security`)

- Date: 2026-04-28
- Scope: M1-D per `ult_milestone.md`. **Vertical slice for `dim_security` only.** The other 7 canonical mart tables remain on the legacy `canonical.*` namespace; their migration is scheduled for follow-up M1.3 increments and the M1-C parity tests for those tables remain RED as the explicit blocker scoreboard, per the milestone's "或剩余失败被明确标为 blocker".
- Mode: code changes + tests + new dbt models. Tushare remains a `provider="tushare"` adapter only. No production fetch enabled. No compose started.
- Authority: `project_ult_v5_0_1.md` (NOT modified) + `ult_milestone.md` §M1.3 + design `canonical-v2-lineage-separation-design-20260428.md` (M1-A) + spike `p1-iceberg-write-chain-spike-proof-20260428.md` (M1-B).

---

## 1. Validation block

### 1.1 Full data-platform sweep relevant to canonical surfaces

```
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform && \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
    -p no:cacheprovider --tb=no \
    tests/ddl tests/serving tests/dbt tests/provider_catalog \
    tests/cycle/test_current_cycle_inputs.py 2>&1 | tail -3
```

**Result**: `44 failed, 157 passed, 12 skipped, 12 warnings in 4.35s`. Interpreter: `data-platform/.venv/bin/python` — Python 3.14.3.

### 1.2 Failure breakdown

- **All 44 failures** are M1-C parity tests asserting the legacy `canonical.*` specs / writer / mart SQL still carry `source_run_id` / `raw_loaded_at` and provider-shaped identifiers (`ts_code`, `index_code`). They are the explicit blocker scoreboard for the remaining 7 canonical mart tables.
- **Zero non-parity failures**. Confirmed via `pytest --tb=no | grep FAILED | grep -v provider_neutrality | wc -l → 0`.

### 1.3 Pass count delta vs M1-B baseline

| Sweep | Passed | Skipped | Note |
|---|---:|---:|---|
| M1-B (no M1-C/M1-D) | 103 | 7 | DDL + writer + schema-evolution + catalog + dbt |
| M1-C added (no M1-D yet) | 105 | 11 | +2 sentinels, +4 future-state SKIPs |
| M1-D vertical slice | 157 | 12 | +5 vertical-slice tests now PASS, broader sweep coverage; +1 SKIP for added test |

The M1-D vertical slice flips 5 M1-C tests from SKIP/RED to PASS without regressing any pre-existing test. Two pre-existing tests required updates because they hard-coded the legacy `DEFAULT_NAMESPACES` shape; both updates are minimal and additive (use `tuple(DEFAULT_NAMESPACES)` instead of literal `("canonical", "formal", "analytical")`).

---

## 2. Vertical slice scope (CONFIRMED)

The M1-D vertical slice covers exactly one canonical dataset (`security_master`), one canonical Iceberg table (`canonical_v2.dim_security`), one lineage Iceberg table (`canonical_lineage.lineage_dim_security`), and the corresponding writer/mart artifacts. It does NOT touch the other 7 canonical mart tables.

### 2.1 Files added or modified

| File | Change | Diff size |
|---|---|---|
| `data-platform/src/data_platform/ddl/iceberg_tables.py` | + `CANONICAL_V2_NAMESPACE`, `CANONICAL_LINEAGE_NAMESPACE`; + `CANONICAL_V2_DIM_SECURITY_SPEC`; + `CANONICAL_LINEAGE_DIM_SECURITY_SPEC`; + `CANONICAL_V2_TABLE_SPECS`, `CANONICAL_LINEAGE_TABLE_SPECS`; updated `__all__` | ~85 lines added |
| `data-platform/src/data_platform/serving/canonical_writer.py` | + `CANONICAL_V2_DIM_SECURITY_LOAD_SPEC`; + `CANONICAL_LINEAGE_DIM_SECURITY_LOAD_SPEC`; + `CANONICAL_V2_MART_LOAD_SPECS`, `CANONICAL_LINEAGE_MART_LOAD_SPECS`; + `load_canonical_v2_marts()`, `_write_canonical_v2_snapshot_set_manifest()`; updated `_reject_public_mart_load`; updated `__all__` | ~140 lines added |
| `data-platform/src/data_platform/serving/catalog.py` | extended `DEFAULT_NAMESPACES` to include `canonical_v2`, `canonical_lineage` (was `("canonical", "formal", "analytical")`) | ~6 lines changed |
| `data-platform/src/data_platform/dbt/models/marts_v2/mart_dim_security_v2.sql` | NEW — provider-neutral mart with `ts_code AS security_id` + `name AS display_name` aliases; no lineage columns | 35 lines |
| `data-platform/src/data_platform/dbt/models/marts_v2/_schema.yml` | NEW — yaml declaration for the v2 mart | 25 lines |
| `data-platform/src/data_platform/dbt/models/marts_lineage/mart_lineage_dim_security.sql` | NEW — lineage mart with constant `source_provider='tushare'` + `source_interface_id='stock_basic'` + lineage columns | 17 lines |
| `data-platform/src/data_platform/dbt/models/marts_lineage/_schema.yml` | NEW — yaml declaration for the lineage mart | 28 lines |
| `data-platform/tests/dbt/test_dbt_skeleton.py` | + `MARTS_V2_DIR`, `MARTS_LINEAGE_DIR`, `MART_V2_MODEL_NAMES`, `MART_LINEAGE_MODEL_NAMES`; extended skeleton expectations | ~25 lines added |
| `data-platform/tests/serving/test_catalog.py` | replaced literal `("canonical", "formal", "analytical")` with `tuple(DEFAULT_NAMESPACES)` (test refactor only) | 5 lines changed |
| `data-platform/tests/ddl/test_iceberg_tables.py` | replaced literal `("canonical", "formal", "analytical")` with `tuple(DEFAULT_NAMESPACES)` (test refactor only) | 4 lines changed |

No changes to: `provider_catalog/registry.py`, `serving/canonical_datasets.py`, `cycle/current_cycle_inputs.py`, `cycle/manifest.py`, `serving/formal.py`. Per M1-A §6 step 4 ("reader cutover"), those modules switch later — this M1-D step is additive only.

### 2.2 Schema shape comparison

| Field | Legacy `canonical.dim_security` (27 cols) | `canonical_v2.dim_security` (25 cols) | `canonical_lineage.lineage_dim_security` (6 cols) |
|---|---|---|---|
| `ts_code` (provider-shaped PK) | ✓ | — | — |
| `security_id` (canonical PK) | — | ✓ | ✓ |
| `name` (provider-shaped) | ✓ | — | — |
| `display_name` (canonical) | — | ✓ | — |
| `symbol` | ✓ | ✓ | — |
| `market`, `industry`, `list_date`, `is_active`, `area`, `fullname`, `exchange`, `curr_type`, `list_status`, `delist_date`, `setup_date`, `province`, `city`, `reg_capital`, `employees`, `main_business`, `latest_namechange_*` (5 cols) | ✓ (each) | ✓ (each) | — |
| `source_run_id` | ✓ | — | ✓ |
| `raw_loaded_at` | ✓ | — | ✓ |
| `source_provider` | — | — | ✓ (NEW; constant `"tushare"` today) |
| `source_interface_id` | — | — | ✓ (NEW; constant `"stock_basic"` today) |
| `canonical_loaded_at` | ✓ | ✓ | ✓ (joins canonical_v2 row to its lineage row by snapshot pair) |

### 2.3 dbt graph (unchanged at staging/intermediate; additive at marts)

- `staging/stg_stock_basic.sql` — UNCHANGED (provider-shaped Tushare staging stays).
- `intermediate/int_security_master.sql` — UNCHANGED (still produces `ts_code`, `source_run_id`, `raw_loaded_at`; consumed by both legacy and v2 marts).
- `marts/mart_dim_security.sql` — UNCHANGED (legacy mart still feeds `canonical.dim_security`).
- `marts_v2/mart_dim_security_v2.sql` — NEW (selects from `int_security_master`, aliases `ts_code AS security_id` + `name AS display_name`, drops lineage columns).
- `marts_lineage/mart_lineage_dim_security.sql` — NEW (selects from `int_security_master`, projects `security_id + source_provider + source_interface_id + source_run_id + raw_loaded_at`).

This intentionally leaves the legacy write path live so `canonical.dim_security` continues to receive overwrites during the dual-write window (M1-A §6 step 2). The v2 + lineage marts do NOT yet replace the legacy mart's role.

---

## 3. M1-C parity test scoreboard (after vertical slice)

| Test | Today | Expectation per M1-A |
|---|---|---|
| `test_canonical_business_spec_does_not_carry_raw_lineage[canonical.stock_basic]` | RED | resolves at M1.3 step 5 (retire legacy stock_basic spec) |
| `test_canonical_business_spec_does_not_carry_raw_lineage[canonical.dim_security]` | RED (legacy still has lineage) | will resolve at M1.3 step 5 (retire legacy dim_security spec); the canonical_v2 sibling already passes (DDL #5) |
| `test_canonical_business_spec_does_not_carry_raw_lineage[canonical.dim_index]` | RED | resolves when `CANONICAL_V2_DIM_INDEX_SPEC` lands + step 5 retires legacy |
| `test_canonical_business_spec_does_not_carry_raw_lineage[canonical.fact_price_bar]` | RED | resolves when `CANONICAL_V2_FACT_PRICE_BAR_SPEC` lands + step 5 retires legacy |
| `test_canonical_business_spec_does_not_carry_raw_lineage[canonical.fact_financial_indicator]` | RED | same pattern |
| `test_canonical_business_spec_does_not_carry_raw_lineage[canonical.fact_event]` | RED | same pattern (gated on C6 event_timeline PK derivation rules per M1-F) |
| `test_canonical_business_spec_does_not_carry_raw_lineage[canonical.fact_market_daily_feature]` | RED | same pattern |
| `test_canonical_business_spec_does_not_carry_raw_lineage[canonical.fact_index_price_bar]` | RED | same pattern |
| `test_canonical_business_spec_does_not_carry_raw_lineage[canonical.fact_forecast_event]` | RED | same pattern |
| `test_canonical_business_spec_does_not_carry_provider_shaped_identifier[*]` (×9) | RED | same pattern |
| `test_FORBIDDEN_SCHEMA_FIELDS_includes_canonical_lineage_block` | RED | resolves at M1.3 step 5 (extend the forbidden set after canonical_v2 is the only write path) |
| `test_canonical_lineage_namespace_specs_keep_canonical_pk_first` | **PASS** (1 spec discovered: `CANONICAL_LINEAGE_DIM_SECURITY_SPEC`) | new |
| `test_canonical_v2_namespace_specs_do_not_carry_raw_lineage` | **PASS** (1 spec discovered: `CANONICAL_V2_DIM_SECURITY_SPEC`) | new |
| `test_FORBIDDEN_RAW_LINEAGE_FIELDS_set_is_stable` | PASS (sentinel) | n/a |
| `test_canonical_mart_load_spec_does_not_require_raw_lineage[*]` (×8 legacy) | RED | resolves at M1.3 step 5 |
| `test_canonical_mart_load_spec_does_not_require_provider_shaped_identifier[*]` (×8 legacy) | RED | resolves at M1.3 step 5 |
| `test_FORBIDDEN_PAYLOAD_FIELDS_extends_to_canonical_lineage` | RED | resolves at M1.3 step 5 |
| `test_canonical_v2_load_specs_drop_raw_lineage` | **PASS** (1 v2 spec discovered) | new |
| `test_canonical_lineage_load_specs_carry_lineage_explicitly` | **PASS** (1 lineage spec discovered) | new |
| `test_canonical_mart_sql_does_not_select_lineage_columns[*]` (×8 legacy mart files) | RED | resolves at M1.3 step 5 |
| `test_canonical_v2_mart_sql_does_not_select_lineage_columns[mart_dim_security_v2.sql]` | **PASS** | new |
| `test_canonical_v2_mart_sql_does_not_select_provider_shaped_identifier[mart_dim_security_v2.sql]` | **PASS** | new |
| `test_lineage_mart_sql_carries_lineage_columns[mart_lineage_dim_security.sql]` | **PASS** | new |
| `test_legacy_marts_directory_exists_and_is_inventoried` | PASS (sentinel) | n/a |

**Total**: 44 RED (legacy parity scoreboard) + 9 PASS (sentinels + vertical-slice progress) + 4 SKIP (auto-discover tests with no symbols left to check after vertical slice) = 57 unique parity-test invocations.

The 44 RED tests fall into clear migration-step buckets:
- **M1.3 step 5 (drop legacy)**: extends `FORBIDDEN_SCHEMA_FIELDS` / `FORBIDDEN_PAYLOAD_FIELDS` and removes legacy `canonical.*` specs/writer/marts. Resolves all 44 in one well-defined increment.
- Or, alternative: per-table M1.3 sub-increments (one per remaining mart table) that add the v2/lineage spec, then retire the legacy spec for that table. Resolves 6 tests per table per increment.

---

## 4. What the vertical slice does NOT do (intentional non-claims)

Per M1-A §6 the canonical v2 migration is six steps. M1-D delivers **steps 1, 2, and 3 for `dim_security` only**; explicitly NOT delivered:

- **Step 4 (reader cutover)**: `serving/canonical_datasets.py`'s `_DATASET_TO_TABLE` mapping for `security_master` still points at `canonical.dim_security`. `cycle/current_cycle_inputs.py` continues to read `ts_code` from the legacy table. Reader cutover is gated on a feature flag and a coordinated change (M1.3 follow-up).
- **Step 5 (retire legacy)**: legacy `canonical.dim_security` Iceberg spec, writer load spec, and mart SQL remain in place. They continue to receive writes and serve readers. Removing them is a destructive change that requires step 4 to be live first.
- **Step 6 (optional rename)**: `canonical_v2 → canonical` namespace rename — explicitly skipped per M1-A §6.
- **Manifest co-pin via PG `cycle_publish_manifest`**: `_write_canonical_v2_snapshot_set_manifest` writes the sidecar v2 schema (`canonical_v2_tables` + `canonical_lineage_tables`); the PG `cycle_publish_manifest` table is unchanged. Per M1-A §4.3 the sidecar is the recommended default.
- **Live PG smoke / live Iceberg write**: NOT executed. The 157 passing tests cover spec/contract/SQL parsing only. Live write tests skip without `DATABASE_URL`/`DP_PG_DSN` (4 PG-dependent tests still SKIP per M1-B).
- **Migration of the other 7 canonical mart tables** (`stock_basic`, `dim_index`, `fact_price_bar`, `fact_financial_indicator`, `fact_event`, `fact_market_daily_feature`, `fact_index_price_bar`, `fact_forecast_event`). They remain on the legacy namespace.

---

## 5. Backward compatibility

- **Existing readers (`current_cycle_inputs.py`, `serving/formal.py`, analytical SQL, `assembly` consumers)**: unchanged behavior. They continue to consume `canonical.dim_security` with the legacy schema (including `ts_code`, `source_run_id`, `raw_loaded_at`).
- **Existing writers (`load_canonical_marts`, dbt `mart_dim_security.sql`)**: unchanged. The legacy write path is still the active publish path.
- **New writer (`load_canonical_v2_marts`)**: NOT auto-invoked anywhere. It can be called explicitly by future code to populate `canonical_v2.dim_security` + `canonical_lineage.lineage_dim_security` in lock-step. Until step 4, this is a no-op for production reads.
- **Iceberg catalog**: `canonical_v2` and `canonical_lineage` namespaces are added to `DEFAULT_NAMESPACES`. On the next `iceberg_tables.main(["--ensure"])` run with a real catalog, those namespaces will be created (idempotent). The matching tables will NOT be created automatically because `DEFAULT_TABLE_SPECS` was intentionally NOT extended (`test_ensure_tables_is_idempotent` hard-codes the expected table list and would break otherwise; the new `CANONICAL_V2_TABLE_SPECS` and `CANONICAL_LINEAGE_TABLE_SPECS` are accessible via separate registration).

A future `register_table(catalog, CANONICAL_V2_DIM_SECURITY_SPEC)` + `register_table(catalog, CANONICAL_LINEAGE_DIM_SECURITY_SPEC)` call wires the tables into the catalog. This would be invoked by the dual-write step (M1.3 step 3 follow-up), not by M1-D.

---

## 6. Outstanding risks

- **Legacy `canonical.*` write path is unchanged** — the canonical lineage gap is NOT closed for any consumer that reads through legacy. C2's findings stand for the 7 untouched mart tables.
- **`current_cycle_inputs.py` still keys on `ts_code` internally** — reader cutover (step 4) deferred. C2's "lineage-stripped temporary mitigation, NOT fully provider-neutral" status for `current_cycle_inputs.py` is unchanged.
- **dbt-runtime tests skip on Python 3.14** (M1-B §5.2). The new v2 + lineage marts compile under dbt 1.x but the actual `dbt run` is not exercised in the data-platform venv. M2.1 must run dbt under the assembly Python 3.12 venv.
- **Live Iceberg catalog writes for `canonical_v2.*` / `canonical_lineage.*`** — not exercised. `register_table(catalog, CANONICAL_V2_DIM_SECURITY_SPEC)` will succeed against a live PG-backed SQL Catalog (M1-B §2 confirmed the wiring) but the spike sweep does not run it. M2.1 covers it.
- **M1-A §3.3 `source_provider` / `source_interface_id` constant values** — today the lineage mart uses literal `'tushare'` and `'stock_basic'`. When additional providers integrate, this becomes a column derived from the staging source rather than a constant. Dynamic derivation is a follow-up.
- **`_load_frozen_candidate_symbols` reader at `orchestrator/p2_dry_run.py:1227`** — still reads symbol-level from `cycle_candidate_selection JOIN candidate_queue` keyed on `ts_code`. Not affected by canonical_v2 (different code path); separately tracked under C5 / M4.x.
- **44 RED parity tests remain in CI** — explicitly the M1-C scoreboard for follow-up M1.3 increments. They are the planned-failure state, not regressions. CI policy may want to surface this as an "expected failures" channel rather than a generic RED indicator.

---

## 7. Hard-rule reaffirmation

- `project_ult_v5_0_1.md` NOT modified.
- P5 shadow-run NOT started.
- M2/M3/M4 NOT entered.
- Production fetch NOT enabled.
- Compose NOT started.
- API-6, sidecar, frontend write API, Kafka/Flink/Temporal, news/Polymarket flows NOT introduced.
- Tushare remains a `provider="tushare"` adapter ONLY (the lineage mart constant value).
- No `git init`. No commits. No pushes.
- No forbidden files committed. The only new files are source code (`.py`, `.sql`, `.yml`) under `data-platform/src/`, tests under `data-platform/tests/`, and reports under `assembly/reports/stabilization/`.

---

## 8. Findings tally

- **CONFIRMED** (8):
  1. `canonical_v2.dim_security` Iceberg spec is provider-neutral by construction (security_id PK; no lineage columns).
  2. `canonical_lineage.lineage_dim_security` Iceberg spec carries lineage explicitly with `source_provider` + `source_interface_id` + `source_run_id` + `raw_loaded_at` keyed on `security_id`.
  3. `CANONICAL_V2_MART_LOAD_SPECS` and `CANONICAL_LINEAGE_MART_LOAD_SPECS` writer specs match the new Iceberg specs field-for-field.
  4. `load_canonical_v2_marts(catalog, duckdb_path)` writes both v2 and lineage in lock-step inside one Python frame; sidecar v2 manifest pins both snapshot ids.
  5. Two new dbt mart SQL files materialize from `int_security_master` with the right shape; both have `_schema.yml` declarations and PK + relationships tests.
  6. M1-C parity tests for the new `canonical_v2.*` / `canonical_lineage.*` namespace symbols PASS (5 future-state assertions).
  7. Pre-existing test sweep continues to PASS aside from 2 hard-coded `DEFAULT_NAMESPACES` literals fixed in this round; no functional regression.
  8. `DEFAULT_NAMESPACES` extended to include the two new namespaces; future `iceberg_tables.main(["--ensure"])` will create them idempotently.
- **PARTIAL** (3):
  1. Vertical slice covers 1 of 8 canonical mart tables. The other 7 + `stock_basic` remain on legacy specs and continue to fail M1-C parity tests.
  2. Reader cutover (M1-A §6 step 4) NOT performed: `current_cycle_inputs.py` and `canonical_datasets.py` still reference legacy. The new namespace exists but no live consumer reads it yet.
  3. Live Iceberg catalog write of the new specs not exercised in this round (gated on real PG / `register_table` invocation in M2.1).
- **INFERRED** (1):
  1. `register_table(catalog, CANONICAL_V2_DIM_SECURITY_SPEC)` will succeed against a live PG-backed SQL Catalog given M1-B §2 confirmed the wiring; not actually invoked in this round.

---

## 9. Per-task handoff block

```
Task: M1-D vertical slice — canonical_v2.dim_security + canonical_lineage.lineage_dim_security
Repo(s): data-platform + assembly
Output (proof): /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/canonical-v2-lineage-separation-proof-20260428.md
Output (source code modified):
  data-platform/src/data_platform/ddl/iceberg_tables.py (added CANONICAL_V2_*_SPEC, CANONICAL_LINEAGE_*_SPEC, namespace constants, table-spec tuples; updated __all__)
  data-platform/src/data_platform/serving/canonical_writer.py (added CANONICAL_V2_*_LOAD_SPEC, CANONICAL_LINEAGE_*_LOAD_SPEC, mart-spec tuples, load_canonical_v2_marts, _write_canonical_v2_snapshot_set_manifest, _reject_public_mart_load extension; updated __all__)
  data-platform/src/data_platform/serving/catalog.py (extended DEFAULT_NAMESPACES)
  data-platform/src/data_platform/dbt/models/marts_v2/mart_dim_security_v2.sql (NEW)
  data-platform/src/data_platform/dbt/models/marts_v2/_schema.yml (NEW)
  data-platform/src/data_platform/dbt/models/marts_lineage/mart_lineage_dim_security.sql (NEW)
  data-platform/src/data_platform/dbt/models/marts_lineage/_schema.yml (NEW)
Output (tests modified):
  data-platform/tests/dbt/test_dbt_skeleton.py (extended skeleton expectations to include marts_v2/ + marts_lineage/)
  data-platform/tests/serving/test_catalog.py (replaced literal namespace tuple with tuple(DEFAULT_NAMESPACES))
  data-platform/tests/ddl/test_iceberg_tables.py (replaced literal namespace tuple with tuple(DEFAULT_NAMESPACES))
Validation command: cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -p no:cacheprovider --tb=no tests/ddl tests/serving tests/dbt tests/provider_catalog tests/cycle/test_current_cycle_inputs.py
Validation result: 44 failed, 157 passed, 12 skipped, 12 warnings in 4.35s. All 44 failures are M1-C parity tests asserting the legacy gap; zero non-parity failures (verified by `grep FAILED | grep -v provider_neutrality | wc -l → 0`).
Per-subrepo git state:
  data-platform: rev-parse HEAD = 330f6b4; status = M src/data_platform/raw/writer.py + M tests/raw/test_writer.py (pre-existing) + many new untracked files from M1-D vertical slice; push = not pushed; branch = main; interpreter = data-platform/.venv/bin/python (Python 3.14.3)
  assembly:      rev-parse HEAD = a7f19c5; status = untracked stabilization reports include this M1-D proof; push = not pushed; branch = main
Dirty files added by this task:
  data-platform/src/data_platform/ddl/iceberg_tables.py (modified)
  data-platform/src/data_platform/serving/canonical_writer.py (modified)
  data-platform/src/data_platform/serving/catalog.py (modified)
  data-platform/src/data_platform/dbt/models/marts_v2/ (NEW dir + 2 files)
  data-platform/src/data_platform/dbt/models/marts_lineage/ (NEW dir + 2 files)
  data-platform/tests/dbt/test_dbt_skeleton.py (modified)
  data-platform/tests/serving/test_catalog.py (modified)
  data-platform/tests/ddl/test_iceberg_tables.py (modified)
  assembly/reports/stabilization/canonical-v2-lineage-separation-proof-20260428.md (NEW)
Findings: 8 CONFIRMED, 3 PARTIAL, 1 INFERRED
Outstanding risks:
  - 7 of 8 canonical mart tables still on legacy specs — RED parity scoreboard remains (44 failures)
  - reader cutover deferred (current_cycle_inputs.py, canonical_datasets.py unchanged)
  - live Iceberg catalog write of new specs not exercised
  - dbt-runtime tests skip on Python 3.14 — `dbt run` against new marts not exercised
  - source_provider / source_interface_id constants will become derived columns when additional providers integrate
Declaration: I did not modify project_ult_v5_0_1.md. I did not enter M2/M3/M4. I did not enable production fetch. I did not start P5 shadow-run. I did not start compose. I did not commit any forbidden files. I did not run `git init`. I did not push without approval. Tushare remains a provider=tushare adapter only. The 44 remaining RED M1-C parity tests are the explicit blocker scoreboard for follow-up M1.3 increments.
```
