# Formal Serving No-Source-Leak Runtime Proof

**Round:** M1-G4
**Date:** 2026-04-28
**Status:** Runtime guard PROOF — supersedes the prior PARTIAL `formal-serving-no-source-leak-followup-20260428.md`. Does NOT claim production live proof.

## Purpose

Document the data-platform runtime guard `FormalPayloadSourceFieldError` and the frontend-api recursive sanitizer `_sanitize_public_formal_payload` that together enforce no-source-leak across the formal serving boundary. Replace the prior PARTIAL test-only contract evidence with proof that BOTH layers are runtime-active.

## Section 1 — Data-platform runtime guard code path

### Forbidden field set

[formal.py:25-42](data-platform/src/data_platform/serving/formal.py:25) — `FORBIDDEN_PUBLIC_FORMAL_FIELDS` (frozenset, 14 entries):

```
"source", "source_name", "source_run_id", "source_status",
"source_provider", "source_interface_id",
"raw_loaded_at", "submitted_at", "ingest_seq",
"provider", "provider_id", "provider_name",
"ts_code", "index_code"
```

This exact-key set covers (a) raw-zone lineage (`source_run_id`, `raw_loaded_at`),
(b) Layer-B ingest metadata (`submitted_at`, `ingest_seq`), and (c)
provider-shaped identifiers (`ts_code`, `index_code`). The runtime guard also
applies a naming-pattern check outside the frozenset: normalized field names
starting with `source` / `provider`, or containing `_source` / `_provider`, are
rejected.

### Exception class

[formal.py:87-103](data-platform/src/data_platform/serving/formal.py:87) — `FormalPayloadSourceFieldError(ValueError)`. Carries `table_identifier`, `snapshot_id`, and the list of forbidden fields detected.

### Public entry points

- [formal.py:116-124](data-platform/src/data_platform/serving/formal.py:116) — `get_formal_latest(object_type) -> FormalObject`. Resolves the latest publish manifest, then constructs `FormalObject` via `_formal_object_from_manifest()`.
- [formal.py:127-135](data-platform/src/data_platform/serving/formal.py:127) — `get_formal_by_id(cycle_id, object_type) -> FormalObject`. Resolves the manifest for a specific cycle_id.
- Both call paths funnel through `_formal_object_from_manifest()` which calls `_read_formal_snapshot()` at lines 160 and 185.

### Runtime guard call

[formal.py:199-209](data-platform/src/data_platform/serving/formal.py:199) — `_read_formal_snapshot(table_identifier, snapshot_id) -> pa.Table`:
1. Calls `serving_reader.read_iceberg_snapshot()` to fetch the pyarrow Table.
2. Calls `_raise_forbidden_formal_fields(payload, table_identifier, snapshot_id)` at line 202.
3. Returns the payload only if the guard does NOT raise.

[formal.py:212-255](data-platform/src/data_platform/serving/formal.py:212) — `_raise_forbidden_formal_fields()`:
- Walks the full `pa.Schema` recursively, including nested `struct` and list
  value fields.
- Flags exact-key matches in `FORBIDDEN_PUBLIC_FORMAL_FIELDS`.
- Flags source/provider naming patterns (`source*`, `provider*`, `*_source*`,
  `*_provider*`).
- If non-empty, raises `FormalPayloadSourceFieldError` with dotted paths such
  as `payload.source_run_id` or `payload[].provider_ref`.

### Scope

- Schema-level guard: scans the `pa.Table` schema, including nested struct/list
  fields.
- It does not inspect string values; it enforces the public schema/key contract.
- The frontend-api sanitizer (Section 2) handles JSON-payload recursion as a
  complementary response-layer defense.

## Section 2 — Frontend-api route + sanitizer code path

### Forbidden keys set

[frontend-api/src/frontend_api/routes/cycle.py:22-39](frontend-api/src/frontend_api/routes/cycle.py:22) — `_FORMAL_PAYLOAD_FORBIDDEN_KEYS` — frozenset of the SAME 14 entries (identical copy of the data-platform set; drift risk noted in Section 5).

### Public surfaces

- `/api/project-ult/formal/{object_type}` — line 61 in `cycle.py`.
- `/api/project-ult/formal/{object_type}/{cycle_id}` — line 70.
- Three legacy compat routes via `_legacy_payload(...)`:
  - `/api/world-state/latest` (line 88) → `_legacy_payload(request, "world_state_snapshot")`
  - `/api/pool/latest` (line 93) → `_legacy_payload(request, "official_alpha_pool")`
  - `/api/recommendations/latest` (line 98) → `_legacy_payload(request, "recommendation_snapshot")`

### Sanitizer

[cycle.py:103-105](frontend-api/src/frontend_api/routes/cycle.py:103) — `_legacy_payload()` calls `_sanitize_public_formal_payload(...)`.

[cycle.py:123-132](frontend-api/src/frontend_api/routes/cycle.py:123) — `_sanitize_public_formal_payload(payload)`:
- Recursive across dict + list + scalar.
- Strips exact forbidden keys and the same source/provider naming patterns via
  `_is_formal_payload_forbidden_key(...)`.
- Recurses into list items at line 131.

### Scope

- JSON-shape recursion (dict + list + scalar) — handles arbitrarily nested payloads.
- Applied uniformly to both new public routes and legacy compat routes.

## Section 3 — Test coverage

### Data-platform tests

[tests/serving/test_formal_no_source_leak.py](data-platform/tests/serving/test_formal_no_source_leak.py):
- 22 tests (per the latest pytest run; the original count was 10, updated when the runtime guard was promoted from test-only contract and then extended for nested/pattern fields).
- Includes parametrized tests over each of the 14 forbidden fields.
- Includes parametrized tests over source/provider naming-pattern fields such
  as `source_vendor`, `provider_ref`, and `actual_provider`.
- Includes nested `struct` coverage for forbidden field paths inside a formal
  `pa.Table` schema.
- Includes a runtime-guard fixture that synthesizes a pyarrow Table containing each forbidden field and asserts `FormalPayloadSourceFieldError` is raised.
- Includes a positive-path test that synthesizes a canonical_v2-shaped payload (no forbidden fields) and asserts the guard accepts.

### Frontend-api tests

[frontend-api/tests/test_no_source_leak.py](frontend-api/tests/test_no_source_leak.py):
- **4 tests.** Parametrized assertions that responses do NOT carry any forbidden key from the 14-entry set. (`pytest --collect-only -q tests/test_no_source_leak.py` → 4 collected.)

[frontend-api/tests/test_cycle_routes.py](frontend-api/tests/test_cycle_routes.py):
- **6 tests.** Route-level tests for the 5 public surfaces above. The recursive response-sanitizer assertion lives in `test_formal_routes_strip_raw_source_provider_fields`, which includes nested payload keys. (`pytest --collect-only -q tests/test_cycle_routes.py` → 6 collected.)

Combined: **10 tests** across the two frontend-api files.

## Section 4 — Tests run + results

```
$ cd data-platform && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
    -p no:cacheprovider tests/serving/test_formal_no_source_leak.py
==> 22 passed

$ cd frontend-api && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest \
    -p no:cacheprovider tests/test_cycle_routes.py tests/test_no_source_leak.py
==> 10 passed in 0.24s
```

Both suites are green by default. The runtime guard executes on every call to `get_formal_latest` / `get_formal_by_id` (data-platform) and on every public route (frontend-api).

## Section 5 — Remaining limitations (do NOT promote to "P5 complete")

1. **Live formal Iceberg table not exercised**: tests use synthesized pyarrow Tables. M2.6 production daily-cycle proof owns end-to-end exercise of the live formal table path.
2. **Drift risk between two forbidden-field sets**: the 14-entry frozenset plus pattern rule is hardcoded in two places — [formal.py:25-42](data-platform/src/data_platform/serving/formal.py:25) and [routes/cycle.py:22-39](frontend-api/src/frontend_api/routes/cycle.py:22). A future field addition must update both. Consolidation (e.g., a shared protocol package) is NOT proposed in this round.
3. **No publication-time enforcement**: the guard runs at READ time. A future formal table written with a forbidden field would NOT be caught at publish; it would only be caught when first read by a public consumer. M2.6 should consider a publish-time version of the same guard.
4. **`canonical_v2.fact_event` not live-Iceberg exercised**: the fixture proof materialises the v2/lineage marts in DuckDB, but no live Iceberg catalog write is executed in this evidence file.

## Section 6 — Status declarations

- The runtime guard is **ACTIVE** (not test-only) on both data-platform and frontend-api boundaries.
- The 14-field `FORBIDDEN_PUBLIC_FORMAL_FIELDS` exact-key set plus source/provider naming-pattern rule is enforced.
- The frontend-api `_sanitize_public_formal_payload` recursive sanitizer is **ACTIVE** as a complementary defense for JSON payloads.
- This evidence does NOT claim P5 production live proof.
- M2 / M3 / M4 not entered.
- `project_ult_v5_0_1.md` and `ult_milestone.md` UNCHANGED.
