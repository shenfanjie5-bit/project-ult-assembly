from __future__ import annotations

import urllib.error
from pathlib import Path
from subprocess import CompletedProcess
from typing import Sequence

from assembly.contracts.models import HealthStatus
from assembly.health import probes_builtin
from assembly.health.probes_builtin import build_builtin_probes
from assembly.profiles.loader import load_profile
from assembly.profiles.resolver import ResolvedConfigSnapshot, render_profile


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROFILES_ROOT = PROJECT_ROOT / "profiles"
BUNDLES_ROOT = PROJECT_ROOT / "bundles"


def test_postgres_socket_failure_returns_blocked(
    monkeypatch,
) -> None:
    def fail_connect(address: tuple[str, int], timeout: float):
        raise OSError("connection refused")

    monkeypatch.setattr(probes_builtin.socket, "create_connection", fail_connect)
    result = build_builtin_probes(_snapshot())["postgres-ready"].check(
        timeout_sec=0.1
    )

    assert result.status == HealthStatus.blocked
    assert result.module_id == "postgres"
    assert "connection refused" in result.details["failure_reason"]


def test_neo4j_socket_failure_returns_blocked(monkeypatch) -> None:
    def fail_connect(address: tuple[str, int], timeout: float):
        raise TimeoutError("timed out")

    monkeypatch.setattr(probes_builtin.socket, "create_connection", fail_connect)
    result = build_builtin_probes(_snapshot())["neo4j-ready"].check(timeout_sec=0.1)

    assert result.status == HealthStatus.blocked
    assert result.module_id == "neo4j"
    assert result.details["port"] == "7687"


def test_dagster_daemon_non_running_compose_state_returns_blocked() -> None:
    def command_runner(command: Sequence[str]) -> CompletedProcess[str]:
        return CompletedProcess(list(command), 0, stdout="", stderr="")

    result = build_builtin_probes(
        _snapshot(),
        command_runner=command_runner,
    )["dagster-daemon-ready"].check(timeout_sec=0.1)

    assert result.status == HealthStatus.blocked
    assert result.module_id == "dagster-daemon"
    assert result.details["exit_code"] == "1"


def test_dagster_webserver_http_error_returns_blocked(monkeypatch) -> None:
    def fail_urlopen(url: str, timeout: float):
        raise urllib.error.HTTPError(url, 503, "unavailable", hdrs=None, fp=None)

    monkeypatch.setattr(probes_builtin.urllib.request, "urlopen", fail_urlopen)
    result = build_builtin_probes(_snapshot())["dagster-webserver-ready"].check(
        timeout_sec=0.1
    )

    assert result.status == HealthStatus.blocked
    assert result.module_id == "dagster-webserver"
    assert result.details["status_code"] == "503"


def _snapshot() -> ResolvedConfigSnapshot:
    return render_profile(
        "lite-local",
        profiles_root=PROFILES_ROOT,
        bundles_root=BUNDLES_ROOT,
        env=_env(),
    )


def _env() -> dict[str, str]:
    profile = load_profile(PROFILES_ROOT / "lite-local.yaml")
    values = {key: f"value-for-{key.lower()}" for key in profile.required_env_keys}
    values.update(
        {
            "POSTGRES_HOST": "127.0.0.1",
            "POSTGRES_PORT": "5432",
            "NEO4J_URI": "bolt://127.0.0.1:7687",
            "DAGSTER_HOST": "127.0.0.1",
            "DAGSTER_PORT": "3000",
        }
    )
    return values

