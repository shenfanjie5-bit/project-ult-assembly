# Holdings Bounded Canary Live Production Evidence - 2026-05-07

Status: `PASSED`

This report records curated assembly evidence for the bounded, gated holdings
canary run. It is a docs-only evidence artifact derived from sanitized runtime
summary data. It does not commit local runtime JSON, does not include raw
payloads, and does not change contracts.

## Scope

The canary used disposable PostgreSQL and Neo4j canary resources, applied
data-platform migrations `0001` through `0006`, executed a targeted
holdings-only Ex-3 queue/freeze/graph path, and cleaned up the disposable
containers afterward.

The evidence path covered:

```text
holdings readiness
  -> selected queue execute
  -> data-platform worker accept
  -> targeted freeze
  -> frozen reader
  -> graph canary sync
  -> Neo4j edge readback
  -> explicit holdings algorithm diagnostics
```

## Merge References

This canary follows the landed guard/prerequisite handoff recorded in
`reports/stabilization/holdings-production-hardening-prereqs-20260507.md`:

| Repository | Merge reference |
|---|---|
| entity-registry | PR #61 |
| data-platform | PR #110 |
| graph-engine | PR #61 |
| subsystem-sdk | PR #44 / release `v0.1.4` |
| subsystem-holdings | PR #13 |

Earlier M4.9 proof handoff references remain the scope boundary recorded in
`reports/stabilization/m4-9-holdings-scope-decision-20260506.md`.

## Redacted Runtime Status

| Area | Status |
|---|---|
| Runtime summary | sanitized |
| PostgreSQL resource | disposable canary resource |
| Neo4j resource | disposable canary resource |
| PostgreSQL connection setting | configured, value redacted |
| Neo4j connection setting | configured, value redacted |
| Neo4j credential setting | configured, value redacted |
| DuckDB input | verified attempt2 source, path redacted |
| Environment mode | `test` |
| Shared PostgreSQL | not used |
| Shared Neo4j | not used |
| Secret files | removed |
| Containers | cleaned |

No local filesystem path, connection string, credential value, raw payload,
specific security identifier, or specific fund identifier is recorded in this
report.

## Results

| Gate | Result |
|---|---:|
| Readiness ready | yes |
| Readiness payloads | 55 |
| Queue selected payloads | 46 |
| Queue receipts | 46 |
| Queue accepted receipts | 46 |
| Queue rejected receipts | 0 |
| Worker accepted | 46 |
| Worker rejected | 0 |
| Targeted freeze candidates | 46 |
| Frozen reader candidates | 46 |
| Graph expected readback edges | 46 |
| Graph actual readback edges | 46 |
| Missing edge ids | 0 |
| Disallowed relation types | 0 |

Relation counts after targeted freeze, frozen reader readback, and graph edge
readback were:

| Relation | Count |
|---|---:|
| `CO_HOLDING` | 45 |
| `NORTHBOUND_HOLD` | 1 |

The frozen reader relation set was exactly `CO_HOLDING` and `NORTHBOUND_HOLD`.
The graph readback relation set matched that bounded holdings-only relation
set, with no missing edge ids and no disallowed relation types.

## Algorithm Diagnostics

| Diagnostic | Count |
|---|---:|
| Co-holding path count | 0 |
| Northbound path count | 0 |
| Total path count | 0 |
| Impacted entity count | 0 |
| `holder_count_below_minimum` | 45 |
| `z_score_below_threshold` | 1 |

The explicit holdings algorithms ran after the canary graph readback and
returned zero activated paths because the bounded data did not cross the
current thresholds. That is a threshold diagnostic, not a canary failure.

## Pass Criteria

| Criterion | Status |
|---|---|
| Sanitized evidence manifest | passed |
| Readiness ready | passed |
| Execute selected equals accepted receipts | passed |
| Worker rejected zero | passed |
| Freeze candidate count equals selected count | passed |
| Frozen reader relation set exactly holdings | passed |
| Graph edge count positive | passed |
| Graph missing edge ids empty | passed |
| Graph disallowed relation types empty | passed |

## Not Claimed

- Default or full propagation enabled.
- `run_full_propagation` execution.
- Broad production rollout complete.
- No-descope default production queue propagation.
- Destructive cold reload.
- Contracts changes, contracts subtype changes, or new relation scope.
- M4.7 real-document completion.
- Financial-document scope.
- Specific provider payload, security identifier, fund identifier, connection
  string, credential value, or local runtime path.
