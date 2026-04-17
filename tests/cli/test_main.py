from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from assembly.contracts import HealthResult, HealthStatus, IntegrationRunRecord
from assembly.profiles.loader import load_profile

try:
    import click  # noqa: F401
    from click.testing import CliRunner

    from assembly.bootstrap.runner import ComposeCommandError
    from assembly.cli import main
    from assembly.cli.main import entrypoint
    from assembly.registry import RegistryExport

    CLICK_AVAILABLE = True
except ModuleNotFoundError:
    CLICK_AVAILABLE = False
    CliRunner = None  # type: ignore[assignment]
    ComposeCommandError = None  # type: ignore[assignment]
    RegistryExport = None  # type: ignore[assignment]
    entrypoint = None  # type: ignore[assignment]
    main = None  # type: ignore[assignment]

pytestmark = pytest.mark.skipif(
    not CLICK_AVAILABLE,
    reason="click is not installed in the sandbox interpreter",
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROFILES_ROOT = PROJECT_ROOT / "profiles"
BUNDLES_ROOT = PROJECT_ROOT / "bundles"


def test_entrypoint_help_lists_subcommands() -> None:
    result = CliRunner().invoke(entrypoint, ["--help"])

    assert result.exit_code == 0
    for command in (
        "list-profiles",
        "render-profile",
        "bootstrap",
        "shutdown",
        "healthcheck",
        "smoke",
        "export-registry",
    ):
        assert command in result.output


def test_module_invocation_help_lists_subcommands() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    result = subprocess.run(
        [sys.executable, "-m", "assembly.cli.main", "--help"],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "list-profiles" in result.stdout
    assert "healthcheck" in result.stdout
    assert "smoke" in result.stdout
    assert "export-registry" in result.stdout


def test_pyproject_registers_assembly_script() -> None:
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib

    payload = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())

    assert payload["project"]["scripts"]["assembly"] == (
        "assembly.cli.main:entrypoint"
    )


def test_list_profiles_outputs_lite_local() -> None:
    result = CliRunner().invoke(
        entrypoint,
        ["list-profiles", "--profiles-dir", str(PROFILES_ROOT)],
    )

    assert result.exit_code == 0
    assert "lite-local" in result.output


def test_render_profile_writes_redacted_snapshot(tmp_path: Path) -> None:
    env_file = _write_env_file(tmp_path / ".env")
    out = tmp_path / "snapshot.json"

    result = CliRunner().invoke(
        entrypoint,
        [
            "render-profile",
            "--profile",
            "lite-local",
            "--profiles-dir",
            str(PROFILES_ROOT),
            "--bundles-dir",
            str(BUNDLES_ROOT),
            "--env-file",
            str(env_file),
            "--out",
            str(out),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["profile_id"] == "lite-local"
    assert payload["required_env"]["POSTGRES_PASSWORD"] == "<redacted>"
    assert "plain-postgres-password" not in out.read_text(encoding="utf-8")


def test_bootstrap_dry_run_prints_plan_without_docker(tmp_path: Path) -> None:
    env_file = _write_env_file(tmp_path / ".env")
    report_path = tmp_path / "reports/bootstrap/dry-run.json"

    result = CliRunner().invoke(
        entrypoint,
        [
            "bootstrap",
            "--profile",
            "lite-local",
            "--profiles-dir",
            str(PROFILES_ROOT),
            "--bundles-dir",
            str(BUNDLES_ROOT),
            "--env-file",
            str(env_file),
            "--out",
            str(report_path),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "postgres -> neo4j -> dagster-daemon -> dagster-webserver" in result.output
    assert (
        f"docker compose --env-file {env_file} -f compose/lite-local.yaml up -d --wait "
        "postgres neo4j dagster-daemon dagster-webserver"
    ) in result.output
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["dry_run"] is True
    assert [stage["status"] for stage in payload["stages"]] == [
        "passed",
        "planned",
        "planned",
        "planned",
    ]


def test_shutdown_dry_run_prints_stop_plan(tmp_path: Path) -> None:
    env_file = _write_env_file(tmp_path / ".env")

    result = CliRunner().invoke(
        entrypoint,
        [
            "shutdown",
            "--profile",
            "lite-local",
            "--profiles-dir",
            str(PROFILES_ROOT),
            "--bundles-dir",
            str(BUNDLES_ROOT),
            "--env-file",
            str(env_file),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "dagster-webserver -> dagster-daemon -> neo4j -> postgres" in result.output
    assert (
        f"docker compose --env-file {env_file} -f compose/lite-local.yaml stop "
        "dagster-webserver dagster-daemon neo4j postgres"
    ) in result.output


@pytest.mark.parametrize(
    ("status", "expected_exit_code"),
    [
        (HealthStatus.healthy, 0),
        (HealthStatus.degraded, 1),
        (HealthStatus.blocked, 2),
    ],
)
def test_healthcheck_cli_maps_health_status_to_exit_code(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    status: HealthStatus,
    expected_exit_code: int,
) -> None:
    out = tmp_path / "health.json"

    def fake_healthcheck(profile_id: str, **kwargs: object) -> list[HealthResult]:
        return [
            HealthResult(
                module_id="postgres",
                probe_name="postgres-ready",
                status=status,
                latency_ms=0.0,
                message=status.value,
            )
        ]

    monkeypatch.setattr(main, "execute_healthcheck", fake_healthcheck)

    result = CliRunner().invoke(
        entrypoint,
        [
            "healthcheck",
            "--profile",
            "lite-local",
            "--timeout-sec",
            "1",
            "--out",
            str(out),
        ],
    )

    assert result.exit_code == expected_exit_code
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload[0]["status"] == status.value


def test_healthcheck_cli_uses_env_file_then_process_env_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "POSTGRES_HOST=file-host\nONLY_IN_FILE=file-value\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("POSTGRES_HOST", "process-host")
    captured: dict[str, object] = {}

    def fake_healthcheck(profile_id: str, **kwargs: object) -> list[HealthResult]:
        captured.update(kwargs)
        return [
            HealthResult(
                module_id="postgres",
                probe_name="postgres-ready",
                status=HealthStatus.healthy,
                latency_ms=0.0,
                message="healthy",
            )
        ]

    monkeypatch.setattr(main, "execute_healthcheck", fake_healthcheck)

    result = CliRunner().invoke(
        entrypoint,
        ["healthcheck", "--env-file", str(env_file)],
    )

    assert result.exit_code == 0
    env = captured["env"]
    assert env["POSTGRES_HOST"] == "process-host"
    assert env["ONLY_IN_FILE"] == "file-value"


def test_smoke_cli_maps_failed_record_to_exit_code_and_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_smoke(profile_id: str, **kwargs: object) -> IntegrationRunRecord:
        reports_dir = kwargs["reports_dir"]
        report_path = reports_dir / "fake-smoke.json"
        report_path.write_text('{"status":"failed"}\n', encoding="utf-8")
        now = datetime.now(timezone.utc)
        return IntegrationRunRecord(
            run_id="fake-smoke",
            profile_id="lite-local",
            run_type="smoke",
            started_at=now,
            finished_at=now,
            status="failed",
            artifacts=[{"kind": "smoke_report", "path": str(report_path)}],
            failing_modules=["assembly"],
            summary="Smoke failed",
        )

    monkeypatch.setattr(main, "execute_smoke", fake_smoke)

    result = CliRunner().invoke(
        entrypoint,
        ["smoke", "--profile", "lite-local", "--reports-dir", str(tmp_path)],
    )

    assert result.exit_code == 2
    assert (tmp_path / "fake-smoke.json").exists()
    assert "failed\tfake-smoke\tfailing=assembly" in result.output


def test_bootstrap_maps_runner_error_to_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    env_file = _write_env_file(tmp_path / ".env")
    report_path = tmp_path / "reports/bootstrap/failure.json"

    class FailingRunner:
        def __init__(self, env_file: Path | None = None) -> None:
            self.env_file = env_file

        def start(self, plan: object) -> object:
            raise ComposeCommandError(
                [
                    "docker",
                    "compose",
                    "--env-file",
                    str(self.env_file),
                    "up",
                ],
                1,
                stderr="docker unavailable",
            )

    monkeypatch.setattr(main, "Runner", FailingRunner)

    result = CliRunner().invoke(
        entrypoint,
        [
            "bootstrap",
            "--profile",
            "lite-local",
            "--profiles-dir",
            str(PROFILES_ROOT),
            "--bundles-dir",
            str(BUNDLES_ROOT),
            "--env-file",
            str(env_file),
            "--out",
            str(report_path),
        ],
    )

    assert result.exit_code != 0
    assert f"docker compose --env-file {env_file} up" in result.output
    assert "docker unavailable" in result.output
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["stages"][-1]["name"] == "service_startup"
    assert payload["stages"][-1]["status"] == "failed"


def test_export_registry_writes_runtime_artifacts(tmp_path: Path) -> None:
    out = tmp_path / "registry-export"

    result = CliRunner().invoke(
        entrypoint,
        ["export-registry", "--out", str(out)],
    )

    assert result.exit_code == 0
    assert (out / "MODULE_REGISTRY.md").exists()
    assert json.loads((out / "registry.json").read_text(encoding="utf-8"))
    assert json.loads((out / "matrix.json").read_text(encoding="utf-8"))
    assert "modules=14" in result.output
    assert "matrix=1" in result.output


def test_export_registry_cli_uses_runtime_exporter(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    out = tmp_path / "registry-export"
    fake_registry = object()
    calls: dict[str, object] = {}

    def fake_load_all(root: Path) -> object:
        calls["load_root"] = root
        return fake_registry

    def fake_export_module_registry(
        registry: object,
        out_dir: Path,
        *,
        root: Path,
    ) -> object:
        calls["registry"] = registry
        calls["out_dir"] = out_dir
        calls["export_root"] = root
        return RegistryExport(
            out_dir=out_dir,
            registry_json=out_dir / "registry.json",
            matrix_json=out_dir / "matrix.json",
            registry_md=out_dir / "MODULE_REGISTRY.md",
            module_count=2,
            matrix_count=3,
        )

    monkeypatch.setattr(main, "load_all", fake_load_all)
    monkeypatch.setattr(main, "export_module_registry", fake_export_module_registry)

    result = CliRunner().invoke(
        entrypoint,
        ["export-registry", "--out", str(out)],
    )

    assert result.exit_code == 0
    assert calls == {
        "load_root": Path("."),
        "registry": fake_registry,
        "out_dir": out,
        "export_root": Path("."),
    }
    assert "modules=2" in result.output
    assert "matrix=3" in result.output


def _write_env_file(path: Path) -> Path:
    profile = load_profile(PROFILES_ROOT / "lite-local.yaml")
    values = []
    for key in profile.required_env_keys:
        if key == "POSTGRES_PASSWORD":
            value = "plain-postgres-password"
        elif key == "NEO4J_PASSWORD":
            value = "plain-neo4j-password"
        else:
            value = f"value-for-{key.lower()}"
        values.append(f"{key}={value}")

    values.extend(f"{key}=" for key in profile.optional_env_keys)
    path.write_text("\n".join(values) + "\n", encoding="utf-8")
    return path
