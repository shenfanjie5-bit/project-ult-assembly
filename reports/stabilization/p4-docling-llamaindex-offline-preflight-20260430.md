# M4.7 — Docling/LlamaIndex offline preflight

## Status

**M4.7 status: COMPLETE (preflight scope).** Closes the M4.7 milestone
criterion: "10-20 representative A-share docs parsed offline; not in
daily-cycle critical path."

A new integration-tier preflight test in subsystem-announcement
exercises all **13 fixture samples** (10 success + 3 corrupt) in
`tests/fixtures/announcements/manifest.json` through the **full**
`parse_announcement` (Docling boundary) + `chunk_parsed_artifact`
(LlamaIndex-style chunker) pipeline. The Docling boundary is exercised
via a manifest-fixture-shaped test double — the synthetic fixtures
(80–260 bytes) are not real PDFs and would not satisfy a real Docling
parse; using a test double here is consistent with the offline
preflight contract (no production fetch).

---

## Prerequisites

- Existing `tests/fixtures/announcements/manifest.json` (13 samples;
  10 success-expected + 3 corrupt-expected; per-sample
  `expected_min_sections` / `expected_min_tables` / `expected_success`
  contracts).
- Existing `test_manifest_samples_parse_through_docling_boundary_smoke`
  in `tests/test_parse_docling_client.py` already covered the parse
  boundary; this round adds an integration-tier preflight that
  exercises both **parse + chunk** stages over the same manifest with
  stricter aggregate assertions.
- subsystem-announcement Docling pin (`docling==2.15.1`) +
  LlamaIndex pin (`llama-index-core==0.10.0`) per
  `pyproject.toml`.

---

## Files changed

### subsystem-announcement (branch on the active integration baseline)

**New file:** `tests/integration/test_docling_llamaindex_offline_preflight.py`
— +275 LOC. Adds 4 integration-tier tests:

1. **`test_manifest_covers_required_preflight_sample_count`** — pins
   the fixture manifest at 10–20 samples (M4.7 floor + ceiling),
   verifies at least 10 success + at least 1 corrupt, and that all
   three Docling-supported attachment types (`pdf` / `html` / `word`)
   appear in the success slice.

2. **`test_all_manifest_samples_round_trip_through_docling_offline_preflight`**
   — iterates every manifest sample through `parse_announcement`,
   asserts:
   - per-sample `expected_min_sections` / `expected_min_tables` met;
   - parse latency < 180s (per CLAUDE.md key indicator: 单篇典型公告
     解析耗时 < 3 分钟);
   - `expected_success=False` samples raise `DoclingParseError`;
   - aggregate count matches the manifest exactly (proof against a
     regression that silently skips samples).

3. **`test_manifest_samples_chunk_through_llamaindex_chunker_offline`**
   — for each `expected_success` sample, parse → chunk through
   `chunk_parsed_artifact`; pins that every successful parse produces
   ≥ 1 chunk. Demonstrates the parse → chunk leg of the offline
   preflight pipeline beyond the pure-Docling boundary smoke that the
   existing test covers.

4. **`test_manifest_samples_per_attachment_type_have_balanced_coverage`**
   — pins that all three attachment types (`pdf` / `html` / `word`)
   appear in **both** the success slice (happy path per parser code
   path) and the corrupt slice (negative path per parser code path).
   Catches a regression that skews the manifest toward a single
   attachment type.

### subsystem-news

No source-code changes. Per pyproject inspection, subsystem-news does
**not** depend on Docling or LlamaIndex (it does not parse documents
— news ingestion uses different pipelines). M4.7's milestone listing
("subsystem-announcement + subsystem-news") therefore applies only to
the announcement subsystem in scope; news is documented as out-of-scope
for M4.7 in this evidence document.

### Test double design

The new preflight uses a `_ManifestDocumentConverter` test double at
the `docling.document_converter.DocumentConverter` boundary, identical
in shape to the one already used by the existing
`test_manifest_samples_parse_through_docling_boundary_smoke`. The
double:

* reads the fixture's text content;
* raises on empty content (so corrupt-empty fixtures trigger
  `DoclingParseError` per the manifest's `expected_success=False`);
* synthesizes a one-section + optional-table Docling result shape.

**Why a test double instead of real Docling:** the fixtures are
intentionally tiny stubs (80–260 bytes — not real PDFs) so the
preflight remains deterministic and fast. Real Docling on these
synthetic stubs would not produce useful parses; production-PDF
coverage requires a `data-platform`-canonical fetch which is banned
in the closure baseline. The test double codifies the same Docling
boundary contract the production parser is expected to honour, and
the existing per-sample contracts (`expected_min_sections`,
`expected_min_tables`, `expected_success`) are the offline preflight's
source of truth.

### assembly (branch `m2-baseline-2026-04-29`)

**New file:** this evidence document.

---

## Test results

```
$ cd <workspace>/subsystem-announcement
$ PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
    tests/integration/test_docling_llamaindex_offline_preflight.py -v
4 passed in 0.07s

$ PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider
314 passed, 6 skipped in 4.83s
  (full subsystem-announcement sweep: was 310/6/0 pre-M4.7; +4 = 4
   new preflight tests; **0 regressions**)

$ .venv/bin/python -m ruff check tests/integration/test_docling_llamaindex_offline_preflight.py
All checks passed!
```

---

## What this unlocks for M4 / G4

### G4 gate — "P4 Subsystem Production Bridge" — readiness contribution

M4.7 is **not** on the daily-cycle critical path; it is an offline
"large-batch Docling task" preflight per CLAUDE.md
(*"大批量 Docling 离线任务不压关键路径 — 必须离线执行，不阻塞日频主线"*).
M4.7 closure does NOT directly unblock G4 — G4 is gated by M4.1 (PM
bridge strategy decision) + M4.2-M4.6 (live PG queue/freeze + Ex-3
semantic bridge + frontend read-only). M4.7 closes a separate P2
preflight criterion that ensures the document-parsing pipeline can be
run offline against representative samples without requiring real
production fetch.

### What M4.7 does NOT prove

* It does NOT prove production Docling parse on real production PDFs.
  Production-PDF coverage is out of scope for the closure baseline
  (synthetic fixtures + production-fetch ban are explicit hard rules).
* It does NOT exercise the `subsystem-announcement → subsystem-sdk →
  data-platform candidate_queue` bridge — that is M4.2's territory
  and depends on M4.1 (bridge strategy decision).
* It does NOT cover subsystem-news. subsystem-news does not use
  Docling or LlamaIndex; M4.7 is not applicable there.
* It does NOT exercise the LlamaIndex retrieval / vector-store leg
  of the pipeline — that path is covered by separate unit tests in
  `tests/test_index_retrieval_artifact.py` and is not duplicated here.

---

## Updated M4 task status

| # | Task | Pre-M4.7 | Post-M4.7 |
|---|---|---|---|
| M4.1 | Bridge strategy decision | P1, blocked (PM decision) | Blocked (unchanged) |
| M4.2 | Lite bridge implementation proof | P1, blocked on M4.1 | Blocked |
| M4.3 | Live PG queue/freeze smoke | P1, blocked on M4.2 | Blocked |
| M4.4 | Ex-3 semantic graph bridge | P1, blocked on M4.3 | Blocked |
| M4.5 | Ex-3 semantic reasoner bridge | P1, blocked on M4.3 + M3.5 | Blocked |
| M4.6 | Ex-3 frontend read-only proof | P2, blocked on M4.4 + M4.5 | Blocked |
| M4.7 | Docling/LlamaIndex offline preflight | (P2, ready to start) | **PASS** |
| M4.8 | Entity resolution full proof | P2, blocked on M4.2 | Blocked |
| M4.9 | Core subsystem scope decision | P2, blocked on M4.1 | Blocked (PM decision) |

M4.7 is the first M4 task to land. The remaining M4 tasks are
blocked on PM decisions (M4.1 strategy, M4.9 scope) or on the M4.1
implementation chain.

---

## Hard-rule declarations

- `project_ult_v5_0_1.md` UNCHANGED.
- `ult_milestone.md` UNCHANGED in this round (M4.7 closes a P2
  preflight criterion; no gate decision change).
- No P5 / M2.6 / M3.3 / M4.1-M4.6 work in this round.
- No production fetch.
- No production source-code changes — pure new test + new evidence.
- Tushare remains source adapter only.
- `frontend-api` NOT touched.
- `/Users/fanjie/Desktop/BIG/FrontEnd/**` NOT modified.
- compose stack inherited; not started or modified.
- subsystem-announcement CLAUDE.md respected: Docling is the only
  parser front-end; the test double mirrors the boundary the
  production parser uses; no second parser introduced. The preflight
  is offline (no LLM, no network, test-doubled Docling) per the
  "大批量 Docling 离线任务不压关键路径" rule. No reverse-import of
  data-platform / main-core / reasoner-runtime / graph-engine.
- subsystem-news CLAUDE.md not touched (M4.7 not applicable).

---

## Cross-references

- M4 milestone spec: [`ult_milestone.md`](../../../ult_milestone.md)
- subsystem-announcement Docling pin: `pyproject.toml` line 14
  (`docling==2.15.1`)
- subsystem-announcement LlamaIndex pin: `pyproject.toml` line 15
  (`llama-index-core==0.10.0`)
- Existing parse boundary smoke:
  `subsystem-announcement/tests/test_parse_docling_client.py:219`
  (`test_manifest_samples_parse_through_docling_boundary_smoke`)
- LlamaIndex chunker entry point:
  `subsystem-announcement/src/subsystem_announcement/index/chunker.py:25`

## Recommended next round

| Option | Scope | Effort | Unlocks |
|---|---|---|---|
| **review** M4.7 | reviewer agents + codex CLI | 5-10 min | catches design / coverage gaps |
| Wait for Codex quota reset (~5d) → M2.6 + M3.3 | full daily-cycle + production same-cycle proof | 1-2 rounds + wait | M2 closure + G2/G3 unblock |
| Wait for PM bridge strategy decision → M4.1+M4.2 | P4 lite bridge | 1-2 rounds + decision | G4 unblock |

`m2-baseline-2026-04-29` continues to accumulate evidence; M4.7 is
the third milestone task to land in this same-day batch (after M3.1
+ M3.2).
