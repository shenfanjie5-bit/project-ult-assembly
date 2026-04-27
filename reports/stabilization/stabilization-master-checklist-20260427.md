# Project ULT Stabilization Master Checklist

Recorded: 2026-04-26T19:11:06Z

Scope:

- Track Project ULT stabilization work until P1/P2 risks are closed.
- This is a coordination checklist only.
- Do not use this checklist as verified compatibility evidence by itself.
- Do not update `compatibility-matrix.yaml`, `module-registry.yaml`,
  `MODULE_REGISTRY.md`, or assembly `README.md` from this checklist.
- Do not run release-freeze, command, run, compat-run, e2e-run, min-cycle, or
  sidecar auto-start work from this checklist.

Status model:

- `closed`: implementation committed and pushed; required tests reported.
- `fixed_pending_independent_review`: implementation committed and pushed, but
  a separate reviewer still needs to confirm the risk is genuinely closed.
- `open`: not implemented in this stabilization pass.
- `blocked`: cannot proceed without a separate decision.

Current repo snapshot:

| Repo | HEAD | Status notes |
| --- | --- | --- |
| `contracts` | `540f9e8feebd` | clean |
| `entity-registry` | `bbf13487e70c` | only local untracked `.orchestrator/` |
| `main-core` | `53913da402b8` | only local untracked `.orchestrator/` |
| `subsystem-sdk` | `aaa3b0654c35` | clean |
| `subsystem-announcement` | `79d8ec5d141d` | clean |
| `subsystem-news` | `e83363c1f5e3` | only local untracked `PROJECT_REPORT.md` |
| `reasoner-runtime` | `f5183f4765f4` | clean |
| `audit-eval` | `2f41580078c0` | local untracked report/build/dist/egg-info artifacts |
| `orchestrator` | `c004ee326660` | local untracked `.orchestrator/` and dbt runtime state |
| `graph-engine` | `bee527bc1380` | only local untracked `PROJECT_REPORT.md` |
| `data-platform` | `7feebcb39d23` | only local untracked `.orchestrator/` |
| `FrontEnd` | `0c8e0523c72c` | local modified `README.md`, `src/mocks/data/projectUltData.ts` predate FrontEnd polish; do not touch from backend stabilization |
| `assembly` | `4a3ea443e8b1` | local env/cache/tmp/report artifacts only |

## Closed Or Fixed Pending Review

| ID | Priority | Finding / risk | Owner | Repo / files | Status | Fix commit(s) | Required tests | Evidence file | Matrix eligibility |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S1-01 | P2 | `contracts` CI/version/shared fixture pin drift | Backend Batch 1 | `contracts` | `closed` | `e3eb0c4`, later `540f9e8feebd` | `PYTHON=.venv/bin/python bash scripts/ci.sh`; `.venv/bin/python -m pytest`; export + compat tests; `git diff --check` | `reports/stabilization/batch1-independent-review-20260427.md` | No |
| S1-02 | P2 | `entity-registry` monkey patched `contracts.schemas.ResolutionCase` instead of relying on official contract schema | Backend Batch 1 | `entity-registry` | `closed` | `bbf13487e70c` | `make test`; `make contract`; boundary tests; sibling contracts `v0.1.3` roundtrip; `git diff --check` | `reports/stabilization/batch1-independent-review-20260427.md` | No |
| S1-03 | P2 | `main-core` contract pin drift and L8 report key mismatch | Backend Batch 1 | `main-core` | `closed` | `53913da402b8` | `bash scripts/check_boundaries.sh`; full `pytest`; contract alignment tests; regression tests; assembly model validation; `git diff --check` | `reports/stabilization/batch1-independent-review-20260427.md` | No |
| S1-04 | P2 | `subsystem-announcement`, `subsystem-news`, `subsystem-sdk` smoke hooks returned non-assembly `SmokeResult` shape | Backend Batch 1 | `subsystem-sdk`, `subsystem-announcement`, `subsystem-news` | `closed` | `aaa3b0654c35`, `f4f6232`, `79d8ec5d141d`, `e83363c1f5e3` | full `pytest` in each repo; public/smoke/runtime contract tests; assembly `HealthResult`/`SmokeResult`/`VersionInfo` validation; `git diff --check` | `reports/stabilization/batch1-independent-review-20260427.md` | No |
| S1-05 | P2 | Exported `ResolutionCase` JSON Schema did not encode `candidate_entities` invariant | Backend Batch 1 follow-up | `contracts/src/contracts/export/__init__.py`; `contracts/tests/test_export_json_schema_contract.py` | `closed` | `540f9e8feebd` | `PYTHON=.venv/bin/python bash scripts/ci.sh`; `.venv/bin/python -m pytest`; `git diff --check` | `reports/stabilization/batch1-independent-review-20260427.md` | No |
| S1-06 | P2 | `0.1.0` contracts baseline was accidentally moved toward current schema | Backend Batch 1 follow-up | `contracts/src/contracts/baselines/0.1.0/json_schema/**`; `contracts/artifacts/baselines/0.1.0/json_schema/**` | `closed` | `540f9e8feebd` | `.venv/bin/python -m pytest`; explicit no-diff check for 0.1.0 baseline dirs | `reports/stabilization/batch1-independent-review-20260427.md` | No |
| S1-07 | P2 | `ResolutionCase` compat allowlist ignored future `/allOf` changes too broadly | Backend Batch 1 follow-up | `contracts/src/contracts/compat/__init__.py`; `contracts/tests/test_compat_rules.py` | `closed` | `540f9e8feebd` | `PYTHON=.venv/bin/python bash scripts/ci.sh`; `.venv/bin/python -m pytest`; compat regression tests for extra/changed `allOf` rules | `reports/stabilization/batch1-independent-review-20260427.md` | No |
| S1-08 | P2 | Three-backend provider example was not loadable by public reasoner-runtime loader | LLM setup follow-up | `reasoner-runtime/config/providers.three-backends.example.yaml`; reasoner-runtime config loader tests | `closed` | `66f4dc7cd1c7` | `PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/contracts/src .venv/bin/python -m pytest tests/unit/test_config.py tests/unit/test_codex_auth.py tests/unit/test_codex_client.py tests/unit/test_claude_code_cli_client.py -q`; broad pytest excluding shared fixtures; `git diff --check` | `reports/smoke/llm-backend-setup-wiring-smoke-20260427.md` | No |
| S1-09 | P2 | Assembly setup implied host Codex/Claude login would work inside compose containers | LLM setup follow-up | `assembly/.env.example`; `assembly/compose/*.yaml`; `assembly/src/assembly/cli/setup.py`; docs/tests | `closed` | `da2861fb659d`, evidence `aac0c4e3c5bd` | `PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python -m pytest -q -p no:cacheprovider tests/cli/test_setup.py tests/cli/test_main.py tests/bootstrap/test_plan.py`; docs/smoke/registry line; `git diff --check` | `reports/smoke/llm-backend-setup-wiring-smoke-20260427.md` | No |

## Batch 1 Independent Review Gate

Owner: Free subagent / independent reviewer.

Status: `closed`.

Goal:

- Confirm S1-01 through S1-04 are real risk closures, not only test rewrites.
- Confirm S1-05 through S1-09 remain closed on current `main`.
- Do not implement new behavior during this review.

Required review commands:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/contracts
PYTHON=.venv/bin/python bash scripts/ci.sh
.venv/bin/python -m pytest
git diff --check

cd /Users/fanjie/Desktop/Cowork/project-ult/entity-registry
make test
make contract
git diff --check

cd /Users/fanjie/Desktop/Cowork/project-ult/main-core
bash scripts/check_boundaries.sh
.venv/bin/python -m pytest
git diff --check

cd /Users/fanjie/Desktop/Cowork/project-ult/subsystem-sdk
.venv/bin/python -m pytest
git diff --check

cd /Users/fanjie/Desktop/Cowork/project-ult/subsystem-announcement
.venv/bin/python -m pytest
git diff --check

cd /Users/fanjie/Desktop/Cowork/project-ult/subsystem-news
.venv/bin/python -m pytest
git diff --check
```

Evidence file:

- `reports/stabilization/batch1-independent-review-20260427.md`

## Batch 2: LLM / Replay Chain

Status: `closed`.

| ID | Priority | Finding / risk | Owner | Repo / files | Required fix | Required tests | Evidence file | Matrix eligibility |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S2-01 | P2 | `reasoner-runtime` dependency hash lock drift, including known LiteLLM hash mismatch | Backend Batch 2 | `reasoner-runtime/requirements.txt`; dependency lock workflow | `closed`: updated LiteLLM wheel hash to verified PyPI hash | clean dependency hash download; reasoner-runtime unit/integration tests; dependency lock script; `git diff --check` | `reports/stabilization/batch2-llm-replay-smoke-20260427.md` | No |
| S2-02 | P2 | `ReplayBundle.to_contract` missing or not aligned with contracts replay envelope | Backend Batch 2 | `reasoner-runtime` replay/provider models | `closed`: `ReplayBundle.to_contract()` now preserves `sanitized_input`, `input_hash`, `raw_output`, `parsed_result`, `output_hash` | replay unit/integration tests; contract-backed model validation; regression covering all five fields; `git diff --check` | `reports/stabilization/batch2-llm-replay-smoke-20260427.md` | No |
| S2-03 | P2 | `audit-eval` replay hash verification semantics incomplete | Backend Batch 2 | `audit-eval` replay/audit storage/query code | `closed`: AuditRecord recomputes input/output hashes and fails closed on malformed or mismatched hashes | audit-eval replay/audit tests; tamper regression; full pytest; ruff target; `git diff --check` | `reports/stabilization/batch2-llm-replay-smoke-20260427.md` | No |
| S2-04 | P2 | `manifest_cycle_id` semantics ambiguous | Backend Batch 2 | `audit-eval`; contracts references if needed | `closed`: execution `cycle_id` and published `manifest_cycle_id` semantics are separated and tested | audit-eval write bundle and replay query tests; full pytest; ruff target; `git diff --check` | `reports/stabilization/batch2-llm-replay-smoke-20260427.md` | No |

Batch 2 hard constraints:

- Do not change Codex OAuth token handling logic.
- Do not change Claude Code CLI subprocess invocation logic.
- Do not add fallback from subscription-auth failure to API-key providers.
- Do not add command/run/freeze/release-freeze endpoints.

## Batch 3: Execution And Write Boundaries

Status: `closed`.

| ID | Priority | Finding / risk | Owner | Repo / files | Required fix | Required tests | Evidence file | Matrix eligibility |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S3-01 | P2 | `orchestrator` `required_artifacts` path traversal risk | Backend Batch 3 | `orchestrator` artifact/path validation code | `closed`: paths are constrained to artifact root and traversal/symlink escape/non-file targets are rejected | orchestrator full tests; targeted traversal regressions; public entrypoint tests; `git diff --check` | `reports/stabilization/batch3-independent-review-20260427.md` | No |
| S3-02 | P2 | `graph-engine` timeout may leave background writes running | Backend Batch 3 | `graph-engine` timeout/execution code | `closed`: timeout expires a write barrier used by Neo4j write and status write proxies | graph-engine full tests; timeout regression; no post-timeout write assertion; `git diff --check` | `reports/stabilization/batch3-independent-review-20260427.md` | No |
| S3-03 | P2 | `graph-engine` readonly simulation drop barrier insufficient | Backend Batch 3 | `graph-engine` simulation/read-only boundary | `closed`: readonly simulation only permits scoped owned GDS projection project/drop and rejects live mutation writes | graph-engine readonly/simulation tests; persistence regression; `git diff --check` | `reports/stabilization/batch3-independent-review-20260427.md` | No |
| S3-04 | P2 | `data-platform` artifact refs and manifest formal key validation incomplete | Backend Batch 3 | `data-platform` artifact/manifest code | `closed`: artifact refs and formal manifest keys are validated explicitly against allowed roots/registry | data-platform full or approved full-target tests; manifest formal key regressions; artifact ref regressions; `git diff --check` | `reports/stabilization/batch3-independent-review-20260427.md` | No |

Batch 3 hard constraints:

- Do not relax write barriers to make tests pass.
- Do not introduce hidden background write paths.
- Do not stage `.orchestrator`, local dbt state, venv, cache, build, dist, or
  report scratch files.

## FrontEnd Read-Only Polish

Status: `closed`.

Owner: FrontEnd role.

Current snapshot:

- `FrontEnd` HEAD: `0c8e0523c72c`
- Current local state has modified `README.md` and
  `src/mocks/data/projectUltData.ts`; backend stabilization must not touch or
  revert these files.

| ID | Priority | Finding / risk | Required fix | Required tests | Evidence file | Matrix eligibility |
| --- | --- | --- | --- | --- | --- | --- |
| FE-01 | P2 | `data_mode` query/store synchronization can drift | `closed`: query string, persistent store, Project ULT route guards, and quick links preserve `data_mode=projectUlt` without triggering unsupported legacy calls | `npm run check`; `npm run lint`; `npm run build`; browser smoke for refresh/deep-link/store transitions; forbidden write-call grep | `reports/stabilization/frontend-readonly-polish-smoke-20260427.md` | No |
| FE-02 | P2 | API-3A limit clamp must not leak invalid backend queries | `closed`: Data Explorer entity/canonical/raw limits are normalized and clamped to backend bounds before requests and URL sync | `npm run check`; `npm run lint`; `npm run build`; browser smoke with over-limit deep links; console no 422 | `reports/stabilization/frontend-readonly-polish-smoke-20260427.md` | No |
| FE-03 | P2 | unknown route fallback can escape Project ULT read-only mode | `closed`: unknown and risky Project ULT-mode routes land on `/project-ult/system?data_mode=projectUlt`, not legacy write/risk pages | route guard smoke; no unsupported endpoint calls; no blank page | `reports/stabilization/frontend-readonly-polish-smoke-20260427.md` | No |

FrontEnd hard constraints:

- Do not add a new page in this polish batch.
- Do not add POST/PUT/PATCH/DELETE Project ULT calls.
- Do not add command/run/freeze/release-freeze/min-cycle/replay POST/graph
  simulate calls.

## Final Gate Before Verified Matrix Promotion

Status: `closed`; final assembly smoke/registry/compat gate passed and matrix
promotion decision was recorded.

Owner: Stabilization lead.

Required final commands:

```bash
cd /Users/fanjie/Desktop/Cowork/project-ult/assembly
PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python -m pytest -q -p no:cacheprovider \
  tests/release/test_docs.py \
  tests/smoke \
  tests/registry \
  tests/compat
git diff --check
```

Final gate requirements:

- All P1/P2 checklist items are `closed`.
- Each closed item has a commit, test command, and evidence file.
- Independent review confirms risk closure for Batch 1/2/3 and FrontEnd polish.
- No local env/cache/tmp/build/dist/egg-info/report scratch files are staged.
- `frontend-api` remains outside old verified matrix rows unless a separate
  promotion run produces fresh contract/smoke/e2e evidence for the new module
  identity.

Evidence file:

- `reports/stabilization/final-gate-readiness-20260427.md`

After this gate:

1. Decide whether to create a new verified matrix row including frontend-api.
2. Run a real-data mini cycle.
3. Start planning the P5 20 trading day shadow run.
