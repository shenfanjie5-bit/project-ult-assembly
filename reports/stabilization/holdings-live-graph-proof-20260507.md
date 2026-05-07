# Holdings Live Graph Proof - 2026-05-07

Status: `PASSED`

This evidence records the gated live proof:

`subsystem-holdings real queue submit -> data-platform worker accept -> cycle freeze -> PostgresCandidateDeltaReader frozen candidates -> graph-engine Layer A promotion/live proof harness -> Neo4j edge verification -> explicit #55 holdings algorithms`.

## Runtime Isolation

| Resource | Status |
|---|---|
| Neo4j image | `neo4j:5.26.25` local image |
| Neo4j container | disposable proof container |
| Neo4j Bolt | isolated random localhost port, not `127.0.0.1:7687` |
| Neo4j HTTP | isolated random localhost port |
| Neo4j user database | `projectult-holdings-proof-20260507-155801` |
| Neo4j default/shared database | not used; `neo4j` user database was not created |
| PostgreSQL database | `dp_holdings_graph_proof_20260507_160230` |
| PostgreSQL migrations | `0001` through `0005` applied |
| DuckDB input | existing proof workspace DuckDB, path redacted |
| Artifact root | proof workspace, path redacted |

## Gates

| Gate | Result |
|---|---|
| `DP_ENV` | `test` |
| `DP_PG_DSN` / `DATABASE_URL` | `SET`, value redacted |
| `DP_DUCKDB_PATH` | `SET`, value redacted |
| `NEO4J_URI` | `SET`, value redacted |
| `NEO4J_USER` | `SET` |
| `NEO4J_PASSWORD` | `SET`, value redacted |
| `NEO4J_DATABASE` | proof database, non-`neo4j` |
| `SUBSYSTEM_HOLDINGS_LIVE_QUEUE_SUBMIT_CONFIRM` | `1` |
| `GRAPH_ENGINE_LIVE_PROOF_CONFIRM` | `1` |
| `GRAPH_ENGINE_LIVE_PROOF_NAMESPACE` | `holdings-proof-20260507-160230` |

The disposable Neo4j instance was started with `initial.dbms.default_database`
mapped through the Neo4j Docker environment. `SHOW DATABASES` returned only
`system` and the proof user database; the proof user database was default and
online.

## Proof Bootstrap

The proof Neo4j database started empty. Before the final execute run, the
required endpoint nodes were seeded into the disposable proof database only:

| Bootstrap item | Count |
|---|---:|
| Derived queue payloads used for endpoint discovery | 55 |
| Proof endpoint nodes seeded | 12 |
| Pre-run live graph nodes | 12 |
| Pre-run live graph edges | 0 |
| Pre-run graph status | `ready` |
| Pre-run graph generation | 1 |

No shared Neo4j container, shared Bolt port, shared Neo4j database, contracts
repository, `.env` file, token, DSN, raw provider payload, or raw local runtime
path was used in evidence.

## Results

| Step | Count / result |
|---|---:|
| Submitted holdings payloads | 55 |
| Queue receipts | 55 |
| Worker accepted candidates | 55 |
| Worker rejected candidates | 0 |
| Frozen candidates | 55 |
| Frozen reader candidates | 55 |
| Layer A deltas | 55 |
| Layer A edges | 55 |
| Layer A assertions | 0 |
| Neo4j expected unique live edges | 46 |
| Neo4j verified live edges | 46 |
| Neo4j missing edge ids | 0 |
| Neo4j disallowed relation types | 0 |

Relation counts:

| Surface | `CO_HOLDING` | `NORTHBOUND_HOLD` |
|---|---:|---:|
| Queue submit | 45 | 10 |
| Frozen candidates | 45 | 10 |
| Layer A artifact | 45 | 10 |
| Neo4j edge verification | 45 | 1 |

The proof relation set was exactly:

`CO_HOLDING`, `NORTHBOUND_HOLD`

The live Neo4j verification counted unique promoted edge ids. The
`NORTHBOUND_HOLD` queue and Layer A rows converged to one unique live edge id;
the proof still retained a positive verified edge count for both allowed
holdings relation types.

## #55 Algorithm Diagnostics

| Diagnostic | Count |
|---|---:|
| Co-holding path count | 0 |
| Northbound path count | 0 |
| Total path count | 0 |
| Impacted entity count | 0 |
| Co-holding `holder_count_below_minimum` | 45 |
| Northbound `z_score_below_threshold` | 1 |

The explicit #55 holdings algorithms executed after live graph sync and
returned zero activated paths because the proof data did not meet the current
algorithm thresholds. This is a threshold diagnostic, not a live graph sync
failure.

## Notes

The direct CLI execute first exposed a Python dynamic-import issue in the
assembly loader for the subsystem-holdings dataclass script. The successful run
used a command-scoped Python wrapper that registered the dynamically loaded
module in `sys.modules` before calling the same assembly runner. No code guard
was relaxed and no repository code was changed for this workaround.

Neo4j emitted deprecation/property-existence notifications for some Cypher
queries against the fresh proof database. They were warnings only; the runner
completed with `status=passed`.

## Not Claimed

- Default full propagation rollout.
- Production entity registry / M4.8 completion.
- Contracts subtype or holdings-specific Pydantic subtype.
- Financial-doc scope.
- Production queue propagation beyond this gated proof.
