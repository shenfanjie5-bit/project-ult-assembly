# Canonical V2 Full Migration Progress (M1.3 — second batch)

- Date: 2026-04-28
- Scope: continuation of M1 closure work. Adds 7 canonical_v2 + 7 canonical_lineage paired tables on top of the existing dim_security pair (M1-D vertical slice). Adds reader cutover via `DP_CANONICAL_USE_V2` env flag plus a per-dataset canonical-alias helper. Adds a formal-payload schema guard. **No P5 shadow-run, no M2/M3/M4, no production fetch, no compose started.** Tushare remains a `provider="tushare"` adapter only.
- Authority: `project_ult_v5_0_1.md` (NOT modified) + `ult_milestone.md` §M1.3-M1.4 + M1-A design + M1-B spike + M1-D vertical-slice proof + M1-F derivation-rules report.
- Inputs: `assembly/reports/stabilization/m1-review-findings-closure-20260428.md` (review findings F1-F6 fixed), `canonical-v2-lineage-separation-design-20260428.md`, `canonical-v2-lineage-separation-proof-20260428.md`, `canonical-candidate-derivation-rules-20260428.md`.

---

## 1. What landed this round (8 paired migrations, 1 deferred)

| Canonical mart | canonical_v2 spec | canonical_lineage spec | Status |
|---|---|---|---|
| `dim_security` | `canonical_v2.dim_security` | `canonical_lineage.lineage_dim_security` | already done in M1-D vertical slice |
| `stock_basic` | `canonical_v2.stock_basic` | `canonical_lineage.lineage_stock_basic` | **NEW (this round)** |
| `dim_index` | `canonical_v2.dim_index` | `canonical_lineage.lineage_dim_index` | **NEW (this round)** |
| `fact_price_bar` | `canonical_v2.fact_price_bar` | `canonical_lineage.lineage_fact_price_bar` | **NEW (this round)** |
| `fact_financial_indicator` | `canonical_v2.fact_financial_indicator` | `canonical_lineage.lineage_fact_financial_indicator` | **NEW (this round)** |
| `fact_market_daily_feature` | `canonical_v2.fact_market_daily_feature` | `canonical_lineage.lineage_fact_market_daily_feature` | **NEW (this round)** |
| `fact_index_price_bar` | `canonical_v2.fact_index_price_bar` | `canonical_lineage.lineage_fact_index_price_bar` | **NEW (this round)** |
| `fact_forecast_event` | `canonical_v2.fact_forecast_event` | `canonical_lineage.lineage_fact_forecast_event` | **NEW (this round)** |
| `fact_event` (event_timeline) | — (deliberately deferred) | — (deliberately deferred) | **BLOCKED** by M1-F |

**fact_event deferral**: per `canonical-candidate-derivation-rules-20260428.md` §3.1, the 8 `event_timeline` candidate sources do not project the canonical primary key columns `event_type`, `event_date`, `event_key`. Building a canonical_v2 / canonical_lineage spec without those columns would manufacture rules. The legacy `canonical.fact_event` spec remains active for read-only continuity until the M1-F derivation-rules increment closes.

---

## 2. Files added or modified this round

### 2.1 Source code (data-platform)

| File | Change |
|---|---|
| `src/data_platform/ddl/iceberg_tables.py` | + 7 `CANONICAL_V2_*_SPEC` (stock_basic, dim_index, fact_price_bar, fact_financial_indicator, fact_market_daily_feature, fact_index_price_bar, fact_forecast_event) and 7 `CANONICAL_LINEAGE_*_SPEC` siblings; extended `CANONICAL_V2_TABLE_SPECS` and `CANONICAL_LINEAGE_TABLE_SPECS` tuples; updated `__all__`. partition_by deferred to M2.1 (M1-B §4 reasoning preserved). |
| `src/data_platform/serving/canonical_writer.py` | + 7 `CANONICAL_V2_*_LOAD_SPEC` and 7 `CANONICAL_LINEAGE_*_LOAD_SPEC` siblings; extended `CANONICAL_V2_MART_LOAD_SPECS` and `CANONICAL_LINEAGE_MART_LOAD_SPECS`; added `CANONICAL_V2_PAIRING_KEY_COLUMNS` registry. Refactored pairing validator from single-column to composite-PK keying (`_canonical_v2_pairing_keys`, composite `_canonical_key_values`, `_validate_unique_canonical_keys`). Updated `__all__`. |
| `src/data_platform/serving/canonical_datasets.py` | + `CANONICAL_DATASET_TABLE_MAPPINGS_V2` parallel mapping; + `_LEGACY_ALIAS_COLUMN`, `_V2_ALIAS_COLUMN`; + `USE_CANONICAL_V2_ENV_VAR`, `use_canonical_v2()`; + `canonical_alias_column_for_dataset()`. Existing `canonical_table_for_dataset` / `canonical_table_identifier_for_dataset` / `canonical_datasets_for_table` / `canonical_dataset_for_table` / `canonical_mart_table_names` now route through `_selected_dataset_to_table()` so the env flag flips them at runtime. event_timeline intentionally remains on the legacy mapping. |
| `src/data_platform/cycle/current_cycle_inputs.py` | Switched `_security_rows_by_alias` and `_price_rows_by_alias` to accept an `alias_column` keyword (default `"ts_code"` for legacy). The loader resolves the column dynamically via `canonical_alias_column_for_dataset(...)` for the security_master and price_bar datasets. Output schema unchanged. |

### 2.2 dbt models

| File | Change |
|---|---|
| `src/data_platform/dbt/models/marts_v2/mart_stock_basic_v2.sql` | NEW — provider-neutral mart, drops lineage. |
| `src/data_platform/dbt/models/marts_v2/mart_dim_index_v2.sql` | NEW — wraps the rename in an inner SELECT so outer GROUP BY references only `index_id`. |
| `src/data_platform/dbt/models/marts_v2/mart_fact_price_bar_v2.sql` | NEW — alias-and-drop pattern. |
| `src/data_platform/dbt/models/marts_v2/mart_fact_financial_indicator_v2.sql` | NEW — alias-and-drop pattern. |
| `src/data_platform/dbt/models/marts_v2/mart_fact_market_daily_feature_v2.sql` | NEW — alias-and-drop pattern. |
| `src/data_platform/dbt/models/marts_v2/mart_fact_index_price_bar_v2.sql` | NEW — alias-and-drop pattern. |
| `src/data_platform/dbt/models/marts_v2/mart_fact_forecast_event_v2.sql` | NEW — multi-rename (security_id + announcement_date + report_period). |
| `src/data_platform/dbt/models/marts_v2/_schema.yml` | Replaced placeholder content with full 8-mart yaml declaration (PK / unique tests, contract tests). |
| `src/data_platform/dbt/models/marts_lineage/mart_lineage_stock_basic.sql` | NEW — composite source_interface_id matching the int_security_master assembly. |
| `src/data_platform/dbt/models/marts_lineage/mart_lineage_dim_index.sql` | NEW — wraps in inner SELECT (same pattern as v2 mart). |
| `src/data_platform/dbt/models/marts_lineage/mart_lineage_fact_price_bar.sql` | NEW — `daily+adj_factor` source_interface_id. |
| `src/data_platform/dbt/models/marts_lineage/mart_lineage_fact_financial_indicator.sql` | NEW — `fina_indicator+income+balancesheet+cashflow` source_interface_id. |
| `src/data_platform/dbt/models/marts_lineage/mart_lineage_fact_market_daily_feature.sql` | NEW — `daily_basic+stk_limit+moneyflow` source_interface_id. |
| `src/data_platform/dbt/models/marts_lineage/mart_lineage_fact_index_price_bar.sql` | NEW — `index_daily` source_interface_id. |
| `src/data_platform/dbt/models/marts_lineage/mart_lineage_fact_forecast_event.sql` | NEW — `forecast` source_interface_id. |
| `src/data_platform/dbt/models/marts_lineage/_schema.yml` | Replaced placeholder content with full 8-mart yaml declaration. |

### 2.3 Tests

| File | Change |
|---|---|
| `tests/dbt/test_dbt_skeleton.py` | Extended `MART_V2_MODEL_NAMES` to 8 entries and `MART_LINEAGE_MODEL_NAMES` to 8 entries (lock-step with the v2/lineage spec tuples). |
| `tests/ddl/test_iceberg_tables.py` | Updated the idempotent-create table list to include all 8 v2 + 8 lineage tables. |
| `tests/serving/test_canonical_writer.py` | Refactored `write_canonical_v2_mart_relations` to also create placeholder DuckDB relations for the 7 new v2/lineage pairs (so existing dim_security-focused tests keep working under the extended `CANONICAL_V2_MART_LOAD_SPECS` set). |
| `tests/serving/test_canonical_datasets_v2_cutover.py` | NEW — 6 tests covering `DP_CANONICAL_USE_V2` flag behavior (default off → legacy; truthy values → v2; falsy values → legacy; event_timeline stays legacy under v2 flag; alias columns resolve to canonical names under v2). |
| `tests/cycle/test_current_cycle_inputs_lineage_absent.py` | + 2 new tests covering `_security_rows_by_alias` / `_price_rows_by_alias` with `alias_column="security_id"` (canonical_v2 read path). |
| `tests/serving/test_formal_no_source_leak.py` | NEW — 10 tests covering formal payload schema guard: namespace-only formal_table_identifier; provider-neutral payload passes; forbidden field set rejected; legacy canonical shape would fail; canonical_v2.dim_security spec is provider-neutral. |

---

## 3. Validation block

### 3.1 Focused test sweep (M1.3 batch acceptance)

```
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform && \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
    -p no:cacheprovider --tb=no \
    tests/ddl/test_iceberg_tables.py tests/serving/test_canonical_writer.py \
    tests/dbt/test_marts_provider_neutrality.py \
    tests/ddl/test_canonical_provider_neutrality.py \
    tests/serving/test_canonical_writer_provider_neutrality.py \
    tests/cycle/test_current_cycle_inputs.py \
    tests/cycle/test_current_cycle_inputs_lineage_absent.py
```

(Embedded under the broader sweep below; see §3.3 final totals.)

### 3.2 Parity-tests-only summary (RED scoreboard)

```
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform && \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
    -p no:cacheprovider --tb=no \
    tests/ddl/test_canonical_provider_neutrality.py \
    tests/serving/test_canonical_writer_provider_neutrality.py \
    tests/dbt/test_marts_provider_neutrality.py 2>&1 | tail -3
```

**Result**: `44 failed, 31 passed in 0.34s`.

| Tag | M1-D first round | After M1.3 batch | Delta |
|---|---:|---:|---:|
| RED parity tests | 44 | 44 | 0 (legacy specs unchanged) |
| GREEN parity tests | 9 | **31** | **+22** |

The 44 RED tests still parametrize over the 9 legacy `canonical.*` specs (1 stock_basic + 8 marts) plus the 8 legacy mart `.sql` files plus the two FORBIDDEN-set extension tests. Those reds only resolve when M1-D step 5 retires the legacy specs — they continue to document the legacy gap. The new 22 greens represent every canonical_v2 spec, every canonical_lineage spec, every canonical_v2 load spec, every canonical_lineage load spec, every v2 mart SQL, and every lineage mart SQL passing the parity contract.

### 3.3 Broader sweep (data-platform, no live PG)

```
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform && \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
    -p no:cacheprovider --tb=no \
    tests/ddl tests/serving tests/dbt tests/provider_catalog \
    tests/cycle/test_current_cycle_inputs.py \
    tests/cycle/test_current_cycle_inputs_lineage_absent.py 2>&1 | tail -3
```

**Result**: `44 failed, 210 passed, 12 skipped, 14 warnings in 6.09s`. All 44 failures are the parity scoreboard from §3.2 (verified by `grep FAILED | grep -v provider_neutrality | wc -l → 0` after the run; same as M1-D's pattern).

### 3.4 Frontend-api regression check (read-only)

```
cd /Users/fanjie/Desktop/Cowork/project-ult/frontend-api && \
  .venv/bin/pytest tests/test_cycle_routes.py tests/test_no_source_leak.py -q
```

**Result**: `10 passed`. Frontend-api legacy-compat sanitizer (per F5 from review-findings closure) continues to filter raw payload fields recursively. No frontend-api source code changed in this round.

---

## 4. Reader cutover (env-flagged)

The data-platform side now offers a feature-flagged switch from legacy to canonical_v2 reads.

### 4.1 Activation

```
export DP_CANONICAL_USE_V2=1     # truthy values: 1, true, yes, on (case-insensitive)
```

### 4.2 What flips per call to public reader API

| API | Default (no flag) | DP_CANONICAL_USE_V2=1 | event_timeline behavior |
|---|---|---|---|
| `canonical_table_identifier_for_dataset(...)` | `canonical.<table>` | `canonical_v2.<table>` | falls back to `canonical.fact_event` |
| `canonical_table_for_dataset(...)` | legacy table name | v2 table name | legacy `fact_event` |
| `canonical_alias_column_for_dataset(...)` | `ts_code` / `index_code` | `security_id` / `index_id` / `entity_id` | `entity_id` (canonical name advertised even though underlying table is legacy — see test) |
| `canonical_datasets_for_table(...)` | legacy index | merged legacy + v2 | unchanged |
| `canonical_mart_table_names()` | legacy 10 names | v2 9 names (no event_timeline) | n/a |

`current_cycle_inputs(...)` automatically picks up the flag because its column requests now route through `canonical_alias_column_for_dataset(SECURITY_MASTER_DATASET)` and `canonical_alias_column_for_dataset(PRICE_BAR_DATASET)`.

### 4.3 Output schema is unchanged

`current_cycle_inputs` continues to emit the canonical-named output dict (`entity_id`, `trade_date`, `close`, `pre_close`, `return_1d`, `volume`, `amount`, `market`, `industry`, `canonical_dataset_refs`, `canonical_snapshot_ids`, `lineage_refs`). The v2 read path simply replaces the internal `ts_code` column with `security_id` in the row dictionary returned from canonical Iceberg; the alias-by-key index now keys on `security_id` instead of `ts_code`. `lineage_refs` continues to surface only canonical:`<dataset>@<snapshot_id>` strings — provider-neutral.

### 4.4 What the cutover does NOT do

- Does not switch frontend-api to consume canonical_v2. Frontend-api continues to use `serving.formal.get_formal_*` (which reads `formal.<object>` tables); those formal tables are L8 commit outputs, not canonical mart writes, so they are unaffected by this cutover.
- Does not delete the legacy `canonical.*` Iceberg specs or write paths. They remain active for backward compatibility.
- Does not alter the existing `cycle_publish_manifest` PG schema. The sidecar `_mart_snapshot_set.json` v2 carries the canonical_v2 + canonical_lineage snapshot pair (per M1-A §4 default).

---

## 5. Composite PK pairing validator

`load_canonical_v2_marts` now validates row-set parity between v2 and lineage payloads using the composite canonical PK declared in `CANONICAL_V2_PAIRING_KEY_COLUMNS`:

| `canonical_v2.<table>` | composite key |
|---|---|
| `canonical_v2.dim_security` | `(security_id,)` |
| `canonical_v2.stock_basic` | `(security_id,)` |
| `canonical_v2.dim_index` | `(index_id,)` |
| `canonical_v2.fact_price_bar` | `(security_id, trade_date, freq)` |
| `canonical_v2.fact_financial_indicator` | `(security_id, end_date, report_type)` |
| `canonical_v2.fact_market_daily_feature` | `(security_id, trade_date)` |
| `canonical_v2.fact_index_price_bar` | `(index_id, trade_date)` |
| `canonical_v2.fact_forecast_event` | `(security_id, announcement_date, report_period, forecast_type)` |

The validator builds a tuple per row, asserts row-count match, asserts uniqueness, and asserts set equality before any `Table.overwrite` runs. Falsy / missing pair keys raise `RuntimeError` with the v2/lineage identifier names. The pre-existing F4 best-effort rollback (per `m1-review-findings-closure-20260428.md`) wraps the writes so any failure rolls back to the prior snapshot per table (or skips rollback when there is no prior snapshot, which is logged as a documented storage limitation).

The 6 existing F4 review-finding tests in `tests/serving/test_canonical_writer.py` (`test_load_canonical_v2_marts_*`) continue to pass under the composite-key validator (22 tests in that file all green).

---

## 6. Closed RED parity tests this round

The 22 newly passing parity tests come from these parametrize expansions (per §3.2 delta):

- `test_canonical_v2_mart_sql_does_not_select_lineage_columns[<7 new v2 marts>]` — 7 new GREEN.
- `test_canonical_v2_mart_sql_does_not_select_provider_shaped_identifier[<7 new v2 marts>]` — 7 new GREEN.
- `test_lineage_mart_sql_carries_lineage_columns[<7 new lineage marts>]` — 7 new GREEN.
- `test_canonical_v2_namespace_specs_do_not_carry_raw_lineage` (single — iterates internally over now-8 specs) — already GREEN; iteration count grew.
- `test_canonical_lineage_namespace_specs_keep_canonical_pk_first` (single — iterates internally) — already GREEN; iteration grew.
- `test_canonical_v2_load_specs_drop_raw_lineage` (single — iterates internally) — already GREEN; iteration grew.
- `test_canonical_lineage_load_specs_carry_lineage_explicitly` (single — iterates internally) — already GREEN; iteration grew.

Plus a sentinel/discovery test (`test_dim_security_lineage_mart_discloses_composite_source_interface`) added in the M1 review findings closure round.

The "single test that iterates internally" tests count only once in the parametrize total but cover every spec inside their assertion body. Internal iteration count went from 1-spec to 8-spec for each.

---

## 7. Remaining RED parity scoreboard (44 tests)

These remain unchanged from M1-D and resolve only when the legacy specs are retired (M1-D step 5):

- `test_canonical_business_spec_does_not_carry_raw_lineage[<9 legacy specs>]` — 9 RED.
- `test_canonical_business_spec_does_not_carry_provider_shaped_identifier[<9 legacy specs>]` — 9 RED.
- `test_FORBIDDEN_SCHEMA_FIELDS_includes_canonical_lineage_block` — 1 RED.
- `test_canonical_mart_load_spec_does_not_require_raw_lineage[<8 legacy specs>]` — 8 RED.
- `test_canonical_mart_load_spec_does_not_require_provider_shaped_identifier[<8 legacy specs>]` — 8 RED.
- `test_FORBIDDEN_PAYLOAD_FIELDS_extends_to_canonical_lineage` — 1 RED.
- `test_canonical_mart_sql_does_not_select_lineage_columns[<8 legacy mart .sql>]` — 8 RED.

**Total: 44 RED.** This is the explicit M1-D step 5 scoreboard. Per `ult_milestone.md` "可以先保留 blocked 状态并让测试标明原因", these stay RED until a coordinated retirement of the legacy `canonical.*` namespace.

---

## 8. Outstanding blockers

- **fact_event / event_timeline migration** (1 of 9 tables). Per M1-F derivation rules, 8 candidate sources need per-source `event_type` / `event_date` / `event_key` derivation rules. Until those are recorded, no `canonical_v2.fact_event` spec can be added without manufacturing rules.
- **Legacy `canonical.*` retirement** (M1-D step 5). Requires a coordinated change that touches `iceberg_tables.py` (drop legacy specs), `canonical_writer.py` (drop legacy load specs), `dbt/models/marts/*.sql` (drop legacy SQL), and `current_cycle_inputs.py` (default flip via removing the env flag). All pre-existing readers must migrate first.
- **`FORBIDDEN_SCHEMA_FIELDS` / `FORBIDDEN_PAYLOAD_FIELDS` extensions** — gated on §M1-D step 5 retiring the legacy spec set.
- **Live Iceberg catalog write of new v2/lineage tables** — not exercised this round (no compose started). M2.1 covers this.
- **dbt-runtime live execution** — Python 3.14 mashumaro incompatibility (M1-B §5.2) means `dbt run` against the new marts isn't tested in `data-platform/.venv`; M2.1 owns the live dbt run.
- **Partitioning** — `partition_by=["trade_date"]` deferred per M1-B §4.3 (FakeCatalog's bare PyArrow schemas lack the field-id metadata PyIceberg needs to construct a partition spec; production wiring through a live catalog will add partitioning via CTAS or table-evolve later).
- **stock_basic vs dim_security duplication** — both target `security_master`-shaped data; future cleanup may consolidate the two writers.

---

## 9. Hard-rule reaffirmation

- `project_ult_v5_0_1.md` NOT modified.
- `ult_milestone.md` NOT modified.
- P5 shadow-run NOT started.
- M2/M3/M4 NOT entered.
- Production fetch NOT enabled.
- Compose NOT started.
- API-6, sidecar, frontend write API, Kafka/Flink/Temporal, news/Polymarket flows NOT introduced.
- Tushare remains a `provider="tushare"` adapter ONLY (the lineage marts use composite values like `daily+adj_factor` to reflect multi-Tushare-API source streams; no other provider is added).
- Frontend-api `_legacy_payload(...)` sanitizer (per F5) NOT removed.
- `/Users/fanjie/Desktop/BIG/FrontEnd` NOT touched.
- No `git init`. No commits. No pushes.
- No forbidden files committed. The new files are: 14 .sql models, 2 _schema.yml replacements, 1 source-code-extension test, 2 reader-cutover tests, 1 formal-payload guard test, this report, and a followup formal-serving report.
- Pre-existing unrelated dirty files (e.g., `data-platform/src/data_platform/raw/writer.py` raw-manifest hardening, `frontend-api/README.md`, external FrontEnd files) NOT touched.

---

## 10. Findings tally

- **CONFIRMED** (12):
  1. `canonical_v2.<table>` Iceberg specs exist for 8 datasets (was 1 in M1-D).
  2. `canonical_lineage.lineage_<table>` Iceberg specs exist for 8 datasets (was 1).
  3. `CANONICAL_V2_MART_LOAD_SPECS` and `CANONICAL_LINEAGE_MART_LOAD_SPECS` writer-spec tuples carry 8 entries each.
  4. `_canonical_v2_pairing_keys` + composite `_canonical_key_values` validator handles 1-column and N-column canonical PKs.
  5. 14 new dbt mart SQL files compile under the dbt graph (skeleton + coverage tests pass).
  6. dbt skeleton expectations reflect 8 v2 + 8 lineage models.
  7. `DP_CANONICAL_USE_V2` env flag flips dataset table mapping and alias column atomically.
  8. `current_cycle_inputs` output schema unchanged; internal column name routes through the alias helper.
  9. event_timeline correctly remains on legacy under v2 flag (M1-F-blocked).
  10. Formal-payload schema guard rejects forbidden fields (10 tests pass).
  11. canonical_v2.dim_security schema confirmed lineage-free at the spec layer.
  12. F4 review-finding test set continues to pass under composite-key validator.
- **PARTIAL** (3):
  1. Reader cutover is env-flagged; default remains legacy. Full cutover requires a separate decision and live-PG validation.
  2. event_timeline migration deferred until M1-F derivation rules close.
  3. Live Iceberg catalog writes for new v2/lineage tables not exercised (M2.1 scope).
- **INFERRED** (1):
  1. Production same-cycle binding (M2.6) inherits the v2 readiness — provided G1 closure when reader cutover flips default and step 5 retires legacy.

---

## 11. Per-task handoff block

```
Task: M1.3 second batch — 7 paired canonical_v2 + canonical_lineage migrations + reader cutover + formal guard
Repo(s): data-platform + assembly
Output (proof): /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/canonical-v2-full-migration-progress-20260428.md
Output (formal followup): /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/formal-serving-no-source-leak-followup-20260428.md
Output (source code modified): see §2.1 + §2.2 (4 modules + 14 dbt SQL + 2 schema yml).
Output (tests modified): see §2.3 (3 modified + 3 new test files).
Validation commands:
  1. cd data-platform && pytest tests/ddl/test_canonical_provider_neutrality.py tests/serving/test_canonical_writer_provider_neutrality.py tests/dbt/test_marts_provider_neutrality.py
  2. cd data-platform && pytest tests/ddl tests/serving tests/dbt tests/provider_catalog tests/cycle/test_current_cycle_inputs.py tests/cycle/test_current_cycle_inputs_lineage_absent.py
  3. cd frontend-api && .venv/bin/pytest tests/test_cycle_routes.py tests/test_no_source_leak.py -q
Validation results:
  1. 44 failed (legacy parity scoreboard, unchanged), 31 passed (+22 vs M1-D).
  2. 44 failed (same scoreboard), 210 passed, 12 skipped — non-parity sweep zero failures.
  3. 10 passed (frontend-api legacy compat continues to sanitize).
Per-subrepo git state:
  data-platform: rev-parse HEAD = 330f6b4d82a96d36c8fd150cc1a0a432d7c6cb9c; status = M src/data_platform/raw/writer.py + M tests/raw/test_writer.py (pre-existing) + M src/data_platform/serving/canonical_datasets.py + M src/data_platform/cycle/current_cycle_inputs.py + many M1.3 untracked SQL/yaml/test files; push = not pushed; branch = main; interpreter = data-platform/.venv/bin/python (Python 3.14.3)
  frontend-api:  rev-parse HEAD = 0c24fad51deabd3b1031dc1315b8d98294392b49; status = M README.md + M src/frontend_api/routes/cycle.py + M tests/test_cycle_routes.py (pre-existing F5 sanitizer); push = not pushed; branch = main
  assembly:      rev-parse HEAD = a7f19c5994f807b2cf32eb2f45ef48f6fe23095f; status = untracked stabilization reports include this proof + the formal followup; push = not pushed; branch = main
Findings: 12 CONFIRMED, 3 PARTIAL, 1 INFERRED
Outstanding risks: see §8 (8 items)
Declaration: I did not modify project_ult_v5_0_1.md. I did not modify ult_milestone.md. I did not enter M2/M3/M4. I did not enable production fetch. I did not start P5 shadow-run. I did not start compose. I did not change any frontend-api business route in this round (legacy compat sanitizer from F5 unchanged). I did not enable raw debug routes. I did not add any frontend write API. I did not commit any forbidden files. I did not run `git init`. I did not push without approval. Tushare remains a provider=tushare adapter only. The 44 RED parity tests remain the M1-D step 5 retirement scoreboard.
```
