# P4 Subsystem Framework Live Preflight Evidence - 2026-04-27

## Verdict

Status: PASS for scoped P4 live-registry preflight.

This evidence extends the earlier P4 framework preflight with bundled live
entity-registry lookup wiring in `subsystem-sdk`. Production profile now fails
closed when entity-registry lookup is absent/unavailable and blocks unresolved
Ex-2/Ex-3 refs before submit. Dev profile preserves the existing offline-first
unavailable/skip behavior.

This is still a P4 preflight slice. It does not claim a production
news/announcement/Polymarket ingestion chain, sidecar, frontend write
interface, Docling/LlamaIndex model download, or P5 readiness.

## Commits

- subsystem-sdk framework strengthening: `80dd6a32c988f5dbd36a02d964bff8150a6eff91`
- subsystem-news: `e1aada8fa310fbf9e92ac58f2a5ad601ff5e4e58`
- subsystem-announcement: `8561fe0c53385d75ea7911d8120f19c65bf0494f`
- subsystem-sdk live registry follow-up: `a02b4feaead45fe9580c0a6d907dadd721df857e`
- entity-registry live lookup follow-up: `156a2d31a712ced9efdd0b155028bb2cfaef0dd5`

## What Changed

- Entity-registry:
  - Added read-only `lookup_entity_refs(refs)` backed by configured live
    repositories.
  - Verifies producer-supplied canonical entity refs; it does not infer or mint
    new IDs.
- SDK:
  - Added `LiveEntityRegistryLookup` and `build_entity_preflight_wiring()`.
  - Added `SubmitClient(entity_preflight_profile="dev" | "production")`.
  - Production profile forces `preflight_policy="block"` and
    `lookup_unavailable_policy="fail"`.
  - Dev profile keeps existing offline-first skip/warn behavior.
  - Ex-2 `affected_entities` and Ex-3 endpoint refs block submit when
    unresolved in production profile.
- News/announcement:
  - Existing direct adapter block-path coverage remains valid for SDK
    pre-dispatch validation.

## Validation

Main-thread focused validation:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/subsystem-sdk
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/contracts/src:/Users/fanjie/Desktop/Cowork/project-ult/entity-registry/src \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest -q \
  tests/validate/test_entity_registry_wiring.py \
  tests/validate/test_preflight.py \
  tests/submit/test_client_preflight.py \
  tests/test_package_layout.py

result:
48 passed
```

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/entity-registry
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/entity-registry/src \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest -q \
  tests/test_lookup_entity_refs.py

result:
2 passed
```

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/subsystem-sdk
/opt/homebrew/bin/ruff check \
  subsystem_sdk/submit/client.py \
  subsystem_sdk/validate/__init__.py \
  subsystem_sdk/validate/engine.py \
  subsystem_sdk/validate/entity_registry.py \
  subsystem_sdk/validate/preflight.py \
  tests/submit/test_client_preflight.py \
  tests/test_package_layout.py \
  tests/validate/test_entity_registry_wiring.py \
  tests/validate/test_preflight.py

result:
All checks passed
```

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/entity-registry
/opt/homebrew/bin/ruff check src/entity_registry/__init__.py tests/test_lookup_entity_refs.py

result:
All checks passed
```

Backend-E handoff also reported:

- subsystem-sdk full suite with assembly venv: passed.
- entity-registry full suite with assembly venv: passed.
- both repos pushed and clean.

## Residual Risk

- This proves live registry lookup wiring and fail-closed SDK boundary, not a
  production news/announcement/Polymarket ingestion flow.
- Production environments must configure entity-registry repositories before
  using the production SDK profile.

## Findings

- P0: none.
- P1: none.
- P2: none.
- P3: none. The previous live entity-registry residual risk is now closed for
  scoped P4 preflight by commits `a02b4feaead45fe9580c0a6d907dadd721df857e`
  and `156a2d31a712ced9efdd0b155028bb2cfaef0dd5`.
