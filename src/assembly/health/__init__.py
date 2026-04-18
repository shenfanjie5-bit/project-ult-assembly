"""Public healthcheck API."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from assembly.contracts.models import HealthResult
from assembly.health.errors import HealthcheckError
from assembly.health.runner import HealthcheckRunner
from assembly.profiles.resolver import render_profile
from assembly.registry import load_all, resolve_for_profile


def healthcheck(
    profile_id: str,
    *,
    profiles_root: Path = Path("profiles"),
    bundles_root: Path = Path("bundles"),
    registry_root: Path = Path("."),
    env: Mapping[str, str] | None = None,
    timeout_sec: float = 30.0,
) -> list[HealthResult]:
    """Resolve a profile and run its healthcheck convergence probes."""

    registry = load_all(registry_root)
    resolved_entries = resolve_for_profile(
        registry,
        profile_id,
        profiles_root=profiles_root,
    )
    snapshot = render_profile(
        profile_id,
        profiles_root=profiles_root,
        bundles_root=bundles_root,
        env=env,
    ).model_copy(
        update={
            "enabled_modules": [entry.module_id for entry in resolved_entries],
        }
    )
    return HealthcheckRunner().run(snapshot, registry, timeout_sec=timeout_sec)


__all__ = [
    "HealthcheckError",
    "HealthcheckRunner",
    "healthcheck",
]
