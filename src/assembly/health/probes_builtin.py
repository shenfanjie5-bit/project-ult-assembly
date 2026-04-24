"""Built-in Lite service health probes."""

from __future__ import annotations

import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from assembly.bootstrap.service_handle import CommandRunner, ServiceHandle
from assembly.contracts.models import HealthResult, HealthStatus
from assembly.contracts.protocols import HealthProbe
from assembly.profiles.resolver import ResolvedConfigSnapshot


BUILTIN_PROBE_BY_SERVICE = {
    "postgres": "postgres-ready",
    "neo4j": "neo4j-ready",
    "dagster-daemon": "dagster-daemon-ready",
    "dagster-webserver": "dagster-webserver-ready",
    # Optional bundles (full-dev --extra-bundles=...). The probe is built
    # only when the corresponding bundle appears in the resolved snapshot
    # — see ``build_builtin_probes``. Missing-from-snapshot is fine; the
    # service simply isn't enumerated in ``_builtin_probe_plan``.
    "minio": "minio-ready",
}


def build_builtin_probes(
    snapshot: ResolvedConfigSnapshot,
    *,
    compose_file: Path = Path("compose/lite-local.yaml"),
    env_file: Path | None = None,
    command_runner: CommandRunner | None = None,
) -> dict[str, HealthProbe]:
    """Build built-in health probes for the Lite service boundary.

    Optional-bundle probes (e.g. minio) are only added when the
    corresponding bundle appears in ``snapshot.service_bundles``. Their
    spec carries ``optional=True`` (per ``_builtin_probe_plan``), so a
    healthy probe → ``healthy`` and a failing probe → ``degraded`` (not
    ``blocked``). This means an opted-in optional bundle's failure
    doesn't block the e2e — degraded is the documented contract.
    """

    required_env = snapshot.required_env
    neo4j_host, neo4j_port = _neo4j_endpoint(required_env["NEO4J_URI"])

    probes: dict[str, HealthProbe] = {
        "postgres-ready": SocketPortProbe(
            module_id="postgres",
            probe_name="postgres-ready",
            host=required_env["POSTGRES_HOST"],
            port=required_env["POSTGRES_PORT"],
        ),
        "neo4j-ready": SocketPortProbe(
            module_id="neo4j",
            probe_name="neo4j-ready",
            host=neo4j_host,
            port=str(neo4j_port),
        ),
        "dagster-daemon-ready": ComposeRunningProbe(
            module_id="dagster-daemon",
            probe_name="dagster-daemon-ready",
            service_name="dagster-daemon",
            bundle_name="dagster",
            compose_file=compose_file,
            env_file=env_file,
            command_runner=command_runner,
        ),
        "dagster-webserver-ready": DagsterWebserverProbe(
            module_id="dagster-webserver",
            probe_name="dagster-webserver-ready",
            host=required_env["DAGSTER_HOST"],
            port=required_env["DAGSTER_PORT"],
        ),
    }

    bundle_names = {bundle.bundle_name for bundle in snapshot.service_bundles}
    if "minio" in bundle_names:
        # MinIO TCP-readiness on the host-bound port. Default 9000 matches
        # ``compose/full-dev.yaml`` ``${MINIO_PORT:-9000}`` fallback. The
        # probe doesn't validate object-storage protocol; it just verifies
        # the port is open. That matches the existing pattern for
        # postgres / neo4j (also TCP-only). The compose-side healthcheck
        # (``mc ready local``) is the deeper validation that runs inside
        # the container.
        minio_port = (snapshot.optional_env.get("MINIO_PORT") or "9000")
        probes["minio-ready"] = SocketPortProbe(
            module_id="minio",
            probe_name="minio-ready",
            host="127.0.0.1",
            port=minio_port,
        )

    return probes


@dataclass(frozen=True)
class SocketPortProbe:
    """TCP reachability probe for PostgreSQL and Neo4j."""

    module_id: str
    probe_name: str
    host: str
    port: str

    def check(self, *, timeout_sec: float) -> HealthResult:
        started_at = perf_counter()
        try:
            port = int(self.port)
            with socket.create_connection((self.host, port), timeout=timeout_sec):
                pass
        except Exception as exc:
            return _blocked_result(
                module_id=self.module_id,
                probe_name=self.probe_name,
                started_at=started_at,
                message=f"{self.module_id} port is unreachable",
                details={
                    "host": self.host,
                    "port": str(self.port),
                    "failure_reason": str(exc),
                },
            )

        return _healthy_result(
            module_id=self.module_id,
            probe_name=self.probe_name,
            started_at=started_at,
            message=f"{self.module_id} port is reachable",
            details={"host": self.host, "port": str(port)},
        )


@dataclass(frozen=True)
class ComposeRunningProbe:
    """Compose service running-state probe for Dagster daemon."""

    module_id: str
    probe_name: str
    service_name: str
    bundle_name: str
    compose_file: Path
    env_file: Path | None
    command_runner: CommandRunner | None

    def check(self, *, timeout_sec: float) -> HealthResult:
        started_at = perf_counter()
        handle = ServiceHandle(
            name=self.service_name,
            bundle_name=self.bundle_name,
            compose_service=self.service_name,
            compose_file=self.compose_file,
            env_file=self.env_file,
            command_runner=self.command_runner,
        )
        try:
            exit_code = handle.poll()
        except Exception as exc:
            return _blocked_result(
                module_id=self.module_id,
                probe_name=self.probe_name,
                started_at=started_at,
                message=f"{self.service_name} compose state is unavailable",
                details={
                    "service": self.service_name,
                    "failure_reason": str(exc),
                    "timeout_sec": str(timeout_sec),
                },
            )

        if exit_code is None:
            return _healthy_result(
                module_id=self.module_id,
                probe_name=self.probe_name,
                started_at=started_at,
                message=f"{self.service_name} is running",
                details={"service": self.service_name},
            )

        return _blocked_result(
            module_id=self.module_id,
            probe_name=self.probe_name,
            started_at=started_at,
            message=f"{self.service_name} is not running",
            details={"service": self.service_name, "exit_code": str(exit_code)},
        )


@dataclass(frozen=True)
class DagsterWebserverProbe:
    """HTTP server_info probe for Dagster webserver."""

    module_id: str
    probe_name: str
    host: str
    port: str

    def check(self, *, timeout_sec: float) -> HealthResult:
        started_at = perf_counter()
        url = f"http://{self.host}:{self.port}/server_info"
        try:
            with urllib.request.urlopen(url, timeout=timeout_sec) as response:
                status_code = int(response.status)
        except urllib.error.HTTPError as exc:
            return _blocked_result(
                module_id=self.module_id,
                probe_name=self.probe_name,
                started_at=started_at,
                message=f"{self.module_id} server_info returned HTTP {exc.code}",
                details={"url": url, "status_code": str(exc.code)},
            )
        except Exception as exc:
            return _blocked_result(
                module_id=self.module_id,
                probe_name=self.probe_name,
                started_at=started_at,
                message=f"{self.module_id} server_info is unreachable",
                details={"url": url, "failure_reason": str(exc)},
            )

        if status_code == 200:
            return _healthy_result(
                module_id=self.module_id,
                probe_name=self.probe_name,
                started_at=started_at,
                message=f"{self.module_id} server_info returned HTTP 200",
                details={"url": url, "status_code": str(status_code)},
            )

        return _blocked_result(
            module_id=self.module_id,
            probe_name=self.probe_name,
            started_at=started_at,
            message=f"{self.module_id} server_info returned HTTP {status_code}",
            details={"url": url, "status_code": str(status_code)},
        )


def _neo4j_endpoint(uri: str) -> tuple[str, int]:
    parsed = urllib.parse.urlparse(uri if "://" in uri else f"//{uri}")
    return parsed.hostname or "127.0.0.1", parsed.port or 7687


def _healthy_result(
    *,
    module_id: str,
    probe_name: str,
    started_at: float,
    message: str,
    details: dict[str, str],
) -> HealthResult:
    return HealthResult(
        module_id=module_id,
        probe_name=probe_name,
        status=HealthStatus.healthy,
        latency_ms=_latency_ms(started_at),
        message=message,
        details=details,
    )


def _blocked_result(
    *,
    module_id: str,
    probe_name: str,
    started_at: float,
    message: str,
    details: dict[str, str],
) -> HealthResult:
    return HealthResult(
        module_id=module_id,
        probe_name=probe_name,
        status=HealthStatus.blocked,
        latency_ms=_latency_ms(started_at),
        message=message,
        details=details,
    )


def _latency_ms(started_at: float) -> float:
    return max((perf_counter() - started_at) * 1000, 0.0)
