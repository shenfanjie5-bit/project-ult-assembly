# P1 Provider-Neutral Raw/Canonical Runtime - 2026-04-28

## Status

PASS for runtime boundary preflight. This is not P5 readiness and does not
enable 138-interface production ingestion.

This evidence turns the provider-neutral Tushare catalog from documentation into
a runtime admission gate:

- Raw/staging may remain provider-specific and traceable.
- Curated marts, canonical serving, production daily-cycle, graph, reasoner, and
  frontend business surfaces must consume provider-neutral canonical datasets.
- Tushare is only `provider=tushare` source adapter metadata, not a business
  contract.

## Commits Reviewed

- data-platform: `330f6b4d82a96d36c8fd150cc1a0a432d7c6cb9c`
  - Adds `TUSHARE_INTERFACE_REGISTRY` keyed by `source_interface_id`.
  - Adds Raw manifest v2 metadata for provider/source interface/doc API/schema
    hash/request parameter hash.
  - Preserves old manifest readability.
  - Keeps existing typed Tushare assets as the only production fetch set.
  - Makes ambiguous `doc_api` mapping lookups fail closed unless
    `source_interface_id` is supplied.
- data-platform: `4e10c6e3ee441c107e804bef8bbe5a00a81905a6`
  - Adds canonical dataset/table mapping and provider-neutral current-cycle
    loader used by P2 preflight.

## Registry Counts

Command:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
PYTHONPATH=src .venv/bin/python - <<'PY'
from collections import Counter
from data_platform.provider_catalog import TUSHARE_INTERFACE_REGISTRY, catalog_summary
rows = list(TUSHARE_INTERFACE_REGISTRY.values())
print(catalog_summary())
print("registry_total", len(rows))
print("by_status", dict(Counter(r.promotion_status for r in rows)))
print("production_selectable", sum(1 for r in rows if r.production_selectable))
print("fetch_support", dict(Counter(r.fetch_support for r in rows)))
print("trade_cal", [(r.source_interface_id, r.doc_api, r.promotion_status, r.production_selectable) for r in rows if r.doc_api == "trade_cal"])
PY
```

Result:

```text
provider_interface_count: 138
registry_total: 148
production_selectable: 28
generic_unpromoted_count: 107
promotion_candidate_count: 13
legacy_typed_not_in_catalog: 10
fetch_support: typed=28, inventory_only=120
trade_cal:
  trade_cal_stock -> promoted, production_selectable=true
  trade_cal_futures -> inventory_only, production_selectable=false
```

Interpretation:

- The CSV is the 138-row Tushare provider inventory.
- The active registry has 148 rows because it includes 10 explicit legacy typed
  assets that are already in the codebase but not in the current CSV inventory.
- Only 28 typed assets are production-selectable.
- The 107 generic inventory rows and 13 promotion candidates are not enabled for
  production fetch.
- `doc_api` is no longer a unique key; `source_interface_id` is.

## Raw Manifest V2 Sample

Command:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
PYTHONPATH=src .venv/bin/python - <<'PY'
import json
from data_platform.adapters.tushare.assets import TUSHARE_ASSETS
asset = next(asset for asset in TUSHARE_ASSETS if asset.dataset == "daily")
metadata = dict(asset.metadata or {})
print(json.dumps({k: metadata[k] for k in ("provider","source_interface_id","doc_api","partition_key","schema_hash","canonical_dataset","canonical_table","production_selectable")}, sort_keys=True))
PY
```

Redacted sample:

```json
{
  "canonical_dataset": "price_bar",
  "canonical_table": "canonical.fact_price_bar",
  "doc_api": "daily",
  "partition_key": ["trade_date"],
  "production_selectable": true,
  "provider": "tushare",
  "schema_hash": "ba087449eee6af810113d4fb11199874671c999327f74714f026fec5802d7fdb",
  "source_interface_id": "daily"
}
```

Raw writer tests also prove manifest v2 writes `request_params_hash` and accepts
legacy manifests without v2 metadata.

## Validation

Data-platform focused registry/raw/dbt/canonical suite:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
PYTHONPATH=src .venv/bin/python -m pytest -q \
  tests/provider_catalog \
  tests/raw \
  tests/adapters/test_tushare.py \
  tests/test_assets.py \
  tests/dbt/test_tushare_staging_models.py \
  tests/dbt/test_marts_models.py \
  tests/serving/test_canonical_writer.py \
  tests/ddl/test_iceberg_tables.py

result:
82 passed, 2 skipped
```

Canonical loader/reader focused suite:

```text
PYTHONPATH=src .venv/bin/python -m pytest -q \
  tests/cycle/test_current_cycle_inputs.py \
  tests/serving/test_canonical_datasets.py \
  tests/serving/test_reader.py

result:
28 passed
```

Raw health and asset metadata probes:

```text
PYTHONPATH=src .venv/bin/python scripts/check_raw_zone.py \
  --root tests/dbt/fixtures/raw \
  --deep \
  --json

result:
{"checked_artifacts": 3, "issues": [], "ok": true, "root": "tests/dbt/fixtures/raw"}
```

Backend-A full data-platform regression:

```text
.venv/bin/python -m pytest
result:
456 passed, 74 skipped, 12 warnings
```

## Findings

- P0: none.
- P1: none for this runtime boundary.
- P2: none.
- P3: full production ingestion of all 138 interfaces remains intentionally
  deferred; every new production promotion still requires canonical dataset,
  field mapping, primary key, unit, date policy, adjustment policy, refresh
  policy, late-arriving policy, and coverage decision.
