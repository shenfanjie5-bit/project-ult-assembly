from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from typing import Sequence

import pytest

from assembly.bootstrap.plan import BootstrapPlan, BootstrapService
from assembly.bootstrap.runner import (
    ComposeCommandError,
    DockerComposeUnavailableError,
    Runner,
)


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
