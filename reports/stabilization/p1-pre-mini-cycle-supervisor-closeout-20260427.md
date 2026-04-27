# P1 Pre Mini-Cycle Supervisor Closeout - 2026-04-27

## Scope

This closeout records the supervisor decision to enter the real-data mini-cycle
gate. It does not mark P5 shadow-run complete.

## Closed Preconditions

### frontend-api verified matrix promotion

- Assembly commit: `23c3e02971a40d8ab587c1d118d7649f6076f9eb`
- frontend-api commit: `68414ed8423caf51f192a9c1a00c36ddaf19ab93`
- Evidence:
  - `assembly/reports/stabilization/frontend-api-readonly-ui-promotion-20260427.md`
  - `assembly/reports/stabilization/frontend-api-readonly-ui-supervisor-review-20260427.md`
  - `assembly/reports/stabilization/lite-local-readonly-ui-frontend-display-evidence-20260427.md`
- Supervisor decision: closed. The `lite-local-readonly-ui` profile is verified
  without modifying old verified rows and without using `extra_bundles`.

### P1 Iceberg write-chain architecture spike

- data-platform commit: `9323d09473c90484cecbdf31001674135d0aed1b`
- Assembly evidence commit: `3c7069ba19d46cb5f4e184ae93a03202ba61ebdd`
- Evidence:
  - `assembly/reports/stabilization/p1-iceberg-write-chain-spike-20260427.md`
  - `data-platform/docs/spike/iceberg-write-chain.md`
- Independent review: no P0/P1/P2/P3 findings.
- Supervisor decision: closed as an architecture spike. It proves PG-backed
  SQL catalog use, single-table Iceberg commit snapshots, `publish_manifest()`
  semantics, manifest-pinned formal serving, and visibility-boundary failure
  handling. It is not yet a production Dagster daily-cycle execution proof.

### P1 Tushare coverage table

- Assembly commit: `6b55087711baedf504921d064db05318b9db4a9c`
- Evidence:
  - `assembly/reports/stabilization/p1-tushare-coverage-table-20260427.md`
- Independent review: no P0/P1/P2/P3 findings.
- Supervisor decision: closed for planning. Current coverage is 28 declared
  Tushare API/assets and 28 staging models; 20 have downstream use; 8 are
  raw+staging-only; the gap to the approximate 40 API target remains 12.

## Open Boundaries

- P5 is not complete.
- The next gate is a real-data mini cycle over 1-3 trading days and a small
  A-share symbol set, not a 20 trading day shadow-run.
- The mini cycle must not relabel fixture, mock, or assembly-only probes as
  real data execution.
- Orchestrator `min-cycle` remains assembly-probe only until a separate real
  execution path proves otherwise.
- P2 real L1-L8 dry run remains blocked until the real-data mini cycle produces
  clean evidence.

## Next Assigned Batch

Backend/data-platform/orchestrator role owns the first mini-cycle batch:

- prove or hard-block real Tushare/raw ingestion;
- run dbt staging/intermediate/marts;
- prove candidate freeze and cycle metadata;
- prove formal object commit, publish manifest, and manifest-pinned formal
  serving;
- inspect audit/replay integration and run it if a real-cycle entrypoint exists;
- write `assembly/reports/stabilization/real-data-mini-cycle-20260427.md`;
- commit and push each touched repo.

Testing role will run after backend completion and must independently verify the
commands, evidence, and that no mock path was represented as real execution.
