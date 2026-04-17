"""Runtime loading for registry and compatibility matrix artifacts."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from assembly.registry.schema import CompatibilityMatrixEntry, ModuleRegistryEntry
from assembly.registry.validator import (
    RegistryError,
    assert_md_yaml_consistent,
    load_registry_yaml,
)


class Registry(BaseModel):
    """Runtime view of registry facts consumed by assembly modules."""

    model_config = ConfigDict(extra="forbid")

    root: Path
    modules: list[ModuleRegistryEntry]
    compatibility_matrix: list[CompatibilityMatrixEntry]


def load_all(root: Path = Path(".")) -> Registry:
    """Load all registry artifacts from a project root."""

    root = Path(root)
    registry_md = root / "MODULE_REGISTRY.md"
    registry_yaml = root / "module-registry.yaml"
    matrix_yaml = root / "compatibility-matrix.yaml"

    for path in (registry_md, registry_yaml, matrix_yaml):
        if not path.exists():
            raise RegistryError(f"Registry artifact not found: {path}")

    assert_md_yaml_consistent(registry_md, registry_yaml)

    return Registry(
        root=root,
        modules=load_registry_yaml(registry_yaml),
        compatibility_matrix=load_compatibility_matrix(matrix_yaml),
    )


def load_compatibility_matrix(path: Path) -> list[CompatibilityMatrixEntry]:
    """Load and validate the compatibility matrix artifact."""

    path = Path(path)
    if not path.exists():
        raise RegistryError(f"Compatibility matrix not found: {path}")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RegistryError(f"Invalid YAML in {path}: {exc}") from exc

    if raw is None:
        raw = []

    if not isinstance(raw, list):
        raise RegistryError(
            f"Invalid compatibility matrix in {path}: YAML root must be a list"
        )

    entries: list[CompatibilityMatrixEntry] = []
    for index, item in enumerate(raw):
        try:
            entries.append(CompatibilityMatrixEntry.model_validate(item))
        except ValidationError as exc:
            raise RegistryError(
                f"Invalid compatibility matrix entry at index {index} in {path}: {exc}"
            ) from exc

    return entries
