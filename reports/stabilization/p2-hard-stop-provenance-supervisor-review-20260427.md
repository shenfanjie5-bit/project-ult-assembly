# P2 Hard-Stop And Provenance Supervisor Review - 2026-04-27

## Scope

This supervisor review covers the second P2 prerequisite batch after P2 planning evidence was accepted.

Reviewed commits:

- `orchestrator` `caf6340f7eb3cb9042bac9de5bd70feef76dd152` (`test no-LLM daily cycle hard stop`)
- `assembly` `a354837` (`add no-LLM hard-stop evidence`)
- `data-platform` `65a79cf7ec7c31298069563b7920451a598b59e4` (`Guard recommendation snapshot provenance`)
- `data-platform` `b61020a7eca0c0faba90396699c50c8135043e58` (`Add explicit provenance to formal publish callers`)
- `assembly` `c3bde2a` (`Add P2 recommendation provenance guardrail evidence`)
- `assembly` `2d2692801ebd216b1f29f4b6875f9e0a85294062` (`Document PG-backed provenance guardrail validation`)

Primary evidence:

- `reports/stabilization/p2-no-llm-hard-stop-20260427.md`
- `reports/stabilization/p2-no-llm-hard-stop-20260427-artifacts/`
- `reports/stabilization/p2-recommendation-provenance-guardrails-20260427.md`
- `reports/stabilization/p2-recommendation-provenance-guardrails-20260427-artifacts/`

This review accepts prerequisite evidence only. It does not claim P2 dry-run completion.

## No-LLM Hard-Stop

Accepted for prerequisite evidence.

Verified behavior:

- Daily cycle happy path still passes.
- When all fake LLM provider/model health targets are unavailable, `llm_health_check` evaluates `passed=False`.
- The hard-stop metadata includes:
  - `scenario_id=phase0_llm_health_check_failed`
  - `action=fail_run`
  - `all_critical_targets_available=false`
  - `unavailable_target_count=3`
- Phase 2 LLM-dependent assets `l4`, `l6`, `l7`, and `l8` do not materialize.
- Phase 3 `formal_objects_commit` does not materialize.
- Phase 3 `cycle_publish_manifest` does not materialize.

Supervisor validation:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/orchestrator
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
  /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python \
  -m pytest tests/integration/test_daily_cycle_four_phase.py -q --tb=short
```

Result: `2 passed`.

Caveat:

- This is an orchestrator integration test with fake provider health statuses. It proves dependency and publish blocking behavior, not a production reasoner-runtime provider outage.

## Recommendation Provenance Guardrail

Accepted for prerequisite evidence after follow-up correction.

Verified behavior:

- `data-platform` now enforces a fail-closed provenance preflight at `publish_manifest()`.
- A manifest containing `formal.recommendation_snapshot` must include explicit `recommendation_provenance`.
- The proof must include:
  - current cycle binding
  - `source_layer=L8`
  - `source_kind=current-cycle`
  - matching recommendation snapshot id
  - non-empty `audit_record_ids`
  - non-empty `replay_record_ids`
- The guardrail rejects fixture, historical, and synthetic source kinds.
- Missing provenance fails before the database write path opens.

Initial review finding:

- The first guardrail patch passed only `tests/cycle/test_publish_manifest.py`.
- PG-backed broader tests then showed legitimate old `publish_manifest()` callers failing because they had no explicit provenance.

Correction:

- `data-platform` commit `b61020a7eca0c0faba90396699c50c8135043e58` updated legitimate manifest-chain, formal-serving, cycle metadata, and P1c smoke callers to provide explicit provenance.
- The production guardrail was not weakened.
- P1c smoke remains a technical chain smoke only. Its provenance must not be treated as meaningful P2 recommendation provenance.

Supervisor validation:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
  /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python \
  -m pytest tests/cycle/test_publish_manifest.py -q
```

Result: `26 passed, 15 skipped`.

PG-backed broader validation:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
# DP_PG_DSN was constructed in-process from local compose-postgres-1 and was not printed.
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
  /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest \
  tests/spike/test_iceberg_publish_manifest_chain.py \
  tests/serving/test_formal.py \
  tests/serving/test_formal_manifest_consistency.py \
  tests/cycle/test_cycle_metadata.py \
  tests/integration/test_p1c_smoke.py \
  -q -rs
```

Result: `43 passed`.

Warnings:

- Six PyIceberg warnings: `Delete operation did not match any records`. These warnings were also recorded in worker evidence and did not fail the tests.

## Independent Review

Independent test review result:

- P0: none
- P1: none
- P2: none
- P3: local dirty/untracked worktrees remain and must be cleaned or explicitly waived before actual P2 dry-run execution

Independent review also reran:

- C hard-stop command: `2 passed`
- D publish manifest command: `26 passed, 15 skipped`
- D PG-backed broader command: `43 passed`

## Secret And File Hygiene

Secret scanning was performed against committed evidence and changed files using active local environment and Docker-derived values without printing those values.

Result:

- Exact active secret hits: `0`.
- Heuristic hits were variable names or URI-conversion code, not active secret values.

Known uncommitted local files remain:

- `assembly`: `.env`, `.venv-py312/`, `PROJECT_REPORT.md`, pycache, egg-info, temp review dirs.
- `orchestrator`: `.orchestrator/`, `dbt_stub/.user.yml`, `dbt_stub/dagster_home/`, `dbt_stub/logs/`, `dbt_stub/target/`.
- `data-platform`: existing modified `docs/spike/iceberg-write-chain.md`, `.orchestrator/`, `tmp/`.
- `audit-eval`: existing local build/report artifacts from earlier reviews.

These files are excluded from this gate and must not be committed accidentally.

## Gate Decision

C/D are accepted as P2 prerequisite evidence.

Accepted capabilities:

- LLM infrastructure health failure blocks Phase 2 LLM-dependent assets and prevents formal publish.
- `publish_manifest()` now fails closed unless a recommendation snapshot carries current-cycle L8 provenance with audit/replay bindable IDs.
- PG-backed manifest, formal serving, cycle metadata, and P1c smoke tests pass with the new guardrail.

This is not a P2 dry-run pass.

## Remaining Blockers For Actual P2 Dry Run

P1 blockers:

- Real current-cycle L8 recommendation generation is not implemented or proven.
- Real L4/L6/L7 LLM audit/replay rows are not produced from the dry-run path.
- Phase 3 production handoff must pass non-smoke current-cycle provenance from L8 into `publish_manifest()`.
- Target-runtime LLM provider credentials/config must pass real health checks before dry-run execution.

P2 blockers:

- Add proof that a real dry-run recommendation snapshot cannot be published without corresponding audit/replay rows.
- Add proof that historical, fixture, or smoke provenance cannot satisfy the production dry-run provenance handoff.
- Clean or explicitly waive local dirty worktrees before actual P2 dry-run evidence collection.

Frontend remains out of scope except read-only evidence display after backend P2 evidence exists.
