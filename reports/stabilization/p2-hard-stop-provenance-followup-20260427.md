# P2 Hard-Stop And Provenance Follow-Up Review - 2026-04-27

## Scope

This follow-up covers the multi-agent review of the P2 prerequisite hard-stop
and recommendation provenance batch.

Reviewed baseline:

- `orchestrator` `caf6340f7eb3cb9042bac9de5bd70feef76dd152`
- `data-platform` `b61020a7eca0c0faba90396699c50c8135043e58`
- `assembly` `9ffb7d9eee9931f48da21b8c62c8b5ca98028f72`

Follow-up correction commits:

- `orchestrator` `139b997bfc62a20cd5e325f2e3f9b78c2b3d1bee`
  (`Enforce phase2 l8 boundary gate`)
- `data-platform` `8b617bd2fe1eb53457dc66ca3b53d706033f683b`
  (`Cover recommendation provenance cycle mismatch`)

This is prerequisite evidence only. It does not claim P2 real L1-L8 dry-run
completion, P5 readiness, or v5.0.1 completion.

## Multi-Agent Review Findings

Initial independent reviews found:

- P0: none
- P1: none
- P2: one orchestrator runtime contract finding
- P3: one data-platform test coverage gap
- P3: local dirty/untracked worktrees remain a readiness risk before actual
  dry-run evidence collection

The assembly evidence review found no overclaiming and no active secret exact
matches in committed evidence or changed files.

## P2 Finding: Phase 2 Boundary Was Still Optional

Finding:

- `_phase2_pool_gate_asset_key()` accepted any single `group_name='phase2'`
  asset when the final `l8` asset was absent.
- That fallback allowed a stale singleton `l7` provider to be treated as the
  Phase 2 boundary for the pool-failure-rate gate and Phase 3 ancestry checks.

Resolution:

- `orchestrator` commit `139b997bfc62a20cd5e325f2e3f9b78c2b3d1bee` removed the
  singleton fallback.
- Phase 2 provider assets now require the final contract asset `l8` before the
  production `phase2_pool_failure_rate_gate` can be built.
- `tests/integration/test_phase2_main_core_wiring.py` now includes a stale
  singleton `l7` provider regression test that must raise before Definitions
  assembly succeeds.

Supervisor validation:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/orchestrator
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
  /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python \
  -m pytest \
  tests/integration/test_phase2_main_core_wiring.py \
  tests/integration/test_phase2_pool_failure_gate.py \
  tests/integration/test_phase3_publish_wiring.py \
  tests/integration/test_daily_cycle_four_phase.py \
  -q -rs
```

Result: `15 passed`.

## P3 Gap: Direct Published-Cycle Mismatch Coverage

Finding:

- The invalid recommendation provenance tests covered current-cycle drift,
  wrong source layer, forbidden source kinds, snapshot mismatch, and empty
  audit/replay IDs.
- They did not directly exercise the separate
  `proof.cycle_id != published cycle_id` branch.

Resolution:

- `data-platform` commit `8b617bd2fe1eb53457dc66ca3b53d706033f683b` adds a
  `cycle_id=CYCLE_20260415` provenance case while publishing
  `CYCLE_20260416`.
- The case keeps `cycle_id == current_cycle_id` inside the proof, so it reaches
  the published-cycle mismatch branch instead of the current-cycle binding
  branch.

Supervisor validation:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
  /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python \
  -m pytest tests/cycle/test_publish_manifest.py -q -rs
```

Result: `27 passed, 15 skipped`.

PG-backed validation:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
# DP_PG_DSN was constructed in-process from local compose-postgres-1 and was not printed.
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
  /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest \
  tests/cycle/test_publish_manifest.py \
  tests/serving/test_formal.py \
  tests/serving/test_formal_manifest_consistency.py \
  tests/spike/test_iceberg_publish_manifest_chain.py \
  -q -rs
```

Result: `55 passed`.

Warnings:

- Five PyIceberg warnings: `Delete operation did not match any records`.

## Gate Decision

Secondary independent re-review after the correction commits:

- `orchestrator` `139b997bfc62a20cd5e325f2e3f9b78c2b3d1bee`:
  - P0/P1/P2/P3: none
  - Re-review result: accepted as P2 prerequisite follow-up
  - Re-run result: `15 passed`
- `data-platform` `8b617bd2fe1eb53457dc66ca3b53d706033f683b`:
  - P0/P1/P2/P3: none
  - Re-review result: accepted as provenance prerequisite follow-up
  - Re-run result: `27 passed, 15 skipped`
  - PG-backed re-run result: `55 passed`

The P2 runtime-contract finding is closed by `orchestrator` `139b997`.

The P3 provenance coverage gap is closed by `data-platform` `8b617bd`.

Accepted as P2 prerequisite follow-up evidence:

- Fake-provider no-LLM hard-stop behavior remains valid prerequisite evidence.
- Phase 2 boundary selection no longer allows stale singleton non-`l8` assets.
- Recommendation snapshot publish provenance still fails closed.
- Published-cycle mismatch is directly covered.

This is not a P2 dry-run pass.

## Hygiene

Known local files remain excluded from this gate:

- `assembly`: `.env`, `.venv-py312/`, `PROJECT_REPORT.md`, pycache, egg-info,
  temp review dirs.
- `orchestrator`: `.orchestrator/`, `dbt_stub/.user.yml`,
  `dbt_stub/dagster_home/`, `dbt_stub/logs/`, `dbt_stub/target/`.
- `data-platform`: existing modified `docs/spike/iceberg-write-chain.md`,
  `.orchestrator/`, `tmp/`.
- `audit-eval`: existing local build/report artifacts.

These files must be cleaned or explicitly waived before actual P2 dry-run
evidence collection.

## Remaining Blockers For Actual P2 Dry Run

P1 blockers:

- Real current-cycle L8 recommendation generation is not implemented or proven.
- Real L4/L6/L7 LLM audit/replay rows are not produced from the dry-run path.
- Phase 3 production handoff must pass non-smoke current-cycle provenance from
  L8 into `publish_manifest()`.
- Target-runtime LLM provider credentials/config must pass real health checks.

P2 blockers:

- Prove a real dry-run recommendation snapshot cannot be published without
  corresponding audit/replay rows.
- Prove historical, fixture, or smoke provenance cannot satisfy the production
  dry-run provenance handoff.
- Clean or explicitly waive local dirty worktrees before actual P2 dry-run
  evidence collection.

Frontend remains out of scope except read-only evidence display after backend
P2 evidence exists.
