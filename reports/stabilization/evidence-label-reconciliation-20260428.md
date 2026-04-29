# Evidence Label Reconciliation — C1-C6 vs Filenames

- Date: 2026-04-28
- Scope: M0.4 per `ult_milestone.md` §M0.
- Mode: documentation only. No source code, no test code, no commits. Tushare remains a `provider="tushare"` adapter only.
- Authority precedence per milestone §0 evidence-naming note: "If older task packet labels disagree, use the file title and report body as the authority."

## 1. Why this exists

The C1-C6 audit task packets used short letter labels (C1...C6). The on-disk evidence reports use longer, topic-shaped filenames. Two of the six (C2 and C6) use different filename prefix conventions — one is anchored on the audit topic (`canonical-physical-...`) and the other is anchored on the blueprint phase tag (`p1-provider-neutral-...`). This document maps the two namespaces in one place so future handoffs do not invert the C2/C6 labels and do not silently re-create files under conflicting names.

## 2. Authoritative C1-C6 ↔ filename mapping

| Task label | On-disk filename (under `assembly/reports/stabilization/`) | One-line scope |
|---|---|---|
| C1 | `production-daily-cycle-gap-audit-20260428.md` | Inventory of `daily_cycle_job` 6 RUNTIME_BLOCKERS + 15-asset gap; audit-only |
| C2 | `canonical-physical-schema-alignment-audit-20260428.md` | Provider catalog vs canonical Iceberg/marts/writer/current-cycle alignment; reports the lineage-leak gap and proposes Reading B (lineage separation) as the target |
| C3 | `formal-serving-no-source-leak-hardening-plan-20260428.md` | Plan-only — no test code added; identifies that current detection is prefix-only and lineage fields are undetected at every boundary |
| C4 | `p3-p2-graph-consumption-audit-20260428.md` | L3/L4 same-cycle confirmed inside fixture only; production same-cycle bounded by C1; L6 has no explicit graph adapter |
| C5 | `p4-controlled-slice-caveat-closure-audit-20260428.md` | No `subsystem_submit_queue → candidate_queue` bridge code in repo; existing symbol-level reader at `p2_dry_run.py:1227` does NOT close Ex-3 semantic consumption |
| C6 | `p1-provider-neutral-canonical-promotion-readiness-20260428.md` | 13 candidate mappings re-derived; 11/13 missing at least one canonical PK column; PROMOTION READINESS only — no fetch enabled |

This is the only mapping. If a future hand-off cites either side and there is a conflict, the row above wins.

## 3. Naming convention drift, observed

Two prefix conventions are present today:

- **Topic-anchored**: `canonical-physical-...`, `formal-serving-...`, `production-daily-cycle-...`, `p3-p2-...`, `p4-controlled-...`. Used by C1, C2, C3, C4, C5.
- **Phase-anchored**: `p1-provider-neutral-...`. Used by C6 and a number of earlier P1 reports (`p1-p2-production-daily-cycle-proof-...`, `p1-provider-neutral-tushare-catalog-...`, `p1-provider-neutral-raw-canonical-runtime-...`).

C2 and C6 are the most likely to be inverted in handoff because both touch the canonical contract:

- C2 = `canonical-physical-schema-alignment-audit-...` — contract gap audit.
- C6 = `p1-provider-neutral-canonical-promotion-readiness-...` — promotion readiness for candidate mappings.

To minimise inversion risk, this document is the single authority for the C2 ↔ C6 mapping. The milestone's `Evidence naming note` (§0) endorses this approach: when the older task packet label disagrees with the file title, the file title and body win.

This reconciliation does NOT propose to rename any file. Renames would invalidate every prior cross-reference in `ult_milestone.md`, the C1 report, and the closure rollup, and would create a churn-only diff. The drift is recorded for awareness; the on-disk filenames stay as they are.

## 4. Cross-references the rest of the project relies on

These cross-reference points must continue to resolve without modification, regardless of the prefix drift:

- `ult_milestone.md` §1, §2, §3 evidence list (lines 7-26) names every C1-C6 file by exact filename — already correct.
- `closure-audits-c1-c6-handoff-20260428.md` (this M0 rollup) §2 names every C1-C6 file by exact filename — already correct.
- The C1-C6 reports themselves cross-reference each other:
  - C2 references C1 as the gating dependency for production proof of the alignment gap.
  - C3 references C2's lineage-separation migration as the gating dependency for §4.4 (`FORBIDDEN_PAYLOAD_FIELDS` extension).
  - C4 references C1's RUNTIME_BLOCKERS as the bound on production same-cycle consumption.
  - C5 references the prior `p4-controlled-live-bridge-...` and `p4-core-subsystem-vertical-slice-...` reports.
  - C6 references the prior `p1-provider-neutral-tushare-catalog-...` report.

No cross-reference today inverts C2 and C6.

## 5. Stale-evidence note (M0.2 in scope, deferred to inline annotation)

The 2026-04-27 reports referenced by `ult_milestone.md` (e.g., `frontend-raw-route-alignment-fix-20260428.md` is dated 2026-04-28 in filename but covers 2026-04-27 alignment work) carry their own status statements; this M0 round does NOT add separate supersession headers. The intent of M0.2 is satisfied by the C1-C6 reports' own "this audit does NOT upgrade prior PARTIAL" declarations and by the explicit rollup in `closure-audits-c1-c6-handoff-20260428.md` §3. If stronger annotation is needed (e.g., a `Superseded-by:` front-matter), it should be added as a separate gate-changing decision, not as part of this M0 reconciliation.

## 6. Hard-rule restatements (apply to this document)

- This document does NOT modify `project_ult_v5_0_1.md`.
- This document does NOT start P5 shadow-run.
- This document does NOT enter M2/M3/M4.
- This document does NOT enable production fetch.
- This document does NOT start compose.
- This document does NOT commit any forbidden files.
- This document does NOT run `git init`.
- This document does NOT push.
- Tushare remains a `provider="tushare"` adapter only.

## 7. Per-task handoff block

```
Task: M0.4 evidence label reconciliation
Repo(s): assembly
Output: /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/evidence-label-reconciliation-20260428.md
Validation: existence of every filename listed in §2 verified by ls (all six files exist under assembly/reports/stabilization/)
Per-subrepo git state: see closure-audits-c1-c6-handoff-20260428.md §9 (assembly: a7f19c5; data-platform: 330f6b4 with pre-existing dirty raw writer files; frontend-api: 0c24fad with pre-existing README.md edit; all other in-scope subrepos clean)
Dirty files added by this task: assembly/reports/stabilization/evidence-label-reconciliation-20260428.md (untracked)
Findings: 1 CONFIRMED (mapping is one-to-one), 0 PARTIAL, 0 INFERRED
Outstanding risks: prefix convention drift between C2 (topic-anchored) and C6 (phase-anchored) is documented but not fixed; rename would create churn-only diff and is intentionally deferred
Declaration: I did not modify project_ult_v5_0_1.md. I did not enter M2/M3/M4. I did not enable production fetch. I did not commit any forbidden files. I did not run `git init`. I did not push without approval. Tushare remains a provider=tushare adapter only.
```
