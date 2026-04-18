from __future__ import annotations

import json
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from assembly.compat import CompatibilityPromotionError, run_contract_suite
from assembly.compat.runner import promote_matrix_entry
from assembly.contracts import VersionInfo
from assembly.contracts.models import IntegrationRunRecord
from assembly.registry import CompatibilityMatrixEntry, RegistryResolutionError, load_all

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_run_contract_suite_writes_default_lite_partial_report(
    tmp_path: Path,
) -> None:
    reports_dir = tmp_path / "reports/contract"

    report = run_contract_suite(
        "lite-local",
        profiles_root=PROJECT_ROOT / "profiles",
        bundles_root=PROJECT_ROOT / "bundles",
        registry_root=PROJECT_ROOT,
        reports_dir=reports_dir,
        env=_env_from_example(),
        timeout_sec=1.0,
    )

    assert report.run_record.run_type == "contract"
    assert report.run_record.status == "partial"
    assert report.matrix_version == "0.1.0"
    assert report.report_path.exists()
    payload = json.loads(report.report_path.read_text(encoding="utf-8"))
    assert payload["run_record"]["run_type"] == "contract"
    assert payload["run_record"]["failing_modules"]
    assert payload["checks"]
    assert payload["matrix_version"] == "0.1.0"


def test_runner_fails_fast_on_matrix_extra_modules(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_app_module(monkeypatch)
    project = _write_project(
        tmp_path,
        modules=[_module_data("app"), _module_data("extra")],
        profile_modules=["app"],
        matrix_modules=[
            {"module_id": "app", "module_version": "0.1.0"},
            {"module_id": "extra", "module_version": "0.1.0"},
        ],
    )

    with pytest.raises(RegistryResolutionError, match="extra"):
        run_contract_suite(
            "full-local",
            profiles_root=project / "profiles",
            bundles_root=project / "bundles",
            registry_root=project,
            reports_dir=project / "reports/contract",
            env={},
        )


def test_promote_rejects_missing_smoke_e2e_records_and_preserves_matrix(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_app_module(monkeypatch)
    project = _write_project(
        tmp_path,
        modules=[_module_data("app")],
        profile_modules=["app"],
        matrix_modules=[{"module_id": "app", "module_version": "0.1.0"}],
        required_tests=["contract-suite", "smoke", "min-cycle-e2e"],
    )

    with pytest.raises(CompatibilityPromotionError, match="missing successful"):
        run_contract_suite(
            "full-local",
            profiles_root=project / "profiles",
            bundles_root=project / "bundles",
            registry_root=project,
            reports_dir=project / "reports/contract",
            env={},
            promote=True,
        )

    matrix = yaml.safe_load((project / "compatibility-matrix.yaml").read_text())
    assert matrix[0]["status"] == "draft"
    assert matrix[0]["verified_at"] is None


def test_promote_updates_matrix_when_required_runs_succeeded(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_app_module(monkeypatch)
    project = _write_project(
        tmp_path,
        modules=[_module_data("app")],
        profile_modules=["app"],
        matrix_modules=[{"module_id": "app", "module_version": "0.1.0"}],
        required_tests=["contract-suite", "smoke", "min-cycle-e2e"],
    )
    _write_run_record(project / "reports/smoke/smoke-success.json", "smoke")
    _write_run_record(project / "reports/e2e/e2e-success.json", "e2e")

    report = run_contract_suite(
        "full-local",
        profiles_root=project / "profiles",
        bundles_root=project / "bundles",
        registry_root=project,
        reports_dir=project / "reports/contract",
        env={},
        promote=True,
    )

    assert report.run_record.status == "success"
    assert report.promoted is True
    reloaded = load_all(project)
    assert reloaded.compatibility_matrix[0].status == "verified"
    assert reloaded.compatibility_matrix[0].verified_at is not None


def test_promote_rejects_deprecated_matrix_entry(tmp_path: Path) -> None:
    project = _write_project(
        tmp_path,
        modules=[_module_data("app")],
        profile_modules=["app"],
        matrix_modules=[{"module_id": "app", "module_version": "0.1.0"}],
        matrix_status="deprecated",
    )
    matrix_entry = CompatibilityMatrixEntry.model_validate(
        yaml.safe_load((project / "compatibility-matrix.yaml").read_text())[0]
    )

    with pytest.raises(CompatibilityPromotionError, match="Deprecated"):
        promote_matrix_entry(
            "full-local",
            registry_root=project,
            reports_root=project / "reports",
            matrix_entry=matrix_entry,
            contract_run_record=_run_record("contract"),
        )


def _env_from_example() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator:
            values[key] = value
    return values


class FakeVersionDeclaration:
    def declare(self) -> VersionInfo:
        return VersionInfo(
            module_id="app",
            module_version="0.1.0",
            contract_version="v0.0.0",
            compatible_contract_range=">=0.0.0 <1.0.0",
        )


class FakeCliEntrypoint:
    def invoke(self, argv: list[str]) -> int:
        return 0


def _install_app_module(monkeypatch: pytest.MonkeyPatch) -> None:
    module = types.ModuleType("compat_app_public")
    module.version_declaration = FakeVersionDeclaration()
    module.cli = FakeCliEntrypoint()
    monkeypatch.setitem(sys.modules, "compat_app_public", module)


def _write_project(
    root: Path,
    *,
    modules: list[dict[str, object]],
    profile_modules: list[str],
    matrix_modules: list[dict[str, str]],
    required_tests: list[str] | None = None,
    matrix_status: str = "draft",
) -> Path:
    (root / "profiles").mkdir(parents=True)
    (root / "bundles").mkdir()
    (root / "profiles/full-local.yaml").write_text(
        yaml.safe_dump(
            {
                "profile_id": "full-local",
                "mode": "full",
                "enabled_modules": profile_modules,
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
    (root / "module-registry.yaml").write_text(
        yaml.safe_dump(modules, sort_keys=False),
        encoding="utf-8",
    )
    (root / "MODULE_REGISTRY.md").write_text(
        _registry_markdown(modules),
        encoding="utf-8",
    )
    (root / "compatibility-matrix.yaml").write_text(
        yaml.safe_dump(
            [
                {
                    "matrix_version": "0.1.0",
                    "profile_id": "full-local",
                    "module_set": matrix_modules,
                    "contract_version": "v0.0.0",
                    "required_tests": required_tests or ["contract-suite"],
                    "status": matrix_status,
                    "verified_at": None,
                }
            ],
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return root


def _module_data(module_id: str) -> dict[str, object]:
    return {
        "module_id": module_id,
        "module_version": "0.1.0",
        "contract_version": "v0.0.0",
        "owner": "test",
        "upstream_modules": [],
        "downstream_modules": [],
        "public_entrypoints": [
            {
                "name": "version",
                "kind": "version_declaration",
                "reference": "compat_app_public:version_declaration",
            },
            {
                "name": "cli",
                "kind": "cli",
                "reference": "compat_app_public:cli",
            },
        ],
        "depends_on": [],
        "supported_profiles": ["full-local"],
        "integration_status": "partial",
        "last_smoke_result": None,
        "notes": "test module",
    }


def _registry_markdown(modules: list[dict[str, object]]) -> str:
    columns = [
        "module_id",
        "module_version",
        "contract_version",
        "owner",
        "upstream_modules",
        "downstream_modules",
        "public_entrypoints",
        "depends_on",
        "supported_profiles",
        "integration_status",
        "last_smoke_result",
        "notes",
    ]
    lines = [
        "# MODULE_REGISTRY",
        "",
        "| " + " | ".join(columns) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
    ]
    for module in modules:
        row = {column: _markdown_value(column, module[column]) for column in columns}
        lines.append("| " + " | ".join(row[column] for column in columns) + " |")
    return "\n".join(lines) + "\n"


def _markdown_value(column: str, value: object) -> str:
    if column in {
        "upstream_modules",
        "downstream_modules",
        "depends_on",
        "supported_profiles",
    }:
        return ", ".join(value)  # type: ignore[arg-type]
    if column == "public_entrypoints":
        return "; ".join(
            f"{entry['name']}:{entry['kind']}={entry['reference']}"
            for entry in value  # type: ignore[union-attr]
        )
    if column == "last_smoke_result" and value is None:
        return "null"
    return str(value)


def _write_run_record(path: Path, run_type: str) -> None:
    record = _run_record(run_type)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(record.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )


def _run_record(run_type: str) -> IntegrationRunRecord:
    now = datetime.now(timezone.utc)
    return IntegrationRunRecord(
        run_id=f"{run_type}-success",
        profile_id="full-local",
        run_type=run_type,  # type: ignore[arg-type]
        started_at=now,
        finished_at=now,
        status="success",
        artifacts=[{"kind": f"{run_type}_report", "path": f"reports/{run_type}.json"}],
        failing_modules=[],
        summary=f"{run_type} succeeded",
    )
