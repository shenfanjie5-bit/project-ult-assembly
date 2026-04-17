"""Assembly module registry namespace."""

from __future__ import annotations

from assembly.registry.schema import (
    CompatibilityMatrixEntry,
    IntegrationStatus,
    ModuleRegistryEntry,
    PublicEntrypoint,
)
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
    "RegistryError",
    "RegistryInconsistentError",
    "assert_md_yaml_consistent",
    "load_registry_yaml",
    "parse_registry_md",
]
