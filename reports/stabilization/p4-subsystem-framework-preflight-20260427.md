# P4 Subsystem Framework Preflight Evidence - 2026-04-27

## Verdict

Status: PASS for the scoped P4 subsystem framework preflight.

This is a framework preflight only. It verifies the current Ex-0..Ex-3 SDK
contract surface, Lite PG candidate queue behavior, Lite PG heartbeat routing,
and SDK entity preflight behavior. It does not claim a production sidecar,
frontend/write interface, new external data source, model download, or
Docling/LlamaIndex production chain.

## Scoped Repos And Commits

- subsystem-sdk: `f7b667824fe5a0c9b4c8e6c2c81328b50b15b585`
  - Locked Lite PG candidate queue JSON payload insertion in
    `tests/backends/test_lite_pg_backend.py`.
  - Added Lite PG submit-client preflight block coverage proving unresolved
    entity refs do not open a PG connection or enqueue a row.

- subsystem-announcement: `d2f25eeebe4faa8af4c68d957dd3863a6fe261fb`
  - Fixed the real SDK heartbeat adapter boundary. The top-level SDK
    `send_heartbeat()` accepts status fields and the configured
    `BaseSubsystemContext` owns Ex-0 envelope construction.
  - Added real announcement -> SDK heartbeat integration coverage and
    adapter-level Ex-1 block-preflight coverage.

- subsystem-news: `b5a6db0d3fce323509f0ad201b9f7832f0aaadde`
  - Added adapter-level Ex-1 block-preflight coverage for the real news
    `DefaultSubsystemSdkClient` path.

## What Was Verified

- Ex-0..Ex-3 export contract current state is locked by the SDK contract,
  validation, submit, heartbeat, and reference subsystem test lanes.
- Lite PG candidate queue submit serializes the candidate payload to the queue
  insert parameter and returns only the public transport-neutral receipt shape.
- Lite PG heartbeat is routed through `SubmitBackendHeartbeatAdapter` and the
  SDK strips routing envelope fields before the backend queue row.
- Entity preflight runs before backend dispatch and blocks unresolved Ex-1
  entity refs in SDK, announcement adapter, and news adapter paths.
- The announcement heartbeat review note was validated against current SDK
  behavior. The current SDK top-level heartbeat API must receive status fields,
  not an adapter-built Ex-0 envelope; the fix maps announcement `ok` to SDK
  `healthy` and lets `BaseSubsystemContext` build and validate Ex-0.

## Verification Commands

- Requested command as written:
  - Command:
    `cd /Users/fanjie/Desktop/Cowork/project-ult/subsystem-sdk && python -m pytest -q tests/contract tests/validate tests/submit tests/heartbeat tests/backends/test_lite_pg_backend.py tests/integration/test_reference_subsystem.py`
  - Result: blocked by local shell, `python: command not found`.

- Requested SDK suite with available interpreter:
  - Command:
    `cd /Users/fanjie/Desktop/Cowork/project-ult/subsystem-sdk && python3 -m pytest -q tests/contract tests/validate tests/submit tests/heartbeat tests/backends/test_lite_pg_backend.py tests/integration/test_reference_subsystem.py`
  - Result: pass, exit code `0`.

- Focused SDK Lite PG / heartbeat / preflight suite:
  - Command:
    `cd /Users/fanjie/Desktop/Cowork/project-ult/subsystem-sdk && python3 -m pytest -q tests/backends/test_lite_pg_backend.py tests/backends/test_lite_pg_heartbeat_backend.py tests/submit/test_client_preflight.py`
  - Result: `12 passed / 1 skipped`.

- Focused announcement real SDK adapter suite:
  - Command:
    `cd /Users/fanjie/Desktop/Cowork/project-ult/subsystem-announcement && PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/subsystem-sdk:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src:/Users/fanjie/Desktop/Cowork/project-ult/subsystem-announcement/src python3 -m pytest -q tests/test_runtime_sdk.py tests/integration/test_sdk_wire_shape_integration.py`
  - Result: `22 passed / 5 skipped`.

- Focused news real SDK adapter suite:
  - Command:
    `cd /Users/fanjie/Desktop/Cowork/project-ult/subsystem-news && PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/subsystem-sdk:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src:/Users/fanjie/Desktop/Cowork/project-ult/subsystem-news/src python3 -m pytest -q tests/integration/test_sdk_wire_shape_integration.py`
  - Result: `5 passed`.

## Dependency Decision Evidence

- No new external data source was introduced.
- No sidecar, frontend, or write interface was introduced.
- No Docling or LlamaIndex runtime chain was added or executed for this
  preflight. Existing announcement dependency pins remain dependency-decision
  context only for this workstream.
- No model download was run.

## Findings

- P0: none remaining.
- P1: none remaining. The announcement heartbeat SDK boundary mismatch was
  fixed and covered by real SDK integration.
- P2: none remaining.
- P3: local shell does not provide a `python` binary; verification used
  `python3`. This is an environment alias issue, not a framework behavior
  failure.

## Residual Risk

- Entity preflight coverage is adapter-level and local. It proves the SDK
  pre-dispatch behavior with injected lookup objects, not live entity-registry
  availability.
- Ex-2 and Ex-3 adapter preflight coverage remains indirect through SDK
  validation suites; the added adapter-level block tests target Ex-1 because
  current canonical Ex-1 exposes the `entity_id` field scanned by SDK preflight.
