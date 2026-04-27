# P1 Iceberg Write Chain Architecture Spike

Recorded: 2026-04-27

Scope:

- Verify the P1 write-chain questions with real local PostgreSQL and
  PyIceberg writes, not code inspection alone.
- Reused the running `assembly` lite-local compose stack Postgres
  (`localhost:5432/proj`, password redacted in this report).
- Added a focused data-platform spike test:
  `tests/spike/test_iceberg_publish_manifest_chain.py`.

Conclusion:

1. PG-backed SQL catalog: yes.
   `data_platform.serving.catalog.load_catalog()` builds a PyIceberg
   `SqlCatalog` from `DP_PG_DSN`, `DP_ICEBERG_CATALOG_NAME`, and
   `DP_ICEBERG_WAREHOUSE_PATH`, converting PostgreSQL/JDBC DSNs to
   `postgresql+psycopg://...` and enabling `init_catalog_tables=true`.
   The new spike creates a real temporary PostgreSQL database, writes
   formal Iceberg tables through that catalog, queries
   `iceberg_tables.metadata_location` in PG, and verifies the referenced
   Iceberg metadata JSON has the expected `current-snapshot-id`.
   Note: the SQL catalog stores catalog records and metadata pointers in
   PG; Iceberg snapshot state lives in the metadata JSON referenced by PG.

2. Single-table commit: yes.
   Existing `tests/spike/test_iceberg_write_chain.py` produced real
   append/overwrite snapshots for `canonical.stock_basic`; the new spike
   also overwrites each formal table and asserts each write creates a
   current snapshot id.

3. `cycle_publish_manifest` semantics: yes, via the existing
   `publish_manifest()` API rather than a function literally named
   `cycle_publish_manifest`.
   It inserts into PostgreSQL table
   `data_platform.cycle_publish_manifest` after a cycle reaches `phase3`.
   The new spike publishes all four registry-required formal tables:
   `formal.world_state_snapshot`, `formal.official_alpha_pool`,
   `formal.alpha_result_snapshot`, and
   `formal.recommendation_snapshot`.

4. Formal serving by manifest snapshot: yes.
   `data_platform.serving.formal` resolves the publish manifest first and
   calls `read_iceberg_snapshot(table_identifier, snapshot_id)`. The new
   spike verifies latest reads `CYCLE_20260417` at the manifest-pinned
   snapshot, and direct `by_snapshot` can read the older published
   `CYCLE_20260416` snapshot.

5. Failure atomicity / visibility: yes at the formal serving boundary.
   The new spike writes a third set of formal Iceberg snapshots, installs
   a PostgreSQL trigger that forces manifest publish failure during the
   status update, and proves the failed cycle has no manifest, latest
   formal serving remains bound to `CYCLE_20260417`, and the unpublished
   v3 snapshot is rejected by `get_formal_by_snapshot()`.
   This does not claim cross-table Iceberg transactionality; partial
   Iceberg table commits may physically exist, but formal serving does not
   expose them without a committed PG publish manifest.

Focused code evidence:

- `data-platform/src/data_platform/serving/catalog.py`
  PG-backed SQL catalog loader and namespace initialization.
- `data-platform/src/data_platform/serving/canonical_writer.py`
  canonical overwrite returns current snapshot id.
- `data-platform/src/data_platform/cycle/manifest.py`
  `publish_manifest()`, `get_publish_manifest()`,
  `get_latest_publish_manifest()`, and snapshot lookup by PG JSONB.
- `data-platform/src/data_platform/serving/formal.py`
  formal readers bind table reads to manifest snapshot ids.
- `data-platform/tests/spike/test_iceberg_publish_manifest_chain.py`
  end-to-end spike harness for this report.

Commands run:

```text
docker compose -f compose/lite-local.yaml --env-file .env ps
result:
  postgres, neo4j, dagster-daemon, and dagster-webserver were healthy;
  postgres was published on 127.0.0.1:5432.

set -a
source /Users/fanjie/Desktop/Cowork/project-ult/assembly/.env
set +a
export DATABASE_URL="postgresql://${POSTGRES_USER}:<redacted>@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
export DP_PG_DSN="$DATABASE_URL"
export PATH="/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH"
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest \
  tests/spike/test_iceberg_publish_manifest_chain.py \
  -q
result:
  1 passed; PyIceberg emitted the expected overwrite warning:
  "Delete operation did not match any records".

/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest \
  tests/spike/test_iceberg_write_chain.py \
  tests/spike/test_iceberg_publish_manifest_chain.py \
  tests/cycle/test_publish_manifest.py \
  tests/serving/test_catalog.py \
  tests/serving/test_canonical_writer.py \
  tests/serving/test_reader.py \
  tests/serving/test_formal.py \
  tests/serving/test_formal_manifest_consistency.py \
  tests/raw \
  -q
result:
  passed; output reached 100%.
  Warnings were PyIceberg overwrite warnings only.

/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest \
  tests/dbt \
  tests/cycle \
  tests/queue \
  tests/ddl \
  tests/integration/test_p1a_smoke.py \
  -q
result:
  passed; output reached 100%.
```

Harness fixes made while running:

- Several PostgreSQL test fixtures used `str(make_url(...))`, which
  serialized SQLAlchemy URLs with `***` as the password and caused
  follow-up migration connections to fail. They now use
  `render_as_string(hide_password=False)`.
- `scripts/smoke_p1a.sh` now respects a caller-provided `dbt` on PATH
  before falling back to `data-platform/.venv/bin`, so the Python 3.12
  dbt runtime can be used instead of the local Python 3.14 venv that
  crashes in dbt/mashumaro.

Generated artifacts:

- `data-platform/docs/spike/iceberg-write-chain.md`
  rewritten by `tests/spike/test_iceberg_write_chain.py` with a passing
  real PostgreSQL run:
  PyIceberg `0.11.1`, PyArrow `24.0.0`, SQLAlchemy `2.0.49`,
  3/3 spike cases passing.

Remaining boundary:

- This is a focused architecture spike, not a Dagster production cycle
  e2e run.
- There is no separate function literally named `cycle_publish_manifest`;
  the existing equivalent is `publish_manifest()`.
- The verified atomicity is publish-manifest visibility atomicity. It
  intentionally does not assert a cross-table Iceberg transaction.
