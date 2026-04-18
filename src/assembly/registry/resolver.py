"""Resolve registry modules for an environment profile."""

from __future__ import annotations

from pathlib import Path

from assembly.profiles.errors import ProfileError
from assembly.profiles.loader import load_profile
from assembly.registry.loader import Registry
from assembly.registry.schema import IntegrationStatus, ModuleRegistryEntry
from assembly.registry.validator import RegistryError


class RegistryResolutionError(RegistryError):
    """Raised when registry facts cannot be resolved for a profile."""


def resolve_for_profile(
    registry: Registry,
    profile_id: str,
    *,
    profiles_root: Path = Path("profiles"),
) -> list[ModuleRegistryEntry]:
    """Return profile-enabled modules in dependency order."""

    profile_path = _profile_path(registry.root, profiles_root, profile_id)
    try:
        profile = load_profile(profile_path)
    except ProfileError as exc:
        raise RegistryResolutionError(str(exc)) from exc

    if profile.profile_id != profile_id:
        raise RegistryResolutionError(
            f"Profile artifact {profile_path} declares profile_id "
            f"{profile.profile_id!r}, expected {profile_id!r}"
        )

    registry_by_id = _entries_by_id(registry.modules)
    enabled_ids = list(profile.enabled_modules)
    enabled_id_set = set(enabled_ids)

    for module_id in enabled_ids:
        if module_id not in registry_by_id:
            raise RegistryResolutionError(
                f"Profile {profile_id} enables unregistered module {module_id}"
            )

        entry = registry_by_id[module_id]
        if profile_id not in entry.supported_profiles:
            raise RegistryResolutionError(
                f"Module {module_id} does not support profile {profile_id}"
            )

        if entry.integration_status == IntegrationStatus.blocked:
            raise RegistryResolutionError(
                f"Module {module_id} is blocked for profile {profile_id}"
            )

        for dependency_id in entry.depends_on:
            if dependency_id not in registry_by_id:
                raise RegistryResolutionError(
                    f"Module {module_id} depends on missing module {dependency_id}"
                )

            dependency = registry_by_id[dependency_id]
            if profile_id not in dependency.supported_profiles:
                raise RegistryResolutionError(
                    f"Dependency {dependency_id} for module {module_id} "
                    f"does not support profile {profile_id}"
                )

            if dependency_id not in enabled_id_set:
                raise RegistryResolutionError(
                    f"Module {module_id} depends on {dependency_id}, "
                    f"but profile {profile_id} does not enable it"
                )

    resolved = _topological_sort(enabled_ids, registry_by_id)
    _assert_matrix_covers_profile(registry, profile_id, resolved)
    return resolved


def _profile_path(root: Path, profiles_root: Path, profile_id: str) -> Path:
    profiles_root = Path(profiles_root)
    if not profiles_root.is_absolute():
        profiles_root = Path(root) / profiles_root

    return profiles_root / f"{profile_id}.yaml"


def _entries_by_id(
    modules: list[ModuleRegistryEntry],
) -> dict[str, ModuleRegistryEntry]:
    by_id: dict[str, ModuleRegistryEntry] = {}
    duplicate_ids: list[str] = []

    for entry in modules:
        if entry.module_id in by_id:
            duplicate_ids.append(entry.module_id)
            continue

        by_id[entry.module_id] = entry

    if duplicate_ids:
        raise RegistryResolutionError(
            f"Duplicate registry module_id values: {sorted(set(duplicate_ids))}"
        )

    return by_id


def _topological_sort(
    module_ids: list[str],
    registry_by_id: dict[str, ModuleRegistryEntry],
) -> list[ModuleRegistryEntry]:
    enabled_id_set = set(module_ids)
    permanent: set[str] = set()
    temporary: list[str] = []
    sorted_entries: list[ModuleRegistryEntry] = []

    def visit(module_id: str) -> None:
        if module_id in permanent:
            return

        if module_id in temporary:
            cycle = temporary[temporary.index(module_id) :] + [module_id]
            raise RegistryResolutionError(
                f"Dependency cycle detected: {' -> '.join(cycle)}"
            )

        temporary.append(module_id)
        entry = registry_by_id[module_id]
        for dependency_id in entry.depends_on:
            if dependency_id in enabled_id_set:
                visit(dependency_id)

        temporary.pop()
        permanent.add(module_id)
        sorted_entries.append(entry)

    for module_id in module_ids:
        visit(module_id)

    return sorted_entries


def _assert_matrix_covers_profile(
    registry: Registry,
    profile_id: str,
    resolved: list[ModuleRegistryEntry],
) -> None:
    entries = [
        entry
        for entry in registry.compatibility_matrix
        if entry.profile_id == profile_id
    ]
    if not entries:
        raise RegistryResolutionError(
            f"No compatibility matrix entry found for profile {profile_id}"
        )

    expected_versions = {
        entry.module_id: entry.module_version
        for entry in resolved
    }
    mismatch_summaries: list[str] = []

    active_entries = [
        entry for entry in entries if entry.status != "deprecated"
    ]
    if not active_entries:
        raise RegistryResolutionError(
            "No active compatibility matrix entry found for profile "
            f"{profile_id}; deprecated entries cannot satisfy runtime resolution"
        )

    for matrix_entry in active_entries:
        matrix_versions = {
            module.module_id: module.module_version
            for module in matrix_entry.module_set
        }
        missing_ids = sorted(set(expected_versions) - set(matrix_versions))
        extra_ids = sorted(set(matrix_versions) - set(expected_versions))
        version_mismatches = sorted(
            module_id
            for module_id, version in expected_versions.items()
            if matrix_versions.get(module_id) not in {None, version}
        )
        if not missing_ids and not extra_ids and not version_mismatches:
            return

        details: list[str] = []
        if missing_ids:
            details.append(f"missing={missing_ids}")
        if extra_ids:
            details.append(f"extra={extra_ids}")
        if version_mismatches:
            details.append(f"version_mismatches={version_mismatches}")
        mismatch_summaries.append(
            f"{matrix_entry.matrix_version}: {', '.join(details)}"
        )

    raise RegistryResolutionError(
        "Compatibility matrix does not cover resolved modules for profile "
        f"{profile_id}: {'; '.join(mismatch_summaries)}"
    )
