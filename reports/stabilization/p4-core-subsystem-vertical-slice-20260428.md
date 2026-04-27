# P4 Core Subsystem Vertical Slice Evidence - 2026-04-28

## Verdict

Status: PASS for the controlled P4 core subsystem vertical slice.

This is a controlled backend slice. It does not claim external news ingestion,
Polymarket production flow, a frontend write API, sidecar/API-6 promotion,
Docling/LlamaIndex model download, or P5 readiness.

## Scoped Repos And Commits

- subsystem-sdk: `97b0f67e642d9fbf7b052d58577ba7c3cdade8b4`
  - Push: `origin/main` updated.
  - Added `tests/integration/test_p4_core_vertical_slice.py`.
  - Proves Ex-1, Ex-2, Ex-3, and Ex-0 heartbeat validate through the SDK,
    write Lite PG queue rows, strip SDK envelope fields before queue insert,
    and return transport refs as the submit audit trail.
  - Production entity preflight uses live entity-registry lookup and blocks an
    unresolved Ex-3 event node before any queue insert.

- entity-registry: `a38944533a2aae2191ee07e699156453a5bf708d`
  - Push: `origin/main` updated.
  - Added deterministic event entity IDs and `anchor_event_entity(...)`.
  - Event entities use `ENT_EVENT_*`, require an anchor code, persist
    idempotently, and are visible to `lookup_entity_refs(...)`.

- subsystem-news: `c27f044ebb97646fe583dfa5e1a737f62903f647`
  - Push: `origin/main` updated.
  - Strengthened the controlled milestone-4 graph pipeline assertion to prove
    the controlled example submits Ex-1 fact, Ex-2 signal, and Ex-3 graph
    delta candidates together.

- subsystem-announcement: `36555beb69ce565ee9a8d2b0f926a01158c32335`
  - Push: `origin/main` updated.
  - Locked the controlled graph pipeline proof to anchored `ENT_*` refs for
    Ex-2 affected entities and Ex-3 source/target nodes.

## Slice Proof

- Public Ex contract:
  - Existing Ex-0..Ex-3 public contract suites still pass for SDK, news,
    announcement, and entity-registry.
  - SDK queue payloads are validated against `contracts.schemas.Ex*` and
    heartbeat validates against `Ex0Metadata`.

- Controlled subsystem examples:
  - News controlled milestone-4 pipeline submits Ex-1, Ex-2, and Ex-3.
  - Announcement controlled graph pipeline submits Ex-1, Ex-2, and Ex-3 in
    order, with Ex-2/Ex-3 gated on accepted Ex-1 source facts.

- Live entity-registry lookup:
  - Production SDK profile uses the configured entity-registry repository.
  - Anchored stock and event nodes pass.
  - Unresolved Ex-3 event refs fail closed before Lite PG dispatch.

- Lite PG Layer B boundary:
  - Controlled Ex-1, Ex-2, Ex-3, and Ex-0 heartbeat each produce queue rows.
  - Queue rows carry wire shape only: no `ex_type`, `semantic`, or
    `produced_at` SDK envelope fields.
  - Receipts carry public `transport_ref` values and no backend-private
    `pg_queue_id` leakage.

- Anchoring-first event node:
  - `entity-registry` now mints deterministic event entity IDs from
    `(namespace, event_key)`.
  - The SDK vertical slice anchors the event first, then emits Ex-3 with
    `source_node=<anchored ENT_EVENT_*>` and `target_node=<anchored stock>`.

## Validation Commands

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/entity-registry
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/entity-registry/src:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest -q \
  tests/test_core.py tests/test_event_anchors.py tests/test_lookup_entity_refs.py

result: pass, exit code 0
```

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/subsystem-sdk
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/subsystem-sdk:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src:/Users/fanjie/Desktop/Cowork/project-ult/entity-registry/src \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest -q \
  tests/integration/test_p4_core_vertical_slice.py \
  tests/backends/test_lite_pg_backend.py \
  tests/backends/test_lite_pg_heartbeat_backend.py \
  tests/submit/test_client_preflight.py

result: pass, exit code 0
```

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/subsystem-news
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/subsystem-news/src:/Users/fanjie/Desktop/Cowork/project-ult/subsystem-sdk:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest -q \
  tests/integration/test_milestone4_graph_pipeline.py \
  tests/integration/test_sdk_wire_shape_integration.py

result: pass, exit code 0
```

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/subsystem-announcement
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/subsystem-announcement/src:/Users/fanjie/Desktop/Cowork/project-ult/subsystem-sdk:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest -q \
  tests/test_graph_delta_pipeline.py \
  tests/test_pipeline_e2e.py \
  tests/integration/test_sdk_wire_shape_integration.py

result: pass, exit code 0
```

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/subsystem-sdk
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/subsystem-sdk:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src:/Users/fanjie/Desktop/Cowork/project-ult/entity-registry/src \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest -q \
  tests/contract tests/validate/test_entity_registry_wiring.py tests/test_package_layout.py

result: pass, exit code 0
```

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/entity-registry
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/entity-registry/src:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest -q \
  tests/contract tests/test_contracts_alignment.py tests/unit/test_public_entrypoints.py

result: pass, exit code 0
```

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/subsystem-news
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/subsystem-news/src:/Users/fanjie/Desktop/Cowork/project-ult/subsystem-sdk:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest -q \
  tests/contract tests/contract_stability/test_backend_config.py \
  tests/test_package_layout.py tests/smoke/test_public_smoke.py

result: pass, exit code 0
```

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/subsystem-announcement
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/subsystem-announcement/src:/Users/fanjie/Desktop/Cowork/project-ult/subsystem-sdk:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest -q \
  tests/contract tests/contracts tests/unit/test_public_entrypoints.py \
  tests/smoke/test_public_smoke.py

result: pass, exit code 0
```

## Lint

```text
/opt/homebrew/bin/ruff check changed files in entity-registry, subsystem-sdk,
subsystem-news, and subsystem-announcement

result: pass, exit code 0
```

## Dirty Files

- subsystem-sdk: clean after commit and push.
- subsystem-news: clean after commit and push.
- subsystem-announcement: clean after commit and push.
- entity-registry: clean after commit and push.
- assembly: this evidence file added in a separate commit.

## Findings

- P0: none.
- P1: none.
- P2: none.
- P3: one validation command was initially invoked in subsystem-news with a
  non-existent `tests/unit/test_public_entrypoints.py` path. The command was
  corrected to existing public/contract paths and passed. This was a command
  path typo, not a code failure.
- P3: independent review confirmed the Ex-3 unresolved-ref block path uses the
  production/default live entity-registry lookup. Ex-2 unresolved-ref blocking
  is covered through the same preflight path with an injected lookup, not a
  separate default `LiveEntityRegistryLookup` test.
- P3: independent review confirmed frontend-api, graph-engine, and
  reasoner-runtime read-only artifact lanes pass separately, but this P4 slice
  does not prove a live graph/reasoner/frontend end-to-end path.

## Residual Risk

- The slice is controlled and local. It proves the backend contract and queue
  boundary, not production external news, Polymarket, or model-backed parsing.
- The Lite PG proof uses an injected recording connection factory rather than
  a live PostgreSQL instance, matching the current SDK adapter test pattern.
- The next P4 hardening gate should add a direct Ex-2
  default-live-entity-registry unresolved-ref block test and a live PostgreSQL
  Layer B queue proof when a DSN is available.
- The graph/reasoner/frontend-api read-only path remains artifact-backed
  adjunct evidence. It should not be counted as live P4 end-to-end until a
  downstream proof consumes this slice's Ex-3 output through graph-engine and
  reasoner-runtime into frontend-api artifacts.
