# MODULE_REGISTRY

Stage 5 promoted state (both lite-local + full-dev profiles), the
frontend-api API-1 read-only BFF registration, and the draft
`lite-local-readonly-ui` profile variant. This file is the human-readable
view of `module-registry.yaml`. All 13 active modules are
`integration_status: verified`: the 11 active subsystem modules per
Stage 3 cross-project compat audit
(`assembly/scripts/stage_3_compat_audit.py` — 11/11 pass
`PublicApiBoundaryCheck`), `assembly` itself per the §4.3 self-verify
upgrade, and `frontend-api` after API-1 public smoke evidence.
`frontend-api` is not folded into the existing verified compatibility
matrix rows; it is only included by the draft `lite-local-readonly-ui`
matrix identity until fresh contract/smoke/e2e evidence is promoted.
`feature-store` and `stream-layer` remain
`not_started` (frozen slots per master plan §1.1; not in scope this
round).

The compatibility matrix records BOTH profiles as `verified` at
`verified_at: 2026-04-24T05:24:14Z`:

- `lite-local`: re-verified at Stage 5 after the audit-eval pin sync
  0.2.2 → 0.2.5 (fixture-only bumps from #2 canonical_entity_id
  reconciliation + #4 historical_replay_pack T+1 tushare extension).
  Original Stage 4 §4.3 PASS evidence was `2026-04-22T06:08:55Z`
  via `test_e2e_runner_consumes_audit_eval_fixtures_minimal_cycle`.
- `full-dev`: newly verified at Stage 5 via
  `test_e2e_runner_consumes_audit_eval_fixtures_minimal_cycle_full_dev`,
  driven against the same 4-service Lite stack since default
  `full-dev` and `lite-local` resolve the same 3 core
  `enabled_service_bundles` per `docs/PROFILE_COMPARISON.md`.
  Per-profile evidence boundary maintained (codex review #10
  strict call from Stage 4 §4.3) — full-dev needed its own PASS.

| module_id | module_version | contract_version | owner | upstream_modules | downstream_modules | public_entrypoints | depends_on | supported_profiles | integration_status | last_smoke_result | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| contracts | 0.1.3 | v0.1.3 | unassigned |  |  | health:health_probe=contracts.public:health_probe; smoke:smoke_hook=contracts.public:smoke_hook; init:init_hook=contracts.public:init_hook; version:version_declaration=contracts.public:version_declaration; cli:cli=contracts.public:cli |  | lite-local, lite-local-readonly-ui, full-dev | verified | null | Stage 3 audit passed; milestone-test-baseline v0.1.3; codex-confirmed. |
| data-platform | 0.1.1 | v0.1.3 | unassigned |  |  | health:health_probe=data_platform.public:health_probe; smoke:smoke_hook=data_platform.public:smoke_hook; init:init_hook=data_platform.public:init_hook; version:version_declaration=data_platform.public:version_declaration; cli:cli=data_platform.public:cli |  | lite-local, lite-local-readonly-ui, full-dev | verified | null | Stage 3 audit passed; milestone-test-baseline v0.1.1; codex-confirmed. |
| entity-registry | 0.1.1 | v0.1.3 | unassigned |  |  | health:health_probe=entity_registry.public:health_probe; smoke:smoke_hook=entity_registry.public:smoke_hook; init:init_hook=entity_registry.public:init_hook; version:version_declaration=entity_registry.public:version_declaration; cli:cli=entity_registry.public:cli |  | lite-local, lite-local-readonly-ui, full-dev | verified | null | Stage 3 audit passed; milestone-test-baseline v0.1.1; codex-confirmed. |
| reasoner-runtime | 0.1.1 | v0.1.3 | unassigned |  |  | health:health_probe=reasoner_runtime.public:health_probe; smoke:smoke_hook=reasoner_runtime.public:smoke_hook; init:init_hook=reasoner_runtime.public:init_hook; version:version_declaration=reasoner_runtime.public:version_declaration; cli:cli=reasoner_runtime.public:cli |  | lite-local, lite-local-readonly-ui, full-dev | verified | null | Stage 3 audit passed; milestone-test-baseline v0.1.1; codex-confirmed. |
| graph-engine | 0.1.1 | v0.1.3 | unassigned |  |  | health:health_probe=graph_engine.public:health_probe; smoke:smoke_hook=graph_engine.public:smoke_hook; init:init_hook=graph_engine.public:init_hook; version:version_declaration=graph_engine.public:version_declaration; cli:cli=graph_engine.public:cli |  | lite-local, lite-local-readonly-ui, full-dev | verified | null | Stage 3 audit passed; milestone-test-baseline v0.1.1 + follow-up #1; codex re-review #2 confirmed; consumes Ex-3 from contracts v0.1.3. |
| main-core | 0.1.1 | v0.1.3 | unassigned |  |  | health:health_probe=main_core.public:health_probe; smoke:smoke_hook=main_core.public:smoke_hook; init:init_hook=main_core.public:init_hook; version:version_declaration=main_core.public:version_declaration; cli:cli=main_core.public:cli |  | lite-local, lite-local-readonly-ui, full-dev | verified | null | Stage 3 audit passed; milestone-test-baseline v0.1.1; codex-confirmed. |
| audit-eval | 0.2.5 | v0.1.3 | unassigned |  |  | health:health_probe=audit_eval.public:health_probe; smoke:smoke_hook=audit_eval.public:smoke_hook; init:init_hook=audit_eval.public:init_hook; version:version_declaration=audit_eval.public:version_declaration; cli:cli=audit_eval.public:cli |  | lite-local, lite-local-readonly-ui, full-dev | verified | null | Stage 3 audit passed; milestone-test-baseline v0.2.5 (canonical_entity_id reconciled to runtime dot form + 2 phase-B tushare cases + historical_replay_pack T+1 tushare extension); codex-confirmed. |
| subsystem-sdk | 0.1.2 | v0.1.3 | unassigned |  |  | health:health_probe=subsystem_sdk.public:health_probe; smoke:smoke_hook=subsystem_sdk.public:smoke_hook; init:init_hook=subsystem_sdk.public:init_hook; version:version_declaration=subsystem_sdk.public:version_declaration; cli:cli=subsystem_sdk.public:cli |  | lite-local, lite-local-readonly-ui, full-dev | verified | null | Stage 3 audit passed; milestone-test-baseline v0.1.2; Stage 4 §4.1.5 harmonized contract_version to v0.1.3 (SDK is a contracts-schema consumer; pinned to the contracts package version it's bound against). |
| orchestrator | 0.1.1 | v0.1.3 | unassigned |  |  | health:health_probe=orchestrator.public:health_probe; smoke:smoke_hook=orchestrator.public:smoke_hook; init:init_hook=orchestrator.public:init_hook; version:version_declaration=orchestrator.public:version_declaration; cli:cli=orchestrator.public:cli |  | lite-local, lite-local-readonly-ui, full-dev | verified | null | Stage 3 audit passed; milestone-test-baseline v0.1.1 with observe-not-assert min-cycle CLI; codex-confirmed. |
| assembly | 0.1.0 | v0.0.0 | assembly |  | frontend-api | health:health_probe=assembly.public:health_probe; smoke:smoke_hook=assembly.public:smoke_hook; init:init_hook=assembly.public:init_hook; version:version_declaration=assembly.public:version_declaration; cli:cli=assembly.public:cli |  | lite-local, lite-local-readonly-ui, full-dev | verified | null | Stage 4 §4.0 + §4.1 + §4.1.5 + §4.2 + §4.3 + Stage 5 done; both lite-local and full-dev profiles verified at 2026-04-24T05:24:14Z (full-dev parallel verification reuses the same 4-service Lite stack per docs/PROFILE_COMPARISON.md equivalence). |
| frontend-api | 0.1.0 | v0.1.3 | frontend-api | assembly |  | health:health_probe=frontend_api.public:health_probe; smoke:smoke_hook=frontend_api.public:smoke_hook; init:init_hook=frontend_api.public:init_hook; version:version_declaration=frontend_api.public:version_declaration; cli:cli=frontend_api.public:cli | assembly | lite-local, lite-local-readonly-ui, full-dev | verified | reports/smoke/frontend-api-api1-public-smoke-20260425.md | API-1 read-only System/Assembly BFF registered after frontend-api public smoke passed for health/modules/profiles/compat; no command endpoints exposed. |
| feature-store | 0.0.0 | v0.0.0 | unassigned |  |  | health:health_probe=feature_store.public:health_probe; smoke:smoke_hook=feature_store.public:smoke_hook; init:init_hook=feature_store.public:init_hook; version:version_declaration=feature_store.public:version_declaration; cli:cli=feature_store.public:cli |  | lite-local, full-dev | not_started | null | Stage 0 placeholder entrypoint declarations. |
| stream-layer | 0.0.0 | v0.0.0 | unassigned |  |  | health:health_probe=stream_layer.public:health_probe; smoke:smoke_hook=stream_layer.public:smoke_hook; init:init_hook=stream_layer.public:init_hook; version:version_declaration=stream_layer.public:version_declaration; cli:cli=stream_layer.public:cli |  | lite-local, full-dev | not_started | null | Stage 0 placeholder entrypoint declarations. |
| subsystem-announcement | 0.1.1 | v0.1.3 | unassigned |  |  | health:health_probe=subsystem_announcement.public:health_probe; smoke:smoke_hook=subsystem_announcement.public:smoke_hook; init:init_hook=subsystem_announcement.public:init_hook; version:version_declaration=subsystem_announcement.public:version_declaration; cli:cli=subsystem_announcement.public:cli |  | lite-local, lite-local-readonly-ui, full-dev | verified | null | Stage 3 audit passed; milestone-test-baseline v0.1.1 + canonical wire mapper; codex review #8 approved; Stage 4 §4.1.5 harmonized contract_version to v0.1.3 (Ex-1/2/3 producer; pinned to the contracts package version this subsystem is bound against). |
| subsystem-news | 0.1.1 | v0.1.3 | unassigned |  |  | health:health_probe=subsystem_news.public:health_probe; smoke:smoke_hook=subsystem_news.public:smoke_hook; init:init_hook=subsystem_news.public:init_hook; version:version_declaration=subsystem_news.public:version_declaration; cli:cli=subsystem_news.public:cli |  | lite-local, lite-local-readonly-ui, full-dev | verified | null | Stage 3 audit passed; milestone-test-baseline v0.1.1 + canonical wire mapper; codex review #4 approved; Stage 4 §4.1.5 harmonized contract_version to v0.1.3 (Ex-1/2/3 producer; pinned to the contracts package version this subsystem is bound against). |
