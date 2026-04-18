from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

try:
    import click  # noqa: F401
    from click.testing import CliRunner

    from assembly.cli import main
    from assembly.cli.main import entrypoint
    from assembly.contracts.models import IntegrationRunRecord
    from assembly.contracts.reporting import compatibility_context_artifact
    from assembly.registry import (
        CompatibilityMatrixEntry,
        IntegrationStatus,
        ReleaseFreezeError,
        VersionLock,
        VersionLockModule,
        VersionLockRunRef,
    )

    CLICK_AVAILABLE = True
except ModuleNotFoundError:
    CLICK_AVAILABLE = False
    CliRunner = None  # type: ignore[assignment]
    entrypoint = None  # type: ignore[assignment]
    main = None  # type: ignore[assignment]
    IntegrationStatus = None  # type: ignore[assignment]
    ReleaseFreezeError = None  # type: ignore[assignment]
    VersionLock = None  # type: ignore[assignment]
    VersionLockModule = None  # type: ignore[assignment]
    VersionLockRunRef = None  # type: ignore[assignment]

pytestmark = pytest.mark.skipif(
    not CLICK_AVAILABLE,
    reason="click is not installed in the sandbox interpreter",
)


def test_help_lists_release_freeze() -> None:
    result = CliRunner().invoke(entrypoint, ["--help"])

    assert result.exit_code == 0
    for command in (
        "list-profiles",
        "render-profile",
        "bootstrap",
        "shutdown",
        "healthcheck",
        "smoke",
        "contract-suite",
        "e2e",
        "export-registry",
        "release-freeze",
    ):
        assert command in result.output


def test_release_freeze_success_prints_lock_profile_and_module_count(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    lock_file = tmp_path / "version-lock/2026-04-18-lite-local.yaml"

    def fake_execute_release_freeze(profile_id: str, **kwargs: object) -> VersionLock:
        return _version_lock(profile_id, lock_file)

    monkeypatch.setattr(main, "execute_release_freeze", fake_execute_release_freeze)

    result = CliRunner().invoke(
        entrypoint,
        ["release-freeze", "--profile", "lite-local", "--out", str(lock_file.parent)],
    )

    assert result.exit_code == 0
    assert f"lock={lock_file}" in result.output
    assert "profile=lite-local" in result.output
    assert "modules=1" in result.output


def test_release_freeze_maps_release_errors_without_writing_lock(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    out_dir = tmp_path / "version-lock"

    def fake_execute_release_freeze(profile_id: str, **kwargs: object) -> VersionLock:
        raise ReleaseFreezeError("verified matrix is missing supporting runs")

    monkeypatch.setattr(main, "execute_release_freeze", fake_execute_release_freeze)

    result = CliRunner().invoke(
        entrypoint,
        ["release-freeze", "--profile", "lite-local", "--out", str(out_dir)],
    )

    assert result.exit_code != 0
    assert "verified matrix is missing supporting runs" in result.output
    assert "Traceback" not in result.output
    assert not out_dir.exists()


def test_release_freeze_passes_path_options_to_executor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry_root = tmp_path / "registry-root"
    profiles_root = tmp_path / "profiles-dir"
    reports_root = tmp_path / "reports-root"
    out_dir = tmp_path / "locks"
    captured: dict[str, object] = {}

    def fake_execute_release_freeze(profile_id: str, **kwargs: object) -> VersionLock:
        captured["profile_id"] = profile_id
        captured.update(kwargs)
        return _version_lock(profile_id, out_dir / "2026-04-18-lite-local.yaml")

    monkeypatch.setattr(main, "execute_release_freeze", fake_execute_release_freeze)

    result = CliRunner().invoke(
        entrypoint,
        [
            "release-freeze",
            "--profile",
            "lite-local",
            "--registry-root",
            str(registry_root),
            "--profiles-dir",
            str(profiles_root),
            "--reports-root",
            str(reports_root),
            "--out",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0
    assert captured == {
        "profile_id": "lite-local",
        "registry_root": registry_root,
        "profiles_root": profiles_root,
        "reports_root": reports_root,
        "out_dir": out_dir,
    }


def test_release_freeze_cli_uses_real_executor_for_lock_and_failure(
    tmp_path: Path,
) -> None:
    project = _write_release_project(tmp_path / "project", include_contract=True)
    out_dir = tmp_path / "locks"

    result = CliRunner().invoke(
        entrypoint,
        [
            "release-freeze",
            "--profile",
            "lite-local",
            "--registry-root",
            str(project),
            "--profiles-dir",
            str(project / "profiles"),
            "--reports-root",
            str(project / "reports"),
            "--out",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0
    lock_path = _lock_path_from_output(result.output)
    payload = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    assert payload["profile_id"] == "lite-local"
    assert payload["matrix_version"] == "0.1.0"
    assert payload["modules"] == [
        {
            "module_id": "app",
            "module_version": "0.1.0",
            "contract_version": "v0.0.0",
            "integration_status": "verified",
        }
    ]
    assert payload["supporting_runs"][0]["run_type"] == "contract"

    failing_project = _write_release_project(
        tmp_path / "failing-project",
        include_contract=False,
    )
    failing_out_dir = tmp_path / "failing-locks"

    failing_result = CliRunner().invoke(
        entrypoint,
        [
            "release-freeze",
            "--profile",
            "lite-local",
            "--registry-root",
            str(failing_project),
            "--profiles-dir",
            str(failing_project / "profiles"),
            "--reports-root",
            str(failing_project / "reports"),
            "--out",
            str(failing_out_dir),
        ],
    )

    assert failing_result.exit_code != 0
    assert "Missing successful supporting run records" in failing_result.output
    assert "Traceback" not in failing_result.output
    assert not failing_out_dir.exists()


def _version_lock(profile_id: str, lock_file: Path) -> VersionLock:
    now = datetime(2026, 4, 18, 12, 30, tzinfo=timezone.utc)
    return VersionLock(
        lock_version="1",
        profile_id=profile_id,
        matrix_version="0.1.0",
        contract_version="v0.0.0",
        matrix_verified_at=now,
        frozen_at=now,
        required_tests=["contract-suite", "smoke", "min-cycle-e2e"],
        modules=[
            VersionLockModule(
                module_id="app",
                module_version="0.1.0",
                contract_version="v0.0.0",
                integration_status=IntegrationStatus.verified,
            )
        ],
        supporting_runs=[
            VersionLockRunRef(
                run_type="contract",
                run_id="contract-success",
                status="success",
                path=Path("reports/contract/contract-success.json"),
            )
        ],
        source_artifacts={
            "module_registry_md": "MODULE_REGISTRY.md",
            "module_registry_yaml": "module-registry.yaml",
            "compatibility_matrix_yaml": "compatibility-matrix.yaml",
        },
        lock_file=lock_file,
    )


def _write_release_project(root: Path, *, include_contract: bool) -> Path:
    root.mkdir(parents=True)
    modules = [_release_module()]
    matrix_entry = CompatibilityMatrixEntry.model_validate(
        {
            "matrix_version": "0.1.0",
            "profile_id": "lite-local",
            "module_set": [{"module_id": "app", "module_version": "0.1.0"}],
            "contract_version": "v0.0.0",
            "required_tests": ["contract-suite"],
            "status": "verified",
            "verified_at": "2026-04-17T09:00:00Z",
        }
    )

    profiles_root = root / "profiles"
    profiles_root.mkdir()
    (profiles_root / "lite-local.yaml").write_text(
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
                "notes": "release cli e2e profile",
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
        _release_registry_markdown(modules),
        encoding="utf-8",
    )
    (root / "compatibility-matrix.yaml").write_text(
        yaml.safe_dump([matrix_entry.model_dump(mode="json")], sort_keys=False),
        encoding="utf-8",
    )

    if include_contract:
        _write_contract_record(root / "reports/contract/contract-success.json", matrix_entry)

    return root


def _release_module() -> dict[str, object]:
    return {
        "module_id": "app",
        "module_version": "0.1.0",
        "contract_version": "v0.0.0",
        "owner": "test",
        "upstream_modules": [],
        "downstream_modules": [],
        "public_entrypoints": [],
        "depends_on": [],
        "supported_profiles": ["lite-local"],
        "integration_status": "verified",
        "last_smoke_result": None,
        "notes": "release cli test module",
    }


def _write_contract_record(
    path: Path,
    matrix_entry: CompatibilityMatrixEntry,
) -> None:
    now = datetime(2026, 4, 18, 12, 30, tzinfo=timezone.utc)
    record = IntegrationRunRecord(
        run_id="contract-success",
        profile_id="lite-local",
        run_type="contract",
        started_at=now,
        finished_at=now,
        status="success",
        artifacts=[
            {"kind": "contract_report", "path": str(path)},
            compatibility_context_artifact(matrix_entry),
        ],
        failing_modules=[],
        summary="contract succeeded",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(record.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )


def _release_registry_markdown(modules: list[dict[str, object]]) -> str:
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
            + " | ".join(
                _release_markdown_value(column, module[column]) for column in columns
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def _release_markdown_value(column: str, value: object) -> str:
    if column in {
        "upstream_modules",
        "downstream_modules",
        "depends_on",
        "supported_profiles",
    }:
        return ", ".join(value)  # type: ignore[arg-type]
    if column == "public_entrypoints":
        return ""
    if column == "last_smoke_result" and value is None:
        return "null"
    return str(value)


def _lock_path_from_output(output: str) -> Path:
    lock_cell = next(cell for cell in output.strip().split("\t") if cell.startswith("lock="))
    return Path(lock_cell.removeprefix("lock="))
