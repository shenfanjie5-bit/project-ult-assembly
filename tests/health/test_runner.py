from __future__ import annotations

import time
from pathlib import Path

from assembly.contracts.models import HealthResult, HealthStatus
from assembly.health.runner import HealthcheckRunner
from assembly.profiles.loader import load_profile
from assembly.profiles.resolver import ResolvedConfigSnapshot, render_profile
from assembly.registry import IntegrationStatus, ModuleRegistryEntry, Registry


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROFILES_ROOT = PROJECT_ROOT / "profiles"
BUNDLES_ROOT = PROJECT_ROOT / "bundles"


class RecordingProbe:
    def __init__(
        self,
        probe_name: str,
        order: list[str],
        *,
        status: HealthStatus = HealthStatus.healthy,
        delay_sec: float = 0.0,
    ) -> None:
        self.probe_name = probe_name
        self.order = order
        self.status = status
        self.delay_sec = delay_sec

    def check(self, *, timeout_sec: float) -> HealthResult:
        self.order.append(self.probe_name)
        if self.delay_sec:
            time.sleep(self.delay_sec)
        return HealthResult(
            module_id=self.probe_name.removesuffix("-ready"),
            probe_name=self.probe_name,
            status=self.status,
            latency_ms=0.0,
            message=f"{self.probe_name} {self.status.value}",
            details={"timeout_sec": str(timeout_sec)},
        )


class FlakyProbe:
    def __init__(
        self,
        probe_name: str,
        statuses: list[HealthStatus],
        order: list[str],
        timeouts: list[float],
    ) -> None:
        self.probe_name = probe_name
        self.statuses = statuses
        self.order = order
        self.timeouts = timeouts
        self.calls = 0

    def check(self, *, timeout_sec: float) -> HealthResult:
        self.order.append(self.probe_name)
        self.timeouts.append(timeout_sec)
        status = self.statuses[min(self.calls, len(self.statuses) - 1)]
        self.calls += 1
        return HealthResult(
            module_id=self.probe_name.removesuffix("-ready"),
            probe_name=self.probe_name,
            status=status,
            latency_ms=0.0,
            message=f"{self.probe_name} attempt {self.calls} {status.value}",
            details={"attempt": self.calls},
        )


def test_healthcheck_runner_executes_lite_builtin_probes_in_order() -> None:
    snapshot = _snapshot()
    order: list[str] = []
    probes = {
        probe_name: RecordingProbe(probe_name, order)
        for probe_name in (
            "postgres-ready",
            "neo4j-ready",
            "dagster-daemon-ready",
            "dagster-webserver-ready",
        )
    }

    results = HealthcheckRunner(builtin_probes=probes).run(snapshot)

    assert order == [
        "postgres-ready",
        "neo4j-ready",
        "dagster-daemon-ready",
        "dagster-webserver-ready",
    ]
    assert [result.status for result in results] == [HealthStatus.healthy] * 4


def test_required_builtin_probe_converges_after_transient_failure() -> None:
    snapshot = _snapshot().model_copy(
        update={"service_bundles": [_snapshot().service_bundles[0]]}
    )
    order: list[str] = []
    timeouts: list[float] = []
    probe = FlakyProbe(
        "postgres-ready",
        [HealthStatus.blocked, HealthStatus.healthy],
        order,
        timeouts,
    )

    results = HealthcheckRunner(
        builtin_probes={"postgres-ready": probe},
    ).run(snapshot, timeout_sec=0.5)

    assert order == ["postgres-ready", "postgres-ready"]
    assert results[0].status == HealthStatus.healthy
    assert results[0].details["convergence_attempts"] == 2
    assert results[0].details["convergence_deadline_exceeded"] is False
    assert results[0].details["last_failure_status"] == HealthStatus.blocked.value
    assert results[0].details["last_failure_message"].endswith("attempt 1 blocked")
    assert all(0 < seen_timeout <= 0.5 for seen_timeout in timeouts)


def test_timeout_maps_required_builtin_probe_to_blocked() -> None:
    snapshot = _snapshot().model_copy(
        update={"service_bundles": [_snapshot().service_bundles[0]]}
    )
    order: list[str] = []
    runner = HealthcheckRunner(
        builtin_probes={
            "postgres-ready": RecordingProbe(
                "postgres-ready",
                order,
                delay_sec=0.05,
            )
        }
    )

    results = runner.run(snapshot, timeout_sec=0.001)

    assert results[0].status == HealthStatus.blocked
    assert results[0].details["timeout"] == "true"


def test_optional_bundle_failure_maps_to_degraded() -> None:
    snapshot = _snapshot()
    optional_postgres = snapshot.service_bundles[0].model_copy(
        update={"optional": True}
    )
    snapshot = snapshot.model_copy(update={"service_bundles": [optional_postgres]})
    order: list[str] = []
    runner = HealthcheckRunner(
        builtin_probes={
            "postgres-ready": RecordingProbe(
                "postgres-ready",
                order,
                status=HealthStatus.blocked,
            )
        }
    )

    results = runner.run(snapshot)

    assert results[0].status == HealthStatus.degraded
    assert results[0].details["optional"] is True


def test_not_started_registry_health_probe_is_skipped_without_import() -> None:
    snapshot = _snapshot().model_copy(
        update={"enabled_modules": ["contracts"], "service_bundles": []}
    )
    registry = Registry(
        root=PROJECT_ROOT,
        modules=[
            _registry_entry(
                "contracts",
                IntegrationStatus.not_started,
                "does_not_exist.public:health_probe",
            )
        ],
        compatibility_matrix=[],
    )

    results = HealthcheckRunner().run(snapshot, registry)

    assert len(results) == 1
    assert results[0].module_id == "contracts"
    assert results[0].status == HealthStatus.healthy
    assert results[0].details == {
        "skipped": True,
        "integration_status": "not_started",
    }


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


def _registry_entry(
    module_id: str,
    integration_status: IntegrationStatus,
    reference: str,
) -> ModuleRegistryEntry:
    return ModuleRegistryEntry(
        module_id=module_id,
        module_version="0.0.0",
        contract_version="v0.0.0",
        owner="test",
        upstream_modules=[],
        downstream_modules=[],
        public_entrypoints=[
            {
                "name": "health",
                "kind": "health_probe",
                "reference": reference,
            }
        ],
        depends_on=[],
        supported_profiles=["lite-local"],
        integration_status=integration_status,
        last_smoke_result=None,
        notes="test entry",
    )
