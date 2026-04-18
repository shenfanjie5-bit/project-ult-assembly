# Startup Guide

This guide lists the minimum repeatable commands for local assembly workflows.
The registry and public entrypoint boundaries are described in
[PUBLIC_ENTRYPOINTS.md](PUBLIC_ENTRYPOINTS.md), and release locking is described
in [VERSION_LOCK.md](VERSION_LOCK.md).

## Environment

Create a local `.env` from `.env.example` and fill every key required by the
selected profile. The CLI reads `.env` first and lets process environment
variables override those values.

```bash
cp .env.example .env
```

## Direct API

Use the public Python APIs when tests or automation need to avoid Click.

```bash
PYTHONPATH=src python3 - <<'PY'
from pathlib import Path
from assembly.profiles.loader import list_profiles
from assembly.profiles.resolver import render_profile
from assembly.bootstrap import bootstrap
from assembly.health import healthcheck
from assembly.tests.smoke import run_smoke
from assembly.compat import run_contract_suite
from assembly.tests.e2e import run_min_cycle_e2e
from assembly.registry import export_module_registry, load_all
from assembly.registry.freezer import freeze_profile

profiles = list_profiles(Path("profiles"))
snapshot = render_profile("lite-local")
registry = load_all(Path("."))
print([profile.profile_id for profile in profiles])
print(snapshot.profile_id, len(registry.modules))

# Long-running actions are explicit:
# bootstrap("lite-local")
# healthcheck("lite-local")
# run_smoke("lite-local")
# run_contract_suite("lite-local")
# run_min_cycle_e2e("lite-local")
# export_module_registry(registry)
# freeze_profile("lite-local")
PY
```

## CLI Commands

List profiles:

```bash
PYTHONPATH=src python3 -m assembly.cli.main list-profiles
```

Render the Lite profile:

```bash
PYTHONPATH=src python3 -m assembly.cli.main render-profile \
  --profile lite-local \
  --env-file .env \
  --out reports/bootstrap/lite-local-resolved-config.json
```

Bootstrap Lite without starting Docker, then run the real bootstrap when the
plan is correct:

```bash
PYTHONPATH=src python3 -m assembly.cli.main bootstrap \
  --profile lite-local \
  --env-file .env \
  --dry-run

PYTHONPATH=src python3 -m assembly.cli.main bootstrap \
  --profile lite-local \
  --env-file .env
```

Shutdown Lite:

```bash
PYTHONPATH=src python3 -m assembly.cli.main shutdown \
  --profile lite-local \
  --env-file .env
```

Run health, smoke, contract, and e2e:

```bash
PYTHONPATH=src python3 -m assembly.cli.main healthcheck \
  --profile lite-local \
  --env-file .env \
  --out reports/health/lite-local.json

PYTHONPATH=src python3 -m assembly.cli.main smoke \
  --profile lite-local \
  --env-file .env \
  --reports-dir reports/smoke

PYTHONPATH=src python3 -m assembly.cli.main contract-suite \
  --profile lite-local \
  --env-file .env \
  --reports-dir reports/contract

PYTHONPATH=src python3 -m assembly.cli.main e2e \
  --profile lite-local \
  --env-file .env \
  --reports-dir reports/e2e
```

Export registry artifacts:

```bash
PYTHONPATH=src python3 -m assembly.cli.main export-registry \
  --out reports/registry
```

Freeze a verified release baseline:

```bash
PYTHONPATH=src python3 -m assembly.cli.main release-freeze \
  --profile lite-local \
  --reports-root reports \
  --out version-lock
```

## Full Dev

The default `full-dev` profile uses only the core service bundles:
`postgres`, `neo4j`, and `dagster`.

```bash
PYTHONPATH=src python3 -m assembly.cli.main render-profile \
  --profile full-dev \
  --env-file .env \
  --out reports/bootstrap/full-dev-resolved-config.json
```

Optional service bundles are enabled only when explicitly requested. Use
`full-dev --extra-bundles=...` for slots such as MinIO and Grafana:

```bash
PYTHONPATH=src python3 -m assembly.cli.main bootstrap \
  --profile full-dev \
  --env-file .env \
  --extra-bundles=minio,grafana \
  --dry-run
```

The same explicit optional bundle list must be used for matching shutdown or
render commands when those optional services are part of the selected run.
