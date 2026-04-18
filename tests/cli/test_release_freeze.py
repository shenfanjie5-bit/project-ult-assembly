from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

try:
    import click  # noqa: F401
    from click.testing import CliRunner

    from assembly.cli import main
    from assembly.cli.main import entrypoint
    from assembly.registry import (
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
