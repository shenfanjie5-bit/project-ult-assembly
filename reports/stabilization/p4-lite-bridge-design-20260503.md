# P4 Lite Bridge Design - 2026-05-03

## Status

DECISION RECORDED for M4.1. This report closes the bridge strategy decision
and defines the implementation proof expected for M4.2-M4.4. It does not by
itself close the live PostgreSQL queue/freeze smoke.

Live proof addendum: M4.3/M4.4 PostgreSQL evidence was produced on 2026-05-03
and is recorded in `m4-bridge-live-proof-20260503.md` plus
`m4-ex3-queue-promotion-proof-20260503.json`.

## Decision

Use a direct SDK backend named `data_platform_queue` for production-relevant
Lite submission:

```text
producer payload
  -> subsystem-sdk SubmitClient validation
  -> SDK strips ex_type / semantic / produced_at
  -> data_platform_queue builds {payload_type, submitted_by, ...wire_payload}
  -> data_platform.queue.api.submit_candidate(payload)
  -> data_platform.candidate_queue
```

Rejected alternatives:

- Do not overload `lite_pg`: it remains the legacy SDK-local
  `subsystem_submit_queue` adapter for dev/local tests.
- Do not add a transfer worker from `subsystem_submit_queue` to
  `data_platform.candidate_queue`; this would preserve a non-production queue
  as an unnecessary intermediate boundary.
- Do not change `data_platform.queue.api.submit_candidate(payload)`; the SDK
  bridge adapts to its current envelope requirement.

## Public Boundary

- `subsystem-sdk` owns validation and producer-side dispatch.
- `data-platform` owns queue storage, PostgreSQL DSN resolution, validation
  worker, freeze, and `candidate_queue` ingest metadata.
- `contracts` remains unchanged; Ex-3 continues to use
  `Ex3CandidateGraphDelta` / `CandidateGraphDelta`.
- `graph-engine` remains a consumer; M4.4 proves existing
  `PostgresCandidateDeltaReader` and `promote_graph_deltas`.

## Acceptance Evidence

M4.2 is accepted when a controlled SDK Ex payload reaches an injected
`submit_candidate` as a data-platform queue envelope and returns a
transport-neutral receipt.

M4.3 is accepted only when live PostgreSQL tests or smoke run without skips and
prove:

```text
submit_candidate -> validate_pending_candidates -> freeze_cycle_candidates
```

M4.4 is accepted when
`assembly/scripts/m4_ex3_queue_promotion_proof.py` records a successful
candidate_queue Ex-3 row flowing through:

```text
PostgresCandidateDeltaReader -> CandidateGraphDelta -> promote_graph_deltas
```

If `DATABASE_URL` / `DP_PG_DSN` is unavailable in another environment, M4.2
can pass with injected tests, but M4.3/M4.4 live proof must be treated as
blocked there until the same live evidence is rerun.

## Issue Handling

Current open GitHub issues are not prerequisites for M4.1-M4.4. After the
bridge closes, execute data-platform #96 first, then graph-engine #56. Keep
graph-engine #55, data-platform #94, subsystem-announcement #42, orchestrator
#113, and model-layer issues deferred until their upstream gates are met.
