# M1.10 — Controlled v2 Proof Feasibility Preflight (2026-04-29)

## Scope

Assess whether legacy retirement **precondition 3** (controlled production-like
v2 proof: `dbt run` over `marts_v2` + `marts_lineage`, `load_canonical_v2_marts`,
and read-side smoke through `read_canonical_dataset` under
`DP_CANONICAL_USE_V2=1`) can be exercised:

1. **Locally as a fixture/closed-loop proof** without docker compose, without
   production fetch.
2. **Production-like** against the `lite-local` Docker compose PostgreSQL
   service for the PG-backed Iceberg catalog, without entering Dagster/M2
   daily-cycle execution.

This file began as plan-mode preflight evidence. After explicit user approval,
the controlled compose-Postgres proof was executed successfully on
2026-04-29. The boundary classification is now
`CONTROLLED_COMPOSE_PROOF_PASSED` — local fixture proof landed in M1.10, and
the approved follow-up used the existing `lite-local` PostgreSQL service plus
a host-side Python 3.12 runtime. The command is intentionally **not** a Dagster
daily-cycle proof: the Lite `dagster-daemon` image remains probe-only and
ships no business code or `dbt` CLI.

## Probes Executed

All probes are read-only and do not require network or production fetch.

```sh
# 1. Existing v2 writer/reader/integration tests still pass
cd data-platform && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
  -p no:cacheprovider \
  tests/serving/test_canonical_writer.py \
  tests/serving/test_reader.py \
  tests/integration/test_daily_refresh.py
# → 56 passed, 1 skipped, 14 warnings in 4.17s

# 2. dbt importability probe (no run)
cd data-platform && .venv/bin/python -c "import dbt; print(getattr(dbt,'__version__','unknown'))"
# → "unknown" (namespace package importable; no top-level __version__)

# 3. dbt CLI invocation probe (no run)
cd data-platform && .venv/bin/dbt --version
# → mashumaro.exceptions.UnserializableField: Field "schema" of type
#   Optional[str] in JSONObjectSchema is not serializable
# (CLI startup crashes under Python 3.14 / mashumaro / current dbt-core)

# 4. dbt project + profile inspection
ls data-platform/src/data_platform/dbt/
# → README.md, __init__.py, dbt_project.yml, macros/, models/,
#   profiles.yml.example, seeds/, tests/
#   (NO profiles.yml — only .example)

# 5. Compose layout inspection
ls assembly/compose/
# → dagster/, full-dev.yaml, lite-local.yaml

# 6. Host Python 3.12 runtime probe (no dbt run)
which python3.12
# → /Users/fanjie/.local/bin/python3.12
python3.12 --version
# → Python 3.12.12

# 7. uv probe for a throwaway out-of-repo runtime (no env creation)
which uv
# → /opt/homebrew/bin/uv
```

## Feasibility Table

| Item | Status | Evidence |
|---|---|---|
| Can dbt execute with current Python 3.14? | **BLOCKED on the existing `.venv`** | `dbt --version` crashes with `mashumaro.exceptions.UnserializableField: Field "schema" of type Optional[str] in JSONObjectSchema` — dbt CLI startup fails before any command runs under Python 3.14. This is no longer a command-derivation blocker because `/Users/fanjie/.local/bin/python3.12` is present and `data-platform/pyproject.toml` declares `requires-python = ">=3.12,<3.14"`. The derived command uses a throwaway Python 3.12 venv outside the repo. |
| Is a DuckDB profile available locally? | **PASS via `daily_refresh.py` runtime profile generation** | A checked-in `profiles.yml` is still absent, but `_run_dbt_step()` writes `daily_refresh_dbt_profiles/profiles.yml` beside `DP_DUCKDB_PATH` before each dbt invocation. A static repo profile is not required for the derived `python -m data_platform.daily_refresh --mock` command. |
| Can `marts_v2` + `marts_lineage` be selected without production fetch? | **PASS (executed after approval)** | Full-asset `daily_refresh.py --mock` uses `DEFAULT_DBT_SELECTORS = ("staging", "intermediate", "marts", "marts_v2", "marts_lineage")`, so dbt run/test includes both v2 selector groups while fetching only local fixture data. The executed command did not pass `--select`, deliberately forcing the all-datasets path and the v2 loader. |
| Can `load_canonical_v2_marts()` be invoked on a fixture/local catalog only? | **PASS** | `tests/serving/test_canonical_writer.py:225-272` (`test_load_canonical_v2_marts_writes_manifest_with_paired_snapshot_ids`) exercises the loader against `pyiceberg.catalog.memory.InMemoryCatalog` with a tmp_path warehouse and a local DuckDB staging file. M1.10-3 extends this with a closed-loop test (`test_load_canonical_v2_marts_closed_loop_under_v2_flag_reads_pinned_snapshots`) covering all 9 paired marts. |
| Can `read_canonical_dataset` smoke under `DP_CANONICAL_USE_V2=1` read pinned v2 snapshot manifests? | **PASS** | `tests/serving/test_reader.py:668-742` (`test_read_canonical_dataset_uses_canonical_v2_manifest`) and `tests/serving/test_reader.py:745-829` (`test_read_canonical_dataset_routes_event_timeline_to_v2_under_flag`) cover individual datasets with mocked DuckDB. M1.10-3 extends with a real-DuckDB closed-loop test that drives `iceberg_scan` against the manifest-pinned snapshot for all 9 v2 marts in one fixture run. |
| Is compose required for full production-like proof? | **YES, executed after approval** | The proof needs a real PG-backed Iceberg SQL catalog. The approved command started only the existing `lite-local` PostgreSQL service, then ran data-platform from a host Python 3.12 venv. This avoided the probe-only Dagster image while proving dbt materialization, PG-backed catalog writes, cross-process snapshot pinning, and v2 reader smoke. |

## Boundary Classification

**`CONTROLLED_COMPOSE_PROOF_PASSED`** (approved and executed on 2026-04-29)

- Local fixture closed-loop proof landed in M1.10-3
  (`test_load_canonical_v2_marts_closed_loop_under_v2_flag_reads_pinned_snapshots`)
  and passes under `DP_CANONICAL_USE_V2=1`. All assertions A–I are now
  covered by tests in `data-platform/tests/serving/`.
- Full controlled production-like proof (`dbt run` of `marts_v2` +
  `marts_lineage`, real PG-backed Iceberg catalog, separate writer/reader
  processes) can be run without using the probe-only Dagster container.
  The derived command starts only the existing compose PostgreSQL service,
  installs data-platform into a throwaway Python 3.12 venv under `/tmp`,
  runs `daily_refresh.py --mock`, then runs a separate v2 reader smoke
  process against the same warehouse.
- This remains M1 controlled proof only. It is not M2 `daily_cycle_job`
  production proof, not P5 readiness, and not a production fetch.

## Controlled Proof Command — **EXECUTED, PASSED**

The command below was executed after explicit user approval for precondition 3.
It is derived from the actual CLI (`--date`, `--mock`, `--json-report`) and
uses a local fixture adapter only. It starts compose, creates a temporary
runtime outside the repo, and writes evidence under
`assembly/tmp-runtime/m1-controlled-v2-proof/`.

```sh
set -euo pipefail

ULT_ROOT=/Users/fanjie/Desktop/Cowork/project-ult
PROOF_DATE=20260429
PROOF_ROOT="$ULT_ROOT/assembly/tmp-runtime/m1-controlled-v2-proof"
PROOF_VENV=/tmp/project-ult-m1-controlled-v2-proof-py312

cd "$ULT_ROOT"
mkdir -p "$PROOF_ROOT"

set -a
. "$ULT_ROOT/assembly/.env"
set +a

# Approval-gated compose boundary: starts only the existing lite-local
# PostgreSQL service needed for the PG-backed Iceberg SqlCatalog.
docker compose \
  --env-file "$ULT_ROOT/assembly/.env" \
  -f "$ULT_ROOT/assembly/compose/lite-local.yaml" \
  up -d postgres

for attempt in $(seq 1 60); do
  if docker compose \
    --env-file "$ULT_ROOT/assembly/.env" \
    -f "$ULT_ROOT/assembly/compose/lite-local.yaml" \
    exec -T postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    break
  fi
  if [ "$attempt" -eq 60 ]; then
    echo "postgres did not become ready after 120s" >&2
    exit 1
  fi
  sleep 2
done

/Users/fanjie/.local/bin/python3.12 - "$POSTGRES_PORT" <<'PY'
import socket
import sys
import time

host = "127.0.0.1"
port = int(sys.argv[1])
deadline = time.time() + 120
last_error = None
while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=2):
            break
    except OSError as exc:
        last_error = exc
        time.sleep(2)
else:
    raise SystemExit(
        f"postgres host port {host}:{port} not reachable after 120s: {last_error}"
    )
PY

# Host-side Python 3.12 dbt/data-platform runtime, outside the repo.
uv venv --clear --python /Users/fanjie/.local/bin/python3.12 "$PROOF_VENV"
uv pip install --python "$PROOF_VENV/bin/python" -e "$ULT_ROOT/data-platform"

export DP_PG_DSN="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@127.0.0.1:${POSTGRES_PORT}/${POSTGRES_DB}"
export DP_RAW_ZONE_PATH="$PROOF_ROOT/raw"
export DP_ICEBERG_WAREHOUSE_PATH="$PROOF_ROOT/iceberg/warehouse"
export DP_DUCKDB_PATH="$PROOF_ROOT/duckdb/data_platform.duckdb"
export DP_ICEBERG_CATALOG_NAME="data_platform_m1_controlled_v2_proof"
export DP_DBT_EXECUTABLE="$PROOF_VENV/bin/dbt"
export DP_CANONICAL_USE_V2=1
export PYTHONDONTWRITEBYTECODE=1

"$PROOF_VENV/bin/python" - <<'PY'
import os
import time

from sqlalchemy import create_engine, text

deadline = time.time() + 120
last_error = None
engine = create_engine(os.environ["DP_PG_DSN"])
while time.time() < deadline:
    try:
        with engine.connect() as conn:
            conn.execute(text("select 1"))
        break
    except Exception as exc:
        last_error = exc
        time.sleep(2)
else:
    raise SystemExit(f"postgres SQL readiness failed after 120s: {last_error}")
PY

"$PROOF_VENV/bin/python" -m data_platform.daily_refresh \
  --date "$PROOF_DATE" \
  --mock \
  --json-report "$PROOF_ROOT/daily-refresh-$PROOF_DATE.json"

"$PROOF_VENV/bin/python" - "$PROOF_ROOT/reader-smoke-$PROOF_DATE.json" <<'PY'
import json
import sys
from pathlib import Path

from data_platform.serving.canonical_datasets import CANONICAL_DATASET_TABLE_MAPPINGS_V2
from data_platform.serving.reader import (
    canonical_snapshot_id_for_dataset,
    get_canonical_stock_basic,
    read_canonical_dataset,
)

output_path = Path(sys.argv[1])
dataset_results = []
for mapping in CANONICAL_DATASET_TABLE_MAPPINGS_V2:
    snapshot_id = canonical_snapshot_id_for_dataset(mapping.dataset_id)
    table = read_canonical_dataset(mapping.dataset_id)
    assert table.num_rows >= 1, mapping.dataset_id
    dataset_results.append(
        {
            "dataset_id": mapping.dataset_id,
            "table_identifier": mapping.table_identifier,
            "snapshot_id": snapshot_id,
            "row_count": table.num_rows,
        }
    )
    print(
        f"{mapping.dataset_id} {mapping.table_identifier} "
        f"snapshot={snapshot_id} rows={table.num_rows}"
    )

stock_basic = get_canonical_stock_basic(active_only=True)
assert stock_basic.num_rows >= 1
print(f"stock_basic_helper rows={stock_basic.num_rows}")
payload = {
    "ok": True,
    "dataset_count": len(dataset_results),
    "datasets": dataset_results,
    "stock_basic_helper": {"row_count": stock_basic.num_rows},
}
output_path.parent.mkdir(parents=True, exist_ok=True)
tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
tmp_path.replace(output_path)
assert output_path.exists() and output_path.stat().st_size > 0
PY

test -s "$PROOF_ROOT/reader-smoke-$PROOF_DATE.json"
```

Expected proof properties:

- `daily_refresh.py --mock` avoids Tushare / production fetch.
- dbt runs through the runtime-generated profile and includes
  `marts_v2` + `marts_lineage` through `DEFAULT_DBT_SELECTORS`.
- `load_canonical_v2_marts()` writes canonical_v2 and canonical_lineage
  tables into a PG-backed Iceberg SQL catalog.
- The final Python process proves reader-side `DP_CANONICAL_USE_V2=1`
  smoke from a separate process, reads manifest-pinned snapshots, and
  persists `reader-smoke-20260429.json` atomically under `PROOF_ROOT`.
- The command waits for both container-side `pg_isready` and host-side
  TCP/SQL readiness before invoking the PG-backed Iceberg catalog, closing
  the prior host-port readiness race.
- It is still not a Dagster `daily_cycle_job.execute_in_process(...)`
  proof and must not be reported as M2 or P5 evidence.

What this controlled run would prove that the fixture proof cannot
(unchanged from the original analysis):

- Real PG-backed Iceberg SqlCatalog write (vs `InMemoryCatalog` file
  warehouse).
- Real `dbt run` materialization of `marts_v2/*` + `marts_lineage/*`
  SQL models (vs hand-populated DuckDB relations).
- Cross-process snapshot pinning: writer process publishes the
  `_mart_snapshot_set.json` manifest; reader process consumes it
  across a process boundary (vs same-process publish + read).
- End-to-end ingest → staging → mart materialization through the
  `--mock` path, which is the closest production approximation that
  does not call Tushare.

After explicit approval, the controlled compose-Postgres proof was executed and
passed. It remains M1 controlled proof only: it does not claim M2 Dagster
`daily_cycle_job` proof or P5 readiness.

## Controlled Proof Result — PASSED

Artifacts:

- `assembly/tmp-runtime/m1-controlled-v2-proof/daily-refresh-20260429.json`
- `assembly/tmp-runtime/m1-controlled-v2-proof/reader-smoke-20260429.json`

Result summary:

- `daily_refresh.py --mock`: `ok=true`.
- Daily refresh steps: `adapter=ok`, `dbt_run=ok`, `dbt_test=ok`,
  `canonical=ok`, `raw_health=ok`.
- Canonical write results: 27 writes, 0 skipped writes.
- Reader smoke: 10 v2 dataset mappings read through
  `read_canonical_dataset()` under `DP_CANONICAL_USE_V2=1`; stock_basic helper
  also returned rows.
- Reader smoke row counts: security_master=1, security_profile=1, price_bar=3,
  adjustment_factor=3, market_daily_feature=1, index_master=1,
  index_price_bar=1, event_timeline=8, financial_indicator=1,
  financial_forecast_event=1, stock_basic_helper=1.

## Pre-existing Test Sweep — M1 baseline still green

Quoted from the probe-1 result:

```
56 passed, 1 skipped, 14 warnings in 4.17s
```

Coverage:

- `tests/serving/test_canonical_writer.py` — 39 tests (writer publish + manifest + paired pairing + provider-neutrality)
- `tests/serving/test_reader.py` — 14 tests (reader manifest + v2 routing + fail-closed)
- `tests/integration/test_daily_refresh.py` — 4 tests (daily refresh pipeline integration)

Total: 56 passed, 1 skipped (real-PG path skipped when no PG instance is up
locally — expected on host without compose). No regressions vs M1.9
baseline.

## What Lands in M1.10 vs What Stays Gated

| Item | M1.10 | Gated behind approval |
|---|---|---|
| Closed-loop fixture proof for write→read across all 9 datasets under v2 flag | ✓ done | — |
| `_mart_snapshot_set.json` manifest contains both `canonical_v2_tables` and `canonical_lineage_tables` dicts (9 entries each) | ✓ asserted | — |
| Reader uses pinned snapshot from manifest under `DP_CANONICAL_USE_V2=1` for all 9 marts (real `iceberg_scan`) | ✓ asserted | — |
| Reader fails closed when manifest absent (no unpublished-head fallback for v2 marts) | ✓ asserted | — |
| `canonical_loaded_at` paired across v2/lineage rows | ✓ asserted | — |
| Canonical PK row sets match across v2/lineage pair | ✓ asserted | — |
| `dbt run` over `marts_v2` + `marts_lineage` in production-like runtime | ✓ executed after approval | — |
| Real PG-backed Iceberg SqlCatalog write | ✓ executed after approval | — |
| Cross-process writer/reader snapshot pinning | ✓ executed after approval | — |

## Decision

Precondition 3 is now **DONE — local fixture closed-loop proof passed and
controlled compose-Postgres proof executed successfully after approval**.
M1 may now proceed to Phase B legacy retirement sequencing. This proof is still
not M2 `daily_cycle_job` proof and not P5 readiness.

## Cross-References

- Controlled-proof results write-up (PASSED): [`m1-10-controlled-v2-proof-results-20260429.md`](m1-10-controlled-v2-proof-results-20260429.md)
- New closed-loop test: `data-platform/tests/serving/test_canonical_writer.py::test_load_canonical_v2_marts_closed_loop_under_v2_flag_reads_pinned_snapshots`
- Phase B inventory: [`m1-10-legacy-retirement-phase-b-inventory-20260429.md`](m1-10-legacy-retirement-phase-b-inventory-20260429.md)
- Progress evidence (updated): [`m1-legacy-retirement-preconditions-progress-20260428.md`](m1-legacy-retirement-preconditions-progress-20260428.md)
- Readiness evidence (appended): [`m1-legacy-canonical-retirement-readiness-20260428.md`](m1-legacy-canonical-retirement-readiness-20260428.md)
