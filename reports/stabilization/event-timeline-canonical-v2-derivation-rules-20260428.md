# Event-Timeline canonical_v2 Derivation Rules

**Round:** M1-G1
**Date:** 2026-04-28
**Status:** Design evidence only. No code change made by this report.

## Purpose

Document the per-source canonical PK derivation rules for `event_timeline` so the matching M1-G2 controlled implementation lands a **safe-subset** `canonical_v2.fact_event` covering only the 6 sources currently in `int_event_timeline.sql`. The remaining sources (`namechange`, `block_trade`, the 8 candidates) stay BLOCKED. Full M1 closure is NOT achieved by this design + the M1-G2 controlled implementation alone.

## Canonical contract (re-derived from registry)

The event_timeline canonical dataset declares (`registry.py:629-645`):
- `primary_key = ("event_type", "entity_id", "event_date", "event_key")`
- Fields: `event_type` (enum), `entity_id` (canonical id), `event_date` (date), `event_key` (text), `summary` (text)
- `date_policy = "event date; announcement date retained when distinct"`
- `update_policy = "event-time with late-arriving corrections"`

Provider catalog mappings (`registry.py:880-903` PROVIDER_MAPPINGS, `registry.py:982-1005` PROMOTION_CANDIDATE_MAPPINGS):
- 8 PROVIDER_MAPPINGS entries map a source interface to `event_timeline`. Field mapping is uniformly `(ts_code → entity_id)` — NO field mapping for `event_type`, `event_date`, or `event_key` (these must be derived in dbt or in the writer).
- 8 PROMOTION_CANDIDATE_MAPPINGS entries (status `"candidate"`) also map to `event_timeline`. Same shape: only `(ts_code → entity_id)` mapping; no derivation for the other 3 PK columns.

This means **every event_timeline row's canonical PK requires per-source derivation in dbt** (or in the writer). The M1-G1 task documents what those rules are.

## A. Source inventory

The table below cross-references three sources of truth: `registry.py` (status), `int_event_timeline.sql` (current UNION branches and their derived constants), and the 8 staging models for the safe subset (column lists for `event_key` derivation choices).

| `source_interface_id` | Registry status | Source PK | int_event_timeline branch | `event_type` derived as | `event_date` derived as | `event_key` candidate columns | `entity_id` derived as | Verdict |
|---|---|---|---|---|---|---|---|---|
| `anns` | `legacy_typed_not_in_catalog` (registry.py:895) | `(ts_code, ann_date, title)` | YES — branch at int_event_timeline.sql:3-15 | constant `'announcement'` (l.4) | `ann_date` (l.6) | title, summary (=name), reference_url, rec_time | `ts_code → entity_id` (mart_v2 rename) | **SAFE** — already in UNION; rules are pinned in dbt |
| `suspend_d` | `legacy_typed_not_in_catalog` (registry.py:896) | `(ts_code, trade_date)` | YES — branch at int_event_timeline.sql:19-31 | constant `'suspend'` (l.20) | `trade_date` (l.22) | event_subtype, summary (=suspend_timing), related_date | `ts_code → entity_id` | **SAFE** — already in UNION; rules pinned |
| `dividend` | `promoted` (registry.py:897) | `(ts_code, ann_date, end_date)` | YES — branch at int_event_timeline.sql:35-47 | constant `'dividend'` (l.36) | `ann_date` (l.38) | summary, event_subtype (=div_proc), related_date (=end_date) | `ts_code → entity_id` | **SAFE** |
| `share_float` | `promoted` (registry.py:898) | `(ts_code, ann_date, float_date)` | YES — branch at int_event_timeline.sql:51-63 | constant `'share_float'` (l.52) | `float_date` (l.54) | summary (=holder_name), event_subtype (=share_type), related_date (=ann_date) | `ts_code → entity_id` | **SAFE** |
| `stk_holdernumber` | `promoted` (registry.py:899) | `(ts_code, ann_date, end_date)` | YES — branch at int_event_timeline.sql:67-79 | constant `'holder_number'` (l.68) | `ann_date` (l.70) | summary (=holder_num), related_date (=end_date) | `ts_code → entity_id` | **SAFE** |
| `disclosure_date` | `promoted` (registry.py:900) | `(ts_code, ann_date, end_date)` | YES — branch at int_event_timeline.sql:83-98 | constant `'disclosure_date'` (l.84) | `coalesce(actual_date, pre_date, ann_date, modify_date)` (l.86) | summary, related_date (=end_date) | `ts_code → entity_id` | **SAFE** |
| `namechange` | `promoted` (registry.py:894) | `(ts_code, start_date)` | **NO branch in int_event_timeline.sql** | n/a | n/a | n/a | n/a | **BLOCKED** — registry-promoted but no UNION branch. Closing this would require implementing AND testing a real `'name_change'` branch in int_event_timeline.sql. Out of safe-subset scope. |
| `block_trade` | `promoted` (registry.py:901) | `(ts_code, trade_date)` | **NO branch in int_event_timeline.sql** | n/a | n/a | n/a | n/a | **BLOCKED** — registry-promoted but no event_type rule and no UNION branch. |
| `pledge_stat` | `candidate` (registry.py:996) | `(ts_code, end_date)` | NO | MISSING | n/a | n/a | n/a | **BLOCKED** — candidate; no UNION branch; no field_mapping for event_type/event_date/event_key. |
| `pledge_detail` | `candidate` (registry.py:997) | `(ts_code, ann_date)` | NO | MISSING | n/a | n/a | n/a | **BLOCKED** — same reason. |
| `repurchase` | `candidate` (registry.py:998) | `(ts_code, ann_date)` | NO | MISSING | n/a | n/a | n/a | **BLOCKED** — same reason. |
| `stk_holdertrade` | `candidate` (registry.py:999) | `(ts_code, ann_date)` | NO | MISSING | n/a | n/a | n/a | **BLOCKED** — same reason. |
| `limit_list_ths` | `candidate` (registry.py:1000) | `(trade_date, ts_code)` | NO | MISSING | n/a | n/a | n/a | **BLOCKED** — same reason. |
| `limit_list_d` | `candidate` (registry.py:1001) | `(trade_date, ts_code)` | NO | MISSING | n/a | n/a | n/a | **BLOCKED** — same reason. |
| `hm_detail` | `candidate` (registry.py:1002) | `(trade_date, ts_code)` | NO | MISSING | n/a | n/a | n/a | **BLOCKED** — same reason. |
| `stk_surv` | `candidate` (registry.py:1003) | `(ts_code, ann_date)` | NO | MISSING | n/a | n/a | n/a | **BLOCKED** — same reason. |

**Counts:** 6 SAFE (in current int_event_timeline.sql UNION) | 2 promoted-but-not-in-UNION (namechange, block_trade) | 8 candidate (no UNION branch).

## B. Per-source verdict

- **6 SAFE sources** can produce canonical PK NOW:
  - `anns`, `suspend_d`, `dividend`, `share_float`, `stk_holdernumber`, `disclosure_date`.
  - Rule pinned in `int_event_timeline.sql` constants + `mart_fact_event_v2.sql` derivation in M1-G2.
  - Note: `anns` and `suspend_d` carry registry status `legacy_typed_not_in_catalog`, but they ARE in the int_event_timeline UNION today (driving the legacy `canonical.fact_event`). For canonical_v2.fact_event we honor the existing UNION layout — registry status does not gate us, the UNION does.

- **`namechange` BLOCKED**:
  - Registry-promoted but NO branch in int_event_timeline.sql.
  - Closing this requires (a) deciding the canonical event_type constant (`'name_change'` proposed but UNRECORDED), (b) implementing a new UNION branch that reads `stg_namechange` and produces `(event_type, ts_code, event_date, ...)`, (c) adding tests for the new branch. All three steps are out of M1-G2 safe-subset scope.

- **`block_trade` BLOCKED**:
  - Registry-promoted but no event_type rule documented anywhere; no int_event_timeline UNION branch.
  - Same closure path as namechange.

- **8 candidate sources BLOCKED**:
  - All 8 lack a UNION branch and lack field_mapping for `event_type` / `event_date` / `event_key`.
  - M1.6 promotion will need to (a) add per-source canonical event_type constants to the registry (e.g., `'pledge'`, `'repurchase'`, `'limit_up'`, `'hot_money_trade'`, `'institution_survey'`, `'holder_trade'`), (b) add UNION branches in int_event_timeline.sql, (c) add tests, (d) extend the v2 mart's `accepted_values` constraint.

## C. Canonical PK proposal

**`(event_type, entity_id, event_date, event_key)`** — matches `registry.py:632`.

Justification:
- `event_type` first: filter-first dimension. Analysts query "all dividends" or "all suspensions" before further drilling. Indexable.
- `entity_id` second: high-selectivity after type. Joins to `canonical_v2.dim_security`.
- `event_date` third: temporal coherence. Date contiguity for time-series workloads.
- `event_key` fourth: intra-day disambiguation. Stable per-row key derived from source-specific intra-event fields (see §E).

## D. `event_type` taxonomy (recorded for the safe subset)

Pinned set for canonical_v2.fact_event in this round:
```
{'announcement', 'suspend', 'dividend', 'share_float', 'holder_number', 'disclosure_date'}
```

This is enforced by the `accepted_values` dbt test on `mart_fact_event_v2.event_type`. Any future source promotion must extend this set and the test in lockstep.

**Suggested but UNRECORDED for blocked sources** (do NOT promote in this round):
- `'name_change'` for `namechange`
- `'block_trade'` for `block_trade`
- `'pledge'` for `pledge_stat` and `pledge_detail` (or two distinct types if scope warrants)
- `'repurchase'` for `repurchase`
- `'holder_trade'` for `stk_holdertrade`
- `'limit_up_ths'` / `'limit_up'` for `limit_list_ths` / `limit_list_d`
- `'hot_money_trade'` for `hm_detail`
- `'institution_survey'` for `stk_surv`

These are domain-inferred names, not authoritative. M1.6 owns the canonical taxonomy decision.

## E. `event_key` derivation rule (per-source)

Single deterministic expression, identical in v2 and lineage marts:
```sql
md5(
    concat_ws(
        '|',
        source_interface_id,
        event_type,
        coalesce(title, ''),
        coalesce(summary, ''),
        coalesce(event_subtype, ''),
        coalesce(cast(related_date as varchar), ''),
        coalesce(reference_url, ''),
        coalesce(rec_time, '')
    )
) as event_key
```

Rationale (per user direction in M1-G1 review):
- **Includes `source_interface_id`**: two distinct sources accidentally producing the same `(event_type, entity_id, event_date)` tuple still get distinct keys.
- **Includes `reference_url` and `rec_time`**: distinct legacy `anns` events on the same date with different titles, URLs, or recording times do NOT collapse into one row.
- **Includes business columns (`title`, `summary`, `event_subtype`, `related_date`)**: provides per-source discrimination. The 6 safe sources all populate at least one of these.
- **Pre-image is fully reproducible**: re-running dbt produces the same hash for the same row.
- **Stable across raw_loaded_at**: `raw_loaded_at` is excluded from the pre-image so two loads of the same source row produce the same `event_key`. Uniqueness is enforced UPSTREAM by `int_event_timeline`'s `unique_combination_of_columns` dbt test — both marts are direct SELECTs, NO dedup CTE inside the marts. See §F for the full rationale and failure semantics.

**Pre-existence of `source_interface_id`**: this column is NOT in `int_event_timeline.sql` today. M1-G2 Step 3a adds a constant column per UNION branch (`'anns'`, `'suspend_d'`, `'dividend'`, `'share_float'`, `'stk_holdernumber'`, `'disclosure_date'`). This is an additive change to the intermediate; legacy `mart_fact_event.sql` SELECTs by name and is unaffected.

## F. Deduplication / ordering rule

**Decision (revised after codex review):** uniqueness is delegated UPSTREAM to `int_event_timeline.sql`'s dbt `unique_combination_of_columns` test on `(event_type, ts_code, event_date, title, related_date, reference_url)`. Both `mart_fact_event_v2.sql` and `mart_lineage_fact_event.sql` are **direct SELECTs with NO dedup CTE** — they read int_event_timeline as-is and apply the identical event_key derivation expression.

Why this works:
- The intermediate's uniqueness key `(event_type, ts_code, event_date, title, related_date, reference_url)` already pins each unique source row.
- Both marts read the SAME upstream and apply the SAME event_key md5 expression, so their `(event_type, entity_id, event_date, event_key)` row sets are byte-identical by construction. The `canonical_writer._validate_canonical_v2_mart_pairings` validator passes because each side of the pair has the same row count and the same composite-key set.

Why no mart-local dedup CTE inside the marts:
- `mart_fact_event_v2.sql` (canonical_v2 namespace) cannot reference `raw_loaded_at` — the existing `test_canonical_v2_mart_sql_does_not_select_lineage_columns` (in [test_marts_provider_neutrality.py](data-platform/tests/dbt/test_marts_provider_neutrality.py)) regex-scans for raw-zone lineage tokens at the SQL-text level and would fail on raw-zone lineage references.
- Adding dedup ONLY to lineage would produce v2/lineage row-set asymmetry and break the pairing validator.
- The clean resolution is to delegate uniqueness upstream and keep both marts as direct SELECTs.

Failure semantics (fail-loud, not fail-silent):
- `daily_refresh` runs dbt models first, then dbt tests, then canonical publication. The dbt run materializes the marts, but `dbt_test` must pass before the canonical write/publication step starts.
- If upstream `int_event_timeline.sql` ever loses uniqueness (the dbt `unique_combination_of_columns` test fails), `daily_refresh` skips the canonical step, so no failing mart output is published to canonical.
- If somehow duplicates do reach the writer, the canonical writer's `_validate_unique_canonical_keys` step remains the second line of defense before pairing comparison, raising a clear duplicate-key error.
- Either way, the upstream regression is the diagnostic signal; both downstream marts surface the same failure mode together.

`int_event_timeline.sql` does NOT carry an `update_flag` column. If late-arriving corrections create same-key duplicates, the upstream uniqueness test fires during `dbt_test`; `daily_refresh` then skips canonical write/publication for that run. (M1.6 may revisit this if the 8 candidate sources require explicit late-correction handling.)

## G. Files to read / modify in M1-G2

Direct handoff list:

- DDL — `data-platform/src/data_platform/ddl/iceberg_tables.py`:
  - Add `CANONICAL_V2_FACT_EVENT_SPEC` after line 636 (mirror forecast_event spec at lines 618-636).
  - Add `CANONICAL_LINEAGE_FACT_EVENT_SPEC` after line 799 (mirror forecast_event lineage spec at lines 782-799).
  - Append both to `CANONICAL_V2_TABLE_SPECS` (line 641-650) and `CANONICAL_LINEAGE_TABLE_SPECS` (line 801-810).
  - Use the existing `TIMESTAMP_TYPE` constant for `canonical_loaded_at`. Read the forecast_event spec to confirm the exact constant name.
  - Update `__all__` exports.

- Writer — `data-platform/src/data_platform/serving/canonical_writer.py`:
  - Add `CANONICAL_V2_FACT_EVENT_LOAD_SPEC` after line 690 (mirror forecast_event at lines 656-690).
  - Add `CANONICAL_LINEAGE_FACT_EVENT_LOAD_SPEC` after line 718.
  - `required_columns` does NOT include `canonical_loaded_at` (writer injects).
  - Append to `CANONICAL_V2_MART_LOAD_SPECS` (line 692-701) and `CANONICAL_LINEAGE_MART_LOAD_SPECS` (line 703-718). Length-match invariant maintained.
  - Add `"canonical_v2.fact_event": ("event_type", "entity_id", "event_date", "event_key")` to `CANONICAL_V2_PAIRING_KEY_COLUMNS` (line 719-734).
  - Update `__all__`.

- dbt intermediate — `data-platform/src/data_platform/dbt/models/intermediate/int_event_timeline.sql`:
  - Add per-branch `source_interface_id` constant column (6 branches).
  - Place column in a consistent position (e.g., after `event_type`).
  - Confirm via grep that no consumer of `int_event_timeline` uses `select *` (legacy mart_fact_event SELECTs by name).

- dbt marts (NEW):
  - `data-platform/src/data_platform/dbt/models/marts_v2/mart_fact_event_v2.sql`
  - `data-platform/src/data_platform/dbt/models/marts_lineage/mart_lineage_fact_event.sql`
  - Both are direct SELECTs from `int_event_timeline` and use a byte-identical `event_key` expression.
  - `mart_fact_event_v2.sql` does not project raw lineage columns or `canonical_loaded_at`; lineage lives on the sibling mart, and the canonical writer injects `canonical_loaded_at`.
  - `mart_lineage_fact_event.sql` projects source lineage columns and does not project `canonical_loaded_at`; the canonical writer injects it.

- Schema YML — `data-platform/src/data_platform/dbt/models/marts_v2/_schema.yml` and `data-platform/src/data_platform/dbt/models/marts_lineage/_schema.yml`:
  - Add `mart_fact_event_v2` entry with composite-PK `unique_combination_of_columns` test, `accepted_values` test on `event_type`, `not_null` on PK columns.
  - Add lineage entry with composite-PK test plus `not_null` on `source_provider`, `source_interface_id`, `source_run_id`, `raw_loaded_at`.

- Datasets — `data-platform/src/data_platform/serving/canonical_datasets.py`:
  - Add `CanonicalDatasetTable("event_timeline", "canonical_v2.fact_event")` to `CANONICAL_DATASET_TABLE_MAPPINGS_V2` at line 98-108.
  - Add `"event_timeline": "entity_id"` to `_V2_ALIAS_COLUMN` at line 125-135.
  - Update docstring/comment at lines 1-17 and 93-97.

- Tests:
  - `data-platform/tests/dbt/test_dbt_skeleton.py` — extend `MART_V2_MODEL_NAMES` and `MART_LINEAGE_MODEL_NAMES`.
  - `data-platform/tests/ddl/test_iceberg_tables.py` — extend the idempotent-ensure expected table list.
  - `data-platform/tests/serving/test_canonical_writer.py` — extend `_write_canonical_v2_mart_placeholder_relations` with fact_event placeholder rows carrying `source_interface_id`.
  - `data-platform/tests/serving/test_canonical_datasets_v2_cutover.py` — add event_timeline cutover assertion.
  - The 3 provider-neutrality scoreboard files iterate by introspection; new specs will auto-discover.

## H. Constraints

- partition_by = None (M2.1 owns partition_by addition; bare PyArrow lacks field-id metadata).
- No live `dbt run` (Python 3.14 mashumaro incompatibility; M2.1 owns it).
- No live Iceberg catalog write (M2.1 owns it).
- No production fetch / compose / shadow-run.
- Do NOT extend `FORBIDDEN_SCHEMA_FIELDS` or `FORBIDDEN_PAYLOAD_FIELDS` in this round (legacy specs still need lineage; M1-G3 retirement plan owns the extension sequencing).

## I. Acceptance

- This evidence file is written.
- Source-by-source table cites file paths and line numbers for every claim.
- The 8 candidate sources, `namechange`, and `block_trade` are explicitly BLOCKED in the report.
- No code change made by this report.

## J. Status declarations

- This is a **DESIGN** evidence file. It does NOT close M1.
- M1-G2 is a **SAFE-SUBSET CONTROLLED IMPLEMENTATION** that lands the 6 safe sources. It does NOT close M1 either.
- Full M1 closure requires (a) namechange / block_trade UNION branches with tests, (b) M1.6 promotion of the 8 candidates, (c) legacy `canonical.*` retirement (per M1-G3 readiness plan).
- P5 remains BLOCKED. M2 / M3 / M4 not entered.
- `project_ult_v5_0_1.md` and `ult_milestone.md` UNCHANGED.
