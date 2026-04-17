from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from assembly.registry import (
    CompatibilityMatrixEntry,
    IntegrationStatus,
    ModuleRegistryEntry,
    Registry,
    RegistryResolutionError,
    load_all,
    resolve_for_profile,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_resolve_for_profile_matches_real_lite_profile_modules() -> None:
    registry = load_all(PROJECT_ROOT)
    entries = resolve_for_profile(
        registry,
        "lite-local",
        profiles_root=PROJECT_ROOT / "profiles",
    )
    profile = yaml.safe_load(
        (PROJECT_ROOT / "profiles/lite-local.yaml").read_text(encoding="utf-8")
    )

    assert [entry.module_id for entry in entries] == profile["enabled_modules"]


def test_resolve_for_profile_topologically_sorts_dependencies(
    tmp_path: Path,
) -> None:
    _write_profile(tmp_path, ["app", "base", "mid"])
    registry = _registry(
        tmp_path,
        [
            _module("app", depends_on=["mid"]),
            _module("base"),
            _module("mid", depends_on=["base"]),
        ],
    )

    entries = resolve_for_profile(registry, "lite-local")

    assert [entry.module_id for entry in entries] == ["base", "mid", "app"]


def test_resolve_for_profile_missing_dependency_raises(tmp_path: Path) -> None:
    _write_profile(tmp_path, ["app"])
    registry = _registry(tmp_path, [_module("app", depends_on=["missing"])])

    with pytest.raises(RegistryResolutionError, match="missing module missing"):
        resolve_for_profile(registry, "lite-local")


def test_resolve_for_profile_dependency_must_support_profile(
    tmp_path: Path,
) -> None:
    _write_profile(tmp_path, ["app", "base"])
    registry = _registry(
        tmp_path,
        [
            _module("app", depends_on=["base"]),
            _module("base", supported_profiles=["full-local"]),
        ],
    )

    with pytest.raises(RegistryResolutionError, match="does not support"):
        resolve_for_profile(registry, "lite-local")


def test_resolve_for_profile_rejects_disabled_dependency(tmp_path: Path) -> None:
    _write_profile(tmp_path, ["app"])
    registry = _registry(
        tmp_path,
        [
            _module("app", depends_on=["base"]),
            _module("base"),
        ],
        matrix_modules=["app"],
    )

    with pytest.raises(RegistryResolutionError, match="does not enable"):
        resolve_for_profile(registry, "lite-local")


def test_resolve_for_profile_rejects_blocked_modules(tmp_path: Path) -> None:
    _write_profile(tmp_path, ["app"])
    registry = _registry(
        tmp_path,
        [_module("app", integration_status=IntegrationStatus.blocked.value)],
    )

    with pytest.raises(RegistryResolutionError, match="blocked"):
        resolve_for_profile(registry, "lite-local")


def test_resolve_for_profile_allows_not_started_modules(tmp_path: Path) -> None:
    _write_profile(tmp_path, ["app"])
    registry = _registry(
        tmp_path,
        [_module("app", integration_status=IntegrationStatus.not_started.value)],
    )

    entries = resolve_for_profile(registry, "lite-local")

    assert [entry.module_id for entry in entries] == ["app"]


def test_resolve_for_profile_detects_dependency_cycles(tmp_path: Path) -> None:
    _write_profile(tmp_path, ["app", "base"])
    registry = _registry(
        tmp_path,
        [
            _module("app", depends_on=["base"]),
            _module("base", depends_on=["app"]),
        ],
    )

    with pytest.raises(RegistryResolutionError, match="Dependency cycle"):
        resolve_for_profile(registry, "lite-local")


def test_resolve_for_profile_requires_matrix_for_profile(tmp_path: Path) -> None:
    _write_profile(tmp_path, ["app"])
    registry = _registry(
        tmp_path,
        [_module("app")],
        matrix_profile_id="full-local",
    )

    with pytest.raises(RegistryResolutionError, match="No compatibility matrix"):
        resolve_for_profile(registry, "lite-local")


def test_resolve_for_profile_requires_matrix_to_cover_versions(
    tmp_path: Path,
) -> None:
    _write_profile(tmp_path, ["app"])
    registry = _registry(
        tmp_path,
        [_module("app", module_version="1.2.3")],
        matrix_versions={"app": "9.9.9"},
    )

    with pytest.raises(RegistryResolutionError, match="version_mismatches"):
        resolve_for_profile(registry, "lite-local")


def _registry(
    root: Path,
    modules: list[ModuleRegistryEntry],
    *,
    matrix_profile_id: str = "lite-local",
    matrix_modules: list[str] | None = None,
    matrix_versions: dict[str, str] | None = None,
) -> Registry:
    module_ids = matrix_modules or [module.module_id for module in modules]
    versions = {
        module.module_id: module.module_version
        for module in modules
    }
    versions.update(matrix_versions or {})

    return Registry(
        root=root,
        modules=modules,
        compatibility_matrix=[
            CompatibilityMatrixEntry.model_validate(
                {
                    "matrix_version": "0.1.0",
                    "profile_id": matrix_profile_id,
                    "module_set": [
                        {
                            "module_id": module_id,
                            "module_version": versions[module_id],
                        }
                        for module_id in module_ids
                    ],
                    "contract_version": "v0.0.0",
                    "required_tests": ["contract-suite"],
                    "status": "draft",
                    "verified_at": None,
                }
            )
        ],
    )


def _module(
    module_id: str,
    *,
    module_version: str = "0.1.0",
    depends_on: list[str] | None = None,
    supported_profiles: list[str] | None = None,
    integration_status: str = "partial",
) -> ModuleRegistryEntry:
    return ModuleRegistryEntry.model_validate(
        {
            "module_id": module_id,
            "module_version": module_version,
            "contract_version": "v0.0.0",
            "owner": "test",
            "upstream_modules": [],
            "downstream_modules": [],
            "public_entrypoints": [],
            "depends_on": depends_on or [],
            "supported_profiles": supported_profiles or ["lite-local"],
            "integration_status": integration_status,
            "last_smoke_result": None,
            "notes": "test module",
        }
    )


def _write_profile(root: Path, enabled_modules: list[str]) -> None:
    profiles_root = root / "profiles"
    profiles_root.mkdir(parents=True, exist_ok=True)
    (profiles_root / "lite-local.yaml").write_text(
        yaml.safe_dump(
            {
                "profile_id": "lite-local",
                "mode": "lite",
                "enabled_modules": enabled_modules,
                "enabled_service_bundles": [],
                "required_env_keys": [],
                "optional_env_keys": [],
                "storage_backends": {},
                "resource_expectation": {
                    "cpu_cores": 1,
                    "memory_gb": 1,
                    "disk_gb": 1,
                },
                "max_long_running_daemons": 4,
                "notes": "test profile",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
