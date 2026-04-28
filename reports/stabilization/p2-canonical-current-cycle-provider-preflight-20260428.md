# P2 Canonical Current-Cycle Provider Preflight - 2026-04-28

## Status

PASS for P2 provider preflight. This closes the source-specific P2 input
provider blocker, but it is not a full production `daily_cycle_job` pass.

Production P2 now defaults to provider-neutral canonical current-cycle inputs.
The previous Tushare staging provider remains only as an explicit legacy
test/debug provider.

## Commits Reviewed

- data-platform: `4e10c6e3ee441c107e804bef8bbe5a00a81905a6`
  - Adds `data_platform.cycle.current_cycle_inputs`.
  - Loads current-cycle rows from canonical tables/datasets only.
  - Fails closed when canonical snapshots, entity aliases, or candidate rows are
    missing.
- orchestrator: `361bfe6fc0104414aaa55c3f1e11699acdffcfd3`
  - Adds `DataPlatformCanonicalCurrentCycleInputProvider`.
  - Makes `P2DryRunAssetFactoryProvider` default to the canonical provider.
  - Changes production provider surface to
    `phase2_current_cycle_canonical_inputs`.
  - Adds no-source-leak checks for P2 input evidence.
- frontend-api: `0c24fad51deabd3b1031dc1315b8d98294392b49`
  - Keeps raw data routes out of the default read-only production surface.
  - Disables direct data-platform public API fallback by default.
- main-core: `efaa4f697267257c5936ddd8df6f3c16b3b5634d`
  - Removes provider-specific labels from the controlled vertical-slice event
    fixture.

## Canonical Input Contract

`DataPlatformCanonicalCurrentCycleInputProvider` emits this provider-neutral
evidence shape:

```json
{
  "cycle_id": "CYCLE_20260416",
  "trade_date": "2026-04-16",
  "selection_ref": "cycle_candidate_selection:CYCLE_20260416",
  "candidate_ids": [10, 11],
  "entity_ids": ["ENT_STOCK_600519.SH", "ENT_STOCK_000001.SZ"],
  "canonical_dataset_refs": ["price_bar", "security_master"],
  "canonical_snapshot_ids": {"price_bar": 101, "security_master": 202},
  "row_count": 2,
  "lineage_refs": [
    "cycle:CYCLE_20260416",
    "selection:cycle_candidate_selection:CYCLE_20260416",
    "candidate:10",
    "candidate:11",
    "canonical:price_bar@101",
    "canonical:security_master@202"
  ]
}
```

Forbidden production P2 input evidence markers:

- `stg_daily`
- `stg_stock_basic`
- `tushare-staging`
- `doc_api`
- raw `source_run_id`
- raw `raw_loaded_at`

The canonical provider raises if these markers appear in serialized input
evidence.

## Production Provider Status

Command:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/orchestrator
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/orchestrator/src:/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src \
  /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python - <<'PY'
from orchestrator_adapters.production_daily_cycle import production_daily_cycle_provider
provider = production_daily_cycle_provider()
print(provider.status().supported_surfaces)
print(provider.p2_provider.input_provider.__class__.__name__)
PY
```

Result:

```text
phase2_current_cycle_canonical_inputs present
phase2_current_cycle_tushare_inputs absent
DataPlatformCanonicalCurrentCycleInputProvider
```

## Validation

Data-platform:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
PYTHONPATH=src .venv/bin/python -m pytest -q \
  tests/cycle/test_current_cycle_inputs.py \
  tests/serving/test_canonical_datasets.py \
  tests/serving/test_reader.py

result:
28 passed
```

Orchestrator:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/orchestrator
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/orchestrator/src:/Users/fanjie/Desktop/Cowork/project-ult/main-core/src:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src:/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src:/Users/fanjie/Desktop/Cowork/project-ult/reasoner-runtime \
  /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest -q \
  tests/integration/test_production_daily_cycle_provider.py \
  tests/integration/test_p2_dry_run_handoff.py

result:
completed with 5 dbt CLI skips; no failures
```

Frontend-api:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/frontend-api
PYTHONDONTWRITEBYTECODE=1 /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python \
  -m pytest -p no:cacheprovider -q \
  tests/test_boundary_imports.py \
  tests/test_no_source_leak.py \
  tests/test_entity_data_routes.py \
  tests/test_cycle_routes.py \
  tests/test_graph_routes.py \
  tests/test_operations_routes.py

result:
41 passed
```

Main-core:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/main-core
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python \
  -m pytest -p no:cacheprovider -q \
  tests/integration/test_new_data_interface_vertical_slice.py

result:
1 passed
```

No-source scan:

```text
rg -n --hidden -i "tushare|doc_api|stg_tushare" \
  /Users/fanjie/Desktop/Cowork/project-ult/graph-engine/graph_engine \
  /Users/fanjie/Desktop/Cowork/project-ult/reasoner-runtime \
  /Users/fanjie/Desktop/Cowork/project-ult/main-core/src \
  /Users/fanjie/Desktop/Cowork/project-ult/frontend-api/src

result:
no matches
```

Lint:

```text
ruff check changed orchestrator/frontend-api/main-core files
result:
All checks passed
```

## Findings

- P0: none.
- P1: full production Dagster `daily_cycle_job` proof still pending; this file
  only proves P2 canonical input provider readiness.
- P2: none for source-specific P2 input leakage.
- P3: the explicit legacy Tushare provider remains in orchestrator tests for
  regression/debug coverage; it is no longer the production default.
