"""Assembly module registry namespace."""

from __future__ import annotations

from assembly.registry.schema import (
    CompatibilityMatrixEntry,
    IntegrationStatus,
    ModuleRegistryEntry,
    PublicEntrypoint,
    matrix_entry_key,
)
from assembly.registry.exporter import RegistryExport, export_module_registry
from assembly.registry.freezer import (
    ReleaseFreezeError,
    VersionLock,
    VersionLockModule,
    VersionLockRunRef,
    freeze,
    freeze_profile,
)
from assembly.registry.loader import Registry, load_all, load_compatibility_matrix
from assembly.registry.resolver import RegistryResolutionError, resolve_for_profile
from assembly.registry.validator import (
    RegistryError,
    RegistryInconsistentError,
    assert_md_yaml_consistent,
    load_registry_yaml,
    parse_registry_md,
)

__all__ = [
    "CompatibilityMatrixEntry",
    "IntegrationStatus",
    "ModuleRegistryEntry",
    "PublicEntrypoint",
    "ReleaseFreezeError",
    "Registry",
    "RegistryError",
    "RegistryExport",
    "RegistryInconsistentError",
    "RegistryResolutionError",
    "VersionLock",
    "VersionLockModule",
    "VersionLockRunRef",
    "assert_md_yaml_consistent",
    "export_module_registry",
    "freeze",
    "freeze_profile",
    "load_all",
    "load_compatibility_matrix",
    "load_registry_yaml",
    "matrix_entry_key",
    "parse_registry_md",
    "resolve_for_profile",
]
