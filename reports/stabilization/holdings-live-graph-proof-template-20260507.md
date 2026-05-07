# Holdings Live Graph Proof Evidence Template - 2026-05-07

Status: `TEMPLATE_ONLY`

This template is for the future gated live proof:

`subsystem-holdings real queue submit -> data-platform worker accept -> cycle freeze -> PostgresCandidateDeltaReader frozen candidates -> graph-engine Layer A promotion/live proof harness -> Neo4j edge verification -> explicit #55 holdings algorithms`.

## Required Runtime Gates

| Gate | Required value |
|---|---|
| `DP_ENV` | `test` |
| PostgreSQL DB name | contains `proof`, `smoke`, or `test` |
| `SUBSYSTEM_HOLDINGS_LIVE_QUEUE_SUBMIT_CONFIRM` | `1` |
| `GRAPH_ENGINE_LIVE_PROOF_CONFIRM` | `1` |
| `GRAPH_ENGINE_LIVE_PROOF_NAMESPACE` | unique proof namespace |
| `NEO4J_DATABASE` | disposable DB name containing `proof`, `smoke`, or `test` |
| DuckDB input | existing verified holdings mart DB |

## Curated Summary Fields

The proof summary should include:

- redacted env status: `SET` / `missing`, never raw values.
- submitted payload count, worker accepted count, frozen candidate count, and
  Neo4j edge count.
- relation set exactly `CO_HOLDING` and `NORTHBOUND_HOLD`.
- Layer A artifact counts and redacted artifact references.
- explicit #55 algorithm path counts and diagnostics.

## Not Claimed

- default full propagation rollout.
- production entity registry or M4.8 completion.
- contracts subtype or holdings-specific Pydantic subtype.
- financial-doc scope.
- production queue propagation beyond this gated proof.

## Hygiene

Do not commit environment files, credentials, connection strings, provider
response bodies, runtime databases, dbt logs, Neo4j dumps, or absolute proof
workspace paths.
