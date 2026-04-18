from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

import assembly.registry.freezer as freezer
from assembly.contracts.models import IntegrationRunRecord
from assembly.registry import (
    CompatibilityMatrixEntry,
    ReleaseFreezeError,
    freeze,
    freeze_profile,
    load_all,
)


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
        return ""
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
            _compatibility_context_artifact(matrix_entry),
        ],
        failing_modules=[],
        summary=f"{run_type} succeeded",
    )


def _compatibility_context_artifact(
    matrix_entry: CompatibilityMatrixEntry,
) -> dict[str, str]:
    module_set = sorted(
        (
            {
                "module_id": module.module_id,
                "module_version": module.module_version,
            }
            for module in matrix_entry.module_set
        ),
        key=lambda item: (item["module_id"], item["module_version"]),
    )
    matrix_context = {
        "profile_id": matrix_entry.profile_id,
        "matrix_version": matrix_entry.matrix_version,
        "contract_version": matrix_entry.contract_version,
        "module_set": module_set,
    }
    return {
        "kind": "compatibility_context",
        "profile_id": matrix_entry.profile_id,
        "matrix_version": matrix_entry.matrix_version,
        "contract_version": matrix_entry.contract_version,
        "module_set_digest": _stable_digest(module_set),
        "matrix_digest": _stable_digest(matrix_context),
    }


def _stable_digest(payload: object) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
