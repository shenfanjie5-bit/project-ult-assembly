from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from assembly.profiles.loader import load_profile

try:
    import click  # noqa: F401
    from click.testing import CliRunner

    from assembly.bootstrap.runner import ComposeCommandError
    from assembly.cli import main
    from assembly.cli.main import entrypoint

    CLICK_AVAILABLE = True
except ModuleNotFoundError:
    CLICK_AVAILABLE = False
    CliRunner = None  # type: ignore[assignment]
    ComposeCommandError = None  # type: ignore[assignment]
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
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "postgres -> neo4j -> dagster-daemon -> dagster-webserver" in result.output
    assert (
        f"docker compose --env-file {env_file} -f compose/lite-local.yaml up -d --wait "
        "postgres neo4j dagster-daemon dagster-webserver"
    ) in result.output


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


def test_bootstrap_maps_runner_error_to_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    env_file = _write_env_file(tmp_path / ".env")

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
        ],
    )

    assert result.exit_code != 0
    assert f"docker compose --env-file {env_file} up" in result.output
    assert "docker unavailable" in result.output


def test_export_registry_validates_and_copies_artifacts(tmp_path: Path) -> None:
    out = tmp_path / "registry-export"

    result = CliRunner().invoke(
        entrypoint,
        ["export-registry", "--out", str(out)],
    )

    assert result.exit_code == 0
    assert (out / "MODULE_REGISTRY.md").exists()
    assert (out / "module-registry.yaml").exists()
    assert (out / "compatibility-matrix.yaml").exists()


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
