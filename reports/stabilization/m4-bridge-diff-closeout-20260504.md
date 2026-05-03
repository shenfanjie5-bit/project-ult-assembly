# M4 Bridge Diff Closeout - 2026-05-04

This note records the post-live-proof closeout state for the M4.1-M4.4 bridge
diff. It does not expand scope into holdings implementation.

## Status

- M4.1 bridge decision: direct SDK backend `data_platform_queue`.
- M4.2 bridge implementation: SDK validates Ex payloads, prepares the
  data-platform queue envelope, and calls `data_platform.queue.api.submit_candidate`
  through lazy import or injection.
- M4.3 live PG queue/freeze evidence: produced on 2026-05-03 via
  non-skipped `make smoke-p1c` against `dp_p1c_smoke_m4bridge`.
- M4.4 live Ex-3 graph proof: produced on 2026-05-03 via
  `scripts/m4_ex3_queue_promotion_proof.py` against
  `m4_bridge_proof_20260503`.
- Evidence files:
  - `m4-bridge-live-proof-20260503.md`
  - `m4-ex3-queue-promotion-proof-20260503.json`

## Diff Hygiene

- The unrelated data-platform dbt runtime log path is ignored via
  `src/data_platform/dbt/logs/`.
- The bridge diff intentionally spans `subsystem-sdk`, `data-platform`,
  `assembly`, and README status notes in `graph-engine` /
  `subsystem-announcement`.
- No database password or raw DSN is stored in reports; proof JSON records
  `database_url` as `<redacted:set>`.

## Issue Queue

- `contracts #81` was closed as `not planned` on 2026-05-04 because its
  Ex-3 subtype expansion design conflicts with the current holdings-first
  interface decision.
- Next implementation issue remains `data-platform #96`.
- After #96, execute `graph-engine #56`.
- Keep graph-engine propagation algorithms and financial-doc schema work gated
  behind those prerequisites.

## Next Gate

Before starting `data-platform #96`, review this bridge diff as a unit and keep
the public-interface decision intact:

```text
holdings producers -> existing Ex-3 graph delta contract -> data_platform_queue
```

Do not add holdings-specific contracts classes in this phase.
