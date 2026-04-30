# M4.7 — Docling/LlamaIndex offline preflight

## Status

**M4.7 status: PARTIAL / PREFLIGHT ARTIFACT.** This does **not** close
M4.7 and must not be recorded as PASS.

The current artifact proves only that subsystem-announcement's synthetic
manifest contract can run offline through the parser boundary,
chunker, and one LlamaIndex vector-index path without entering the
daily-cycle critical path. It does **not** prove the milestone criterion
of "10-20 representative A-share docs parsed offline" because real
Docling parsing was skipped in this environment and the fixtures are
small synthetic stubs, not representative documents.

M4.7 should remain partial until the milestone owner accepts this as a
preflight-only artifact or a later run supplies representative documents
and real Docling parse evidence. It also should not be promoted ahead of
the unresolved M4.1 bridge strategy decision unless the milestone owner
explicitly decides that M4.7 can close independently.

## What Ran

Focused file:

- `subsystem-announcement/tests/integration/test_docling_llamaindex_offline_preflight.py`

The file contains **7 tests**:

1. Manifest sample-count and attachment-type coverage guard.
2. Synthetic manifest samples through `parse_announcement` with a fake
   `docling.document_converter.DocumentConverter`.
3. Synthetic successful samples through `chunk_parsed_artifact`.
4. Real Docling package/version availability check.
5. Real `llama-index-core` package/version availability check.
6. One synthetic successful sample through `build_vector_index` with
   mock embeddings and real LlamaIndex persistence.
7. Balanced success/corrupt fixture coverage across pdf/html/word.

## Current Evidence

Focused M4.7 run in the local subsystem-announcement venv:

```text
$ cd /Users/fanjie/Desktop/Cowork/project-ult/subsystem-announcement
$ PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
    tests/integration/test_docling_llamaindex_offline_preflight.py -v
6 passed, 1 skipped
```

The skipped test is
`test_real_docling_package_is_installed_and_version_resolves`. In this
environment the real `docling` package is not installed, so the test
explicitly skips instead of forcing a heavy install. Therefore this
artifact contains **no real Docling parse proof**.

The LlamaIndex side is stronger than the Docling side: the focused run
does resolve the installed `llama-index-core==0.10.0` package and builds
a real `SimpleVectorStore` persistence artifact using mock embeddings.
That still rests on a synthetic parse artifact produced by the fake
Docling boundary.

## Fixture Scope

The manifest at
`subsystem-announcement/tests/fixtures/announcements/manifest.json`
contains 13 samples: 10 expected-success fixtures and 3 expected-corrupt
fixtures. These samples are useful for a deterministic manifest-contract
smoke, including positive and negative parser-path assertions.

They are **not representative A-share documents**:

- They are tiny synthetic files, roughly 80-260 bytes.
- The Docling result is synthesized by a test double.
- The test double asserts the parser boundary contract, not Docling's
  real document understanding.
- Passing this manifest smoke cannot be used as evidence that real
  production PDFs, HTML filings, or Word attachments parse correctly.

## Subsystem Scope

Only subsystem-announcement is exercised by this artifact.

subsystem-news was previously scoped out based on local dependency
inspection, but that is **not** a milestone decision. Whether M4.7
requires subsystem-news evidence remains unresolved and should be
tracked as a separate milestone-owner decision. This document does not
declare subsystem-news out of scope.

## What This Proves

- The synthetic 13-sample manifest is stable and covers pdf/html/word
  success and corrupt paths.
- subsystem-announcement can run the synthetic parser-boundary smoke
  offline without production fetch, network, LLM calls, or daily-cycle
  coupling.
- The chunker emits chunks for all synthetic expected-success samples.
- The local LlamaIndex dependency and vector-store persistence path are
  exercised with mock embeddings.

## What This Does Not Prove

- No real Docling parse ran in this environment.
- No representative A-share PDF/HTML/Word document parse is proven.
- No subsystem-news M4.7 decision is made.
- No M4.1 bridge strategy decision is made.
- No subsystem-announcement to subsystem-sdk or data-platform bridge is
  exercised.
- No production fetch or production source-code path is introduced.

## Updated M4 Task Status

| # | Task | Current status |
|---|---|---|
| M4.1 | Bridge strategy decision | Blocked / unresolved PM decision |
| M4.2 | Lite bridge implementation proof | Blocked on M4.1 |
| M4.3 | Live PG queue/freeze smoke | Blocked on M4.2 |
| M4.4 | Ex-3 semantic graph bridge | Blocked on M4.3 |
| M4.5 | Ex-3 semantic reasoner bridge | Blocked on M4.3 + M3.5 |
| M4.6 | Ex-3 frontend read-only proof | Blocked on M4.4 + M4.5 |
| M4.7 | Docling/LlamaIndex offline preflight | **PARTIAL / PREFLIGHT ARTIFACT, not PASS** |
| M4.8 | Entity resolution full proof | Blocked on M4.2 |
| M4.9 | Core subsystem scope decision | Blocked / unresolved PM decision |

## Hard-Rule Declarations

- `project_ult_v5_0_1.md` unchanged.
- The original M4.7 round did not change `ult_milestone.md`; the current
  dependency remains unresolved rather than closed by this preflight.
- No M4.1-M4.6 implementation work in this round.
- No production fetch.
- No production source-code changes.
- No forced Docling install.
- No subsystem-news source changes.
- No `/Users/fanjie/Desktop/BIG/FrontEnd/**` changes.
- The compose stack was not started or modified.

## Required Follow-Up Before M4.7 PASS

- Obtain a milestone-owner decision on whether M4.7 can close
  independently of M4.1.
- Obtain a milestone-owner decision on whether subsystem-news requires
  M4.7 evidence or is formally out of scope.
- Run real Docling parsing on 10-20 representative A-share documents, or
  explicitly downgrade the milestone requirement to a synthetic
  preflight-only criterion.

## M4.7a vs M4.7 — milestone-table annotation

This section pins, in pushed evidence, the same status delta carried
by `ult_milestone.md` Section 4 (the M4.7a-vs-M4.7 annotation block
appended after the M4 task table) and Section 6 (the
`subsystem-announcement (m4-7-docling-llamaindex-preflight)` line).
`ult_milestone.md` is a workspace-root local-handoff artifact and is
**not** in any git repo; this section is the persistent record that
survives the local checkout.

### What M4.7a delivers

`M4.7a synthetic offline preflight artifact` — committed and pushed
across two repos:

- `subsystem-announcement` branch `m4-7-docling-llamaindex-preflight`,
  HEAD `c26ffad "M4.7 review fixes: mark preflight partial"`. Carries
  `tests/integration/test_docling_llamaindex_offline_preflight.py`
  with explicit PARTIAL / PREFLIGHT framing throughout the
  module docstring + per-test docstrings. Focused-suite count
  recorded at this round's verification: **6 passed, 1 skipped**
  (the skip is the real Docling availability check; in this venv
  the `docling` package is not installed because of the heavy
  `deepsearch-glm` build dep, and the test explicitly skips with a
  clear message rather than silently passing).
- `assembly` branch `m2-baseline-2026-04-29`, HEAD `8708850 "Evidence
  hygiene for M1-M4 review fixes"` (rewrote this very evidence file
  to PARTIAL/PREFLIGHT). The append below adds this annotation
  section as the next persistent record on top of that commit.

### What M4.7 still requires for PASS (verbatim with the milestone)

All three closure conditions must hold simultaneously; M4.7 is not
PASS until each is independently satisfied:

1. **M4.1 (Bridge strategy decision)** is closed by the milestone
   owner, **or** the milestone owner explicitly de-couples M4.7
   from M4.1. The milestone table still lists M4.7 as depending on
   M4.1; this round does not change that.
2. **subsystem-news scope decision.** Whether subsystem-news
   requires its own M4.7 evidence or is formally out-of-scope for
   M4.7 has been assumed but not decided. This evidence file
   previously asserted "out of scope" — that assertion is hereby
   downgraded to "unresolved pending milestone-owner decision".
3. **Real Docling parse on 10-20 representative A-share documents**
   (PDF / HTML / Word). The synthetic 80-260-byte fixtures in
   `subsystem-announcement/tests/fixtures/announcements/` do not
   satisfy this; the closure baseline forbids production fetch, so
   a curated representative-document regression fixture set must
   be made available in some other way before this can be proven.

### Hard rules (verbatim from codex's repair plan)

- Do NOT change M4.7's dependency on M4.1 in the milestone table.
- Do NOT force a Docling install (the build broke last time on
  `deepsearch-glm`).
- Do NOT add new production fetch.
- Do NOT fabricate representative documents.
- Do NOT change subsystem-news source.
- Do NOT change `/Users/fanjie/Desktop/BIG/FrontEnd/**`.

### Cross-reference

- `ult_milestone.md` Section 4 (M4 task table + the M4.7a-vs-M4.7
  annotation block immediately after).
- `ult_milestone.md` Section 6 (per-repo branch / status snapshot;
  the `subsystem-announcement` line carries the same partial-status
  framing).
- This file's `## Status` block (top): `PARTIAL / PREFLIGHT
  ARTIFACT`, `must not be recorded as PASS`.
- This file's `## What This Does Not Prove` and `## Required
  Follow-Up Before M4.7 PASS` blocks (above).

### Verification at this round

| Suite | Result |
|---|---|
| `subsystem-announcement` `pytest tests/integration/test_docling_llamaindex_offline_preflight.py` | 6 passed, 1 skipped (real Docling skip is the M4.7 status proof). |
| `subsystem-announcement` full `pytest -p no:cacheprovider` | 316 passed, 7 skipped, 0 failed. |
| `data-platform` `pytest tests/cycle/test_graph_phase1_adapters.py tests/integration/test_iceberg_canonical_graph_writer_live.py tests/ddl/test_iceberg_tables.py` | 42 passed, 0 failed (pythonpath rolled back to `["src"]`; `tests._graph_promotion_fakes` resolves via pytest rootdir-aware collection without needing a `tests/__init__.py`). |
| `main-core` `pytest tests/integration/test_graph_readonly_consumption.py tests/integration/test_graph_snapshot_round_trip_preflight.py` | 8 passed, 0 failed. |

These counts are recorded for traceability; they do **not**
constitute M4.7 closure (per the three closure conditions above).
