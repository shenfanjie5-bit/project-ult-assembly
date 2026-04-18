from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Callable

import pytest
import yaml

from assembly.contracts.models import HealthResult, HealthStatus, SmokeResult
from assembly.health import healthcheck
from assembly.registry import RegistryResolutionError
from assembly.tests.smoke import run_smoke


PROFILE_ID = "test-profile"


def test_healthcheck_uses_registry_resolution_dependency_order(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    profiles_root, bundles_root = _write_profile(tmp_path, ["app", "base"])
    order: list[str] = []
    _install_public_module(monkeypatch, "base_public", "base", order)
    _install_public_module(monkeypatch, "app_public", "app", order)
    _write_registry(
        tmp_path,
        [
            _module("app", public_module="app_public", depends_on=["base"]),
            _module("base", public_module="base_public"),
        ],
    )

    results = healthcheck(
        PROFILE_ID,
        profiles_root=profiles_root,
        bundles_root=bundles_root,
        registry_root=tmp_path,
        env={},
    )

    assert order == ["health:base", "health:app"]
    assert [result.module_id for result in results] == ["base", "app"]
    assert [result.status for result in results] == [
        HealthStatus.healthy,
        HealthStatus.healthy,
    ]


def test_run_smoke_uses_registry_resolution_dependency_order(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    profiles_root, bundles_root = _write_profile(tmp_path, ["app", "base"])
    order: list[str] = []
    _install_public_module(monkeypatch, "base_public", "base", order)
    _install_public_module(monkeypatch, "app_public", "app", order)
    _write_registry(
        tmp_path,
        [
            _module("app", public_module="app_public", depends_on=["base"]),
            _module("base", public_module="base_public"),
        ],
    )

    record = run_smoke(
        PROFILE_ID,
        profiles_root=profiles_root,
        bundles_root=bundles_root,
        registry_root=tmp_path,
        reports_dir=tmp_path / "reports",
        env={},
    )

    assert order == [
        "health:base",
        "health:app",
        "smoke:base",
        "smoke:app",
    ]
    assert record.status == "success"
    assert record.failing_modules == []


@pytest.mark.parametrize(
    (
        "case_name",
        "enabled_modules",
        "modules_factory",
        "matrix_versions",
        "match",
    ),
    [
        (
            "unregistered",
            ["ghost"],
            lambda: [],
            None,
            "unregistered module ghost",
        ),
        (
            "disabled_dependency",
            ["app"],
            lambda: [_module("app", depends_on=["base"]), _module("base")],
            None,
            "does not enable",
        ),
        (
            "blocked_module",
            ["app"],
            lambda: [_module("app", integration_status="blocked")],
            None,
            "blocked",
        ),
        (
            "matrix_version_mismatch",
            ["app"],
            lambda: [_module("app", module_version="1.2.3")],
            {"app": "9.9.9"},
            "version_mismatches",
        ),
    ],
)
@pytest.mark.parametrize("api", ["healthcheck", "run_smoke"])
def test_public_runtime_apis_fail_fast_on_registry_resolution_errors(
    tmp_path: Path,
    case_name: str,
    enabled_modules: list[str],
    modules_factory: Callable[[], list[dict[str, object]]],
    matrix_versions: dict[str, str] | None,
    match: str,
    api: str,
) -> None:
    profiles_root, bundles_root = _write_profile(tmp_path, enabled_modules)
    modules = modules_factory()
    _write_registry(
        tmp_path,
        modules,
        matrix_modules=[
            str(module["module_id"])
            for module in modules
            if str(module["module_id"]) in enabled_modules
        ],
        matrix_versions=matrix_versions,
    )
    reports_dir = tmp_path / f"reports-{case_name}"

    call: Callable[[], object]
    if api == "healthcheck":
        call = lambda: healthcheck(
            PROFILE_ID,
            profiles_root=profiles_root,
            bundles_root=bundles_root,
            registry_root=tmp_path,
            env={},
        )
    else:
        call = lambda: run_smoke(
            PROFILE_ID,
            profiles_root=profiles_root,
            bundles_root=bundles_root,
            registry_root=tmp_path,
            reports_dir=reports_dir,
            env={},
        )

    with pytest.raises(RegistryResolutionError, match=match):
        call()

    assert not any(reports_dir.glob("*.json"))


def _write_profile(root: Path, enabled_modules: list[str]) -> tuple[Path, Path]:
    profiles_root = root / "profiles"
    bundles_root = root / "bundles"
    profiles_root.mkdir()
    bundles_root.mkdir()
    (profiles_root / f"{PROFILE_ID}.yaml").write_text(
        yaml.safe_dump(
            {
                "profile_id": PROFILE_ID,
                "mode": "full",
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
                "max_long_running_daemons": 1,
                "notes": "test profile",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return profiles_root, bundles_root


def _write_registry(
    root: Path,
    modules: list[dict[str, object]],
    *,
    matrix_modules: list[str] | None = None,
    matrix_versions: dict[str, str] | None = None,
) -> None:
    (root / "module-registry.yaml").write_text(
        yaml.safe_dump(modules, sort_keys=False),
        encoding="utf-8",
    )
    (root / "MODULE_REGISTRY.md").write_text(
        _registry_md(modules),
        encoding="utf-8",
    )
    versions = {
        str(module["module_id"]): str(module["module_version"])
        for module in modules
    }
    versions.update(matrix_versions or {})
    matrix_ids = matrix_modules
    if matrix_ids is None:
        matrix_ids = [str(module["module_id"]) for module in modules]
    (root / "compatibility-matrix.yaml").write_text(
        yaml.safe_dump(
            [
                {
                    "matrix_version": "0.1.0",
                    "profile_id": PROFILE_ID,
                    "module_set": [
                        {
                            "module_id": module_id,
                            "module_version": versions[module_id],
                        }
                        for module_id in matrix_ids
                    ],
                    "contract_version": "v0.0.0",
                    "required_tests": ["smoke"],
                    "status": "draft",
                    "verified_at": None,
                }
            ],
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _module(
    module_id: str,
    *,
    module_version: str = "0.1.0",
    public_module: str | None = None,
    depends_on: list[str] | None = None,
    integration_status: str = "partial",
) -> dict[str, object]:
    public_entrypoints: list[dict[str, str]] = []
    if public_module is not None:
        public_entrypoints = [
            {
                "name": "health",
                "kind": "health_probe",
                "reference": f"{public_module}:health_probe",
            },
            {
                "name": "smoke",
                "kind": "smoke_hook",
                "reference": f"{public_module}:smoke_hook",
            },
        ]

    return {
        "module_id": module_id,
        "module_version": module_version,
        "contract_version": "v0.0.0",
        "owner": "test",
        "upstream_modules": [],
        "downstream_modules": [],
        "public_entrypoints": public_entrypoints,
        "depends_on": depends_on or [],
        "supported_profiles": [PROFILE_ID],
        "integration_status": integration_status,
        "last_smoke_result": None,
        "notes": "test module",
    }


def _install_public_module(
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
    module_id: str,
    order: list[str],
) -> None:
    module = types.ModuleType(module_name)

    class HealthProbe:
        def check(self, *, timeout_sec: float) -> HealthResult:
            order.append(f"health:{module_id}")
            return HealthResult(
                module_id=module_id,
                probe_name="health",
                status=HealthStatus.healthy,
                latency_ms=0.0,
                message=f"{module_id} healthy",
                details={"timeout_sec": str(timeout_sec)},
            )

    class SmokeHook:
        def run(self, *, profile_id: str) -> SmokeResult:
            order.append(f"smoke:{module_id}")
            return SmokeResult(
                module_id=module_id,
                hook_name="smoke",
                passed=True,
                duration_ms=0.0,
                failure_reason=None,
            )

    module.health_probe = HealthProbe()
    module.smoke_hook = SmokeHook()
    monkeypatch.setitem(sys.modules, module_name, module)


def _registry_md(modules: list[dict[str, object]]) -> str:
    header = (
        "| module_id | module_version | contract_version | owner | "
        "upstream_modules | downstream_modules | public_entrypoints | "
        "depends_on | supported_profiles | integration_status | "
        "last_smoke_result | notes |"
    )
    separator = "|---|---|---|---|---|---|---|---|---|---|---|---|"
    rows = [
        "| "
        + " | ".join(
            [
                str(module["module_id"]),
                str(module["module_version"]),
                str(module["contract_version"]),
                str(module["owner"]),
                _list_cell(module["upstream_modules"]),
                _list_cell(module["downstream_modules"]),
                _entrypoints_cell(module["public_entrypoints"]),
                _list_cell(module["depends_on"]),
                _list_cell(module["supported_profiles"]),
                str(module["integration_status"]),
                "null"
                if module["last_smoke_result"] is None
                else str(module["last_smoke_result"]),
                str(module["notes"]),
            ]
        )
        + " |"
        for module in modules
    ]
    return "\n".join(["# MODULE_REGISTRY", "", header, separator, *rows]) + "\n"


def _list_cell(value: object) -> str:
    return ", ".join(str(item) for item in value)


def _entrypoints_cell(value: object) -> str:
    return "; ".join(
        f"{entrypoint['name']}:{entrypoint['kind']}={entrypoint['reference']}"
        for entrypoint in value
    )
