# M4.9 Holdings Scope Decision - 2026-05-06

This report records the assembly-owned M4.9 subsystem scope decision and
handoff after M4.6, assembly PR #52
(`a6bb671aff39cdd31db3ef28104e6119e13ad3ba`), and the first four
`subsystem-holdings` PRs landed. It records the PR #5 blocker state and the
newer attempt2 live proof handoff state after sibling repo progress. It is an
assembly docs/report artifact only. It does not change code, does not change
contracts, and does not perform derivations or backfill.

## Status

- M4.9 decision: recorded and updated for the holdings adapter handoff.
- `subsystem-holdings` status: selected as the next P0 domain extension; its
  producer scaffold exists.
- Read-only mart adapter proof: complete.
- Proof boundary: attempt2 is reported as runtime-verified PASS, and tracked
  sibling evidence is merged via data-platform PR #107 commit
  `841f7c0f95e8c613e5bac9fe0fe78c09e1f9f152` and `subsystem-holdings`
  PR #9 commit `b046ecf6b54220ceedf517089ebcc883571184d1`.
- Not proven by assembly: queue submit, live graph propagation, graph-engine
  #55 entry, provider/backfill execution from assembly, financial-doc scope, or
  contracts/subtype change.
- `subsystem-financial-doc` status: deferred.
- M4.7 status: partial; real-document validation remains open.
- M4.8 status: future validation gate.
- Evidence type: docs-only scope decision and handoff with a structured JSON
  sibling.
- Structured artifact:
  `reports/stabilization/m4-9-holdings-scope-decision-20260506.json`.
- Post-PR1-3 handoff: recorded after the data-platform holdings live smoke,
  backfill orchestration, derivation marts, and evidence/docs PRs landed.
- Post-PR1-4 holdings adapter handoff: recorded after the
  `subsystem-holdings` scaffold, mart shape fidelity, read-only mart adapter,
  and evidence PRs landed.
- PR #5 live producer blocker handoff: recorded after exact blocker evidence
  landed in `subsystem-holdings`.
- Attempt2 live proof handoff: data-platform PR #105 / #106 and
  `subsystem-holdings` PR #6 / #7 / #8 have landed in sibling repos. Runtime
  attempt2 is reported PASS, with tracked evidence merged in data-platform
  PR #107 commit `841f7c0f95e8c613e5bac9fe0fe78c09e1f9f152` and
  `subsystem-holdings` PR #9 commit
  `b046ecf6b54220ceedf517089ebcc883571184d1`.

## Decision

`subsystem-holdings` is the next P0 domain extension because it can produce
bounded Ex-3 graph deltas from already-canonical holdings facts without
requiring new document parsing, new contract subtypes, or raw provider access.

This PR only records the scope decision and updated handoff. The producer
scaffold now exists in `subsystem-holdings`, and the real read-only mart
adapter proof is complete. PR #5 blocker evidence is no longer the current
terminal state: attempt2 live proof is reported as runtime PASS after
data-platform PR #105 / #106 and `subsystem-holdings` PR #6 / #7 / #8 landed.
Assembly now points to the merged sibling evidence PRs for repository-tracked
handoff evidence.

Assembly was already aligned at the boundary level. This update syncs assembly
to the current attempt2 handoff without changing the boundary, contracts,
subtype scope, graph-engine scope, or sibling repositories.

## Subsystem-Holdings Adapter Handoff

`subsystem-holdings` PR #1 scaffolded the producer:

- Commit: `e384b48a0260cf1b6636d3fd6de6177ca05f5db8`.
- Handoff meaning: the producer repository is no longer future-only or
  unscaffolded.

`subsystem-holdings` PR #2 landed mart shape fidelity:

- Commit: `b62cb0b98348f5d5f090397200430edfae2c54b4`.
- Handoff meaning: the adapter proof uses the intended mart-shaped inputs.

`subsystem-holdings` PR #3 landed the read-only mart adapter:

- Commit: `752c9842d75048a12b28472ed55c83615f7bd199`.
- Handoff meaning: the adapter proof exercises a real read-only mart access
  path rather than a placeholder producer.

`subsystem-holdings` PR #4 landed evidence:

- Commit: `41ac033125fab3f810b98ad5e7ad5c5606ae227a`.
- Handoff meaning: the non-live proof evidence is recorded in the producer
  repository.

The proof boundary is intentionally narrow:

- Historical PR #1 through #5 evidence remains bounded to non-live adapter and
  blocker evidence.
- Attempt2 live proof is reported PASS in runtime, and tracked evidence is
  merged in sibling evidence PRs #107 and #9.
- No provider call from `subsystem-holdings`.
- No live holdings backfill.
- No production queue propagation proof.
- No live graph propagation proof.
- No M4.7 or M4.8 closure.
- No contracts or subtype change.

## Data-Platform Readiness Handoff

Data-platform holdings readiness is now available for downstream planning. The
`subsystem-holdings` producer has bounded read-only mart adapter proof, PR #5
blocker evidence, and newer attempt2 runtime PASS status with tracked sibling
evidence merged via data-platform PR #107 commit
`841f7c0f95e8c613e5bac9fe0fe78c09e1f9f152` and `subsystem-holdings` PR #9
commit `b046ecf6b54220ceedf517089ebcc883571184d1`.

- Holdings live smoke is complete in data-platform for five promoted
  interfaces: `top10_holders`, `top10_floatholders`, `fund_portfolio`,
  `hsgt_top10`, and `hsgt_hold_top10`. Curated evidence is repo-relative at
  `data-platform/docs/evidence/holdings-live-smoke-20260506.md`; credential
  status and code scopes are redacted, and no provider payloads or execution
  traces are recorded here.
- Backfill orchestration is merged and available via data-platform PR #102 /
  commit `9629604dae9ed64dafd4d6c223e8b89941f6ad72`. It requires bounded
  inputs, defaults to plan-only, and live execution remains explicit opt-in.
- Derivation marts are merged and available via data-platform PR #103 /
  commit `32289f14252d530fab6cc1aed46c2f0cd5b7c39e`. The read-only producer
  inputs are top-holder quarter-over-quarter change, fund co-holding, and
  northbound z-score.
- Data-platform evidence/docs are merged via PR #104 / commit
  `81f3a57ee3fde8d1dc2a157737af2cd2abba91e5`.
- Data-platform PR #105 / #106 are merged in sibling repo history. Assembly
  does not record provider payloads, runtime paths, secrets, or live execution
  traces for those changes.
- Attempt2 live proof evidence is merged via data-platform PR #107 / commit
  `841f7c0f95e8c613e5bac9fe0fe78c09e1f9f152` and
  `subsystem-holdings` PR #9 / commit
  `b046ecf6b54220ceedf517089ebcc883571184d1`.

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
- No derivations or backfill are included in this assembly PR.

The intended write path is:

```text
data-platform canonical / mart holdings outputs
  -> subsystem-holdings producer
  -> subsystem-sdk submission of existing Ex3CandidateGraphDelta
  -> existing assembly / data-platform / graph-engine promotion path
```

This path is not production-proven by the current holdings adapter evidence.
Assembly points to merged tracked attempt2 evidence PRs for handoff evidence,
and this handoff still does not enter live graph propagation.

## PR #5 Live Producer Blocker Handoff

`subsystem-holdings` PR #5 landed blocker evidence for the live producer proof.
This is historical blocker evidence, not the current terminal state:

- Commit: `abfa7603484acc3a0bb09887a4332d490be05046`.
- Evidence path:
  `subsystem-holdings/docs/evidence/live-producer-proof-blockers-20260506.md`.
- Handoff meaning: assembly was already aligned at the boundary level and is
  keeps the PR #5 blocker evidence as historical context.

The blocker class was missing live backfill and complete mart/lineage inputs.
It has been superseded for handoff purposes by the attempt2 runtime PASS state,
with sibling evidence now merged via PR #107 and PR #9.

## Attempt2 Live Proof Handoff

- Data-platform PR #105 / #106 have landed in the sibling repo.
- `subsystem-holdings` PR #6 / #7 / #8 have landed in the sibling repo.
- Attempt2 live proof is reported as runtime-verified PASS.
- Tracked sibling evidence is merged via data-platform PR #107 commit
  `841f7c0f95e8c613e5bac9fe0fe78c09e1f9f152` and `subsystem-holdings`
  PR #9 commit `b046ecf6b54220ceedf517089ebcc883571184d1`.
- The subsystem-holdings adapter fix for incomplete top-holder QoQ rows is
  fail-closed skip diagnostic behavior. It does not block `CO_HOLDING` /
  `NORTHBOUND_HOLD`.

This evidence does not claim any of the following:

- Queue submit.
- Live graph proof.
- Provider/backfill execution from assembly.
- Financial-doc scope.
- Live graph contracts subtype work.
- Graph-engine #55 entry.
- Contracts or subtype change.

Graph-engine #55 remains not entered. This handoff must not mix #55 and #56
scope and must not revive the older financial-doc / contracts-subtype scope.

## Graph Relation Scope

M4.9 narrows holdings graph production to these relation types:

- `CO_HOLDING`
- `NORTHBOUND_HOLD`

Top-shareholder facts and pledge status must use the existing `OWNERSHIP`
relation plus properties. They must not create new relation types or contract
subtypes in this scope decision.

## Graph-Engine Follow-Up

`graph-engine #55` remains not entered and unimplemented. This handoff records
that the producer scaffold and non-live read-only adapter proof now exist, but
it does not shift #56/#55 scope and does not enter graph propagation work. The
future #55 scope must not revive the older financial-doc / contracts-subtype
scope and must not assume financial-doc availability.

The dependency order is:

1. Keep this M4.9 scope decision and handoff as the assembly boundary.
2. Add a separate live producer proof only when live execution is intentionally
   in scope.
3. Only then enter graph-engine #55 propagation work.

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

- modify `data-platform`, `contracts`, `graph-engine`, or any sibling repo;
- add data derivations, backfill, or raw-provider ingestion;
- add holdings-specific contract classes, subtypes, or relation contracts;
- claim live producer execution;
- claim live holdings backfill;
- claim provider calls from `subsystem-holdings`;
- claim production queue propagation or live graph propagation;
- enter graph-engine #55;
- claim that M4.7 or M4.8 is complete;
- start `subsystem-financial-doc`.

## Evidence Hygiene

- Execution traces: not recorded.
- Secrets, database connection strings, and API keys: not recorded.
- Local filesystem paths: not recorded beyond this repo-relative report path.
- Contract files: not touched.
- Sibling repos: not touched.
