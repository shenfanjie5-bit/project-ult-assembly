"""YAML loaders for assembly profile schemas."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from assembly.profiles.errors import (
    ProfileConstraintError,
    ProfileNotFoundError,
    ProfileSchemaError,
)
from assembly.profiles.schema import EnvironmentProfile, ServiceBundleManifest


ProfileModel = TypeVar("ProfileModel", bound=BaseModel)


def load_profile(path: Path) -> EnvironmentProfile:
    """Load and validate an EnvironmentProfile YAML file."""

    return _validate_yaml_model(path, EnvironmentProfile)


def load_bundle(path: Path) -> ServiceBundleManifest:
    """Load and validate a ServiceBundleManifest YAML file."""

    return _validate_yaml_model(path, ServiceBundleManifest)


def list_profiles(root: Path = Path("profiles")) -> list[EnvironmentProfile]:
    """Load every profile YAML file under root in deterministic order."""

    return [load_profile(path) for path in _iter_yaml_files(root)]


def list_bundles(root: Path = Path("bundles")) -> list[ServiceBundleManifest]:
    """Load every service bundle YAML file under root in deterministic order."""

    return [load_bundle(path) for path in _iter_yaml_files(root)]


def _validate_yaml_model(path: Path, model_type: type[ProfileModel]) -> ProfileModel:
    data = _load_yaml_mapping(path)
    try:
        return model_type.model_validate(data)
    except ProfileConstraintError as exc:
        raise ProfileSchemaError(f"Invalid schema in {path}: {exc}") from exc
    except ValidationError as exc:
        raise ProfileSchemaError(f"Invalid schema in {path}: {exc}") from exc


def _load_yaml_mapping(path: Path) -> dict[str, object]:
    path = Path(path)
    if not path.exists():
        raise ProfileNotFoundError(f"Profile manifest not found: {path}")

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise ProfileSchemaError(_format_yaml_error(path, exc)) from exc

    if data is None:
        data = {}

    if not isinstance(data, dict):
        raise ProfileSchemaError(
            f"Invalid schema in {path}: YAML root must be a mapping"
        )

    return data


def _format_yaml_error(path: Path, exc: yaml.YAMLError) -> str:
    mark = getattr(exc, "problem_mark", None)
    location = ""
    if mark is not None:
        location = f" at line {mark.line + 1}, column {mark.column + 1}"

    return f"Invalid YAML in {path}{location}: {exc}"


def _iter_yaml_files(root: Path) -> list[Path]:
    root = Path(root)
    if not root.exists():
        return []

    paths = [path for path in root.iterdir() if path.suffix in {".yaml", ".yml"}]
    return sorted(paths)
