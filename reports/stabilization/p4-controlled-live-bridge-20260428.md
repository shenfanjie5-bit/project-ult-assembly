# P4 Controlled Live Bridge Hardening - 2026-04-28

## Status

PARTIAL PASS for the scoped P4 hardening gate. This closes the direct
production-default Ex-2 unresolved-ref block-path and adds an SDK-local
same-cycle read-only projection scaffold. It is not a full live PG,
graph-engine, reasoner-runtime, or frontend-api end-to-end proof.

## What Changed

- `subsystem-sdk`: `5f131237df9101bde0a41293df151f6f9ea47fe7`
- `subsystem-sdk` now directly tests `SubmitClient(...,
  entity_preflight_profile="production")` with the default
  `LiveEntityRegistryLookup`: unresolved Ex-2 entity refs are rejected before
  PG dispatch.
- The P4 vertical-slice test now records PG connection attempts, commits, and
  closed connections so pre-dispatch blocks prove no transport write happened.
- A controlled same-cycle scaffold preserves explicit `cycle_id`, `signal_id`,
  `delta_id`, canonical entity IDs, event entity ID, and evidence refs across
  SDK-local graph, reasoner-context, and frontend-read-model projection inputs.
  It does not treat `producer_context` as a public bridge contract.

## Validation

subsystem-sdk:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/subsystem-sdk
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/subsystem-sdk:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src:/Users/fanjie/Desktop/Cowork/project-ult/entity-registry/src \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest -q \
  tests/submit/test_client_preflight.py \
  tests/validate/test_entity_registry_wiring.py \
  tests/backends/test_lite_pg_backend.py \
  tests/integration/test_p4_core_vertical_slice.py
```

result:

```text
29 passed
```

entity-registry:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/entity-registry
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/entity-registry/src \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest -q \
  tests/test_lookup_entity_refs.py \
  tests/test_event_anchors.py \
  tests/contract/test_frontend_api_artifacts.py
```

result:

```text
5 passed
```

lint/checks:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/subsystem-sdk
/Users/fanjie/Desktop/Cowork/project-ult/subsystem-sdk/.venv/bin/python -m ruff check \
  tests/integration/test_p4_core_vertical_slice.py
git diff --check
```

result:

```text
All checks passed
```

## Remaining Caveats

- The PG proof is SDK adapter/pre-dispatch coverage with an injected connection
  factory. It does not exercise a live PostgreSQL server.
- The bridge is a controlled scaffold over local read-only projection input
  shapes. It does not call graph-engine Phase 1, reasoner-runtime live LLM,
  frontend-api HTTP routes, external news, or Polymarket.
- No frontend write API, sidecar, API-6, Docling/LlamaIndex model download, or
  P5 shadow-run was introduced.

## Findings

- P0/P1/P2: none for the scoped hardening gate.
- P3: full P4 live bridge remains open until the same-cycle Ex-3 output is
  consumed by graph-engine, reasoner-runtime, and frontend-api read-only routes
  in one live backend proof.
