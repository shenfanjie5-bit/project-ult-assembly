"""Public smoke-suite API."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from assembly.contracts.models import IntegrationRunRecord
from assembly.profiles.resolver import render_profile
from assembly.registry import load_all, resolve_for_profile
from assembly.tests.smoke.runner import SmokeSuite


def run_smoke(
    profile_id: str,
    *,
    profiles_root: Path = Path("profiles"),
    bundles_root: Path = Path("bundles"),
    registry_root: Path = Path("."),
    reports_dir: Path = Path("reports/smoke"),
    env: Mapping[str, str] | None = None,
    timeout_sec: float = 30.0,
) -> IntegrationRunRecord:
    """Resolve a profile and run the system-level smoke suite."""

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
    return SmokeSuite().run(
        snapshot,
        registry,
        timeout_sec=timeout_sec,
        reports_dir=reports_dir,
    )


__all__ = [
    "SmokeSuite",
    "run_smoke",
]
