# Holdings Post-Canary Production Rollout Runbook

Status: `OPERATIONALIZATION_ONLY`

This runbook operationalizes the next gate after the holdings bounded gated
canary/live production evidence passed. It is a rollout operating procedure,
not a broader rollout claim and not a propagation default change.

## Allowed Current Claims

| Claim | Source |
|---|---|
| Production hardening prerequisites and guards have landed. | `reports/stabilization/holdings-production-hardening-prereqs-20260507.md` |
| Bounded gated canary/live production evidence passed. | `reports/stabilization/holdings-bounded-canary-live-production-evidence-20260507.md` |
| Current assembly next step is production rollout operationalization/runbook hardening. | `README.md`, `docs/PROGRESS.md` |
| The next runtime gate is a controlled opt-in/default propagation canary after this runbook, rollback, monitoring, ownership, audit, and fail-closed procedures are reviewable. | `README.md`, `docs/PROGRESS.md` |

## Operator Gates

Every gate below must be recorded in the evidence template before entering a
controlled canary. Missing, ambiguous, or stale evidence is a stop condition.

| Gate | Required operator evidence | Stop condition |
|---|---|---|
| Ownership and approval | Named operator, reviewer, approving owner, change window, rollback owner, and incident commander. | Any owner is missing or the approval is not bound to the exact canary window. |
| Scope lock | Relation set is limited to `CO_HOLDING` and `NORTHBOUND_HOLD`; unresolved entity alignment remains fail-closed. | Any new relation, contracts subtype, financial-doc scope, guarantee scope, related-party scope, or unresolved entity auto-selection appears. |
| Environment lock | Runtime is an explicit bounded canary environment with redacted settings only; shared/default resources are excluded from the evidence record. | A shared/default database, destructive reload, unredacted DSN, token, credential, local proof path, or raw payload body is present. |
| Execution lock | Propagation is explicit, bounded, reversible, and scoped to the approved canary window. | An unscoped propagation command, broad enablement flag, or `run_full_propagation` appears in the plan. |
| Observability lock | Evidence records readiness payloads, selected queue payloads, accepted/rejected receipts, worker accepted/rejected counts, targeted freeze counts, frozen reader counts, graph readback counts, missing edge ids, disallowed relation counts, and holdings algorithm diagnostics. | Any count is missing, graph readback has missing edge ids, disallowed relation count is nonzero, or worker rejected count is unexplained. |
| Rollback lock | Rollback checklist is completed before execution and re-checked after execution. | Any rollback action lacks an owner, trigger, verification method, or audit note. |
| Evidence hygiene lock | Evidence uses curated counts, statuses, and references only. | Runtime artifact files, parquet files, raw manifests, stdout/stderr/exitcode files, tokens, DSNs, credentials, raw payloads, or local proof paths are attached or committed. |

## Rollback Checklist

Complete this checklist before the controlled canary starts. Repeat the
verification steps after any rollback trigger fires.

| Step | Required action | Verification evidence |
|---|---|---|
| 1 | Pause or disable new holdings canary submissions for the approved scope. | Queue selected count stops increasing for the canary scope. |
| 2 | Stop canary worker processing for unprocessed holdings candidates. | Worker accepted/rejected counts stop changing after the rollback timestamp. |
| 3 | Prevent any additional targeted freeze for the canary cycle. | Frozen reader count stays at the rollback baseline. |
| 4 | Stop canary graph sync or promotion entry points for holdings deltas. | Graph readback edge count stays at the rollback baseline and no new missing/disallowed relation diagnostics appear. |
| 5 | Preserve existing frozen/readback evidence without committing runtime artifacts. | Curated evidence contains only redacted counts, statuses, references, and operator notes. |
| 6 | Record user-facing and downstream impact assessment. | Incident note states affected scope, duration, owner, and whether any downstream consumer action is required. |
| 7 | Re-open only through a new approval tied to a new bounded canary window. | New approval references this rollback record and the updated canary evidence template. |

Rollback triggers:

- Worker rejected count is nonzero without an approved explanation.
- Frozen reader count diverges from accepted queue receipt count.
- Graph readback count diverges from the approved expected count.
- Missing edge ids are nonzero.
- Disallowed relation count is nonzero.
- Any non-holdings relation, contracts subtype, financial-doc scope, guarantee
  scope, or related-party scope appears.
- Any DSN, token, credential, raw payload body, local proof path, stdout/stderr
  capture, exitcode file, parquet file, or raw manifest is introduced into
  evidence.

## Evidence Template Use

Use
`reports/stabilization/holdings-post-canary-rollout-evidence-template-20260508.md`
as the required evidence shape for the operationalization gate and the later
controlled canary. The template must remain `TEMPLATE_ONLY` until a reviewed
runtime evidence report replaces it.

The completed evidence must include:

- the allowed current claims table;
- operator gate outcomes with owners and timestamps;
- rollback checklist status before and after execution;
- observability counts and diagnostics;
- evidence hygiene review;
- explicit not-claimed boundaries.

## Not Claimed

- Broad production rollout complete.
- Production rollout complete.
- Default/full propagation enabled.
- Default full-propagation rollout.
- `run_full_propagation` execution.
- M4.7 real-document completion.
- M4.7/financial-doc complete.
- Financial-doc scope.
- Contracts subtype changes.
- New relation types beyond `CO_HOLDING` and `NORTHBOUND_HOLD`.
