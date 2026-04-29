# M1.5 Reader Cutover Audit

**Round:** M1.5-1
**Date:** 2026-04-28
**Status:** Audit-only. NO production code changed. Cross-repo audit covers data-platform, orchestrator, main-core, graph-engine, frontend-api, subsystem-sdk, entity-registry, subsystem-news, subsystem-announcement, reasoner-runtime, audit-eval, assembly, contracts, feature-store, stream-layer; plus read-only audit of `/Users/fanjie/Desktop/BIG/FrontEnd`.

## Purpose

After M1-G2, every legacy `canonical.<mart>` mapping has a `canonical_v2.<mart>` sibling that resolves under `DP_CANONICAL_USE_V2=1` via [canonical_datasets.py](data-platform/src/data_platform/serving/canonical_datasets.py)'s `_selected_dataset_to_table()`. This audit verifies that **no production reader bypasses the v2 cutover** by:
- calling `read_canonical("<bare>")` directly with a hardcoded canonical mart table name, OR
- hardcoding `ts_code` / `index_code` in a place where `canonical_alias_column_for_dataset()` should be used.

## Classifications

- **OK_SELECTED_MAPPING** — resolves through `canonical_datasets.py` helpers (`canonical_table_for_dataset`, `canonical_table_identifier_for_dataset`, `canonical_alias_column_for_dataset`, `read_canonical_dataset`, `read_canonical_dataset_snapshot`).
- **OK_TEST_FIXTURE** — test code, fixture, or scoreboard test (including `_M1D_LEGACY_RETIREMENT_XFAIL`-decorated tests).
- **OK_RESPONSE_SHAPE** — frontend formal-route forbidden-keys list; the recursive sanitizer strips these before responding.
- **INTENTIONAL_LEGACY_WRITE** — legacy writer/load spec/dbt mart explicitly retained until [m1-legacy-canonical-retirement-readiness-20260428.md](assembly/reports/stabilization/m1-legacy-canonical-retirement-readiness-20260428.md) Phase B retirement runs.
- **INTENTIONAL_ENTITY_STORE_READ** — direct read of `canonical.canonical_entity` / `canonical.entity_alias` entity-store tables. Entity stores are NOT in M1-G2 scope (which migrated only the 9 mart pairs). Entity-registry owns these tables; they have no `canonical_v2` equivalent in this round. Decision deferred to a separate entity-store migration (out of M1.5).
- **BLOCKED_DIRECT_LEGACY_READ** — production code calling `read_canonical("<bare_mart>")` or hardcoding `canonical.<mart>` table identifier.
- **BLOCKED_HARDCODED_ALIAS** — production code hardcoding `ts_code` / `index_code` where `canonical_alias_column_for_dataset` should be used.
- **DOC_ONLY** — docstrings, comments, evidence reports, schema-name string literals not used as table identifiers.
- **EXTERNAL** — `/Users/fanjie/Desktop/BIG/FrontEnd` hits — read-only by hard rule; reported for downstream owner awareness.

## Per-repo summary

| repo | total hits | OK_SELECTED_MAPPING | OK_TEST_FIXTURE | OK_RESPONSE_SHAPE | INTENTIONAL_LEGACY_WRITE | INTENTIONAL_ENTITY_STORE_READ | BLOCKED_* | DOC_ONLY | EXTERNAL |
|---|---|---|---|---|---|---|---|---|---|
| data-platform | 209 | 25 | 35+ | 0 | 41 | 1 (group of 2 calls in cycle) | **0** | ~107 | 0 |
| orchestrator | 7 | 7 | 0 | 0 | 0 | 0 | **0** | 0 | 0 |
| main-core | 6 | 6 | 0 | 0 | 0 | 0 | **0** | 0 | 0 |
| graph-engine | 175 | 0 | 0 | 0 | 0 | 0 | **0** | 175 (canonical_entity_id node property) | 0 |
| frontend-api | 1 | 0 | 0 | 1 | 0 | 0 | **0** | 0 | 0 |
| subsystem-sdk | 16 | 0 | 0 | 0 | 0 | 0 | **0** | 16 | 0 |
| subsystem-news | 1 | 0 | 0 | 0 | 0 | 0 | **0** | 1 | 0 |
| subsystem-announcement | 0 | 0 | 0 | 0 | 0 | 0 | **0** | 0 | 0 |
| entity-registry | 5 | 1 | 4 | 0 | 0 | 0 | **0** | 0 | 0 |
| reasoner-runtime | 0 | 0 | 0 | 0 | 0 | 0 | **0** | 0 | 0 |
| audit-eval | 2 | 0 | 1 | 0 | 0 | 0 | **0** | 1 | 0 |
| assembly | 0 (in code) | 0 | 0 | 0 | 0 | 0 | **0** | 30+ (evidence reports) | 0 |
| contracts | 0 | 0 | 0 | 0 | 0 | 0 | **0** | 0 | 0 |
| feature-store | 0 | 0 | 0 | 0 | 0 | 0 | **0** | 0 | 0 (empty placeholder, NOT a git repo) |
| stream-layer | 0 | 0 | 0 | 0 | 0 | 0 | **0** | 0 | 0 (empty placeholder, NOT a git repo) |
| BIG/FrontEnd | 44 | 0 | 0 | 0 | 0 | 0 | **0** | 0 | 44 (read-only TypeScript names) |

**Total BLOCKED hits: 0.**

## BLOCKED hits (none)

There are zero `BLOCKED_DIRECT_LEGACY_READ` or `BLOCKED_HARDCODED_ALIAS` hits anywhere in the audited tree.

## Notable findings

### data-platform

- [serving/reader.py:63, 118, 136, 173](data-platform/src/data_platform/serving/reader.py:63) — public reader API (`read_canonical`, `read_canonical_dataset`, `read_canonical_dataset_snapshot`, `get_canonical_stock_basic`). `read_canonical("<bare>")` remains the legacy-namespace compatibility reader; `get_canonical_stock_basic` is now v2-aware under `DP_CANONICAL_USE_V2=1` and returns the legacy helper shape for entity-registry compatibility. **No BLOCKED direct mart reader remains in data-platform production code.**
- [cycle/current_cycle_inputs.py:74-82, 291-308](data-platform/src/data_platform/cycle/current_cycle_inputs.py:74) — `_read_canonical_table` is called twice with `CANONICAL_ENTITY_TABLE = "canonical_entity"` (line 75) and `ENTITY_ALIAS_TABLE = "entity_alias"` (line 82). These are **entity-store tables, not marts** (see registry distinction at [iceberg_tables.py:24, CANONICAL_ENTITY_SPEC, ENTITY_ALIAS_SPEC](data-platform/src/data_platform/ddl/iceberg_tables.py:24)). M1-G2 scope migrated only the 9 mart pairs — entity stores are owned by entity-registry per data-platform CLAUDE.md ("BAN: 定义 canonical_entity_id 生成规则或别名消歧规则（归 entity-registry）"). Classified as `INTENTIONAL_ENTITY_STORE_READ`. Decision to migrate entity stores to a `canonical_v2.canonical_entity` / `canonical_v2.entity_alias` is **deferred** to a separate round (out of M1.5 / M1-G3 scope).
- [daily_refresh.py:36-37, 522, 532](data-platform/src/data_platform/daily_refresh.py:36) — calls legacy `load_canonical_marts` and `load_canonical_stock_basic`. These are `INTENTIONAL_LEGACY_WRITE` — see M1-G3 retirement plan §7 for sequencing.
- [assets.py:35, 37](data-platform/src/data_platform/assets.py:35) — registers legacy callables. `INTENTIONAL_LEGACY_WRITE`.
- [serving/canonical_writer.py:32, 141-363](data-platform/src/data_platform/serving/canonical_writer.py:32) — 8 legacy `CanonicalLoadSpec` entries + dim_security spec. `INTENTIONAL_LEGACY_WRITE`.
- [serving/schema_evolution.py:228](data-platform/src/data_platform/serving/schema_evolution.py:228) — calls `load_canonical_table(catalog, duckdb_path, spec)` with whatever spec is passed in by the caller. `OK_SELECTED_MAPPING` (the spec selection happens at the call site, which goes through writer entry points).

### orchestrator

7 hits, all **`OK_SELECTED_MAPPING`** via `data_platform.cycle` / `data_platform.config` / `data_platform.serving.catalog` imports. Hardcoded `ts_code` references in `production_daily_cycle.py:392-397, 1263-1315` come from staging tables (`stg_daily`, `stg_stock_basic`), NOT canonical reads — staging is provider-shaped by design and is upstream of canonical. **No canonical mart reader integration in orchestrator.**

### main-core

All 6 hits go through the `DataPlatformPort` protocol abstraction at [l1_l2_basis/ports.py:16, 22](main-core/src/main_core/l1_l2_basis/ports.py:16). Implementation wrappers at [readers.py:16, 32](main-core/src/main_core/l1_l2_basis/readers.py:16) call into data-platform; the call chain resolves through `read_canonical_dataset` (which respects v2 flag). Graph adapters at `l3_features/graph_adapter.py` and `l4_world_state/graph_adapter.py` consume snapshot artifacts (provider-neutral by design — `entity_id` already), NOT canonical marts. **All `OK_SELECTED_MAPPING`.**

### graph-engine

175 hits all reference `canonical_entity_id` as a Neo4j node property name OR as a column in graph-engine's own SQL queries. **None are canonical mart reads.** Graph-engine produces graph snapshot artifacts with `entity_id` already canonicalised; it does not consume `canonical.<mart>` or `canonical_v2.<mart>` tables.

### frontend-api

The single hit is `_FORMAL_PAYLOAD_FORBIDDEN_KEYS` at [routes/cycle.py:36-37](frontend-api/src/frontend_api/routes/cycle.py:36) — `ts_code` and `index_code` are listed as forbidden keys for the runtime sanitizer to STRIP. This is `OK_RESPONSE_SHAPE`: defensive, not a leak. The recursive sanitizer at lines 123-132 strips these before any response goes out. M1-G4 evidence covers this.

[entity_data.py:39-50](frontend-api/src/frontend_api/routes/entity_data.py:39) — debug `read_canonical_table` route reads from filesystem artifact JSON (entity-data-adapter), NOT from the canonical Iceberg namespace. `OK_SELECTED_MAPPING` (or `OK_DEBUG_ROUTE`; not in production-canonical path).

### subsystem-sdk / subsystem-news / subsystem-announcement

These are submission subsystems — they push events INTO data-platform via the Layer-B ingest queue. They **do not read canonical data**. The 17 hits across the three repos are all DOC_ONLY (variable names like `canonical_class_name`, fixture path normalisation, comment references).

### entity-registry

[src/entity_registry/init.py](entity-registry/src/entity_registry/init.py) — `from data_platform.serving.reader import get_canonical_stock_basic`. This is the bootstrap path for entity-registry to read its source data; it is **`OK_SELECTED_MAPPING`** because `get_canonical_stock_basic` is now a v2-aware compatibility helper: with `DP_CANONICAL_USE_V2=1` it reads `canonical_v2.stock_basic` and returns the legacy helper columns expected by entity-registry (`security_id -> ts_code`, `display_name -> name`), while the default path still reads legacy `canonical.stock_basic`. Evidence: [reader.py:173-204](data-platform/src/data_platform/serving/reader.py:173), [test_reader.py:169-358](data-platform/tests/serving/test_reader.py:169). Test references at [tests/test_init.py:407, 428, 456, 461](entity-registry/tests/test_init.py:407) are `OK_TEST_FIXTURE`.

### reasoner-runtime

Zero hits. No canonical reader integration.

### audit-eval

[src/audit_eval/audit/real_cycle.py:124, 167](audit-eval/src/audit_eval/audit/real_cycle.py:124) — imports `data_platform.cycle` and `data_platform.serving.formal` for reading PUBLISHED FORMAL snapshots (NOT canonical mart reads). Formal serving is governed by the M1-G4 runtime guard. `OK_SELECTED_MAPPING`.

[tests/test_real_cycle_binding.py:181](audit-eval/tests/test_real_cycle_binding.py:181) — explicitly asserts `canonical.stock_basic` is REJECTED as an invalid binding target. `OK_TEST_FIXTURE`.

### assembly

Zero hits in non-evidence code. The 30+ markdown files under `assembly/reports/stabilization/` are DOC_ONLY by definition.

### contracts

Zero hits. Protocol package only.

### feature-store / stream-layer

Empty placeholder directories; not git repos.

### BIG/FrontEnd (read-only)

44 hits, all in TypeScript naming conventions (variable names like `canonicalTable`, `canonicalQuery`, `canonicalLimit`; query keys; UI labels). One TypeScript type definition at `src/api/projectUlt/contracts.ts:210` defines `canonical_entity?: Record<string, unknown>` as a downstream consumer of the API response shape. `EXTERNAL`. **Cannot edit.** No actionable items for M1.5.

## Verdict

**M1.5 reader cutover is safe to proceed.** Zero `BLOCKED_*` hits across the entire audited tree. The only "questionable" data-platform finding (cycle/current_cycle_inputs.py reading `canonical_entity` and `entity_alias` directly) is reclassified as `INTENTIONAL_ENTITY_STORE_READ` because entity stores are out of M1-G2 scope (they belong to entity-registry's domain, not the mart migration).

This audit alone does NOT close legacy retirement; it confirms that the cutover gate (step 1 in [m1-legacy-canonical-retirement-readiness-20260428.md](assembly/reports/stabilization/m1-legacy-canonical-retirement-readiness-20260428.md) §5) is now **VERIFIED**. The remaining preconditions (steps 2-7) are tracked in M1.5-5.

## Next-owner action items

| concern | action | owner |
|---|---|---|
| Entity-store migration to `canonical_v2.canonical_entity` / `canonical_v2.entity_alias` | Decide whether entity stores migrate to v2 in a future round; out of M1.5 scope | entity-registry owner |
| `BIG/FrontEnd` TypeScript naming review | When the canonical API response shape changes (post-retirement), update TS types | frontend-api owner |
| Per [m1-legacy-canonical-retirement-readiness-20260428.md](assembly/reports/stabilization/m1-legacy-canonical-retirement-readiness-20260428.md) §7 Phase A step 4 | Run controlled Lite-compose v2 cycle (gated separately, not in M1.5) | M1.5 → M1.6 transition owner |

## Status declarations

- This is an AUDIT-ONLY round. NO production code changed.
- `project_ult_v5_0_1.md` and `ult_milestone.md` UNCHANGED.
- compose / production fetch / P5 shadow-run NOT started.
- API-6 / sidecar / frontend write API / Kafka/Flink/Temporal / news/Polymarket NOT touched.
- Legacy `canonical.*` specs/load specs/dbt marts NOT deleted.
- `_M1D_LEGACY_RETIREMENT_XFAIL` NOT removed.
- `FORBIDDEN_SCHEMA_FIELDS` / `FORBIDDEN_PAYLOAD_FIELDS` NOT extended.
- `/Users/fanjie/Desktop/BIG/FrontEnd` NOT modified (read-only audit).
- Pre-existing dirty files NOT reverted.
- No `git init`. No commits. No push.
