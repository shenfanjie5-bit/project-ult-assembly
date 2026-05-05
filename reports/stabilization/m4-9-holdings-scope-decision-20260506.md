# M4.9 Holdings Scope Decision - 2026-05-06

This report records the assembly-owned M4.9 subsystem scope decision after
M4.6 and PR #52 (`a6bb671aff39cdd31db3ef28104e6119e13ad3ba`) landed. It is
a decision artifact only. It does not scaffold `subsystem-holdings`, does not
change contracts, and does not perform derivations or backfill.

## Status

- M4.9 decision: recorded.
- `subsystem-holdings` status: selected as the next P0 domain extension, not
  scaffolded by this PR.
- `subsystem-financial-doc` status: deferred.
- M4.7 status: partial; real-document validation remains open.
- M4.8 status: future validation gate.
- Evidence type: docs-only scope decision with a structured JSON sibling.
- Structured artifact:
  `reports/stabilization/m4-9-holdings-scope-decision-20260506.json`.
- Post-PR1-3 handoff: recorded after the data-platform holdings live smoke,
  backfill orchestration, derivation marts, and evidence/docs PRs landed.

## Decision

`subsystem-holdings` is the next P0 domain extension because it can produce
bounded Ex-3 graph deltas from already-canonical holdings facts without
requiring new document parsing, new contract subtypes, or raw provider access.

This PR only records the scope decision. The producer repository, runtime
wiring, tests, and proof artifacts remain future work.

## Post-PR1-3 Readiness Handoff

Data-platform holdings readiness is now available for downstream planning, but
the future `subsystem-holdings` producer still needs its own bounded proof.

- Holdings live smoke is complete in data-platform for five promoted
  interfaces: `top10_holders`, `top10_floatholders`, `fund_portfolio`,
  `hsgt_top10`, and `hsgt_hold_top10`. Curated evidence is repo-relative at
  `data-platform/docs/evidence/holdings-live-smoke-20260506.md`; token status
  and code scopes are redacted, and no provider payloads or raw logs are
  recorded here.
- Backfill orchestration is merged and available via data-platform PR #102 /
  commit `9629604dae9ed64dafd4d6c223e8b89941f6ad72`. It requires bounded
  inputs, defaults to plan-only, and live execution remains explicit opt-in.
- Derivation marts are merged and available via data-platform PR #103 /
  commit `32289f14252d530fab6cc1aed46c2f0cd5b7c39e`. The read-only producer
  inputs are top-holder quarter-over-quarter change, fund co-holding, and
  northbound z-score.
- Data-platform evidence/docs are merged via PR #104 / commit
  `81f3a57ee3fde8d1dc2a157737af2cd2abba91e5`.
- Live backfill was not executed. The recorded local status was
  `DP_TUSHARE_TOKEN=SET/redacted` with blocker
  `DP_TUSHARE_LIVE_HOLDINGS_BACKFILL missing`.

## Producer Boundary

- `subsystem-holdings` must read data-platform canonical or mart outputs only.
- `subsystem-holdings` must use the data-platform derivation marts only as
  read-only inputs.
- `subsystem-holdings` must not call Tushare, raw provider clients, raw-zone
  storage, or provider-specific source tables directly.
- `subsystem-holdings` must perform entity alignment and must fail closed with
  unresolved-entity audit records when alignment is incomplete.
- `subsystem-holdings` must submit only the existing
  `Ex3CandidateGraphDelta` shape through `subsystem-sdk`.
- `contracts` remain unchanged.
- No holdings-specific subtype is introduced.
- `#81` remains CLOSED / NOT_PLANNED.
- No derivations or backfill are included in this decision PR.

The intended write path is:

```text
data-platform canonical / mart holdings outputs
  -> future subsystem-holdings producer
  -> subsystem-sdk submission of existing Ex3CandidateGraphDelta
  -> existing assembly / data-platform / graph-engine promotion path
```

## Graph Relation Scope

M4.9 narrows holdings graph production to these relation types:

- `CO_HOLDING`
- `NORTHBOUND_HOLD`

Top-shareholder facts and pledge status must use the existing `OWNERSHIP`
relation plus properties. They must not create new relation types or contract
subtypes in this scope decision.

## Graph-Engine Follow-Up

`graph-engine #55` remains open and unimplemented. It must be narrowed later to
holdings-only propagation after producer proof exists. The future #55 scope
must supersede the older financial-doc / contracts-subtype scope and must not
assume financial-doc availability.

The dependency order is:

1. Record this M4.9 scope decision.
2. Prove a bounded `subsystem-holdings` producer using existing contracts and
   canonical / mart inputs.
3. Only then narrow `graph-engine #55` to holdings-only propagation.

## Financial-Doc Gate

`subsystem-financial-doc` is deferred until both conditions are met:

- M4.7 real-document validation proves representative A-share documents parse
  successfully with Docling / LlamaIndex or the selected replacement path.
- The holdings producer has shown enough usefulness to justify document scope
  as an additional domain extension rather than a substitute for holdings.

Until then, financial-doc scope must not drive new contracts, new Ex-3
subtypes, or graph-engine #55 planning.

## M4.7 / M4.8 Interaction

M4.7 remains partial. It is still the real-document validation gate for
document parsing and extraction claims.

M4.8 remains a future validation gate. This M4.9 decision does not close
entity-resolution validation and does not relax fail-closed handling for
unresolved entities.

## Scope Exclusions

This decision does not:

- scaffold, register, or version `subsystem-holdings`;
- modify `data-platform`, `contracts`, `graph-engine`, or any sibling repo;
- add data derivations, backfill, or raw-provider ingestion;
- add holdings-specific contract classes, subtypes, or relation contracts;
- claim that a holdings producer exists or has passed proof;
- claim that M4.7 or M4.8 is complete;
- start `subsystem-financial-doc`.

## Evidence Hygiene

- Raw logs: not recorded.
- Secrets, DSNs, API keys, bearer tokens: not recorded.
- Local filesystem paths: not recorded beyond this repo-relative report path.
- Contract files: not touched.
- Sibling repos: not touched.
