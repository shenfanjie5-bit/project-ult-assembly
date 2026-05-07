# M4.8 Entity Resolution Proof Closeout - 2026-05-07

This report records the assembly handoff for the M4.8 entity-resolution proof.
It aggregates already-merged sibling evidence and updates the downstream M4.9
handoff boundary. It is an evidence closeout only: it does not change
contracts, does not run production registry rollout, and does not claim
production queue or live graph rollout.

## Status

- M4.8 proof status: complete for deterministic and fail-closed
  entity-resolution evidence.
- Evidence type: merged sibling PR evidence plus assembly documentation
  aggregation.
- M4.7 status: parked; representative real-document validation remains open.
- M4.9 status: handoff updated; production rollout hardening may be planned
  only after this M4.8 proof boundary.

## Repository Evidence

| Repository / scope | PR | Merge SHA | Evidence meaning |
|---|---:|---|---|
| entity-registry | #60 | `6debd8cc137ee57572fd862959cd845c6dffcab5` | Focused entity-resolution proof merged. |
| subsystem-holdings | #12 | `11c1b1cf62be32c49940293c2e04e89d93ae1ecc` | Holdings producer integration with registry-backed boundary merged. |
| holdings live graph proof | #62 | `3736799bf362970670b0769e363c75bc15123f79` | Holdings live graph proof evidence merged as adjacent handoff context. |

## Covered Cases

The merged entity-registry proof covers:

- deterministic exact alias resolution;
- deterministic code resolution;
- deterministic rule resolution;
- ambiguous fuzzy candidates are not selected automatically;
- unresolved entities fail closed;
- `ResolutionCase` and audit payload shape are covered;
- contracts projection remains covered without changing contracts.

The fuzzy backend used for the focused proof is `injected_fake`. This report
does not claim a real Splink production backend rollout.

## Subsystem-Holdings Integration Boundary

The merged `subsystem-holdings` integration remains bounded to the public
entity-registry surface:

- `EntityRegistryAdapter` uses only public `lookup_alias` and
  `lookup_entity_refs` calls.
- Unresolved entities fail closed before graph-delta submission.
- SDK entity preflight provides a second protection layer before queue submit.
- The integration does not change contracts, subtype definitions, or relation
  contracts.
- The producer boundary remains read-only with respect to upstream canonical or
  mart outputs and does not introduce provider/raw-source reads here.

## Not Claimed

This closeout explicitly does not claim:

- production entity registry rollout;
- production queue or live graph rollout;
- production live Neo4j graph propagation;
- default or full propagation rollout;
- M4.7 real-document completion;
- financial-doc scope;
- contracts subtype work;
- real Splink production backend rollout;
- provider/backfill execution from assembly;
- provider payload contents, database connection string, or local path values.

## M4.9 Handoff Update

M4.8 proof is now complete as a bounded evidence closeout. The next M4.9 work
may plan production rollout hardening for entity registry, queue propagation,
live graph propagation, and default/full propagation, but those are future
planning items and are not claimed by this report.

M4.7 remains parked until representative A-share real-document parsing and
extraction are accepted under its own milestone criteria.

## Validation

| Command | Result |
|---|---|
| `.venv-py312/bin/python -m pytest -q tests/release/test_docs.py tests/registry/` | PASS; 73 tests collected and the quiet run completed with all dots green. |
| docs-specific test discovery | PASS; no additional docs-specific tests exist beyond `tests/release/test_docs.py` in this checkout. |
| `git diff --check origin/main...HEAD` | PASS; no whitespace errors. |
| `git diff --check` | PASS; no whitespace errors. |
| Added-line hygiene scan for environment files, credentials, connection-string patterns, provider payload contents, local path values, build-log markers, and concrete code identifiers | PASS; no matches. |
