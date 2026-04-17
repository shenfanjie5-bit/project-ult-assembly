from __future__ import annotations

import json
from pathlib import Path
from subprocess import CompletedProcess
from typing import Sequence

import assembly.bootstrap as bootstrap_api
import pytest

from assembly.bootstrap.plan import BootstrapPlan, BootstrapService
from assembly.bootstrap.runner import (
    BootstrapResult,
    ComposeCommandError,
    DockerComposeUnavailableError,
    Runner,
)
from assembly.contracts.models import HealthResult, SmokeResult
from assembly.profiles.loader import load_profile

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROFILES_ROOT = PROJECT_ROOT / "profiles"
BUNDLES_ROOT = PROJECT_ROOT / "bundles"
COMPOSE_FILE = PROJECT_ROOT / "compose/lite-local.yaml"


def test_runner_start_uses_docker_compose_wait_in_startup_order() -> None:
    calls: list[list[str]] = []

    def fake_runner(command: Sequence[str]) -> CompletedProcess[str]:
        calls.append(list(command))
        return CompletedProcess(list(command), 0, stdout="started", stderr="")

    plan = _plan()
    result = Runner(command_runner=fake_runner).start(plan)

    assert calls == [
        [
            "docker",
            "compose",
            "-f",
            "compose/lite-local.yaml",
            "up",
            "-d",
            "--wait",
            "postgres",
            "neo4j",
            "dagster-daemon",
            "dagster-webserver",
        ]
    ]
    assert result.service_order == plan.startup_order
    assert [handle.compose_service for handle in result.handles] == plan.startup_order


def test_runner_stop_uses_plan_shutdown_order() -> None:
    calls: list[list[str]] = []

    def fake_runner(command: Sequence[str]) -> CompletedProcess[str]:
        calls.append(list(command))
        return CompletedProcess(list(command), 0, stdout="stopped", stderr="")

    plan = _plan()
    result = Runner(command_runner=fake_runner).stop(plan)

    assert calls == [
        [
            "docker",
            "compose",
            "-f",
            "compose/lite-local.yaml",
            "stop",
            "dagster-webserver",
            "dagster-daemon",
            "neo4j",
            "postgres",
        ]
    ]
    assert result.service_order == plan.shutdown_order


def test_runner_threads_env_file_into_compose_commands(tmp_path: Path) -> None:
    calls: list[list[str]] = []
    env_file = tmp_path / ".env"
    env_file.write_text("POSTGRES_DB=assembly\n", encoding="utf-8")

    def fake_runner(command: Sequence[str]) -> CompletedProcess[str]:
        calls.append(list(command))
        return CompletedProcess(list(command), 0, stdout="", stderr="")

    plan = _plan()
    runner = Runner(command_runner=fake_runner, env_file=env_file)

    start_result = runner.start(plan)
    stop_result = runner.stop(plan)
    start_result.handles[0].poll()

    assert calls[0] == [
        "docker",
        "compose",
        "--env-file",
        str(env_file),
        "-f",
        "compose/lite-local.yaml",
        "up",
        "-d",
        "--wait",
        "postgres",
        "neo4j",
        "dagster-daemon",
        "dagster-webserver",
    ]
    assert calls[1] == [
        "docker",
        "compose",
        "--env-file",
        str(env_file),
        "-f",
        "compose/lite-local.yaml",
        "stop",
        "dagster-webserver",
        "dagster-daemon",
        "neo4j",
        "postgres",
    ]
    assert calls[2] == [
        "docker",
        "compose",
        "--env-file",
        str(env_file),
        "-f",
        "compose/lite-local.yaml",
        "ps",
        "--status",
        "running",
        "-q",
        "postgres",
    ]
    assert start_result.command == calls[0]
    assert stop_result.command == calls[1]


def test_runner_maps_nonzero_compose_result_to_command_error() -> None:
    def fake_runner(command: Sequence[str]) -> CompletedProcess[str]:
        return CompletedProcess(list(command), 2, stdout="", stderr="compose failed")

    with pytest.raises(ComposeCommandError) as exc_info:
        Runner(command_runner=fake_runner).start(_plan())

    message = str(exc_info.value)
    assert "docker compose" in message
    assert "exit code 2" in message
    assert exc_info.value.stderr == "compose failed"


def test_runner_maps_missing_docker_to_unavailable_error() -> None:
    def fake_runner(command: Sequence[str]) -> CompletedProcess[str]:
        raise FileNotFoundError("docker")

    with pytest.raises(DockerComposeUnavailableError) as exc_info:
        Runner(command_runner=fake_runner).start(_plan())

    assert "docker compose" in str(exc_info.value)
    assert exc_info.value.returncode == 127


def test_service_handle_poll_and_terminate_use_injected_runner() -> None:
    calls: list[list[str]] = []

    def fake_runner(command: Sequence[str]) -> CompletedProcess[str]:
        calls.append(list(command))
        return CompletedProcess(list(command), 0, stdout="container-id\n", stderr="")

    handle = Runner(command_runner=fake_runner).start(_plan()).handles[0]

    assert handle.poll() is None
    handle.terminate()
    assert calls[-2:] == [
        [
            "docker",
            "compose",
            "-f",
            "compose/lite-local.yaml",
            "ps",
            "--status",
            "running",
            "-q",
            "postgres",
        ],
        [
            "docker",
            "compose",
            "-f",
            "compose/lite-local.yaml",
            "stop",
            "postgres",
        ],
    ]


def test_bootstrap_helper_loads_profile_by_id_without_filename_assumption(
    tmp_path: Path,
) -> None:
    profiles_root = tmp_path / "profiles"
    profiles_root.mkdir()
    profile_path = profiles_root / "renamed-profile.yaml"
    profile_path.write_text(
        (Path(__file__).resolve().parents[2] / "profiles/lite-local.yaml").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    profile = load_profile(profile_path)
    env = {key: f"value-for-{key.lower()}" for key in profile.required_env_keys}

    class FakeRunner:
        def start(self, plan: BootstrapPlan) -> BootstrapResult:
            return BootstrapResult(
                profile_id=plan.profile_id,
                action="start",
                command=["docker", "compose", "up"],
                service_order=list(plan.startup_order),
                returncode=0,
            )

    result = bootstrap_api.bootstrap(
        "lite-local",
        profiles_root=profiles_root,
        bundle_root=Path(__file__).resolve().parents[2] / "bundles",
        compose_file=Path(__file__).resolve().parents[2] / "compose/lite-local.yaml",
        env=env,
        runner=FakeRunner(),
        report_path=tmp_path / "reports/bootstrap/helper.json",
        orchestrator_entrypoint=_HealthyOrchestrator(),
        smoke_hooks=[_PassingSmokeHook()],
    )

    assert result.service_order == [
        "postgres",
        "neo4j",
        "dagster-daemon",
        "dagster-webserver",
    ]


def test_bootstrap_executes_boundaries_after_services_and_writes_report(
    tmp_path: Path,
) -> None:
    profile = load_profile(PROFILES_ROOT / "lite-local.yaml")
    env = {key: f"value-for-{key.lower()}" for key in profile.required_env_keys}
    calls: list[str] = []

    class FakeRunner:
        def start(self, plan: BootstrapPlan) -> BootstrapResult:
            calls.append("service_startup")
            return BootstrapResult(
                profile_id=plan.profile_id,
                action="start",
                command=["docker", "compose", "up"],
                service_order=list(plan.startup_order),
                returncode=0,
            )

    class RecordingOrchestrator(_HealthyOrchestrator):
        def check(self, *, timeout_sec: float) -> HealthResult:
            calls.append("orchestrator_entrypoint")
            return super().check(timeout_sec=timeout_sec)

    class RecordingSmokeHook(_PassingSmokeHook):
        def run(self, *, profile_id: str) -> SmokeResult:
            calls.append(f"public_smoke:{profile_id}")
            return super().run(profile_id=profile_id)

    report_path = tmp_path / "reports/bootstrap/lite-local.json"

    result = bootstrap_api.bootstrap(
        "lite-local",
        profiles_root=PROFILES_ROOT,
        bundle_root=BUNDLES_ROOT,
        compose_file=COMPOSE_FILE,
        env=env,
        runner=FakeRunner(),
        report_path=report_path,
        orchestrator_entrypoint=RecordingOrchestrator(),
        smoke_hooks=[RecordingSmokeHook()],
    )

    assert calls == [
        "service_startup",
        "orchestrator_entrypoint",
        "public_smoke:lite-local",
    ]
    assert [stage.name for stage in result.stage_results] == [
        "env_filesystem_readiness",
        "service_startup",
        "orchestrator_entrypoint_readiness",
        "public_smoke_probes",
    ]
    assert all(stage.status == "passed" for stage in result.stage_results)
    assert report_path.exists()
    assert "reports/bootstrap" in str(report_path)
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert [stage["name"] for stage in payload["stages"]] == [
        "env_filesystem_readiness",
        "service_startup",
        "orchestrator_entrypoint_readiness",
        "public_smoke_probes",
    ]


def _plan() -> BootstrapPlan:
    startup_order = [
        "postgres",
        "neo4j",
        "dagster-daemon",
        "dagster-webserver",
    ]
    shutdown_order = [
        "dagster-webserver",
        "dagster-daemon",
        "neo4j",
        "postgres",
    ]
    return BootstrapPlan(
        profile_id="lite-local",
        mode="lite",
        compose_file=Path("compose/lite-local.yaml"),
        services=[
            BootstrapService(
                name=name,
                bundle_name="dagster" if name.startswith("dagster") else name,
                compose_service=name,
                image_or_cmd=name,
                health_probe=f"{name}-ready",
            )
            for name in startup_order
        ],
        startup_order=startup_order,
        shutdown_order=shutdown_order,
    )


class _HealthyOrchestrator:
    def check(self, *, timeout_sec: float) -> HealthResult:
        return HealthResult(
            module_id="orchestrator",
            probe_name="health",
            status="healthy",
            latency_ms=timeout_sec,
            message="ready",
        )


class _PassingSmokeHook:
    def run(self, *, profile_id: str) -> SmokeResult:
        return SmokeResult(
            module_id="contracts",
            hook_name=f"{profile_id}-smoke",
            passed=True,
            duration_ms=1.0,
        )
