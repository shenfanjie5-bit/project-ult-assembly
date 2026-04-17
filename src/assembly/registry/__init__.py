"""Registry schemas and consistency helpers."""

from assembly.registry.schema import (
    CompatibilityMatrix,
    CompatibilityMatrixEntry,
    CompatibilityModuleVersion,
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
    "CompatibilityMatrix",
    "CompatibilityMatrixEntry",
    "CompatibilityModuleVersion",
    "IntegrationStatus",
    "ModuleRegistryEntry",
    "PublicEntrypoint",
    "RegistryError",
    "RegistryInconsistentError",
    "assert_md_yaml_consistent",
    "load_registry_yaml",
    "parse_registry_md",
]
