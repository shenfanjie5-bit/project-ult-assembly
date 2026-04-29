# M2.5 — audit-eval ↔ data-platform Round-Trip Smoke (Live PG)

## Status

**M2.5 status: COMPLETE (review-folded).** Live PostgreSQL round-trip tests
for `DataPlatformManifestGateway` land on `m2-5-live-pg-roundtrip` branch
in audit-eval. The first pass added 4 tests; a review-pass fold-in added 2
more hardening tests + 1 maintenance fix. Six tests in total prove the
audit-eval-internal chain `audit_eval.audit.real_cycle.DataPlatformManifestGateway`
→ live PG `cycle_publish_manifest` works end-to-end against compose PG, with
a real DuckDB durability path on the audit-eval side.

**Blocker #5 (`configured_audit_eval_retrospective_hook_runtime`) status
update: PARTIAL → READY.** The transitive dependency on blocker #1 (closed
to READY in M2.2) is now demonstrated end-to-end against live PG. The
audit-eval gateway no longer has any unverified production code path.

> **Scope clarification (review pass):** The 4th test
> (`test_real_retrospective_hook_with_live_pg_manifest_gateway`) exercises
> the **audit-eval-internal** chain (`run_real_retrospective_hook` +
> `DataPlatformManifestGateway` + `DuckDBReplayRepository` + live PG +
> tmp DuckDB). It does NOT exercise the orchestrator-side wrapper
> `_EnvBackedRetrospectiveHookRuntime.run()` at
> `production_daily_cycle.py:298-343` — that wrapper additionally reads
> `AUDIT_EVAL_DUCKDB_PATH_ENV`, validates the input as
> `P2PublishedManifest`, and constructs `RetrospectiveHookRequest` from
> the validated manifest. End-to-end orchestrator-wrapped smoke is a
> separate concern (M2.6 scope: real Dagster-job execution).
>
> **Review pass folded in:** Three independent reviewer agents
> (code-reviewer + architectural verification + test adequacy) cross-checked
> this round. Code reviewer verdict: APPROVED-WITH-COMMENTS (2 P1, 3 P2,
> 2 P3). Architectural verifier verdict: NEEDS-PATCH (1 misleading
> evidence claim about orchestrator wrapping). Test adequacy verdict:
> GAPS-EXIST (4 HIGH coverage gaps). After deep-verification, 1 of the P1
> findings was REFUTED (the "exact-equality" theory on
> `formal_snapshot_refs` — hook does subset match per
> `audit-eval/src/audit_eval/retro/hook.py:487-498`); other findings
> classified per the decision matrix in this evidence. Net delta: +2
> hardening tests + 1 maintenance fix (decouple from local copy of
> data-platform's REQUIRED_FORMAL_OBJECT_NAMES) + this evidence
> clarification.

---

## Prerequisites

- M2.2 closed blocker #1 → READY (live PG cycle freeze proven, commit
  `a18da75` on data-platform `m2-2-live-pg-integ-test`).
- Compose PG healthy at `postgresql://postgres:changeme@localhost:5432/proj`.

---

## Files changed

### audit-eval (branch `m2-5-live-pg-roundtrip` off main)

**New file:** `tests/integration/test_data_platform_manifest_gateway_live_pg.py`

Six live PG tests (4 first-pass + 2 review-fold hardening), all skipping
cleanly when `DATABASE_URL` / `DP_PG_DSN` is unset OR data-platform is
not on `PYTHONPATH`:

| Test | What it pins | Round |
|---|---|---|
| `test_gateway_loads_manifest_with_required_formal_table_snapshots` | End-to-end: a published manifest with all 4 required formal tables (`world_state_snapshot`, `official_alpha_pool`, `alpha_result_snapshot`, `recommendation_snapshot`) round-trips through the lazy `data_platform.cycle.get_publish_manifest` import path; `DataPlatformManifestGateway()` (no override) returns a `CyclePublishManifestDraft` with the correct `formal_object_ref → data_platform_snapshot_ref` mapping. | first |
| `test_gateway_load_for_two_distinct_cycles_returns_distinct_drafts` | Per-cycle isolation — two manifests in the same database with different snapshot_id values produce drafts whose snapshot_refs reflect each cycle's own values (no caching / cross-talk). | first |
| `test_gateway_propagates_invalid_manifest_for_missing_required_key` | If the manifest row's JSONB is missing a `REQUIRED_FORMAL_OBJECT_NAMES` key, `_normalize_snapshot_manifest` raises `InvalidFormalSnapshotManifest`; the gateway surfaces it cleanly rather than returning a partial draft. | review |
| `test_gateway_propagates_invalid_manifest_for_malformed_table_identifier` | If the manifest row's JSONB carries a key not starting with `"formal."` (e.g. `"analytical.bogus_table"`), `_normalize_snapshot_manifest` or `formal_object_ref` raises a typed exception; the gateway propagates it cleanly. | review |
| `test_gateway_propagates_publish_manifest_not_found_for_unknown_cycle` | A cycle without a manifest row surfaces `data_platform.cycle.PublishManifestNotFound` upward — audit-eval's gateway does not swallow it; orchestrator can rely on the typed exception to detect the missing-publish case. | first |
| `test_real_retrospective_hook_with_live_pg_manifest_gateway` | Full audit-eval-internal chain: write audit/replay rows to a real DuckDB tmp file + insert manifest in live PG + call `run_real_retrospective_hook(repository=DuckDBReplayRepository(tmp_db), manifest_gateway=DataPlatformManifestGateway())` (no override). Asserts 3 pending statuses (T+1, T+5, T+20 horizons) all bound to the right cycle_id, with replay/audit lineage preserved through the live PG manifest gateway. **Does NOT exercise orchestrator's `_EnvBackedRetrospectiveHookRuntime.run()` wrapping (separate M2.6 concern).** | first |

**New file:** `tests/integration/__init__.py` (empty package marker;
audit-eval previously had no `tests/integration/` package).

The fixture `manifest_test_env` provisions a fresh PostgreSQL database
per test (using the admin DSN's `CREATE DATABASE`), applies the
data-platform migrations via `MigrationRunner().apply_pending(test_dsn)`,
seeds rows directly via SQL (bypassing
`data_platform.cycle.publish_manifest`'s phase3 +
`recommendation_provenance` preconditions which are tested in
data-platform's own suite), and tears down with `DROP DATABASE`. Mirrors
the M2.2 `freeze_test_env` pattern verbatim.

### audit-eval venv changes (test-runtime only)

The audit-eval venv was missing two transitively-needed packages:
`psycopg[binary]` and `pydantic-settings`. Both installed via:

```sh
.venv/bin/python -m pip install 'psycopg[binary]>=3.0' 'sqlalchemy>=2.0' \
                                'pydantic-settings>=2.0'
```

These are not added to audit-eval's `pyproject.toml` because they're not
runtime deps of audit-eval itself — they're transitive deps of the
data-platform package this test cross-imports under
`PYTHONPATH=…/data-platform/src`. M2.6 deployment env will install
data-platform's full dependency tree, so this is a developer-environment
hygiene step rather than a packaging change.

### assembly (`m2-baseline-2026-04-29`)

**New file:** `reports/stabilization/m2-5-audit-eval-roundtrip-20260429.md`
(this file)

---

## Test results (post review fold)

```
$ DATABASE_URL=postgresql://postgres:changeme@localhost:5432/proj \
   PYTHONPATH=src:…/data-platform/src:…/contracts/src \
   PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest \
   tests/integration/test_data_platform_manifest_gateway_live_pg.py -v
6 passed in 1.22s

$ PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
   -p no:cacheprovider
423 passed, 7 skipped, 2 warnings in 1.97s
```

- New live PG tests: **6 passed** (against compose-postgres-1; 4
  first-pass + 2 review-fold hardening).
- Full audit-eval sweep without `DATABASE_URL`: **423 passed / 7 skipped
  / 0 failed**. The 7 skips include the 6 new tests skipping cleanly when
  env is absent + 1 pre-existing alphalens skip; no regressions.

---

## What this proves about blocker #5

The M2.0 audit (`m2-0-runtime-readiness-audit-20260429.md` §5) flagged
blocker #5 as PARTIAL with this gap:

> Audit-eval side structurally complete, but it operationally inherits
> blocker #1's PARTIAL status: the manifest gateway delegates to
> `data_platform.cycle.get_publish_manifest`, which only returns real
> PG data when blocker #1 is itself live.

M2.2 closed blocker #1 → READY. **M2.5 closes the M2.0 gap statement** by
proving:

1. `DataPlatformManifestGateway()` (no override) lazy-imports
   `data_platform.cycle.get_publish_manifest` and reads from live PG.
2. The manifest's JSONB `formal_table_snapshots` deserialises back into
   `CyclePublishManifestDraft.snapshot_refs` with the correct
   `formal_object_ref → data_platform_snapshot_ref` shape.
3. The `PublishManifestNotFound` exception path propagates correctly
   from data-platform up through audit-eval (typed, not swallowed).
4. End-to-end the full retrospective-hook chain runs against live PG +
   real DuckDB without any silent fallback to fixtures.

---

## Updated M2 blocker status

| # | Blocker | Pre-M2.5 | Post-M2.5 |
|---|---|---|---|
| 1 | `configured_data_platform_current_cycle_runtime` | READY | READY (unchanged) |
| 2 | `configured_graph_phase0_status_runtime` | READY-IN-CODE | READY-IN-CODE (unchanged) |
| 3 | `configured_graph_phase1_runtime` | READY-IN-CODE-WITH-STUBS | READY-IN-CODE-WITH-STUBS (unchanged) |
| 4 | `configured_reasoner_runtime` | PARTIAL (Codex 429 quota; resets ~5.6d) | PARTIAL (unchanged) |
| 5 | `configured_audit_eval_retrospective_hook_runtime` | PARTIAL | **READY** |
| 6 | `production_current_cycle_dagster_run_evidence` | DEFERRED-TO-M2.6 | DEFERRED-TO-M2.6 |

**Aggregate:** 2 READY + 1 PARTIAL + 0 STUBBED + 1 DEFERRED + 2
READY-IN-CODE.

The remaining PARTIAL is blocker #4 (reasoner-runtime, Codex quota
limited; resets ~5.6 days from 2026-04-29). All other M2.6 prerequisites
that can be code-proven are now READY-or-better.

---

## Hard-rule declarations

- `project_ult_v5_0_1.md` and `ult_milestone.md` UNCHANGED.
- No production fetch (live PG access uses the fixture-provisioned
  database, not any production data store).
- No P5 / M3 / M4 work.
- No source code modified in audit-eval, data-platform, or any other
  module repo — pure new integration test + evidence.
- canonical_v2 + canonical_lineage spec sets unchanged.
- Tushare remains source adapter only.
- `frontend-api` NOT touched.
- `/Users/fanjie/Desktop/BIG/FrontEnd/**` NOT modified.
- compose stack inherited from previous session (not started or modified).

---

## Review fold-in (4 HIGH gaps + 1 maintenance fix closed; 1 misleading claim corrected)

The post-implementation review pass landed the following changes in the
same audit-eval commit:

**Code (audit-eval `tests/integration/test_data_platform_manifest_gateway_live_pg.py`):**
- Replaced local `_REQUIRED_FORMAL_TABLES` constant with a runtime-imported
  helper that calls `data_platform.formal_registry.REQUIRED_FORMAL_OBJECT_NAMES`,
  so this test stays in sync if data-platform extends the required-set in
  a future migration (P3, code reviewer). The local copy was a stale-
  shadow risk.

**Tests (2 new live PG, hardening review-fold):**
- `test_gateway_propagates_invalid_manifest_for_missing_required_key` —
  seeds JSONB missing one of the 4 `REQUIRED_FORMAL_OBJECT_NAMES` keys;
  asserts the gateway propagates `InvalidFormalSnapshotManifest` from
  `_normalize_snapshot_manifest` (HIGH gap, test reviewer).
- `test_gateway_propagates_invalid_manifest_for_malformed_table_identifier` —
  seeds JSONB with a non-`formal.` table identifier (`analytical.bogus_table`);
  asserts the gateway propagates either `InvalidFormalSnapshotManifest` or
  `DataPlatformBindingError` (whichever fires first in the validation
  chain — both are valid fail-closed surfaces) (HIGH gap, test reviewer).

**Evidence (this file):**
- Clarified the 4th test's scope: it exercises the **audit-eval-internal**
  chain, NOT the orchestrator's `_EnvBackedRetrospectiveHookRuntime.run()`
  wrapping. The original wording "full chain orchestrator → audit-eval →
  data-platform" overstated; orchestrator-wrapped end-to-end smoke is a
  separate M2.6 concern.

**Findings explicitly NOT addressed in this round:**

- **Reviewer 1 P1 #1 (formal_snapshot_refs "exact equality" theory):**
  REFUTED on deep verification. The hook's comparison logic at
  `audit-eval/src/audit_eval/retro/hook.py:487-498` is **subset match**
  — it iterates `replay.formal_snapshot_refs.items()` and verifies each
  key is present in `manifest.snapshot_refs` with equal value. The
  4-key-vs-1-key concern was a false alarm. Test 4 passes correctly.
- **P1 #2 (UUID f-string DROP DATABASE pattern):** Inherited from M2.2
  `freeze_test_env`. UUID-only invariant is implicit but consistent
  across both fixtures. No fix needed.
- **P2/P3 cosmetic items (one-liner vs two-liner pattern divergence,
  combined skip mechanism, date_ref comment):** Out of scope for
  hardening round.
- **Test reviewer LOW (concurrent calls, FK constraint enforcement):**
  Out of audit-eval scope (data-platform's own suite covers FK; Dagster
  asset model is single-threaded today).
- **Test reviewer MEDIUM (orchestrator wrapping):** Documented as M2.6
  scope. Test 4's evidence wording corrected to reflect this.

## Cross-references

- M2 roadmap: [`m2-roadmap-20260429.md`](m2-roadmap-20260429.md)
- M2.0 audit (blocker #5 PARTIAL classification): [`m2-0-runtime-readiness-audit-20260429.md`](m2-0-runtime-readiness-audit-20260429.md)
- M2.1 preflight (env vars): [`m2-1-runtime-preflight-20260429.md`](m2-1-runtime-preflight-20260429.md)
- M2.2 live PG cycle freeze (closes blocker #1): [`m2-2-live-pg-test-20260429.md`](m2-2-live-pg-test-20260429.md)
- M2.4 LLM credentials probe: [`m2-4-llm-creds-20260429.md`](m2-4-llm-creds-20260429.md)
- audit-eval CLAUDE.md (module ownership constraints): `audit-eval/CLAUDE.md`

## Recommended next round

With 5 of 6 blockers in READY-or-equivalent state and only blocker #4
operationally limited by Codex quota (resets ~5.6 days), the remaining
M2.6 unblock options are:

1. **M2.6 followup #1** — real `IcebergCanonicalGraphWriter` in
   data-platform (replaces `StubCanonicalGraphWriter`; ~1 round). This
   is required for M2.6's Phase 1 graph_promotion asset to actually
   write canonical records vs. raise `NotImplementedError`.
2. **M2.6 followup #2** — real `WorldStateRegimeContextReader` in
   main-core (replaces `PlaceholderRegimeContextReader`; needs PM
   regime-mapping decision). Not blocking M2.6 functionally — neutral
   1.0 multipliers preserve graph-engine's test contract — but
   recommended before claiming production-grade Phase 1 propagation.
3. **Wait for Codex quota reset** (~5.6d) OR provision MiniMax key
   then run **M2.6** itself: full Dagster job proof.

The cleanest M2.6-prep path is **followup #1 first** (data-platform
canonical write-back), since Phase 1 will halt at
`StubCanonicalGraphWriter.write_canonical_records()` without it.
