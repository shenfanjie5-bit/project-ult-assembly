"""Public smoke-suite API."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

from assembly.contracts.models import IntegrationRunRecord
from assembly.profiles.resolver import render_profile
from assembly.registry import (
    CompatibilityMatrixEntry,
    ModuleRegistryEntry,
    Registry,
    load_all,
    resolve_for_profile,
)
from assembly.tests.smoke.runner import SmokeSuite


def run_smoke(
    profile_id: str,
    *,
    profiles_root: Path = Path("profiles"),
    bundles_root: Path = Path("bundles"),
    registry_root: Path = Path("."),
    reports_dir: Path = Path("reports/smoke"),
    env: Mapping[str, str] | None = None,
    extra_bundles: Sequence[str] | None = None,
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
        extra_bundles=extra_bundles,
    ).model_copy(
        update={
            "enabled_modules": [entry.module_id for entry in resolved_entries],
        }
    )
    matrix_entry = _select_matrix_entry(registry, profile_id, resolved_entries)
    return SmokeSuite().run(
        snapshot,
        registry,
        timeout_sec=timeout_sec,
        reports_dir=reports_dir,
        matrix_entry=matrix_entry,
    )


def _select_matrix_entry(
    registry: Registry,
    profile_id: str,
    resolved_entries: Sequence[ModuleRegistryEntry],
) -> CompatibilityMatrixEntry:
    expected_versions = {
        entry.module_id: entry.module_version for entry in resolved_entries
    }
    for matrix_entry in registry.compatibility_matrix:
        if matrix_entry.profile_id != profile_id or matrix_entry.status == "deprecated":
            continue

        matrix_versions = {
            module.module_id: module.module_version
            for module in matrix_entry.module_set
        }
        if matrix_versions == expected_versions:
            return matrix_entry

    raise LookupError(
        f"No active compatibility matrix entry matches profile {profile_id}"
    )


__all__ = [
    "SmokeSuite",
    "run_smoke",
]
