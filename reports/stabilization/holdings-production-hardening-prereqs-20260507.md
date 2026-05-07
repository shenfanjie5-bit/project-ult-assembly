# Holdings Production Hardening Prerequisites - 2026-05-07

Status: `PREREQUISITES_AND_GUARDS_LANDED`

This report aggregates the assembly handoff after the bounded M4.8 / M4.9
proofs and the sibling production-hardening guard work landed. It is an
assembly docs/evidence handoff only. It does not change contracts, does not
run production workloads, and does not declare production rollout complete.

## Summary

Production hardening prerequisites and guards are now landed across the
relevant sibling repos:

- Entity-registry has a production readiness gate and evidence runner.
- Data-platform has queue idempotency, safe receipt, targeted freeze, and
  worker rejection metrics.
- Graph-engine has rollout guard, canary, and evidence plumbing with no
  default propagation.
- Subsystem-sdk has the idempotent-required queue submission support released
  in `v0.1.4`.
- Subsystem-holdings has a production queue submit runner using the SDK
  idempotent-required mode.

The historical next step for this prerequisite report was gated canary/live
production evidence and independent review. That bounded evidence has since
passed in assembly #66 and is recorded in
`reports/stabilization/holdings-bounded-canary-live-production-evidence-20260507.md`.
The current next step is production rollout operationalization/runbook
hardening, followed by a controlled opt-in/default propagation canary. This
report still claims only that the prerequisites and guards have landed.

## Landed Inputs

| Repo | Merged input | Handoff meaning |
|---|---|---|
| `entity-registry` | PR #61, merge `ad00cb726ad0576330756f37bf2155a43e4b0e71` | Production readiness gate and evidence runner are available for the entity-registry rollout path. |
| `data-platform` | PR #110, merge `74c12cd36b404882ec4425eea3f1b6a14fbfdf02` | Ex-3 `delta_id` idempotency, safe receipt behavior, targeted freeze controls, and worker rejection metrics are landed. |
| `graph-engine` | PR #61, merge `dea63caeec89b16bbd89fb7d5a4174b677e2c394` | Rollout guard, canary, and evidence support are landed; default propagation remains off. |
| `subsystem-sdk` | PR #44, merge `82177a4627d2ce1ac59738da2a13c6e4baee3994`; release PR #45 merged; tag `v0.1.4` target `8d18ccb1877d4243196412322654ab2e8e9d999a` | SDK queue submission can require idempotency, and the version bump is released for downstream producer use. |
| `subsystem-holdings` | PR #13, merge `612bd5cda3c8054c06e5cbd51de66955a7f0ed58` | Holdings production queue submit runner uses the SDK idempotent-required mode. |

## Boundary

This handoff keeps the existing M4.9 boundary:

- `subsystem-holdings` reads data-platform canonical or mart outputs only.
- `subsystem-holdings` submits existing Ex-3 graph deltas through
  `subsystem-sdk`.
- Entity alignment must remain fail-closed when unresolved.
- Relation scope remains limited to existing holdings relations already
  covered by the bounded proof handoff.
- Assembly does not execute provider backfill, queue workers, graph sync, or
  graph algorithms in this PR.
- Contracts remain unchanged.

## Explicitly Not Claimed

This report does not claim:

- production rollout complete;
- production queue propagation complete;
- production live graph propagation complete;
- production entity-registry rollout complete;
- default or full propagation enabled;
- M4.7 real-document validation complete;
- financial-doc scope;
- contracts subtype changes;
- new relation types;
- raw provider ingestion, provider backfill, or production workload execution
  from assembly.

## Tests And CI Summary

Curated sibling status:

- Entity-registry PR #61 is merged with the production readiness gate and
  evidence runner.
- Data-platform PR #110 is merged with idempotency, safe receipt, targeted
  freeze, and rejection metrics guards.
- Graph-engine PR #61 is merged with rollout guard, canary, and evidence
  support while default propagation remains disabled.
- Subsystem-sdk PR #44 and release PR #45 are merged; tag `v0.1.4` is
  available at the recorded tag target.
- Subsystem-holdings PR #13 is merged with the production queue submit runner
  on SDK idempotent-required mode.

Assembly validation for this PR:

- Passed:
  `.venv-py312/bin/python -m pytest -q tests/release/test_docs.py tests/registry/`
- Passed:
  `git diff --check origin/main...HEAD && git diff --check`
- Passed: hygiene scan over files touched by this PR.

## Evidence Hygiene

This report intentionally records only curated merge facts and bounded handoff
meaning. It does not include secrets, DSNs, local runtime paths, raw provider
payloads, concrete security or fund codes, dbt logs, Neo4j dumps, or
production execution traces.
