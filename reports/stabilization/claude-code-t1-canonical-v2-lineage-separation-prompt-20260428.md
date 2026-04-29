# Claude Code Prompt: Project ULT v5.0.1 T1 Canonical V2 Lineage Separation

You are Claude Code working in the Project ULT v5.0.1 workspace.

Workspace root:

`/Users/fanjie/Desktop/Cowork/project-ult`

Authoritative blueprint:

`/Users/fanjie/Desktop/Cowork/project-ult/project_ult_v5_0_1.md`

Current execution milestone:

`/Users/fanjie/Desktop/Cowork/project-ult/ult_milestone.md`

## Mission

Execute the next milestone work package only:

1. M0 quick baseline check.
2. T1 / M1 Provider-Neutral Data Platform Closure:
   - M1.0 Iceberg write-chain architecture spike.
   - M1.1 Canonical v2 migration design.
   - M1.2 Canonical schema parity tests.
   - M1.3 Lineage separation implementation or a clearly staged implementation if a blocking architectural issue is found.
   - M1.4 Formal serving no-source hardening where it depends on the M1.3 canonical shape.
   - M1.5 candidate derivation rules only if needed to support safe M1.6 planning.

Do not proceed to M2, M3, M4, or P5 in this run.

## Hard Rules

- Do not edit `project_ult_v5_0_1.md`.
- Do not start P5 shadow-run.
- Do not enable production fetch.
- Do not introduce API-6, sidecar, frontend write API, Kafka, Flink, Temporal, news/Polymarket production flows, or production external-source flows.
- Tushare remains only `provider=tushare` source adapter.
- Raw/staging may be source-specific.
- Curated marts, production daily-cycle, graph, reasoner, frontend-api, and formal serving must consume provider-neutral canonical datasets.
- Do not mark stabilization pass, P2 preflight, P3 live proof, P4 controlled slice, fixture proof, or this T1 work as P5 complete.
- Do not commit `.orchestrator/`, `venv/`, cache, tmp, build, dist, egg-info, `PROJECT_REPORT.md`, or local `.env`.
- Do not start compose, run production fetch, or use external secrets unless the user explicitly approves inside this Claude Code session.

## Required Reading Before Edits

Read these files first and cite the relevant lines in your implementation notes:

- `/Users/fanjie/Desktop/Cowork/project-ult/ult_milestone.md`
- `/Users/fanjie/Desktop/Cowork/project-ult/project_ult_v5_0_1.md`
- `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/canonical-physical-schema-alignment-audit-20260428.md`
- `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/formal-serving-no-source-leak-hardening-plan-20260428.md`
- `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/p1-provider-neutral-canonical-promotion-readiness-20260428.md`
- `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/p1-provider-neutral-tushare-catalog-20260428.md`
- `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/p1-provider-neutral-raw-canonical-runtime-20260428.md`
- `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/p2-canonical-current-cycle-provider-preflight-20260428.md`
- `/Users/fanjie/Desktop/Cowork/project-ult/assembly/compatibility-matrix.yaml`
- `/Users/fanjie/Desktop/Cowork/project-ult/assembly/module-registry.yaml`

Then inspect the data-platform implementation using `rg` before editing. Start with:

- `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/ddl/iceberg_tables.py`
- `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/serving/canonical_writer.py`
- `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/serving/formal.py`
- `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/serving/canonical_datasets.py`
- `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/provider_catalog/registry.py`
- `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/cycle/current_cycle_inputs.py`
- `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/cycle/manifest.py`
- `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/dbt/models/intermediate/`
- `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/dbt/models/marts/`
- `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/tests/ddl/`
- `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/tests/serving/`
- `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/tests/cycle/`
- `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/tests/provider_catalog/`
- `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/tests/dbt/`

## Baseline Commands

Before edits, capture dirty state:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult
for repo in assembly data-platform frontend-api orchestrator graph-engine main-core subsystem-sdk entity-registry subsystem-news subsystem-announcement reasoner-runtime audit-eval; do
  echo "## $repo"
  git -C "$repo" status -s
done
echo "## /Users/fanjie/Desktop/BIG/FrontEnd"
git -C /Users/fanjie/Desktop/BIG/FrontEnd status -s
```

If unrelated dirty files exist, do not revert them. Work around them and call them out in the final report.

## Implementation Scope

Primary write scope:

- `data-platform/src/data_platform/ddl/iceberg_tables.py`
- `data-platform/src/data_platform/serving/canonical_writer.py`
- `data-platform/src/data_platform/serving/canonical_datasets.py`
- `data-platform/src/data_platform/serving/formal.py`
- `data-platform/src/data_platform/cycle/current_cycle_inputs.py`
- `data-platform/src/data_platform/cycle/manifest.py`
- `data-platform/src/data_platform/provider_catalog/registry.py`
- `data-platform/src/data_platform/dbt/models/intermediate/`
- `data-platform/src/data_platform/dbt/models/marts/`
- focused tests under `data-platform/tests/ddl/`, `data-platform/tests/serving/`, `data-platform/tests/cycle/`, `data-platform/tests/provider_catalog/`, `data-platform/tests/dbt/`

Secondary evidence/doc write scope:

- `assembly/reports/stabilization/p1-iceberg-write-chain-spike-proof-20260428.md`
- `assembly/reports/stabilization/canonical-v2-lineage-separation-design-20260428.md`
- `assembly/reports/stabilization/canonical-schema-parity-test-plan-20260428.md`
- `assembly/reports/stabilization/canonical-v2-lineage-separation-proof-20260428.md`
- `assembly/reports/stabilization/formal-serving-no-source-leak-proof-20260428.md`

Only create evidence files that are true for what you actually proved. If a proof is partial, name it as partial/blocker evidence and explain the remaining blocker.

## Required Design Outcome

Canonical business rows must be provider-neutral by construction.

Remove provider/raw lineage from canonical business schemas and public formal/business surfaces, especially fields like:

- `provider`
- `ts_code` when it is provider-shaped rather than a canonical security identifier
- `source_run_id`
- `raw_loaded_at`
- raw artifact paths
- raw debug/source fields

Move required source/run lineage into raw, audit, or explicitly named lineage tables. If lineage moves to separate tables, `cycle_publish_manifest` or equivalent manifest logic must co-pin canonical snapshot ids and lineage snapshot ids for the same `cycle_id`.

Do not solve this only by projecting fields away in `current_cycle_inputs`; projection can remain as defense-in-depth, but the physical canonical schema must not rely on provider-shaped canonical rows.

If a low-risk physical rename is too risky, implement or stage an explicitly named `canonical_v2` namespace and a dual-write/read-compatibility path, with tests proving public reads use the provider-neutral shape.

## M1.0 Iceberg Write-Chain Spike Requirements

Prove or document the exact viable path for:

- staging -> intermediate -> marts materialization,
- PG-backed SQL catalog or a named alternate catalog/write path,
- `cycle_date` partitioning,
- add-column schema evolution,
- dbt-duckdb / PyIceberg / DuckDB integration boundaries.

If PG or compose is unavailable, do not start compose without approval. Instead:

- add/adjust focused unit tests where possible,
- document the exact command that would prove the live path,
- record the blocker and alternate path in the spike evidence.

## Test Requirements

Add or update tests that fail if canonical/public surfaces leak provider/raw lineage after the migration target is enabled.

Minimum expected coverage:

- DDL/spec tests for canonical tables.
- Canonical writer tests.
- Formal serving response/schema tests.
- Current-cycle input/readback tests.
- Provider catalog parity tests.
- dbt mart/intermediate tests that assert marts do not expose provider/raw lineage fields.
- Manifest tests if lineage snapshots are co-pinned with canonical snapshots.

Run the narrowest meaningful test set first. Suggested commands, adjust to the repo's actual tooling:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
python -m pytest tests/ddl tests/serving tests/cycle tests/provider_catalog tests/dbt -q
```

If dependencies are missing, report the exact missing dependency and the command that failed. Do not fabricate pass status.

## Acceptance Criteria

This run is successful only if:

- M1.0 has a real spike proof or a precise blocker/alternate-path report.
- Provider catalog fields, Iceberg specs, canonical writer specs, formal serving, current-cycle inputs, and dbt marts agree on provider-neutral identifiers.
- Canonical physical business rows do not include provider/raw lineage fields.
- Required lineage exists in raw/audit/lineage tables or a clearly named equivalent.
- Manifest/publish metadata co-pins canonical and lineage snapshot ids for a cycle if lineage was split out.
- Formal serving and frontend-api-facing public schemas cannot leak raw/provider fields.
- Focused tests pass, or failures are documented as real blockers with exact commands/output summaries.

## Final Response Format

When done, provide:

1. Files changed.
2. Evidence files created.
3. Tests/commands run and result.
4. Remaining blockers, if any.
5. Clear gate status:
   - `G1 Provider-neutral canonical`: pass / still blocked / partial.
   - `M1.0-M1.4`: pass / partial / blocked per item.

Do not claim P5 readiness or production completion.
