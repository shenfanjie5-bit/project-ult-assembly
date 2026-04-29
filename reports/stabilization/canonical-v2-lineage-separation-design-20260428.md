# Canonical V2 Lineage Separation Design (M1-A)

- Date: 2026-04-28
- Scope: M1-A per `ult_milestone.md`. Read-only inventory + design proposal for `canonical_v2` / lineage-separation. **No code changes, no migration started.**
- Mode: design only. Tushare remains a `provider="tushare"` adapter only.
- Authority: `project_ult_v5_0_1.md` (NOT modified) + `ult_milestone.md` §M1.1.
- Inputs: C2 audit `assembly/reports/stabilization/canonical-physical-schema-alignment-audit-20260428.md`; C3 audit `formal-serving-no-source-leak-hardening-plan-20260428.md`; C6 audit `p1-provider-neutral-canonical-promotion-readiness-20260428.md`; data-platform `CLAUDE.md`.

---

## 1. Where the leak lives today (CONFIRMED, by file and line)

### 1.1 Canonical Iceberg DDL (`data-platform/src/data_platform/ddl/iceberg_tables.py`)

`FORBIDDEN_SCHEMA_FIELDS` (line 23) only blocks `submitted_at` / `ingest_seq` (Layer-B ingest metadata per data-platform CLAUDE.md). It does NOT block raw-zone lineage fields, and does NOT enforce a provider-neutral identifier rename. Per-spec leak surface:

| Spec | Lines | Provider-shaped identifiers | Lineage fields embedded |
|---|---|---|---|
| `CANONICAL_STOCK_BASIC_SPEC` (`canonical.stock_basic`) | 69-86 | `ts_code` (74) | `source_run_id` (82) |
| `CANONICAL_DIM_SECURITY_SPEC` (`canonical.dim_security`) | 112-146 | `ts_code` (117) | `source_run_id` (141), `raw_loaded_at` (142) |
| `CANONICAL_DIM_INDEX_SPEC` (`canonical.dim_index`) | 148-164 | `index_code` (153) — provider-shaped per index taxonomy | `source_run_id` (159), `raw_loaded_at` (160) |
| `CANONICAL_FACT_PRICE_BAR_SPEC` (`canonical.fact_price_bar`) | 166-189 | `ts_code` (171) | `source_run_id` (184), `raw_loaded_at` (185) |
| `CANONICAL_FACT_FINANCIAL_INDICATOR_SPEC` (`canonical.fact_financial_indicator`) | 191-239 | `ts_code` (196) | `source_run_id` (234), `raw_loaded_at` (235) |
| `CANONICAL_FACT_EVENT_SPEC` (`canonical.fact_event`) | 241-260 | `ts_code` (247) | `source_run_id` (255), `raw_loaded_at` (256) |
| `CANONICAL_FACT_MARKET_DAILY_FEATURE_SPEC` (`canonical.fact_market_daily_feature`) | 262-310 | `ts_code` (267) | `source_run_id` (305), `raw_loaded_at` (306) |
| `CANONICAL_FACT_INDEX_PRICE_BAR_SPEC` (`canonical.fact_index_price_bar`) | 312-336 | `index_code` (317) | `source_run_id` (331), `raw_loaded_at` (332) |
| `CANONICAL_FACT_FORECAST_EVENT_SPEC` (`canonical.fact_forecast_event`) | 338-361 | `ts_code` (343) | `source_run_id` (356), `raw_loaded_at` (357) |
| `CANONICAL_ENTITY_SPEC`, `ENTITY_ALIAS_SPEC` | 88-110 | `canonical_entity_id` only — already provider-neutral | none |

`canonical_loaded_at` is on every spec — that is intentional canonical-side load metadata (when the canonical row was written), not raw-zone lineage. It stays in canonical.

### 1.2 Canonical writer (`data-platform/src/data_platform/serving/canonical_writer.py`)

`FORBIDDEN_PAYLOAD_FIELDS` (line 34) mirrors the DDL — only `submitted_at` / `ingest_seq`. 9 `CanonicalLoadSpec` entries require lineage columns:

| Spec | Identifier | required_columns lines for lineage / provider-shaped id |
|---|---|---|
| `STOCK_BASIC_LOAD_SPEC` | `canonical.stock_basic` | `ts_code` (128), `source_run_id` (136) |
| `CANONICAL_MART_LOAD_SPECS[0]` | `canonical.dim_security` | `ts_code` (145), `source_run_id` (169), `raw_loaded_at` (170) |
| `CANONICAL_MART_LOAD_SPECS[1]` | `canonical.dim_index` | `index_code` (177), `source_run_id` (183), `raw_loaded_at` (184) |
| `CANONICAL_MART_LOAD_SPECS[2]` | `canonical.fact_price_bar` | `ts_code` (191), `source_run_id` (204), `raw_loaded_at` (205) |
| `CANONICAL_MART_LOAD_SPECS[3]` | `canonical.fact_financial_indicator` | `ts_code` (212), `source_run_id` (250), `raw_loaded_at` (251) |
| `CANONICAL_MART_LOAD_SPECS[4]` | `canonical.fact_event` | `ts_code` (259), `source_run_id` (267), `raw_loaded_at` (268) |
| `CANONICAL_MART_LOAD_SPECS[5]` | `canonical.fact_market_daily_feature` | `ts_code` (275), `source_run_id` (313), `raw_loaded_at` (314) |
| `CANONICAL_MART_LOAD_SPECS[6]` | `canonical.fact_index_price_bar` | `index_code` (321), `source_run_id` (335), `raw_loaded_at` (336) |
| `CANONICAL_MART_LOAD_SPECS[7]` | `canonical.fact_forecast_event` | `ts_code` (343), `source_run_id` (356), `raw_loaded_at` (357) |

`_validate_payload_fields_match_target` (line 575-595) enforces an exact field-set match between the DuckDB payload and the Iceberg target schema; therefore changes to either side must move in lock-step.

### 1.3 dbt marts (`data-platform/src/data_platform/dbt/models/marts/*.sql`)

8 mart files; all explicitly SELECT `source_run_id, raw_loaded_at` and most explicitly SELECT `ts_code`/`index_code`. From C2 audit table:

| Mart file | `source_run_id` line | `raw_loaded_at` line |
|---|---|---|
| `mart_dim_security.sql` | 30 | 31 |
| `mart_dim_index.sql` | 10 | 11 |
| `mart_fact_event.sql` | 13 | 14 |
| `mart_fact_financial_indicator.sql` | 43 | 44 |
| `mart_fact_forecast_event.sql` | 22 | 23 |
| `mart_fact_index_price_bar.sql` | 22 | 23 |
| `mart_fact_market_daily_feature.sql` | 67 | 68 |
| `mart_fact_price_bar.sql` | 17 | 18 |

`_schema.yml` (lines 25-225 per C2) declares both lineage columns on every mart.

Intermediate layer (`int_*.sql`) computes business values; staging layer (`stg_tushare_*`) is the entry point that brings lineage in from raw. The current dbt graph propagates lineage from staging → intermediate → marts → canonical writer.

### 1.4 Provider catalog (`data-platform/src/data_platform/provider_catalog/registry.py`)

The catalog is **already provider-neutral** at the contract level. 28 promoted + 13 candidate mappings encode `("ts_code", "security_id")`, `("ts_code", "index_id")`, `("ts_code", "entity_id")` rename pairs explicitly (registry.py:751-1030). 17 canonical datasets declare `primary_key=("security_id",...)` / `("index_id",...)` / `("entity_id",...)` etc. The catalog says the right thing; the physical layer does not implement the rename.

### 1.5 Canonical dataset → table mapping (`data-platform/src/data_platform/serving/canonical_datasets.py`)

10 mappings (lines 63-74) bind provider-neutral dataset ids to physical Iceberg tables:

```
security_master         -> canonical.dim_security
security_profile        -> canonical.dim_security      (same physical table, two dataset views)
price_bar               -> canonical.fact_price_bar
adjustment_factor       -> canonical.fact_price_bar    (same physical table)
market_daily_feature    -> canonical.fact_market_daily_feature
index_master            -> canonical.dim_index
index_price_bar         -> canonical.fact_index_price_bar
event_timeline          -> canonical.fact_event
financial_indicator     -> canonical.fact_financial_indicator
financial_forecast_event -> canonical.fact_forecast_event
```

This module is the seam where dataset id maps to physical table identifier; a `canonical_v2` switch can pivot here.

### 1.6 Current-cycle inputs (`data-platform/src/data_platform/cycle/current_cycle_inputs.py`)

Output row schema is **already provider-neutral**:
- `entity_id`, `trade_date`, `close`, `pre_close`, `return_1d`, `volume`, `amount`, `market`, `industry`, `canonical_dataset_refs`, `canonical_snapshot_ids`, `lineage_refs` (lines 457-470).
- `lineage_refs` carries `cycle:`, `selection:`, `candidate:`, `canonical:<dataset>@<snapshot_id>` — provider-neutral snapshot lineage, NOT provider-specific.

The leak is INTERNAL: `_security_rows_by_alias` (line 387-395) and `_price_rows_by_alias` (line 398-413) read `ts_code` from `canonical.dim_security` / `canonical.fact_price_bar` to use as the alias-join key against `entity_alias`. Once canonical exposes `security_id`, those readers must switch.

`current_cycle_inputs` does NOT need to gain a downstream-facing change in v2 — it already produces the right output. It simply needs to stop reading `ts_code` from canonical when the rename lands.

### 1.7 Manifest (`data-platform/src/data_platform/cycle/manifest.py`)

`CyclePublishManifest.formal_table_snapshots: dict[str, FormalTableSnapshot]` co-pins multiple formal tables in one PG-stored JSON object (line 68). The DDL accepts any `formal.<object_name>` key whose `<object_name>` is in `formal_registry.formal_object_names()`; `REQUIRED_FORMAL_OBJECT_NAMES` (line 18-23 of `formal_registry.py`) is `{world_state_snapshot, official_alpha_pool, alpha_result_snapshot, recommendation_snapshot}`. **Adding a new `formal.<x>_lineage` table simply requires adding `<x>_lineage` to `FALLBACK_FORMAL_OBJECT_NAMES` (or to contracts' `FORMAL_OBJECT_NAMES`) — the manifest co-pinning mechanism already exists.**

Important: today's canonical Iceberg tables live under `canonical.*`, NOT `formal.*`. The `formal_table_snapshots` field tracks formal namespace tables specifically. So to co-pin canonical+lineage we have two options:
- **Option C-1**: keep canonical tables in `canonical.*`, add `canonical_lineage.*` namespace, and extend the manifest's snapshot map to also accept `canonical.*` and `canonical_lineage.*` keys (requires manifest schema change).
- **Option C-2**: make publish promote canonical+lineage into the `formal.*` namespace explicitly (requires upstream "publish" step to mirror canonical → formal). This matches data-platform CLAUDE.md "Formal Zone = Iceberg + manifest" but requires additional plumbing.

Neither option is a one-line change; they will be revisited in M1-D.

---

## 2. Field-by-field classification

For every column on every canonical Iceberg table today, classify into:

- **B** (canonical business): keeps in canonical_v2.
- **L** (lineage): moves to a sibling lineage table.
- **D** (debug-only): keeps OUT of canonical_v2 entirely.
- **M** (canonical metadata): canonical-side metadata, stays in canonical (e.g., `canonical_loaded_at`).
- **R** (rename): same business value, new column name (e.g., `ts_code` → `security_id`).

### 2.1 `canonical.stock_basic` (10 columns)

| Column | Class | Notes |
|---|---|---|
| `ts_code` | R | rename to `security_id` per registry `field_mapping` (registry.py:754) |
| `symbol` | B | stays |
| `name` | R | rename to `display_name` per registry mapping |
| `area`, `industry`, `market` | B | stays |
| `list_date` | B | stays (date) |
| `is_active` | B | stays |
| `source_run_id` | L | moves to `canonical_lineage.lineage_stock_basic` |
| `canonical_loaded_at` | M | stays |

### 2.2 `canonical.dim_security` (27 columns)

| Column | Class | Notes |
|---|---|---|
| `ts_code` | R | → `security_id` |
| `symbol`, `name` | B | (`name` may also rename to `display_name` per registry) |
| `market`, `industry`, `list_date`, `is_active`, `area`, `fullname`, `exchange`, `curr_type`, `list_status`, `delist_date`, `setup_date`, `province`, `city`, `reg_capital`, `employees`, `main_business`, `latest_namechange_*` (5 cols) | B | stays |
| `source_run_id` | L | → `canonical_lineage.lineage_dim_security` |
| `raw_loaded_at` | L | → `canonical_lineage.lineage_dim_security` |
| `canonical_loaded_at` | M | stays |

### 2.3 `canonical.dim_index` (9 columns)

| Column | Class | Notes |
|---|---|---|
| `index_code` | R | → `index_id` per registry mapping (e.g., registry.py:817) |
| `index_name`, `index_market`, `index_category`, `first_effective_date`, `latest_effective_date` | B | stays |
| `source_run_id`, `raw_loaded_at` | L | → `canonical_lineage.lineage_dim_index` |
| `canonical_loaded_at` | M | stays |

### 2.4 `canonical.fact_price_bar` (16 columns)

| Column | Class | Notes |
|---|---|---|
| `ts_code` | R | → `security_id` |
| `trade_date`, `freq`, `open`, `high`, `low`, `close`, `pre_close`, `change`, `pct_chg`, `vol`, `amount`, `adj_factor` | B | stays |
| `source_run_id`, `raw_loaded_at` | L | → `canonical_lineage.lineage_fact_price_bar` |
| `canonical_loaded_at` | M | stays |

### 2.5 `canonical.fact_financial_indicator` (40 columns)

| Column | Class | Notes |
|---|---|---|
| `ts_code` | R | → `security_id` |
| `end_date`, `ann_date`, `f_ann_date`, `report_type`, `comp_type`, `update_flag`, `is_latest`, plus 30 financial decimal fields | B | stays |
| `source_run_id`, `raw_loaded_at` | L | → `canonical_lineage.lineage_fact_financial_indicator` |
| `canonical_loaded_at` | M | stays |

### 2.6 `canonical.fact_event` (12 columns)

| Column | Class | Notes |
|---|---|---|
| `event_type`, `event_date`, `title`, `summary`, `event_subtype`, `related_date`, `reference_url`, `rec_time` | B | stays |
| `ts_code` | R | → `entity_id` per registry mapping (event_timeline) |
| `source_run_id`, `raw_loaded_at` | L | → `canonical_lineage.lineage_fact_event` |
| `canonical_loaded_at` | M | stays |

### 2.7 `canonical.fact_market_daily_feature` (40 columns)

| Column | Class | Notes |
|---|---|---|
| `ts_code` | R | → `security_id` |
| `trade_date`, `close`, `turnover_rate`, `turnover_rate_f`, `volume_ratio`, `pe`, `pe_ttm`, `pb`, `ps`, `ps_ttm`, `dv_ratio`, `dv_ttm`, `total_share`, `float_share`, `free_share`, `total_mv`, `circ_mv`, `up_limit`, `down_limit`, plus 18 buy/sell vol/amount fields, `net_mf_vol`, `net_mf_amount` | B | stays |
| `source_run_id`, `raw_loaded_at` | L | → `canonical_lineage.lineage_fact_market_daily_feature` |
| `canonical_loaded_at` | M | stays |

### 2.8 `canonical.fact_index_price_bar` (16 columns)

| Column | Class | Notes |
|---|---|---|
| `index_code` | R | → `index_id` |
| `trade_date`, `open`, `high`, `low`, `close`, `pre_close`, `change`, `pct_chg`, `vol`, `amount`, `exchange`, `is_open`, `pretrade_date` | B | stays |
| `source_run_id`, `raw_loaded_at` | L | → `canonical_lineage.lineage_fact_index_price_bar` |
| `canonical_loaded_at` | M | stays |

### 2.9 `canonical.fact_forecast_event` (16 columns)

| Column | Class | Notes |
|---|---|---|
| `ts_code` | R | → `security_id` |
| `ann_date`, `end_date`, `forecast_type`, `p_change_min`, `p_change_max`, `net_profit_min`, `net_profit_max`, `last_parent_net`, `first_ann_date`, `summary`, `change_reason`, `update_flag` | B | stays |
| `source_run_id`, `raw_loaded_at` | L | → `canonical_lineage.lineage_fact_forecast_event` |
| `canonical_loaded_at` | M | stays |

### 2.10 `canonical.canonical_entity`, `canonical.entity_alias`

Already provider-neutral; no change required.

### 2.11 Summary

- **9 R renames** required across canonical specs: 7 × (`ts_code` → `security_id` or `entity_id`), 2 × (`index_code` → `index_id`).
- **2 L lineage columns** per canonical mart, moving to a sibling table per mart (9 lineage tables total — one per canonical business table that today carries lineage).
- **0 D debug columns** in canonical today.
- All `canonical_loaded_at` (M) columns stay — they are canonical-side metadata, not raw lineage.

---

## 3. Lineage table design proposal

### 3.1 Where lineage rows live

A new namespace `canonical_lineage` is recommended (sibling of `canonical`). Per data-platform CLAUDE.md "Raw Zone ≠ Canonical Zone, Canonical ≠ Formal", this stays inside the Iceberg layer (not raw Parquet/JSON) so it can be queried with the same DuckDB/PyIceberg path. The name `canonical_lineage` is preferred over `audit_lineage` because:

- audit-eval owns the L7/L8 audit/replay records — calling this "audit_lineage" would create a name collision.
- "lineage" makes the intent self-describing; "canonical_lineage" makes it discoverable next to `canonical`.

### 3.2 Per-table shape

Each canonical lineage table mirrors the canonical PK + adds the lineage payload:

```
canonical_lineage.lineage_dim_security
  - security_id            (string)        — canonical PK reference
  - source_run_id          (string)
  - raw_loaded_at          (timestamp[us])
  - canonical_loaded_at    (timestamp[us]) — same value as canonical row
  - source_provider        (string)        — = "tushare" today
  - source_interface_id    (string)        — e.g. "stock_basic"
```

Same shape repeated for the 9 lineage tables, with the canonical PK adapted per table:

| Lineage table | Canonical PK columns |
|---|---|
| `canonical_lineage.lineage_stock_basic` | `security_id` |
| `canonical_lineage.lineage_dim_security` | `security_id` |
| `canonical_lineage.lineage_dim_index` | `index_id` |
| `canonical_lineage.lineage_fact_price_bar` | `security_id, trade_date, freq` |
| `canonical_lineage.lineage_fact_financial_indicator` | `security_id, end_date, report_type` |
| `canonical_lineage.lineage_fact_event` | `event_type, entity_id, event_date, event_key` |
| `canonical_lineage.lineage_fact_market_daily_feature` | `security_id, trade_date` |
| `canonical_lineage.lineage_fact_index_price_bar` | `index_id, trade_date` |
| `canonical_lineage.lineage_fact_forecast_event` | `security_id, announcement_date, report_period, forecast_type` |

Each row in `canonical_lineage.<x>` joins 1:1 to a row in `canonical.<x>` (or the renamed `canonical_v2.<x>`) on the canonical PK.

### 3.3 New columns introduced (provider-aware lineage on the lineage table only)

`source_provider` and `source_interface_id` are NEW columns introduced specifically for the lineage table. They are provider-aware **by design** — that is the whole point of the lineage table. They MUST NOT appear on canonical business rows. The reason to introduce them now:

- C5 audit notes that `subsystem_submit_queue → candidate_queue` bridge is absent in repo, but that's a P4 issue. For canonical-side lineage, the producer is the data-platform raw → staging → mart pipeline. The lineage table needs to identify which provider+interface produced each canonical row.
- Today `source_run_id` indirectly encodes provider via the run id encoding, but consumers of canonical have no clean way to query "which provider does this row come from". Making it explicit on the lineage table closes that ambiguity.

### 3.4 What does NOT go to canonical_lineage

- `submitted_at`, `ingest_seq` — these are Layer-B ingest queue metadata and never enter canonical or lineage. They stay in `data_platform.candidate_queue` per data-platform CLAUDE.md.
- Raw zone provenance (e.g., file-system path of the raw Parquet snapshot) — that lives in raw-manifest v2 already (per `raw-manifest-source-interface-hardening-20260428.md`); the canonical lineage table only needs `source_run_id` to point back to the raw manifest, not the raw file path itself.

---

## 4. Manifest co-pinning strategy

The current manifest schema (`data_platform.cycle_publish_manifest`) tracks `formal_table_snapshots: dict[str, FormalTableSnapshot]` where each key starts with `formal.`. It does NOT directly track canonical or lineage table snapshots today. Two coexisting concerns:

1. **Canonical mart snapshot set** is tracked in a sidecar file `_mart_snapshot_set.json` written by `canonical_writer.load_canonical_marts` (lines 642-658) — this is a local FS artifact, not in PG.
2. **Formal table snapshots** are tracked in PG manifest — used by `serving/formal.py` to gate reads.

The lineage tables sit at the canonical layer (per §3.1). To make lineage discoverable in the same publish event:

### 4.1 Recommended: extend the `_mart_snapshot_set.json` to include canonical_lineage tables

Lowest-cost option. The sidecar already pins canonical mart snapshot ids per `load_canonical_marts`; extend its schema to include lineage tables.

Pros:
- No PG manifest schema change.
- Lineage and canonical move in lock-step inside the same `load_canonical_marts` call.
- Atomicity is whatever Iceberg gives you per-table — but since the sidecar is rewritten last and atomically (`temp_path.replace(manifest_path)`, line 658), readers either see the OLD pair or the NEW pair, never split.

Cons:
- The sidecar is a local file, not transactional with PG. If `_mart_snapshot_set.json` writes succeed but `cycle_publish_manifest` PG insert fails (or vice versa), the two pinning sources diverge. Mitigation: keep the existing sidecar as the canonical+lineage co-pin, and treat `cycle_publish_manifest` as the formal-side authority only.

Sidecar v2 shape:

```json
{
  "version": 2,
  "load_id": "<uuid>",
  "published_at": "<iso8601>",
  "canonical_tables": {
    "dim_security": {"identifier": "canonical.dim_security", "snapshot_id": ..., "metadata_location": "..."},
    ...
  },
  "lineage_tables": {
    "lineage_dim_security": {"identifier": "canonical_lineage.lineage_dim_security", "snapshot_id": ..., "metadata_location": "..."},
    ...
  }
}
```

### 4.2 Alternative: add canonical_table_snapshots to PG manifest

Higher-cost. Add a new JSONB column `canonical_table_snapshots` to `data_platform.cycle_publish_manifest`. The new column stores both canonical and canonical_lineage snapshot ids, keyed on table identifier:

```json
{
  "canonical.dim_security": {"snapshot_id": 12345},
  "canonical_lineage.lineage_dim_security": {"snapshot_id": 67890},
  ...
}
```

Pros:
- Single source of truth for canonical+lineage+formal pinning.
- Transactional with the PG `cycle_publish_manifest` insert (already atomic per `publish_manifest`, lines 99-188).

Cons:
- Schema migration on `cycle_publish_manifest` (new column + index).
- Touches more code (new accessor functions in `manifest.py`, new validation in `serving/formal.py`).

### 4.3 Recommendation

**Default: option 4.1 (sidecar v2)**. It is the smaller change and the lineage write is already coupled to the canonical write inside `load_canonical_marts`. Promote to 4.2 only if downstream readers need per-cycle PG-pinned canonical lookup (today they do not — `serving/formal.py` reads via `formal.*`, not `canonical.*`).

**Constraint regardless of choice**: any reader that joins canonical row × lineage row must use canonical_loaded_at (M field) OR the publish-side snapshot pair as the join boundary. Joining on snapshot pair is preferred because it survives canonical re-publish.

---

## 5. canonical_v2 namespace and dual-write strategy

### 5.1 Default: parallel namespace, NOT in-place rename

Per ult_milestone.md M1.1: "If canonical physical rename is too risky, use an explicitly named `canonical_v2` namespace and dual-write window."

This audit recommends `canonical_v2` as the default for lower risk:

- Parallel namespace `canonical_v2` is added under PG-backed Iceberg catalog.
- `canonical_v2.dim_security`, `canonical_v2.fact_price_bar`, etc. are added with the renamed PK and the lineage columns dropped.
- `canonical_lineage.*` is added as the sibling lineage namespace.
- `canonical.*` continues to receive writes during the dual-write window.

### 5.2 Alternative: in-place rename of canonical.*

If the team is confident in transactional cutover, it is technically possible to:

1. Drop and recreate `canonical.*` Iceberg tables with new schemas (after backing up current snapshots).
2. Re-run the canonical writer once to repopulate.

Risk: every consumer that reads `canonical.*` directly (analytical SQL, frontend-api compat routes, M2 production proof attempts) breaks instantly. Rollback requires a re-create + re-population. Not recommended.

### 5.3 Decision

Default to `canonical_v2`. The mart spec set under `CANONICAL_MART_LOAD_SPECS` adds a parallel `CANONICAL_V2_MART_LOAD_SPECS` set; the writer gains a `load_canonical_v2_marts` function paralleling `load_canonical_marts`; the dataset-table mapping in `canonical_datasets.py` gains a feature flag `USE_CANONICAL_V2` (env var) that switches the table identifier per dataset.

---

## 6. Migration path (proposal — do NOT execute in M1-A)

Six steps. Each step is independently revertible by reverting the relevant write surface; no step is irreversible until step 6.

### Step 1 — Additive: add `canonical_v2.*` and `canonical_lineage.*` Iceberg DDL

- New file: `data-platform/src/data_platform/ddl/iceberg_tables_v2.py` (or extension to existing) with `CANONICAL_V2_*_SPEC` and `CANONICAL_LINEAGE_*_SPEC` table specs.
- New tables created via `register_table` with provider-neutral PK + no lineage on canonical_v2; provider-aware lineage on canonical_lineage.
- `canonical.*` left untouched.
- No writer change, no reader change yet.

Validation: schema-creation tests (M1-C) confirm both namespaces exist with the expected schemas; `FORBIDDEN_SCHEMA_FIELDS` does NOT need to be extended yet.

### Step 2 — dbt parallel marts

- Add `marts_v2/mart_dim_security_v2.sql`, etc., that SELECT the same business columns but using the renamed PK column (alias: `ts_code AS security_id`, `index_code AS index_id`, etc.). NO lineage columns.
- Add `marts_v2/mart_lineage_dim_security.sql`, etc., that SELECT only `<canonical_pk_columns>, source_run_id, raw_loaded_at, canonical_loaded_at, source_provider, source_interface_id` per lineage table.
- `_schema.yml` extended for the new marts.
- Original `marts/*.sql` left untouched.

Validation: dbt unit tests (M1-C) confirm all canonical_v2 mart SELECTs and all lineage mart SELECTs compile and run against the existing intermediate layer.

### Step 3 — Writer dual-write

- `serving/canonical_writer.py` gains `CANONICAL_V2_MART_LOAD_SPECS` (renamed PK, no lineage) and `CANONICAL_LINEAGE_LOAD_SPECS` (PK + lineage).
- Add `load_canonical_v2_marts(catalog, duckdb_path)` paralleling `load_canonical_marts` — writes both v2 and lineage in lock-step.
- Sidecar `_mart_snapshot_set.json` v2 schema (per §4.1) adopted.
- Original `load_canonical_marts` continues to run; both are invoked in the publish flow (or `load_canonical_v2_marts` is invoked in addition).

Validation: writer round-trip tests (M1-C) confirm canonical_v2 row count = canonical row count; lineage row count = canonical row count; canonical_v2 has no `source_run_id`/`raw_loaded_at`/`ts_code`/`index_code` columns; lineage has the right join shape.

### Step 4 — Reader cutover

- `serving/canonical_datasets.py` flips `_DATASET_TO_TABLE` to point each dataset id at its `canonical_v2.*` table identifier (gated by `USE_CANONICAL_V2` env var; default off until validated, then default on).
- `cycle/current_cycle_inputs.py` `_security_rows_by_alias` and `_price_rows_by_alias` read `security_id` (was `ts_code`) and the alias-join key flips to `security_id`.
- `serving/formal.py` is unchanged — it still reads `formal.*` tables; if any formal table becomes a copy of canonical, that copy must come from canonical_v2 going forward.

Validation: end-to-end current-cycle-inputs test (M1-C) confirms output is unchanged (provider-neutral output already), but the PARTIAL "still surfaces ts_code internally" tag from C2 is closed.

### Step 5 — `FORBIDDEN_SCHEMA_FIELDS` extension

- Once steps 1-4 are stable: extend `FORBIDDEN_SCHEMA_FIELDS` in `iceberg_tables.py` and `FORBIDDEN_PAYLOAD_FIELDS` in `canonical_writer.py` to include `source_run_id`, `raw_loaded_at`, and provider-shaped identifiers (`ts_code`, `index_code`).
- Drop legacy `canonical.*` table specs and load specs.
- Drop legacy `marts/*.sql`.
- Iceberg drop or namespace retire — coordinate with consumers; see §7 risk.

Validation: M1-C tests now FAIL on any new code that reintroduces lineage in canonical_v2; schema-evolution tests confirm the v2 namespace cannot regress.

### Step 6 — Optional: rename `canonical_v2` → `canonical`

After step 5 is stable for at least one full cycle, optionally rename namespace back. Strictly cosmetic — the namespace is just a name. Skip unless there is downstream pressure.

---

## 7. Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Direct `canonical.*` readers in `assembly`, `main-core`, `entity-registry`, `frontend-api`, or downstream analytical SQL | High during step 4 cutover | Step 4 toggles via env var first; grep audit before flipping default |
| `current_cycle_inputs._security_rows_by_alias` keying on `ts_code` | High | Step 4 explicitly switches the key; M1-C boundary test pins it |
| Iceberg snapshot id pair (canonical_v2 + lineage) drifts if writes are not serialized | Medium | `load_canonical_v2_marts` writes both inside one Python frame; sidecar atomic rename |
| Tests baselined against current schema break en masse | Medium | M1-C plans the parity tests; failing tests are expected during steps 2-4 |
| Iceberg DDL in PG-backed SQL Catalog cannot accept add-column or drop-column without manual migration | Medium | M1-B Iceberg write-chain spike addresses this; if blocked, design switches to "dual-namespace forever, no rename" |
| `formal.*` consumers expect the same column names as `canonical.*` | High if formal mirrors canonical | Confirm with C3 follow-up: today `formal.*` is materialized by L8 commit, NOT by canonical_writer; canonical rename does not directly affect formal column names |
| `data_platform.cycle_publish_manifest` PG schema change (option 4.2) creates a non-trivial migration | Low (default uses 4.1) | Stick with sidecar option |
| Canonical entity_id rename for `event_timeline` collides with C6 PK gap (event_type/event_date/event_key not projected) | Medium | M1-F re-derivation must complete before any event_timeline canonical_v2 promotion |
| dbt-duckdb / PyIceberg behavior on add-column / drop-column for existing snapshots | Medium | Validated in M1-B spike; if blocked, step 5 switches from "drop columns" to "stop reading them" |

---

## 8. M1-A acceptance against milestone

ult_milestone.md §M1-A acceptance:

- [x] Field-by-field mapping — §2.1-2.10 plus the registry rename pairs in §1.4.
- [x] Provider-neutral canonical physical target — §3 (lineage tables) + §5 (canonical_v2 namespace) + §6 step 1.
- [x] Lineage table / audit table / raw ownership — §3.4 explicitly bounds canonical_lineage vs audit-eval vs raw-manifest.
- [x] Migration strategy — §6 (six steps, mostly additive).
- [x] Does not claim implementation complete — every section labels itself "design proposal" / "do NOT execute in M1-A".

---

## 9. Open questions to confirm before M1-D

1. **Sidecar vs PG manifest co-pin** (§4): default is sidecar; confirm before §6 step 3.
2. **canonical_v2 namespace lifecycle** (§5): keep parallel forever (drop step 6) or rename back. Default: keep parallel, decide later.
3. **`source_provider`/`source_interface_id` on lineage tables** (§3.3): confirm whether these are acceptable additions to the canonical_lineage namespace (they are provider-aware by design but never in canonical business rows).
4. **C6 candidate PK gap interaction** (§7 row 7): event_timeline 8/13 candidates miss `event_type`/`event_date`/`event_key`; canonical_v2 of event_timeline cannot launch until those derivations are filled. This is not a blocker for `canonical_v2.fact_price_bar`, etc.
5. **Frontend-api legacy compat** (C3 §3.1): the `_legacy_payload(...)` route in `frontend-api/src/frontend_api/routes/cycle.py:81-82` forwards `FormalObject.payload` verbatim. This continues to need a defensive shape filter at the FE boundary, separately from canonical_v2 rename. M1-E covers it.

---

## 10. Per-task handoff block

```
Task: M1-A canonical v2 lineage separation design
Repo(s): data-platform + assembly (read-only inspection)
Output: /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/canonical-v2-lineage-separation-design-20260428.md
Validation: design-only; no command run; no tests added
Per-subrepo git state:
  data-platform: rev-parse HEAD = 330f6b4; status =  M src/data_platform/raw/writer.py /  M tests/raw/test_writer.py (pre-existing); push = not pushed; branch = main
  assembly:      rev-parse HEAD = a7f19c5; status = untracked stabilization reports include this M1-A design; push = not pushed; branch = main
Dirty files added by this task: assembly/reports/stabilization/canonical-v2-lineage-separation-design-20260428.md
Findings: 9 R renames (per §2 summary); 9 lineage tables planned (one per canonical mart with lineage today); 6-step migration path; 2 manifest co-pin options (default sidecar v2)
Outstanding risks: see §7 (12 rows)
Declaration: I did not modify project_ult_v5_0_1.md. I did not enter M2/M3/M4. I did not enable production fetch. I did not start P5 shadow-run. I did not start compose. I did not commit any forbidden files. I did not run `git init`. I did not push without approval. Tushare remains a provider=tushare adapter only. No canonical_v2 implementation was started in this round.
```
