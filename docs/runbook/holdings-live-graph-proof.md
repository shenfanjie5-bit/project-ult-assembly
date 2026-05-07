# Holdings Live Graph Proof Runbook

This runbook describes the gated proof chain from holdings payload submission to
read-only holdings graph algorithms. It is a proof workflow, not a default
production rollout.

## Scope

The proof validates this chain:

```text
subsystem-holdings real queue submit
-> data-platform worker accept
-> cycle freeze
-> PostgresCandidateDeltaReader frozen candidates
-> graph-engine Layer A promotion/live proof harness
-> Neo4j edge verification
-> explicit #55 holdings algorithms
```

It does not claim default full propagation rollout, production entity registry
or M4.8 completion, new contracts subtype, financial-doc scope, or production
queue propagation.

## Required Gates

Use command-scoped environment only:

```bash
export DP_ENV=test
export DP_PG_DSN=<postgres-dsn-for-proof-db>
export DATABASE_URL=<postgres-dsn-for-proof-db>
export DP_DUCKDB_PATH=<verified-holdings-duckdb>
export SUBSYSTEM_HOLDINGS_LIVE_QUEUE_SUBMIT_CONFIRM=1
export GRAPH_ENGINE_LIVE_PROOF_CONFIRM=1
export GRAPH_ENGINE_LIVE_PROOF_NAMESPACE=<unique-proof-namespace>
export NEO4J_URI=<neo4j-uri>
export NEO4J_USER=<neo4j-user>
export NEO4J_PASSWORD=<neo4j-password>
export NEO4J_DATABASE=<disposable-proof-neo4j-db>
```

Fail closed rules:

- `DP_ENV` must be `test`.
- PostgreSQL database name must contain `proof`, `smoke`, or `test`.
- `--pg-dsn`, when supplied, is bound to `DP_PG_DSN` and `DATABASE_URL`
  before queue submit, worker, freeze, frozen reads, and graph proof steps.
- `NEO4J_DATABASE` is required, must not be `neo4j` or another shared/default
  name, and must contain `proof`, `smoke`, or `test`.
- `--neo4j-database`, when supplied, is bound to `NEO4J_DATABASE` before any
  live side effect.
- `DP_DUCKDB_PATH` or `--duckdb-path` must point to an existing verified
  holdings DuckDB file.
- Payload, frozen candidate, and Neo4j edge counts must be greater than zero.
- Relation set must be exactly `CO_HOLDING` and `NORTHBOUND_HOLD`.

## Dry Run

Dry run validates gates that are safe to check without writing PG or Neo4j:

```bash
cd <workspace>/assembly
.venv-py312/bin/python scripts/holdings_live_graph_proof.py \
  --summary-json reports/stabilization/holdings-live-graph-proof-summary-20260507.json
```

## Live Proof

Only run against one-time PostgreSQL and Neo4j databases:

```bash
cd <workspace>/assembly
.venv-py312/bin/python scripts/holdings_live_graph_proof.py \
  --execute \
  --summary-json reports/stabilization/holdings-live-graph-proof-summary-20260507.json \
  --artifact-root <proof-workspace>/graph-artifacts
```

The summary JSON is curated. It records redacted env status, submitted/frozen
counts, relation set, Layer A artifact counts, Neo4j edge verification, and
#55 algorithm diagnostics. Do not commit runtime databases, raw payloads, dbt
logs, environment files, or proof workspace files.
