# P4 Subsystem Framework Live Preflight Evidence - 2026-04-27

## Verdict

Status: PASS for strengthened P4 preflight.

This evidence extends the earlier P4 framework preflight with direct
news/announcement Ex-2 and Ex-3 block-path coverage plus Lite PG queue
suppression checks. It does not claim a bundled live entity-registry client;
the SDK preflight boundary remains protocol-injected and fail-closed when a
lookup is supplied.

## Commits

- subsystem-sdk: `80dd6a32c988f5dbd36a02d964bff8150a6eff91`
- subsystem-news: `e1aada8fa310fbf9e92ac58f2a5ad601ff5e4e58`
- subsystem-announcement: `8561fe0c53385d75ea7911d8120f19c65bf0494f`

## What Changed

- SDK:
  - Added explicit no-live-lookup preflight boundary coverage.
  - Added Lite PG Ex-2/Ex-3 block-preflight coverage proving unresolved refs
    do not enqueue rows or commit.
- News:
  - Added direct `DefaultSubsystemSdkClient` tests proving unresolved Ex-2
    affected entities and Ex-3 endpoints are rejected before SDK submit.
- Announcement:
  - Added real `AnnouncementSubsystem.submit` adapter integration tests proving
    Ex-2/Ex-3 block preflight prevents backend submission.

## Validation

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/subsystem-sdk
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/subsystem-sdk:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
python3 -m pytest -q \
  tests/validate/test_preflight.py \
  tests/backends/test_lite_pg_backend.py \
  tests/backends/test_lite_pg_heartbeat_backend.py

result:
26 passed, 1 skipped
```

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/subsystem-news
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/subsystem-sdk \
python3 -m pytest -q tests/runtime/test_submit.py

result:
12 passed
```

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/subsystem-announcement
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/subsystem-sdk:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
python3 -m pytest -q \
  tests/test_runtime_submit.py \
  tests/integration/test_sdk_wire_shape_integration.py

result:
21 passed
```

## Residual Risk

- Live entity-registry availability is still not bundled into subsystem-sdk.
  This is now documented by test coverage rather than hidden by a false pass.
- This remains a P4 framework/live-preflight slice, not a production
  news/announcement/Polymarket ingestion chain.

## Findings

- P0: none.
- P1: none.
- P2: none.
- P3: live entity-registry remains an explicit future integration, not a
  completed claim.
