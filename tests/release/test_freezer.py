from __future__ import annotations

import json
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

import assembly.registry.freezer as freezer
from assembly.compat import run_contract_suite
from assembly.contracts import HealthResult, HealthStatus, SmokeResult, VersionInfo
from assembly.contracts.models import IntegrationRunRecord
from assembly.contracts.reporting import compatibility_context_artifact
from assembly.registry import (
    CompatibilityMatrixEntry,
    ReleaseFreezeError,
    freeze,
    freeze_profile,
    load_all,
)
from assembly.tests.e2e import run_min_cycle_e2e
from assembly.tests.smoke import run_smoke


_NOW = datetime(2026, 4, 18, 12, 30, tzinfo=timezone.utc)
_VERIFIED_AT = datetime(2026, 4, 17, 9, 0, tzinfo=timezone.utc)


def test_freeze_profile_writes_stable_version_lock(tmp_path: Path) -> None:
    project = _write_project(tmp_path)
    _write_required_run_records(project)

    lock = freeze_profile(
        "lite-local",
        registry_root=project,
        reports_root=project / "reports",
        out_dir=project / "version-lock",
        now=_NOW,
    )

    assert lock.lock_file == project / "version-lock/2026-04-18-lite-local.yaml"
    payload = yaml.safe_load(lock.lock_file.read_text(encoding="utf-8"))
    assert list(payload) == [
        "lock_version",
        "profile_id",
        "matrix_version",
        "contract_version",
        "matrix_verified_at",
        "frozen_at",
        "required_tests",
        "modules",
        "supporting_runs",
        "source_artifacts",
        "lock_file",
    ]
    assert payload["profile_id"] == "lite-local"
    assert payload["matrix_version"] == "0.1.0"
    assert payload["contract_version"] == "v0.0.0"
    assert payload["required_tests"] == [
        "contract-suite",
        "smoke",
        "min-cycle-e2e",
    ]
    assert payload["modules"] == [
        {
            "module_id": "app",
            "module_version": "0.1.0",
            "contract_version": "v0.0.0",
            "integration_status": "verified",
        }
    ]
    assert {run["run_type"] for run in payload["supporting_runs"]} == {
        "contract",
        "smoke",
        "e2e",
    }
    assert payload["source_artifacts"] == {
        "module_registry_md": str(project / "MODULE_REGISTRY.md"),
        "module_registry_yaml": str(project / "module-registry.yaml"),
        "compatibility_matrix_yaml": str(project / "compatibility-matrix.yaml"),
    }

    first_text = lock.lock_file.read_text(encoding="utf-8")
    second = freeze_profile(
        "lite-local",
        registry_root=project,
        reports_root=project / "reports",
        out_dir=project / "version-lock",
        now=_NOW,
    )
    assert second.lock_file == lock.lock_file
    assert second.lock_file.read_text(encoding="utf-8") == first_text


def test_freeze_profile_accepts_real_runner_records(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_release_public_module(monkeypatch, "release_orchestrator_public")
    project = _write_real_runner_project(tmp_path, "release_orchestrator_public")
    fixture_dir = _write_release_fixture(project)

    smoke_record = run_smoke(
        "full-local",
        profiles_root=project / "profiles",
        bundles_root=project / "bundles",
        registry_root=project,
        reports_dir=project / "reports/smoke",
        env={},
        timeout_sec=1.0,
    )
    e2e_record = run_min_cycle_e2e(
        "full-local",
        profiles_root=project / "profiles",
        bundles_root=project / "bundles",
        registry_root=project,
        fixture_dir=fixture_dir,
        reports_dir=project / "reports/e2e",
        env={},
        timeout_sec=1.0,
        bootstrap_if_needed=False,
    )
    contract_report = run_contract_suite(
        "full-local",
        profiles_root=project / "profiles",
        bundles_root=project / "bundles",
        registry_root=project,
        reports_dir=project / "reports/contract",
        env={},
        timeout_sec=1.0,
        promote=True,
    )

    assert smoke_record.status == "success"
    assert e2e_record.status == "success"
    assert contract_report.run_record.status == "success"
    assert contract_report.promoted is True
    for record in (smoke_record, e2e_record, contract_report.run_record):
        assert any(
            artifact["kind"] == "compatibility_context"
            for artifact in record.artifacts
        )

    lock = freeze_profile(
        "full-local",
        registry_root=project,
        reports_root=project / "reports",
        out_dir=project / "version-lock",
        now=_NOW,
    )

    assert lock.lock_file.exists()
    assert {run.run_type for run in lock.supporting_runs} == {
        "contract",
        "smoke",
        "e2e",
    }


def test_freeze_rejects_draft_matrix(tmp_path: Path) -> None:
    project = _write_project(tmp_path, matrix_status="draft", verified_at=None)

    with pytest.raises(ReleaseFreezeError, match="No verified"):
        freeze_profile(
            "lite-local",
            registry_root=project,
            reports_root=project / "reports",
            out_dir=project / "version-lock",
            now=_NOW,
        )

    assert not (project / "version-lock").exists()


def test_freeze_rejects_deprecated_matrix(tmp_path: Path) -> None:
    project = _write_project(tmp_path, matrix_status="deprecated", verified_at=None)

    with pytest.raises(ReleaseFreezeError, match="No verified"):
        freeze_profile(
            "lite-local",
            registry_root=project,
            reports_root=project / "reports",
            out_dir=project / "version-lock",
            now=_NOW,
        )

    assert not (project / "version-lock").exists()


def test_freeze_rejects_profile_without_verified_entry(tmp_path: Path) -> None:
    project = _write_project(tmp_path, matrix_profile_id="full-dev")

    with pytest.raises(ReleaseFreezeError, match="No verified"):
        freeze_profile(
            "lite-local",
            registry_root=project,
            reports_root=project / "reports",
            out_dir=project / "version-lock",
            now=_NOW,
        )

    assert not (project / "version-lock").exists()


def test_freeze_rejects_multiple_verified_entries(tmp_path: Path) -> None:
    project = _write_project(tmp_path, extra_verified=True)

    with pytest.raises(ReleaseFreezeError, match="Multiple verified"):
        freeze_profile(
            "lite-local",
            registry_root=project,
            reports_root=project / "reports",
            out_dir=project / "version-lock",
            now=_NOW,
        )

    assert not (project / "version-lock").exists()


def test_freeze_rejects_matrix_module_set_mismatch(tmp_path: Path) -> None:
    project = _write_project(
        tmp_path,
        matrix_modules=[{"module_id": "app", "module_version": "9.9.9"}],
        extra_draft_matching=True,
    )

    with pytest.raises(ReleaseFreezeError, match="module_set"):
        freeze_profile(
            "lite-local",
            registry_root=project,
            reports_root=project / "reports",
            out_dir=project / "version-lock",
            now=_NOW,
        )

    assert not (project / "version-lock").exists()


def test_freeze_rejects_non_verified_registry_module(tmp_path: Path) -> None:
    project = _write_project(tmp_path, integration_status="ready")
    _write_required_run_records(project)

    with pytest.raises(ReleaseFreezeError, match="non-verified"):
        freeze_profile(
            "lite-local",
            registry_root=project,
            reports_root=project / "reports",
            out_dir=project / "version-lock",
            now=_NOW,
        )

    assert not (project / "version-lock").exists()


def test_freeze_rejects_missing_supporting_run_record(tmp_path: Path) -> None:
    project = _write_project(tmp_path)
    _write_required_run_records(project, include_e2e=False)

    with pytest.raises(ReleaseFreezeError, match="e2e"):
        freeze_profile(
            "lite-local",
            registry_root=project,
            reports_root=project / "reports",
            out_dir=project / "version-lock",
            now=_NOW,
        )

    assert not (project / "version-lock").exists()


def test_freeze_rejects_stale_supporting_run_record_matrix_context(tmp_path: Path) -> None:
    project = _write_project(tmp_path)
    matrix_entry = _matrix_entry(project)
    stale_data = matrix_entry.model_dump(mode="json")
    stale_data["matrix_version"] = "9.9.9"
    stale_entry = CompatibilityMatrixEntry.model_validate(stale_data)
    _write_run_record(
        project / "reports/contract/contract-success.json",
        "contract",
        matrix_entry,
    )
    _write_run_record(
        project / "reports/smoke/smoke-success.json",
        "smoke",
        stale_entry,
    )
    _write_run_record(
        project / "reports/e2e/e2e-success.json",
        "e2e",
        matrix_entry,
        nested=True,
    )

    with pytest.raises(ReleaseFreezeError, match="smoke"):
        freeze_profile(
            "lite-local",
            registry_root=project,
            reports_root=project / "reports",
            out_dir=project / "version-lock",
            now=_NOW,
        )

    assert not (project / "version-lock").exists()


def test_freeze_atomic_write_failure_preserves_existing_lock(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project = _write_project(tmp_path)
    _write_required_run_records(project)
    lock = freeze_profile(
        "lite-local",
        registry_root=project,
        reports_root=project / "reports",
        out_dir=project / "version-lock",
        now=_NOW,
    )
    original_text = lock.lock_file.read_text(encoding="utf-8")

    def fail_replace(src: object, dst: object) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(freezer.os, "replace", fail_replace)

    with pytest.raises(ReleaseFreezeError, match="atomically write"):
        freeze_profile(
            "lite-local",
            registry_root=project,
            reports_root=project / "reports",
            out_dir=project / "version-lock",
            now=_NOW,
        )

    assert lock.lock_file.read_text(encoding="utf-8") == original_text


def test_freeze_rejects_direct_draft_entry(tmp_path: Path) -> None:
    project = _write_project(tmp_path, matrix_status="draft", verified_at=None)
    registry = load_all(project)
    matrix_entry = registry.compatibility_matrix[0]

    with pytest.raises(ReleaseFreezeError, match="Only verified"):
        freeze(
            registry,
            matrix_entry,
            project / "version-lock",
            reports_root=project / "reports",
            now=_NOW,
        )

    assert not (project / "version-lock").exists()


class ReleaseHealthProbe:
    def check(self, *, timeout_sec: float) -> HealthResult:
        return HealthResult(
            module_id="orchestrator",
            probe_name="health",
            status=HealthStatus.healthy,
            latency_ms=0.0,
            message="orchestrator healthy",
            details={"timeout_sec": str(timeout_sec)},
        )


class ReleaseSmokeHook:
    def run(self, *, profile_id: str) -> SmokeResult:
        return SmokeResult(
            module_id="orchestrator",
            hook_name="smoke",
            passed=True,
            duration_ms=0.0,
            failure_reason=None,
        )


class ReleaseVersionDeclaration:
    def declare(self) -> VersionInfo:
        return VersionInfo(
            module_id="orchestrator",
            module_version="0.1.0",
            contract_version="v0.0.0",
            compatible_contract_range=">=0.0.0 <1.0.0",
        )


class ReleaseCliEntrypoint:
    def invoke(self, argv: list[str]) -> int:
        report_path = Path(argv[argv.index("--report") + 1])
        run_dir = Path(argv[argv.index("--run-artifacts-dir") + 1])
        artifact_path = run_dir / "cycle-summary.json"
        artifact_path.write_text(json.dumps({"ok": True}) + "\n", encoding="utf-8")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(
                {
                    "profile_id": argv[argv.index("--profile") + 1],
                    "phases": ["extract", "publish"],
                    "artifacts": {"cycle_summary": "cycle-summary.json"},
                    "status": "success",
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return 0


def _install_release_public_module(
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
) -> None:
    module = types.ModuleType(module_name)
    module.health_probe = ReleaseHealthProbe()
    module.smoke_hook = ReleaseSmokeHook()
    module.version_declaration = ReleaseVersionDeclaration()
    module.cli = ReleaseCliEntrypoint()
    monkeypatch.setitem(sys.modules, module_name, module)


def _write_real_runner_project(root: Path, public_module: str) -> Path:
    modules = [_real_module_data(public_module)]
    (root / "profiles").mkdir(parents=True)
    (root / "bundles").mkdir()
    (root / "profiles/full-local.yaml").write_text(
        yaml.safe_dump(
            {
                "profile_id": "full-local",
                "mode": "full",
                "enabled_modules": ["orchestrator"],
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
                "notes": "real runner freeze test profile",
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
                    "module_set": [
                        {
                            "module_id": "orchestrator",
                            "module_version": "0.1.0",
                        }
                    ],
                    "contract_version": "v0.0.0",
                    "required_tests": [
                        "contract-suite",
                        "smoke",
                        "min-cycle-e2e",
                    ],
                    "status": "draft",
                    "verified_at": None,
                }
            ],
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return root


def _write_release_fixture(root: Path) -> Path:
    fixture_dir = root / "fixture"
    fixture_dir.mkdir()
    (fixture_dir / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "scenario_id": "release-freeze-real-reports",
                "expected_phases": ["extract", "publish"],
                "required_artifacts": ["cycle_summary"],
                "orchestrator_args": [
                    "min-cycle",
                    "--profile",
                    "{profile_id}",
                    "--fixture",
                    "{fixture_manifest}",
                    "--run-artifacts-dir",
                    "{run_dir}",
                    "--report",
                    "{orchestrator_report_path}",
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return fixture_dir


def _real_module_data(public_module: str) -> dict[str, object]:
    return {
        "module_id": "orchestrator",
        "module_version": "0.1.0",
        "contract_version": "v0.0.0",
        "owner": "test",
        "upstream_modules": [],
        "downstream_modules": [],
        "public_entrypoints": [
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
            {
                "name": "version",
                "kind": "version_declaration",
                "reference": f"{public_module}:version_declaration",
            },
            {
                "name": "cli",
                "kind": "cli",
                "reference": f"{public_module}:cli",
            },
        ],
        "depends_on": [],
        "supported_profiles": ["full-local"],
        "integration_status": "verified",
        "last_smoke_result": None,
        "notes": "test module",
    }


def _write_project(
    root: Path,
    *,
    matrix_status: str = "verified",
    verified_at: datetime | None = _VERIFIED_AT,
    matrix_profile_id: str = "lite-local",
    extra_verified: bool = False,
    extra_draft_matching: bool = False,
    matrix_modules: list[dict[str, str]] | None = None,
    integration_status: str = "verified",
) -> Path:
    modules = [_module_data("app", integration_status=integration_status)]
    (root / "profiles").mkdir(parents=True)
    (root / "profiles/lite-local.yaml").write_text(
        yaml.safe_dump(
            {
                "profile_id": "lite-local",
                "mode": "lite",
                "enabled_modules": ["app"],
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
    (root / "module-registry.yaml").write_text(
        yaml.safe_dump(modules, sort_keys=False),
        encoding="utf-8",
    )
    (root / "MODULE_REGISTRY.md").write_text(
        _registry_markdown(modules),
        encoding="utf-8",
    )

    matrix = [
        _matrix_entry_data(
            profile_id=matrix_profile_id,
            status=matrix_status,
            verified_at=verified_at,
            module_set=matrix_modules
            or [{"module_id": "app", "module_version": "0.1.0"}],
        )
    ]
    if extra_verified:
        matrix.append(
            _matrix_entry_data(
                profile_id="lite-local",
                status="verified",
                verified_at=_VERIFIED_AT,
                matrix_version="0.2.0",
            )
        )
    if extra_draft_matching:
        matrix.append(
            _matrix_entry_data(
                profile_id="lite-local",
                status="draft",
                verified_at=None,
                matrix_version="0.3.0",
            )
        )
    (root / "compatibility-matrix.yaml").write_text(
        yaml.safe_dump(matrix, sort_keys=False),
        encoding="utf-8",
    )
    return root


def _matrix_entry_data(
    *,
    profile_id: str,
    status: str,
    verified_at: datetime | None,
    matrix_version: str = "0.1.0",
    module_set: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    return {
        "matrix_version": matrix_version,
        "profile_id": profile_id,
        "module_set": module_set
        or [{"module_id": "app", "module_version": "0.1.0"}],
        "contract_version": "v0.0.0",
        "required_tests": ["contract-suite", "smoke", "min-cycle-e2e"],
        "status": status,
        "verified_at": None
        if verified_at is None
        else verified_at.isoformat().replace("+00:00", "Z"),
    }


def _module_data(module_id: str, *, integration_status: str) -> dict[str, object]:
    return {
        "module_id": module_id,
        "module_version": "0.1.0",
        "contract_version": "v0.0.0",
        "owner": "test",
        "upstream_modules": [],
        "downstream_modules": [],
        "public_entrypoints": [],
        "depends_on": [],
        "supported_profiles": ["lite-local"],
        "integration_status": integration_status,
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
        lines.append(
            "| "
            + " | ".join(_markdown_value(column, module[column]) for column in columns)
            + " |"
        )
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


def _write_required_run_records(
    project: Path,
    *,
    include_e2e: bool = True,
) -> None:
    matrix_entry = _matrix_entry(project)
    _write_run_record(
        project / "reports/contract/contract-success.json",
        "contract",
        matrix_entry,
    )
    _write_run_record(
        project / "reports/smoke/smoke-success.json",
        "smoke",
        matrix_entry,
    )
    if include_e2e:
        _write_run_record(
            project / "reports/e2e/e2e-success.json",
            "e2e",
            matrix_entry,
            nested=True,
        )
    assert matrix_entry.status == "verified"


def _matrix_entry(project: Path) -> CompatibilityMatrixEntry:
    return CompatibilityMatrixEntry.model_validate(
        yaml.safe_load((project / "compatibility-matrix.yaml").read_text())[0]
    )


def _write_run_record(
    path: Path,
    run_type: str,
    matrix_entry: CompatibilityMatrixEntry,
    *,
    nested: bool = False,
) -> None:
    record = _run_record(run_type, path, matrix_entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: object = (
        {"run_record": record.model_dump(mode="json")}
        if nested
        else record.model_dump(mode="json")
    )
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _run_record(
    run_type: str,
    path: Path,
    matrix_entry: CompatibilityMatrixEntry,
) -> IntegrationRunRecord:
    return IntegrationRunRecord(
        run_id=f"{run_type}-success",
        profile_id="lite-local",
        run_type=run_type,  # type: ignore[arg-type]
        started_at=_NOW,
        finished_at=_NOW,
        status="success",
        artifacts=[
            {"kind": f"{run_type}_report", "path": str(path)},
            compatibility_context_artifact(matrix_entry),
        ],
        failing_modules=[],
        summary=f"{run_type} succeeded",
    )
