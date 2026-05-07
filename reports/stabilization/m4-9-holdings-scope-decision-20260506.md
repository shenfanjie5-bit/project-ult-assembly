# M4.9 Holdings Scope Decision - 2026-05-06

This report records the assembly-owned M4.9 subsystem scope decision and
handoff after M4.6, assembly PR #52
(`a6bb671aff39cdd31db3ef28104e6119e13ad3ba`), and the first four
`subsystem-holdings` PRs landed. It records the PR #5 blocker state, the newer
attempt2 live proof handoff state, the post queue/freeze/promotion handoff,
the post holdings-only algorithms handoff after sibling repo progress, and the
M4.8 entity-resolution proof closeout that landed after the original M4.9
decision. It is an assembly docs/report artifact only. It does not change code,
does not change contracts, and does not perform derivations or backfill.

## Status

- M4.9 decision: recorded and updated for the holdings adapter handoff.
- `subsystem-holdings` status: selected as the next P0 domain extension; its
  producer scaffold exists.
- Read-only mart adapter proof: complete.
- Proof boundary: attempt2 is reported as runtime-verified PASS, and tracked
  sibling evidence is merged via data-platform PR #107 commit
  `841f7c0f95e8c613e5bac9fe0fe78c09e1f9f152` and `subsystem-holdings`
  PR #9 commit `b046ecf6b54220ceedf517089ebcc883571184d1`.
- Queue/freeze/promotion handoff: proof-only queue submit path, holdings Ex-3
  queue/freeze bridge, and offline Layer A promotion/query/channel proof are
  merged in sibling repos.
- Holdings-only algorithms handoff: graph-engine PR #59 merged and closed
  #55 with explicit-entry-only `CO_HOLDING` co-holding crowding and
  `NORTHBOUND_HOLD` northbound anomaly algorithms.
- Not proven by assembly: production queue propagation, live Neo4j graph
  propagation, default full-propagation rollout, provider/backfill execution
  from assembly, financial-doc scope, guarantees or related-party scope, or
  contracts/subtype change.
- `subsystem-financial-doc` status: deferred.
- M4.7 status: partial; real-document validation remains open.
- M4.8 status: proof closeout complete as bounded evidence; production rollout
  hardening remains future planning.
- M4.8 evidence: `reports/stabilization/m4-8-entity-resolution-proof-20260507.md`.
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
- Post queue/freeze/promotion handoff: data-platform PR #108,
  `subsystem-holdings` PR #10, `subsystem-sdk` PR #43 / tag `v0.1.3`, and
  graph-engine PR #58 have landed.
- Post holdings-only algorithms handoff: graph-engine PR #59 merged as
  `8a40fead9a57d67f0b232a52d4ed0d99db78a96e`, and #55 is closed with the
  narrowed holdings-only scope.
- Production hardening prerequisites handoff: entity-registry PR #61,
  data-platform PR #110, graph-engine PR #61, subsystem-sdk PR #44 / release
  tag `v0.1.4`, and subsystem-holdings PR #13 have landed as guard/prereq
  work. Assembly records this as prerequisites/guards landed only.
- Bounded gated canary/live production evidence handoff: passed in curated
  assembly evidence at
  `reports/stabilization/holdings-bounded-canary-live-production-evidence-20260507.md`.
  Readiness was ready for 55 payloads; selected queue execute/receipts/accepted
  count was 46; worker rejected count was 0; targeted freeze count was 46;
  frozen reader and graph readback relation counts were `CO_HOLDING=45` and
  `NORTHBOUND_HOLD=1`; graph expected/readback edges were 46 with no missing
  edge ids and no disallowed relation types; explicit holdings algorithm path
  counts were 0 with threshold diagnostics. Runtime environment details are
  redacted.
- M4.8 proof closeout handoff: entity-registry PR #60 merged as
  `6debd8cc137ee57572fd862959cd845c6dffcab5`, `subsystem-holdings` PR #12
  merged as `11c1b1cf62be32c49940293c2e04e89d93ae1ecc`, and holdings live
  graph proof PR #62 merged as
  `3736799bf362970670b0769e363c75bc15123f79`.

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
to the current queue/freeze/promotion and holdings-only algorithm handoff
without changing contracts, subtype scope, production rollout status, or
sibling repositories.

The M4.8 proof is now complete as a separate bounded evidence closeout. That
allows future M4.9 planning to discuss production rollout hardening, but this
handoff still does not claim production entity registry rollout, production
queue propagation, production live graph propagation, or default/full
propagation.

The production hardening prerequisite work has now landed in sibling repos and
is recorded in
`reports/stabilization/holdings-production-hardening-prereqs-20260507.md`.
This updates the M4.9 handoff from planning-only to prerequisites/guards
landed. The bounded gated canary/live production evidence has also passed and
is recorded in
`reports/stabilization/holdings-bounded-canary-live-production-evidence-20260507.md`.
It still does not declare production rollout complete, and production rollout
remains not default-enabled.

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
- No M4.7 closure.
- No production entity registry rollout.
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

This path is proof-covered through the current sibling handoff only up to
proof-only queue submit, data-platform queue/freeze bridge, and offline Layer A
promotion/query/channel compatibility. Assembly points to merged tracked
attempt2 evidence and queue/freeze/promotion PRs for handoff evidence, and
this handoff still does not enter production queue propagation or live Neo4j
graph propagation.

## PR #5 Live Producer Blocker Handoff

`subsystem-holdings` PR #5 landed blocker evidence for the live producer proof.
This is historical blocker evidence, not the current terminal state:

- Commit: `abfa7603484acc3a0bb09887a4332d490be05046`.
- Evidence path:
  `subsystem-holdings/docs/evidence/live-producer-proof-blockers-20260506.md`.
- Handoff meaning: assembly was already aligned at the boundary level and
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

This attempt2 evidence does not claim any of the following:

- Queue submit; that is covered later only by proof-only handoff evidence.
- Live Neo4j graph propagation.
- Provider/backfill execution from assembly.
- Financial-doc scope.
- Live graph contracts subtype work.
- Graph-engine #55 algorithms; that is covered later only by the scoped
  holdings-only handoff.
- Contracts or subtype change.

This attempt2 handoff must not mix #55 and #56 scope and must not revive the
older financial-doc / contracts-subtype scope.

## Post Queue/Freeze/Promotion Handoff - 2026-05-07

The next holdings handoff layer has landed after the attempt2 producer proof:

- `subsystem-sdk` PR #43 merged as
  `9c220b7a7a9f5f50b3c57131b501b83fab2e75ce` and released
  `data_platform_queue` backend support as tag `v0.1.3`.
- `subsystem-holdings` PR #10 merged as
  `63a09b7ca6e6d152279a51857cd497fd8be60fb7`, adding a proof-only queue
  submit path through the SDK backend.
- Data-platform PR #108 merged as
  `138b78c27b68b1d9b5e7395aec0c396d99dc4202`, proving holdings Ex-3
  queue/freeze bridge behavior for frozen candidates.
- Graph-engine PR #58 merged as
  `7eb363cc74325699de5ac46c1362e93cdf470651`, proving `edge_upsert`
  compatibility for holdings Layer A promotion, query, and propagation-channel
  declarations.

The combined meaning is narrow: proof-only queue submit path plus holdings Ex-3
queue/freeze bridge plus offline Layer A promotion/query/channel proof are
landed. This does not claim:

- production queue propagation;
- live Neo4j graph propagation;
- graph-engine #55 algorithms;
- provider/backfill execution from assembly;
- financial-doc scope;
- holdings-specific contracts subtype or any contracts change.

## Post Holdings-Only Algorithms Handoff - 2026-05-07

Graph-engine PR #59 merged as
`8a40fead9a57d67f0b232a52d4ed0d99db78a96e` and closed issue #55 with the
superseded holdings-only scope. The landed scope is intentionally narrow:

- `CO_HOLDING`: co-holding crowding algorithm.
- `NORTHBOUND_HOLD`: northbound anomaly algorithm.
- Entry mode: explicit holdings algorithm entry points only.
- Channel fit: `CO_HOLDING` remains reflexive; `NORTHBOUND_HOLD` remains event
  aligned while preserving the earlier channel declaration context.

PR #59 CI passed in graph-engine:

- `ci`: pass.
- `test-fast`: pass.
- `smoke`: pass.
- `contract`: pass.
- `regression`: pass.

This handoff does not claim:

- production queue propagation;
- production live graph writeback;
- default full-propagation rollout;
- guarantees, related-party, or financial-doc algorithms;
- `MAJOR_CUSTOMER` / `MAJOR_SUPPLIER`;
- holdings-specific contracts subtype or any contracts change;
- assembly execution of provider/backfill, graph sync, or graph algorithms.

The older #55 scope that mentioned guarantees, related-party, financial-doc,
contracts subtype, `MAJOR_CUSTOMER`, or `MAJOR_SUPPLIER` is superseded and must
not be revived through this M4.9 handoff.

## Graph Relation Scope

M4.9 narrows holdings graph production to these relation types:

- `CO_HOLDING`
- `NORTHBOUND_HOLD`

Top-shareholder facts and pledge status must use the existing `OWNERSHIP`
relation plus properties. They must not create new relation types or contract
subtypes in this scope decision.

## Graph-Engine Follow-Up

`graph-engine #55` is closed through PR #59 with a holdings-only algorithm
scope. This handoff records that producer scaffold, read-only adapter proof,
proof-only queue submit path, holdings Ex-3 queue/freeze bridge, offline Layer
A promotion/query/channel proof, and explicit-entry holdings algorithms now
exist. It does not shift into production queue propagation, production live
graph writeback, default full propagation, or financial-doc scope. The older
financial-doc / contracts-subtype scope remains superseded and must not assume
financial-doc availability.

The dependency order is:

1. Keep this M4.9 scope decision and handoff as the assembly boundary.
2. Treat the bounded live producer proof as merged sibling evidence through
   `subsystem-holdings` PR #9.
3. Treat proof-only queue submit, holdings Ex-3 queue/freeze bridge, and
   offline Layer A promotion/query/channel proof as merged sibling evidence
   through PRs #10, #108, #43, and #58.
4. Treat graph-engine PR #59 as the closed #55 holdings-only algorithm handoff.
5. Treat M4.8 proof as closed through
   `reports/stabilization/m4-8-entity-resolution-proof-20260507.md`.
6. Treat production hardening prerequisites and guards as landed through
   `reports/stabilization/holdings-production-hardening-prereqs-20260507.md`.
7. Enter gated canary/live production evidence review before any claim of
   production entity registry rollout, production queue propagation, live
   Neo4j graph propagation, or default/full propagation.

## Production Hardening Prerequisites Handoff - 2026-05-07

The following sibling guard work has landed after the bounded holdings live
graph and M4.8 entity-resolution proof closeouts:

- Entity-registry PR #61 merged as
  `ad00cb726ad0576330756f37bf2155a43e4b0e71`, adding the production
  readiness gate and evidence runner.
- Data-platform PR #110 merged as
  `74c12cd36b404882ec4425eea3f1b6a14fbfdf02`, adding Ex-3 `delta_id`
  idempotency, safe receipt behavior, targeted freeze controls, and worker
  rejection metrics.
- Graph-engine PR #61 merged as
  `dea63caeec89b16bbd89fb7d5a4174b677e2c394`, adding rollout guard, canary,
  and evidence support without default propagation.
- Subsystem-sdk PR #44 merged as
  `82177a4627d2ce1ac59738da2a13c6e4baee3994`; release PR #45 bumped the
  release, and tag `v0.1.4` points at
  `8d18ccb1877d4243196412322654ab2e8e9d999a`.
- Subsystem-holdings PR #13 merged as
  `612bd5cda3c8054c06e5cbd51de66955a7f0ed58`, adding the production queue
  submit runner using SDK idempotent-required mode.

The combined handoff meaning is narrow: production hardening prerequisites
and guards have landed. The next state is still gated canary/live production
evidence, not a completed rollout.

This prerequisite handoff does not claim:

- production rollout complete;
- production queue propagation complete;
- production live graph propagation complete;
- production entity-registry rollout complete;
- default or full propagation enabled;
- M4.7 real-document completion;
- financial-doc scope;
- contracts subtype changes;
- new relation types;
- assembly execution of provider/backfill, queue worker, graph sync, or graph
  algorithm workloads.

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

M4.8 proof is now complete as a bounded evidence closeout. The closeout covers
deterministic exact/code/rule resolution, ambiguous fuzzy non-selection,
unresolved fail-closed behavior, `ResolutionCase` / audit payload shape,
contracts projection, and the `subsystem-holdings` public adapter boundary.
The focused fuzzy backend is `injected_fake`, not a real Splink production
rollout.

This M4.9 decision does not convert the M4.8 proof into production entity
registry rollout, production queue/live graph rollout, default/full
propagation, financial-doc scope, or contracts subtype work.

## Scope Exclusions

These exclusions do not negate the bounded live backfill and producer proof
evidence already merged through data-platform PR #107 and `subsystem-holdings`
PR #9, or the queue/freeze/promotion proof evidence merged through
data-platform PR #108, `subsystem-holdings` PR #10, `subsystem-sdk` PR #43,
graph-engine PR #58, and graph-engine #55 holdings-only algorithm evidence
merged through PR #59.

This decision does not:

- modify `data-platform`, `contracts`, `graph-engine`, or any sibling repo;
- add new data derivations, additional backfill, or raw-provider ingestion;
- add holdings-specific contract classes, subtypes, or relation contracts;
- claim production queue propagation or live Neo4j graph propagation;
- claim default full-propagation rollout;
- expand graph-engine #55 beyond holdings-only algorithms;
- add contracts subtype scope;
- claim financial-doc scope;
- claim that M4.7 is complete;
- claim production rollout from the M4.8 proof closeout;
- claim production rollout from the production hardening prerequisites;
- start `subsystem-financial-doc`.

## Evidence Hygiene

- Execution traces: not recorded.
- Secrets, database connection strings, and API keys: not recorded.
- Local filesystem paths: not recorded beyond this repo-relative report path.
- Contract files: not touched.
- Sibling repos: not touched.
