# Holdings Post-Canary Rollout Evidence Template - 2026-05-08

Status: `TEMPLATE_ONLY`

This template is for the production rollout operationalization gate and the
later controlled opt-in/default propagation canary. It records operator gates,
rollback readiness, monitoring, audit, and evidence hygiene. It is not a
runtime proof and is not a production rollout completion report.

## Allowed Current Claims

| Claim | Source evidence |
|---|---|
| Production hardening prerequisites and guards have landed. | `reports/stabilization/holdings-production-hardening-prereqs-20260507.md` |
| Bounded gated canary/live production evidence passed. | `reports/stabilization/holdings-bounded-canary-live-production-evidence-20260507.md` |
| Current next step is production rollout operationalization/runbook hardening. | `docs/runbook/holdings-post-canary-production-rollout.md` |
| Later canary work must be controlled, explicit, reversible, observable, auditable, and fail-closed. | `README.md`, `docs/PROGRESS.md` |

## Operator Gate Record

| Gate | Owner | Evidence status | Notes |
|---|---|---|---|
| Ownership and approval | `<owner>` | `<pending>` | Exact canary window and reviewer approval. |
| Scope lock | `<owner>` | `<pending>` | `CO_HOLDING` and `NORTHBOUND_HOLD` only; unresolved entities fail closed. |
| Environment lock | `<owner>` | `<pending>` | Redacted canary settings only; no shared/default resources in the evidence record. |
| Execution lock | `<owner>` | `<pending>` | Explicit bounded canary path only; no broad enablement command. |
| Observability lock | `<owner>` | `<pending>` | Readiness, queue, worker, freeze, frozen reader, graph readback, and algorithm diagnostics recorded as counts. |
| Rollback lock | `<owner>` | `<pending>` | Rollback triggers, owner, verification method, and audit note are complete. |
| Evidence hygiene lock | `<owner>` | `<pending>` | Curated counts, statuses, references, and operator notes only. |

## Rollback Checklist Record

| Step | Status | Evidence note |
|---|---|---|
| Pause or disable new holdings canary submissions. | `<pending>` | `<curated note>` |
| Stop canary worker processing for unprocessed candidates. | `<pending>` | `<curated note>` |
| Prevent additional targeted freeze for the canary cycle. | `<pending>` | `<curated note>` |
| Stop canary graph sync or promotion entry points. | `<pending>` | `<curated note>` |
| Preserve existing frozen/readback evidence without runtime artifacts. | `<pending>` | `<curated note>` |
| Record user-facing and downstream impact assessment. | `<pending>` | `<curated note>` |
| Re-open only through a newly approved bounded canary window. | `<pending>` | `<curated note>` |

## Observability Summary

| Metric | Value |
|---|---:|
| Readiness payloads | `<count>` |
| Selected queue payloads | `<count>` |
| Accepted queue receipts | `<count>` |
| Rejected queue receipts | `<count>` |
| Worker accepted | `<count>` |
| Worker rejected | `<count>` |
| Targeted freeze candidates | `<count>` |
| Frozen reader candidates | `<count>` |
| Graph expected readback edges | `<count>` |
| Graph actual readback edges | `<count>` |
| Missing edge ids | `<count>` |
| Disallowed relation types | `<count>` |
| Co-holding path count | `<count>` |
| Northbound path count | `<count>` |
| Impacted entity count | `<count>` |

## Audit And Incident Record

| Field | Value |
|---|---|
| Operator | `<name-or-role>` |
| Reviewer | `<name-or-role>` |
| Approving owner | `<name-or-role>` |
| Incident commander | `<name-or-role>` |
| Change window | `<start/end>` |
| Rollback owner | `<name-or-role>` |
| Rollback decision | `<not-needed / executed / blocked>` |
| User-facing impact | `<curated summary>` |
| Downstream impact | `<curated summary>` |

## Evidence Hygiene

Record only curated counts, statuses, merge references, review notes, and
operator decisions. Do not attach or commit runtime artifact files, parquet
files, raw manifests, stdout/stderr/exitcode files, tokens, DSNs, credentials,
raw payload bodies, provider responses, Neo4j dumps, local proof paths, or
machine-local environment files.

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
