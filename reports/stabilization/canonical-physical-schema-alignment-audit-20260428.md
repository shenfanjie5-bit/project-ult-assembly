# Canonical Physical Schema Alignment Audit (C2)

- Task: C2 — Canonical Physical Schema Alignment
- Date: 2026-04-28
- Repos: `data-platform` + `assembly`
- Audit-only declaration: This report contains NO source-code changes, NO commits, NO `git init`,
  NO push, NO migrations, and NO column-rename PRs. It documents observed current-state evidence
  and proposes target-direction shape only. Approved plan reference: `~/.claude/plans/project-ult-v5-0-1-cosmic-milner.md` §C2.
- Architectural direction (per user): the current canonical/mart/formal physical schema retaining
  `ts_code`, `source_run_id`, and `raw_loaded_at` IS a confirmed provider-neutral alignment gap.
  This report does not call it compliant. Reading A is treated as a lineage-stripped temporary
  mitigation; Reading B (lineage separation + canonical rename via `field_mapping`) is the target
  direction.
- Tushare role: Tushare remains a `provider="tushare"` source adapter only; no scope change is
  proposed.

---

## 1. Validation block

Command:

```
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform && \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -p no:cacheprovider -q \
  tests/provider_catalog tests/serving/test_canonical_datasets.py \
  tests/cycle/test_current_cycle_inputs.py 2>&1 | tail -10
```

Exact result (tail of pytest output):

```
.....................                                                    [100%]
21 passed in 0.28s
```

Status: PASS (21/21). Interpreter: `data-platform/.venv/bin/python` — `Python 3.14.3`.

Note: `pytest -q | tail -10` swallows the summary line; the verbose run captured to
`/tmp/pytest_c2.log` shows `collected 21 items ... 21 passed in 0.28s` with all four files green.

---

## 2. Per-layer current-state evidence

### 2.1 Provider catalog (`data-platform/src/data_platform/provider_catalog/registry.py`)

CONFIRMED — Catalog defines 17 canonical datasets and exposes a provider-neutral
`security_id` identifier in canonical primary keys; the provider→canonical rename is encoded
explicitly in `field_mapping`.

- File: `data-platform/src/data_platform/provider_catalog/registry.py`
  - Line 163: `field_mapping: tuple[tuple[str, str], ...]` — declarative source→canonical pairs.
  - Line 461: `_dataset("security_master", … primary_key=("security_id",), …)` — canonical PK
    uses `security_id`, not `ts_code`.
  - Line 754: `field_mapping=(("ts_code", "security_id"), ("symbol", "symbol"), ("name", "display_name"))`
    on `stock_basic`. Same pattern recurs on lines 778, 792, 804, 870, 909, 923, 934, 950, 974,
    1010, 1022 — every Tushare promoted/candidate mapping renames `ts_code`→`security_id`
    (and `ts_code`→`index_id` / `entity_id` for index- and entity-keyed sources).
  - Lines 750 (`PROVIDER_MAPPINGS`) and 945 (`PROMOTION_CANDIDATE_MAPPINGS`):
    `len(PROVIDER_MAPPINGS) == 28`, `len(PROMOTION_CANDIDATE_MAPPINGS) == 13`,
    `len(CANONICAL_DATASETS) == 17` (confirmed via interpreter import).

Quote (registry.py:750–767):

```python
PROVIDER_MAPPINGS: Final[tuple[ProviderDatasetMapping, ...]] = (
    _mapping(
        "stock_basic",
        "security_master",
        field_mapping=(("ts_code", "security_id"), ("symbol", "symbol"), ("name", "display_name")),
        source_primary_key=("ts_code",),
        unit_policy="identity/text fields only",
        date_policy="static list_date/delist_date lifecycle",
        adjustment_policy="not applicable",
        update_policy="static with corrections",
        coverage="CN_A",
    ),
```

Implication: the *catalog contract* is provider-neutral. The mismatch is purely at the physical
storage / writer / mart layer that does not adopt this rename or strip provider/lineage fields.

### 2.2 Marts (`data-platform/src/data_platform/dbt/models/marts/*.sql`)

CONFIRMED — 8/8 mart `.sql` files surface `source_run_id` and `raw_loaded_at` in their final
SELECT lists (and most also surface `ts_code` rather than `security_id`). `_schema.yml` documents
both lineage columns on every mart.

Per file (line numbers point at the `source_run_id` / `raw_loaded_at` SELECTs):

| Mart file | `source_run_id` line | `raw_loaded_at` line | Carries `ts_code`? |
| --- | --- | --- | --- |
| `mart_dim_security.sql` | 30 | 31 | n/a (uses `ts_code` upstream; see `_schema.yml`) |
| `mart_dim_index.sql` | 10 (`max(source_run_id) as source_run_id`) | 11 | n/a |
| `mart_fact_event.sql` | 13 | 14 | yes (line 5: `ts_code`) |
| `mart_fact_financial_indicator.sql` | 43 | 44 | upstream `int_financial_reports_latest` keys on ts_code |
| `mart_fact_forecast_event.sql` | 22 | 23 | upstream uses ts_code |
| `mart_fact_index_price_bar.sql` | 22 | 23 | upstream uses ts_code |
| `mart_fact_market_daily_feature.sql` | 67 | 68 | upstream uses ts_code |
| `mart_fact_price_bar.sql` | 17 | 18 | yes (line 4: `ts_code`) |
| `_schema.yml` | 25, 45, 72, 106, 141, 163, 191, 222 | 28, 48, 75, 109, 144, 166, 194, 225 | declared on every mart |

Quote (`mart_fact_price_bar.sql:1–20`):

```sql
{{ config(materialized="table") }}

select
    ts_code,
    trade_date,
    freq,
    cast(nullif(trim(cast(open as varchar)), '') as decimal(38, 18)) as open,
    cast(nullif(trim(cast(high as varchar)), '') as decimal(38, 18)) as high,
    cast(nullif(trim(cast(low as varchar)), '') as decimal(38, 18)) as low,
    cast(nullif(trim(cast(close as varchar)), '') as decimal(38, 18)) as close,
    cast(nullif(trim(cast(pre_close as varchar)), '') as decimal(38, 18)) as pre_close,
    cast(nullif(trim(cast(change as varchar)), '') as decimal(38, 18)) as change,
    cast(nullif(trim(cast(pct_chg as varchar)), '') as decimal(38, 18)) as pct_chg,
    cast(nullif(trim(cast(vol as varchar)), '') as decimal(38, 18)) as vol,
    cast(nullif(trim(cast(amount as varchar)), '') as decimal(38, 18)) as amount,
    cast(nullif(trim(cast(adj_factor as varchar)), '') as decimal(38, 18)) as adj_factor,
    source_run_id,
    raw_loaded_at
from {{ ref('int_price_bars_adjusted') }}
```

Implication: every mart faithfully forwards lineage and Tushare-shaped `ts_code` to its
canonical sink. None of the marts implement the catalog `field_mapping` rename.

### 2.3 DDL Iceberg (`data-platform/src/data_platform/ddl/iceberg_tables.py`)

CONFIRMED — Canonical Iceberg schemas declare `ts_code` (not `security_id`) and embed
`source_run_id` + `raw_loaded_at` directly into the canonical row shape. `FORBIDDEN_SCHEMA_FIELDS`
only blocks the *Layer-B ingest queue* fields (`submitted_at`, `ingest_seq`).

- File: `data-platform/src/data_platform/ddl/iceberg_tables.py`
  - Line 23: `FORBIDDEN_SCHEMA_FIELDS: Final[frozenset[str]] = frozenset({"submitted_at", "ingest_seq"})`.
  - Line 74: `pa.field("ts_code", pa.string())` in `CANONICAL_STOCK_BASIC_SPEC`.
  - Line 82: `pa.field("source_run_id", pa.string())` in `CANONICAL_STOCK_BASIC_SPEC`.
  - Lines 117, 141–142: `dim_security` carries `ts_code`, `source_run_id`, `raw_loaded_at`.
  - Lines 159–160: `dim_index` carries `source_run_id`, `raw_loaded_at`.
  - Lines 171, 184–185: `fact_price_bar` carries `ts_code`, `source_run_id`, `raw_loaded_at`.
  - Lines 196, 234–235: `fact_financial_indicator`.
  - Lines 247, 255–256: `fact_forecast_event`.
  - Lines 267, 305–306: `fact_market_daily_feature`.
  - Lines 331–332, 343, 356–357: additional mart-backed canonical specs.

Quote (`iceberg_tables.py:23` and `:166–189`):

```python
FORBIDDEN_SCHEMA_FIELDS: Final[frozenset[str]] = frozenset({"submitted_at", "ingest_seq"})
…
CANONICAL_FACT_PRICE_BAR_SPEC: Final[TableSpec] = TableSpec(
    namespace=CANONICAL_NAMESPACE,
    name="fact_price_bar",
    schema=pa.schema(
        [
            pa.field("ts_code", pa.string()),
            pa.field("trade_date", pa.date32()),
            pa.field("freq", pa.string()),
            …
            pa.field("source_run_id", pa.string()),
            pa.field("raw_loaded_at", TIMESTAMP_TYPE),
            pa.field("canonical_loaded_at", TIMESTAMP_TYPE),
        ]
    ),
)
```

Implication: `FORBIDDEN_SCHEMA_FIELDS` is intentionally narrow — it guards Layer-B ingest
metadata leakage; it does NOT guard against raw lineage columns (`source_run_id`, `raw_loaded_at`)
or provider-shaped identifiers (`ts_code`) appearing in canonical schemas. Therefore the
canonical *physical* schema is provider-coupled even though the catalog *contract* is
provider-neutral.

### 2.4 Canonical writer (`data-platform/src/data_platform/serving/canonical_writer.py`)

CONFIRMED — Every `CanonicalLoadSpec` requires `source_run_id` (and most also `raw_loaded_at`)
plus `ts_code` for security/price specs. `FORBIDDEN_PAYLOAD_FIELDS` mirrors the DDL: it only
blocks the Layer-B queue fields, not lineage or provider identifiers.

- File: `data-platform/src/data_platform/serving/canonical_writer.py`
  - Line 34: `FORBIDDEN_PAYLOAD_FIELDS = frozenset({"submitted_at", "ingest_seq"})`.
  - Line 54: `required_columns: tuple[str, ...]` on `CanonicalLoadSpec`.
  - Line 124–138: `STOCK_BASIC_LOAD_SPEC` requires `ts_code` (line 128) and `source_run_id`
    (line 136).
  - Lines 144–171: `canonical.dim_security` requires `ts_code` (145), `source_run_id` (169),
    `raw_loaded_at` (170).
  - Lines 174–185: `canonical.dim_index` requires `source_run_id` (183), `raw_loaded_at` (184).
  - Lines 187–207: `canonical.fact_price_bar` requires `ts_code` (191), `source_run_id` (204),
    `raw_loaded_at` (205).
  - Lines 209–268: `canonical.fact_financial_indicator` requires `ts_code` (212),
    `source_run_id` (267), `raw_loaded_at` (268).
  - Lines 274, 313–314: `fact_forecast_event` (subset).
  - Lines 320, 335–336: additional specs (event/index/etc.).
  - Lines 342–358: `canonical.fact_forecast_event` again with `ts_code` (343), `source_run_id`
    (356), `raw_loaded_at` (357).
  - Line 543: `for column in spec.required_columns:` — writer enforces every spec column to be
    present in the DuckDB relation; relaxing this without dual-write would break loads.
  - Lines 564–578: payload-validation reuses `FORBIDDEN_PAYLOAD_FIELDS` and the same narrow
    "no submitted_at/ingest_seq" guarantee.

Quote (`canonical_writer.py:124–138`):

```python
STOCK_BASIC_LOAD_SPEC: Final[CanonicalLoadSpec] = CanonicalLoadSpec(
    identifier=CANONICAL_STOCK_BASIC_IDENTIFIER,
    duckdb_relation="stg_stock_basic",
    required_columns=(
        "ts_code",
        "symbol",
        "name",
        "area",
        "industry",
        "market",
        "list_date",
        "is_active",
        "source_run_id",
    ),
)
```

Implication: the writer contract is the operational gatekeeper that pins the gap in place — any
canonical rename requires a writer-spec change first.

### 2.5 Current-cycle inputs (`data-platform/src/data_platform/cycle/current_cycle_inputs.py`)

PARTIAL (lineage-stripped temporary mitigation, NOT fully provider-neutral) — The current-cycle
loader projects only a small subset of canonical columns and does not request `source_run_id`
or `raw_loaded_at`, so downstream consumers do not see lineage. However, it still selects
`ts_code` from canonical (rather than `security_id`) and uses `ts_code` as the join key for
both security_master and price_bar lookups. Per user direction this is "Reading A: lineage-
stripped temporary mitigation, NOT fully provider-neutral" — it is NOT the target end state.

- File: `data-platform/src/data_platform/cycle/current_cycle_inputs.py`
  - Line 86–92: `security_rows = _records(_read_dataset(SECURITY_MASTER_DATASET,
    columns=["ts_code", "market", "industry"], snapshot_spec=snapshot_spec))` — projection
    excludes `source_run_id` / `raw_loaded_at`, but the canonical column requested is `ts_code`.
  - Line 93–108: same pattern for `price_bar` — projection excludes lineage, includes `ts_code`,
    `trade_date`, `freq`, `close`, `pre_close`, `pct_chg`, `vol`, `amount`.
  - Lines 387–395 (`_security_rows_by_alias`): builds an alias index keyed on `row.get("ts_code", "")`.
  - Lines 398–413 (`_price_rows_by_alias`): keyed on `row.get("ts_code", "")` too.

Quote (`current_cycle_inputs.py:86–108`):

```python
        security_rows = _records(
            _read_dataset(
                SECURITY_MASTER_DATASET,
                columns=["ts_code", "market", "industry"],
                snapshot_spec=snapshot_spec,
            )
        )
        price_rows = _records(
            _read_dataset(
                PRICE_BAR_DATASET,
                columns=[
                    "ts_code",
                    "trade_date",
                    "freq",
                    "close",
                    "pre_close",
                    "pct_chg",
                    "vol",
                    "amount",
                ],
                snapshot_spec=snapshot_spec,
            )
        )
```

Implication: `current_cycle_inputs.py` keeps lineage out of consumer hands (good) but still
binds the cycle pipeline to a Tushare-shaped column name. It is a temporary mitigation and not
the full provider-neutral end state.

### 2.6 Formal serving (`data-platform/src/data_platform/serving/formal.py`)

CONFIRMED — Formal serving is a thin manifest-pinned snapshot reader. It does NOT enumerate
columns and does NOT strip or project anything; its `payload: pa.Table` is whatever Iceberg
returns from `serving_reader.read_iceberg_snapshot(table_identifier, snapshot_id)`. Therefore
formal consumers are exposed to whatever physical schema canonical/mart emits — which today
includes `ts_code`, `source_run_id`, `raw_loaded_at`.

- File: `data-platform/src/data_platform/serving/formal.py`
  - Line 76: `payload: pa.Table` on `FormalObject` — opaque PyArrow table, no schema constraint.
  - Lines 79–98: `get_formal_latest`, `get_formal_by_id` — both delegate to
    `_formal_object_from_manifest`, which delegates to `_read_formal_snapshot`.
  - Lines 162–167: `_read_formal_snapshot` — reads via `serving_reader.read_iceberg_snapshot`
    and returns the Arrow payload unchanged.
  - Line 24: `FORMAL_NAMESPACE: Final[str] = "formal"` — confirms a separate namespace exists,
    but its physical schemas are not enforced to differ from canonical here.

Quote (`formal.py:69–88` and `:162–167`):

```python
@dataclass(frozen=True, slots=True)
class FormalObject:
    """A formal object materialized from one manifest-pinned Iceberg snapshot."""

    cycle_id: str
    object_type: str
    snapshot_id: int
    payload: pa.Table


def get_formal_latest(object_type: str) -> FormalObject:
    """Read the newest published formal object for object_type."""
    …
def _read_formal_snapshot(table_identifier: str, snapshot_id: int) -> pa.Table:
    payload = serving_reader.read_iceberg_snapshot(table_identifier, snapshot_id)
    if isinstance(payload, pa.Table):
        return payload
    msg = "formal DuckDB Iceberg scan did not return a PyArrow table"
    raise TypeError(msg)
```

Implication: formal-layer consumers inherit canonical's provider-coupling. There is no
formal-layer rename or lineage-strip projection that could mask the canonical gap.

---

## 3. Alignment gap statement

CONFIRMED — The canonical *physical* schema (Iceberg specs in `iceberg_tables.py`, mart
emitters in `dbt/models/marts/*.sql`, writer required_columns in `canonical_writer.py`) is
NOT provider-neutral at the storage layer:

1. The catalog contract (`registry.py`) declares `security_id` as the canonical primary key for
   17 datasets and rename pairs `("ts_code","security_id")` for every Tushare-keyed mapping.
2. The physical canonical Iceberg schemas keep `ts_code` columns (not renamed) and embed raw
   ingest lineage (`source_run_id`, `raw_loaded_at`) directly into the canonical row.
3. The mart layer faithfully forwards `ts_code` and lineage to the canonical sink (8/8 marts
   carry both lineage columns; price/event/dim_security marts carry `ts_code`).
4. The writer required_columns enforce both the provider-shaped key and the lineage columns.
5. The formal-serving layer exposes the canonical payload unchanged.

The only compensating control today is the current-cycle loader's column projection
(2.5 above), which strips lineage from one consumer path while still surfacing `ts_code`. By
user direction this is a temporary mitigation, NOT the target.

---

## 4. Temporary mitigation (Reading A) — explicit non-target

`current_cycle_inputs.py` selectively projects canonical Iceberg/DuckDB rows into a small,
deliberately narrowed column set that excludes `source_run_id` and `raw_loaded_at`. This means
that in the *current-cycle consumer path* lineage does not reach downstream consumers. However:

- The projection still uses `ts_code` (provider-shaped) as the candidate-alias key — see
  `_security_rows_by_alias` (line 392) and `_price_rows_by_alias` (line 405).
- The projection only protects this single loader. Any other consumer that calls
  `serving.formal.get_formal_*` or scans the canonical Iceberg tables directly will see
  `ts_code`, `source_run_id`, and `raw_loaded_at`.
- The fix is one-sided: it strips lineage at read time without addressing the storage-layer
  coupling.

Per user direction Reading A is NOT the target end state. It is a lineage-stripped temporary
mitigation acceptable as a short-term hold while the storage-layer migration is planned.

---

## 5. Target migration direction (Reading B / equivalent lineage-separation designs)

Description ONLY — no migration scripts, no merge-ready column renames. The audit proposes the
shape of a future change.

### 5.1 Per-affected-file shape (proposal)

| File | Shape change (proposal) | Dependencies that break | Tests requiring adjustment |
| --- | --- | --- | --- |
| `data-platform/src/data_platform/ddl/iceberg_tables.py` | Drop `source_run_id` and `raw_loaded_at` from every `CANONICAL_*_SPEC` schema; rename `ts_code` → `security_id` (or `index_id` / `entity_id` per `field_mapping` in `registry.py:754, 778, 792, 804, 817, 829, 842, 870, 885, 909, 923, 934, 950, 974, 1010`). Add a sibling `RAW_LINEAGE_*_SPEC` namespace (e.g. `raw_lineage` or `audit_lineage`) carrying `(canonical_pk_columns…, source_provider, source_run_id, raw_loaded_at, canonical_loaded_at)` keyed on the canonical PK. | Every existing canonical Iceberg snapshot becomes incompatible until rewritten. `FORBIDDEN_SCHEMA_FIELDS` would optionally extend to include `source_run_id` and `raw_loaded_at` AFTER migration completes — NOT before. | All Iceberg DDL and round-trip tests that assert `ts_code` / lineage columns; provider-catalog enforcement tests that check schema/catalog parity. |
| `data-platform/src/data_platform/serving/canonical_writer.py` | Update every `CanonicalLoadSpec.required_columns` to drop `source_run_id` / `raw_loaded_at` and rename `ts_code` → canonical id; add a new `LineageLoadSpec` set that loads the new `raw_lineage` tables in lock-step with each canonical write within the same transaction window. | Layer-B writers; Lite-mode `cycle_publish_manifest` flow; `FORBIDDEN_PAYLOAD_FIELDS` may want to extend (after migration) to forbid the lineage columns from canonical payloads. | Writer round-trip tests; spec validation tests. |
| `data-platform/src/data_platform/dbt/models/marts/*.sql` | Remove `source_run_id, raw_loaded_at` SELECT clauses (8/8 files: `mart_dim_security.sql:30–31`, `mart_dim_index.sql:10–11`, `mart_fact_event.sql:13–14`, `mart_fact_financial_indicator.sql:43–44`, `mart_fact_forecast_event.sql:22–23`, `mart_fact_index_price_bar.sql:22–23`, `mart_fact_market_daily_feature.sql:67–68`, `mart_fact_price_bar.sql:17–18`); rename SELECTed `ts_code` to canonical id; add a parallel set of `mart_lineage_*.sql` (or aggregate `mart_lineage.sql`) that emits the lineage rows for the new `raw_lineage` table. Update `_schema.yml` (lines 25, 28, 45, 48, 72, 75, 106, 109, 141, 144, 163, 166, 191, 194, 222, 225) to drop the lineage column declarations on canonical marts and add equivalent declarations on the lineage marts. | dbt downstream consumers that grep `source_run_id`; any analytical SQL referencing `ts_code`. | dbt model unit tests; staging→intermediate→mart contract tests. |
| `data-platform/src/data_platform/provider_catalog/registry.py` | No code change strictly required — the catalog already encodes the canonical names. Optional: surface a `lineage_table_id` per dataset so the writer can find the matching `raw_lineage` sink without hard-coding. | n/a (catalog is consumer of physical schema, not the reverse). | Provider-catalog parity tests against new physical schema. |
| `data-platform/src/data_platform/cycle/current_cycle_inputs.py` | Replace `ts_code` projections (lines 89, 97) with the canonical id name; rename `_security_rows_by_alias` / `_price_rows_by_alias` keys (lines 392, 405) accordingly. After the canonical rename, the lineage-strip projection becomes redundant for the lineage columns (they no longer exist on canonical) but the projection itself can stay for forward-compatibility. | Cycle-binding consumers (`assembly` reports use the row dicts). | `tests/cycle/test_current_cycle_inputs.py` (currently 7 passing) — fixtures that shape canonical rows must use the new column name. |
| `data-platform/src/data_platform/serving/formal.py` | No structural change required (formal returns whatever physical canonical/formal Iceberg has). Once the canonical rename and lineage split land, formal payloads automatically inherit the provider-neutral shape. Optionally add a defensive schema-shape assertion. | None directly. | Formal-serving snapshot tests (must be re-baselined to the new schema). |

### 5.2 Sequencing (proposal)

This list describes ORDER ONLY; it does NOT propose merge-ready changes.

1. Land the new `raw_lineage` Iceberg namespace + `LineageLoadSpec` ALONGSIDE the existing
   canonical schemas (additive only). `FORBIDDEN_SCHEMA_FIELDS` and `FORBIDDEN_PAYLOAD_FIELDS`
   stay unchanged in this step.
2. Open a *dual-write window*: every canonical write also emits a lineage row, but canonical
   schemas still carry `ts_code` / `source_run_id` / `raw_loaded_at`. Reads continue to use the
   old shape. Validation: catalog parity tests still pass, and the new lineage table is
   non-empty.
3. Add new canonical Iceberg schemas (renamed PK + dropped lineage) UNDER A NEW NAMESPACE
   (e.g. `canonical_v2`) and dual-write them. Marts gain `_v2.sql` siblings. Writer specs and
   `current_cycle_inputs.py` are NOT touched yet.
4. Migrate consumers: `current_cycle_inputs.py`, formal-serving callers, and any analytical
   consumers switch reads to `canonical_v2`. Consumers that depend on `source_run_id` for
   audit purposes switch to the `raw_lineage` table joined on canonical PK.
5. Drop the legacy `canonical.*` schemas, drop the old marts, drop the old writer specs, and
   only THEN extend `FORBIDDEN_SCHEMA_FIELDS` / `FORBIDDEN_PAYLOAD_FIELDS` to include
   `source_run_id` and `raw_loaded_at` — making the gap structurally impossible to reintroduce.
6. Audit: re-run the provider-catalog, serving-canonical-datasets, and current-cycle-inputs
   pytest suites; add a new test that asserts no canonical Iceberg spec contains lineage
   columns and no canonical PK column is named `ts_code`.

Equivalent lineage-separation designs (e.g. `audit_lineage` instead of `raw_lineage`, or a
single shared `canonical_audit` table partitioned by dataset) are acceptable; the constraint
is *separation* between provider-neutral canonical rows and provider/run-id audit rows.

### 5.3 Risk

- Rollback cost: highest at step 5 (drop legacy). Steps 1–4 are additive and individually
  reversible by feature-flagging the writer dual-write.
- Double-write window: if dual-write is purely DuckDB→Iceberg, transactional atomicity
  per Iceberg snapshot is per-table; the write to `canonical.*` and `raw_lineage.*` will
  produce two snapshots — manifest publish should bundle both snapshot ids, otherwise readers
  may observe lineage that does not yet match a canonical snapshot. Mitigation: include the
  lineage table in `cycle_publish_manifest.formal_table_snapshots`.
- Rename hazard: any consumer outside `data-platform` that has hard-coded `ts_code` (search
  scope: `assembly/`, `main-core/`, `entity-registry/`) will break at step 4 unless a
  view-aliased compatibility layer is published.
- Test debt: 21 currently-passing tests anchor the *current* behavior. Step 4 will require
  re-baselining most fixtures; step 6 must add new negative tests to make the gap a hard
  failure mode.

This section is PROPOSAL ONLY. No migration script, no PR, and no column-rename change is
made by this audit.

---

## 6. Validation interpretation

The pytest result (21 passed in 0.28s) demonstrates that the *current* schema and writer
contracts agree with each other and with the provider catalog as it stands. It does NOT
validate that the alignment gap is closed. Specifically:

- `tests/provider_catalog/*` confirms the catalog contract (28 promoted + 13 candidate
  mappings, 17 canonical datasets, every mapping has `field_mapping` and `source_primary_key`).
- `tests/serving/test_canonical_datasets.py` confirms the serving-side dataset definitions
  agree with the catalog.
- `tests/cycle/test_current_cycle_inputs.py` confirms the lineage-stripped temporary
  mitigation (projection without `source_run_id` / `raw_loaded_at`) holds.

None of these tests assert that canonical Iceberg schemas drop lineage or that canonical
columns use `security_id`. A green pytest in this audit corresponds to "current behavior is
unchanged"; it is NOT evidence that Reading B is implemented.

---

## 7. Findings tally

- CONFIRMED: 6 (provider catalog, marts 8/8, DDL Iceberg, canonical writer, formal serving,
  alignment-gap statement).
- PARTIAL: 1 (current-cycle inputs — lineage-stripped temporary mitigation, NOT fully
  provider-neutral).
- INFERRED: 0.

Total: 7 findings (6 CONFIRMED + 1 PARTIAL).

---

## 8. Outstanding risks

- Storage-layer provider coupling: every canonical Iceberg snapshot in flight retains
  `ts_code`; renaming requires either a write-side rename + reader compat view, or a
  parallel `canonical_v2` namespace.
- Lineage co-location: `source_run_id` and `raw_loaded_at` are inside canonical row payloads,
  so any reader (formal serving, analytical SQL, future projects) inherits them by default.
  No central enforcement currently prevents this beyond the narrow Layer-B `submitted_at` /
  `ingest_seq` block.
- Mitigation fragility: the `current_cycle_inputs.py` lineage-strip is a single-consumer
  patch. New consumers added without explicit projection will leak lineage.
- Cross-repo contract risk: any downstream repo (`assembly`, `main-core`, `entity-registry`)
  that consumes canonical/formal Iceberg rows directly may have hard-coded `ts_code`. Audit
  scope did not enumerate these consumers — propose a follow-up grep.
- Manifest co-pinning: when lineage is moved to a separate Iceberg table, the publish
  manifest must pin both the canonical and lineage snapshots together to avoid "lineage
  without canonical" or "canonical without lineage" reads.
- Tushare role: the proposed direction does NOT expand Tushare's scope; it simply moves
  Tushare-introduced lineage into a separate audit table. Tushare remains a
  `provider="tushare"` source adapter only.

---

## 9. Per-task handoff block

```
Task: C2
Repo(s): data-platform + assembly
Output report: /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/canonical-physical-schema-alignment-audit-20260428.md
Validation command: cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -p no:cacheprovider -q tests/provider_catalog tests/serving/test_canonical_datasets.py tests/cycle/test_current_cycle_inputs.py 2>&1 | tail -10
Validation result: PASS (21 passed in 0.28s; tail-truncated summary, full log saved to /tmp/pytest_c2.log)
Per-subrepo git state:
  data-platform: rev-parse HEAD = 330f6b4d82a96d36c8fd150cc1a0a432d7c6cb9c
                 status =  M src/data_platform/raw/writer.py
                           M tests/raw/test_writer.py
                 push status = N/A (audit did not push; pre-existing dirty files unrelated to C2)
                 interpreter = /Users/fanjie/Desktop/Cowork/project-ult/data-platform/.venv/bin/python — Python 3.14.3
                 branch = main
  assembly:      rev-parse HEAD = a7f19c5994f807b2cf32eb2f45ef48f6fe23095f
                 status = ?? reports/stabilization/frontend-raw-route-alignment-fix-20260428.md
                          ?? reports/stabilization/production-daily-cycle-gap-audit-20260428.md
                          ?? reports/stabilization/project-ult-v5-0-1-supervisor-review-20260428.md
                          ?? reports/stabilization/raw-manifest-source-interface-hardening-20260428.md
                          ?? reports/stabilization/canonical-physical-schema-alignment-audit-20260428.md (NEW — this audit)
                 push status = not pushed (audit-only)
                 interpreter = N/A (no Python execution against assembly)
                 branch = main
Dirty files:
  Pre-existing (NOT introduced by this audit):
    data-platform/src/data_platform/raw/writer.py (M)
    data-platform/tests/raw/test_writer.py (M)
    assembly/reports/stabilization/frontend-raw-route-alignment-fix-20260428.md (??)
    assembly/reports/stabilization/production-daily-cycle-gap-audit-20260428.md (??)
    assembly/reports/stabilization/project-ult-v5-0-1-supervisor-review-20260428.md (??)
    assembly/reports/stabilization/raw-manifest-source-interface-hardening-20260428.md (??)
  Newly added by this audit:
    assembly/reports/stabilization/canonical-physical-schema-alignment-audit-20260428.md
Findings: 6 CONFIRMED, 1 PARTIAL, 0 INFERRED
Outstanding risks:
  - Canonical Iceberg snapshots in flight retain `ts_code`; rename requires dual-write or canonical_v2 namespace.
  - Lineage columns sit inside canonical rows; new readers leak audit data by default.
  - `current_cycle_inputs.py` mitigation is single-consumer; new consumers will not inherit it.
  - Cross-repo consumers (`assembly`, `main-core`, `entity-registry`) may have hard-coded `ts_code`; not enumerated in this audit.
  - Publish manifest must pin canonical + lineage snapshots together once split.
  - Tushare scope unchanged; remains a `provider="tushare"` adapter only.
Declaration: I did not mark any PARTIAL or PREFLIGHT finding as PASS. I did not commit any forbidden files. Tushare remains a provider=tushare adapter only. I did not run `git init`. I did not push without approval.
```
