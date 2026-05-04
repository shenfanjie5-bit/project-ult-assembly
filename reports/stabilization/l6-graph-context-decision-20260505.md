# M3.5 L6 Graph-Context Decision - 2026-05-05

This report records the M3.5 decision that unblocks M4.5 planning for
L6 graph-context injection. It is a decision artifact only; it does not close
M4.5 and does not change contracts or implementation code.

## Status

- M3.5 decision: recorded.
- M4.5 status: planned / not complete.
- Evidence type: docs-only architecture decision with a structured JSON
  sibling.
- Structured artifact:
  `reports/stabilization/l6-graph-context-decision-20260505.json`.

## Decision

M3.5 chooses `AlphaAnalysisContext.feature_bundle.graph_features` /
main-core-managed context as the allowed L6 graph context attach point for
M4.5.

M4.5 will let orchestrator/main-core inject sanitized Ex-3 graph-delta
summaries into reasoner input. The reasoner input may carry the sanitized
summary as part of the main-core-owned alpha analysis context, not as a
reasoner-runtime-owned graph reader.

## Boundary

- `reasoner-runtime` must not import `graph-engine` or `data-platform`.
- `reasoner-runtime` must not read raw Ex-3 tables or queue tables directly.
- `contracts` remain unchanged.
- No holdings-specific subtype is introduced.
- No financial-doc scope is introduced.
- No `graph-engine #55` algorithms are included in this decision.

## Implementation Implication

M4.5 should keep the graph-context path on the orchestrator/main-core side:

```text
public Ex-3 graph-delta evidence
  -> orchestrator/main-core sanitization
  -> AlphaAnalysisContext.feature_bundle.graph_features
  -> reasoner input
```

The reasoner boundary stays provider-focused. It receives sanitized context
from main-core; it does not discover, load, or compute graph deltas.

## Scope Exclusions

This decision does not:

- mutate historical evidence reports;
- alter Ex-3 or recommendation contracts;
- add holdings-specific contract classes or subtypes;
- start subsystem-financial-doc;
- adopt graph-engine propagation or algorithm work from `graph-engine #55`;
- prove M4.5 end-to-end runtime behavior.

## Evidence Hygiene

- Raw logs: not recorded.
- Secrets, DSNs, API keys, bearer tokens: not recorded.
- Contract files: not touched.
