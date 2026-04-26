# LLM Backend Setup Wiring Smoke Evidence

Recorded: 2026-04-26T19:06:47Z

Scope:

- Record smoke evidence for the reasoner-runtime gated LLM backend clients and
  assembly setup wiring.
- Documentation and test evidence only.
- No Project ULT frontend-api endpoint is added.
- No sidecar runtime, command, run, freeze, release-freeze, compat-run,
  e2e-run, min-cycle, replay trigger, or graph simulate surface is added.
- Keep this evidence outside the verified compatibility matrix rows; no matrix
  `module_set` promotion or `verified_at` update is implied.

Commits under smoke:

- contracts ResolutionCase schema follow-up:
  `540f9e8feebd`
- reasoner-runtime gated LLM backend clients:
  `66f4dc7cd1c7`
- assembly setup wiring:
  `da2861fb659d`

Review findings covered:

```text
reasoner-runtime/config/providers.three-backends.example.yaml
  Finding:
    The example file used provider-group keys that were not loadable through
    the public provider loader.

  Evidence:
    The example is now selector-loadable. Callers must select exactly one
    provider group, so the selected backend yields one active provider profile
    rather than a fallback chain.

assembly/.env.example and compose wiring
  Finding:
    Codex/Claude setup previously implied host login state would work inside
    Docker containers, but the Dagster images do not include Codex/Claude CLI
    tooling or host keychain/auth mounts.

  Evidence:
    The setup/docs now state the subscription backends are host-managed for
    this phase. MiniMax is the only container-ready compose path. Codex OAuth
    and Claude Code CLI paths are exposed through host/runtime configuration
    only until a separate container packaging design exists.
```

Reasoner-runtime evidence:

```text
Provider example:
  config/providers.three-backends.example.yaml

Supported selected groups:
  providers_minimax
  providers_codex
  providers_claude_code

Expected behavior:
  explicit selector required for grouped examples
  selected group loads as the public provider profile list
  unknown selector fails validation
  no implicit fallback across MiniMax, Codex, and Claude Code

Boundary:
  Codex OAuth auth source remains read-only against ~/.codex/auth.json.
  Claude Code integration remains a claude CLI subprocess wrapper.
  This smoke evidence does not alter Codex OAuth token handling or Claude Code
  CLI invocation logic.
```

Assembly setup evidence:

```text
assembly setup --backend minimax
  writes MINIMAX_API_KEY
  clears Codex and Claude Code enable gates
  is documented as container-ready through compose env pass-through

assembly setup --backend codex
  validates host auth file presence
  writes REASONER_RUNTIME_ENABLE_CODEX_OAUTH=1
  clears MiniMax key and Claude Code gate
  is documented as host-managed/runtime-only in this phase

assembly setup --backend claude-code
  validates claude is present on host PATH
  writes REASONER_RUNTIME_ENABLE_CLAUDE_CODE_CLI=1
  clears MiniMax key and Codex gate
  is documented as host-managed/runtime-only in this phase

Unrelated .env keys:
  preserved by setup.

Compose boundary:
  lite-local and full-dev pass through LLM env variables.
  compose does not claim to install Codex or Claude CLI tooling.
  compose does not mount host OAuth/keychain state for subscription backends.
```

Validation:

```text
contracts:
  git HEAD:
    540f9e8feebd
  status:
    ## main...origin/main

reasoner-runtime targeted:
  command:
    PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
      .venv/bin/python -m pytest \
      tests/unit/test_config.py \
      tests/unit/test_codex_auth.py \
      tests/unit/test_codex_client.py \
      tests/unit/test_claude_code_cli_client.py \
      -q
  result:
    53 passed

reasoner-runtime broad:
  command:
    PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/contracts/src \
      .venv/bin/python -m pytest -q \
      --ignore=tests/regression/test_with_shared_fixtures.py
  result:
    passed

reasoner-runtime diff check:
  command:
    git diff --check origin/main..HEAD
  result:
    passed before push

assembly targeted:
  command:
    PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python -m pytest -q \
      -p no:cacheprovider \
      tests/cli/test_setup.py \
      tests/cli/test_main.py \
      tests/bootstrap/test_plan.py
  result:
    59 passed

assembly docs/smoke/registry/cli/bootstrap:
  command:
    PYTHONDONTWRITEBYTECODE=1 .venv-py312/bin/python -m pytest -q \
      -p no:cacheprovider \
      tests/release/test_docs.py \
      tests/smoke \
      tests/registry \
      tests/cli/test_setup.py \
      tests/cli/test_main.py \
      tests/bootstrap/test_plan.py
  result:
    passed

assembly diff check:
  command:
    git diff --check origin/main..HEAD
  result:
    passed before push
```

Read-only and packaging boundary:

- This report records LLM backend setup wiring evidence only.
- It does not implement a managed sidecar runtime.
- It does not introduce a backend endpoint.
- It does not introduce any command/run/freeze/release-freeze surface.
- It does not modify frontend-api route behavior.
- It does not promote `frontend-api`, reasoner-runtime, or assembly LLM setup
  into the old verified compatibility matrix rows.
- Host subscription backends remain host-managed/runtime-only until a separate
  container packaging story installs required CLIs and handles auth material
  explicitly.
- Local `.orchestrator`, `.env`, virtualenv, cache, tmp, build, dist, egg-info,
  and report artifacts are not part of this evidence and were not committed.

Matrix boundary:

- `compatibility-matrix.yaml` verified rows remain unchanged.
- `module-registry.yaml`, `MODULE_REGISTRY.md`, and assembly `README.md` remain
  unchanged by this evidence.
- Future promotion into verified matrix rows requires a separate fresh
  contract/smoke/e2e evidence run and matching `verified_at` update.
