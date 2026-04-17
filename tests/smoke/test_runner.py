from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest
from pydantic import ValidationError

from assembly.contracts.models import HealthResult, HealthStatus, SmokeResult
from assembly.profiles.loader import load_profile
from assembly.profiles.resolver import ResolvedConfigSnapshot, render_profile
from assembly.registry import IntegrationStatus, ModuleRegistryEntry, Registry
from assembly.tests.smoke.runner import SmokeSuite


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROFILES_ROOT = PROJECT_ROOT / "profiles"
BUNDLES_ROOT = PROJECT_ROOT / "bundles"


class FakeHealthRunner:
    def __init__(self, results: list[HealthResult], order: list[str]) -> None:
        self.results = results
        self.order = order

    def run(
        self,
        snapshot: ResolvedConfigSnapshot,
        registry: Registry,
        *,
        timeout_sec: float,
    ) -> list[HealthResult]:
        self.order.append("health")
        return self.results


def test_smoke_suite_runs_health_before_hooks_and_writes_success_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    order: list[str] = []
    _install_hook_module(
        monkeypatch,
        "fake_success_public",
        SmokeResult(
            module_id="assembly",
            hook_name="smoke",
            passed=True,
            duration_ms=0.0,
        ),
        order,
    )
    snapshot = _snapshot(["assembly", "contracts", "missing-module"])
    registry = _registry(
        [
            _entry("assembly", IntegrationStatus.partial, "fake_success_public:smoke_hook"),
            _entry("contracts", IntegrationStatus.not_started, "missing.public:smoke_hook"),
        ]
    )

    record = SmokeSuite(
        health_runner=FakeHealthRunner([_health("assembly")], order)
    ).run(snapshot, registry, reports_dir=tmp_path)

    assert order == ["health", "smoke:lite-local"]
    assert record.status == "success"
    assert record.failing_modules == []
    payload = json.loads((tmp_path / f"{record.run_id}.json").read_text())
    assert payload["run_id"] == record.run_id
    assert payload["profile_id"] == "lite-local"
    assert payload["run_type"] == "smoke"
    assert payload["status"] == "success"
    assert payload["failing_modules"] == []
    assert {
        "kind": "smoke_skip",
        "module_id": "contracts",
        "skipped": "true",
        "integration_status": "not_started",
    } in payload["artifacts"]
    assert {
        "kind": "smoke_skip",
        "module_id": "missing-module",
        "skipped": "true",
        "integration_status": "unregistered",
    } in payload["artifacts"]


def test_smoke_suite_fails_without_running_hooks_when_health_is_blocked(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    order: list[str] = []
    _install_hook_module(
        monkeypatch,
        "fake_unreached_public",
        SmokeResult(
            module_id="assembly",
            hook_name="smoke",
            passed=True,
            duration_ms=0.0,
        ),
        order,
    )
    snapshot = _snapshot(["assembly"])
    registry = _registry(
        [_entry("assembly", IntegrationStatus.partial, "fake_unreached_public:smoke_hook")]
    )

    record = SmokeSuite(
        health_runner=FakeHealthRunner(
            [_health("postgres", status=HealthStatus.blocked)],
            order,
        )
    ).run(snapshot, registry, reports_dir=tmp_path)

    assert order == ["health"]
    assert record.status == "failed"
    assert record.failing_modules == ["postgres"]


def test_failing_smoke_hook_enters_failing_modules_and_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    order: list[str] = []
    _install_hook_module(
        monkeypatch,
        "fake_failure_public",
        SmokeResult(
            module_id="assembly",
            hook_name="smoke",
            passed=False,
            duration_ms=0.0,
            failure_reason="boom",
        ),
        order,
    )
    snapshot = _snapshot(["assembly"])
    registry = _registry(
        [_entry("assembly", IntegrationStatus.partial, "fake_failure_public:smoke_hook")]
    )

    record = SmokeSuite(
        health_runner=FakeHealthRunner([_health("assembly")], order)
    ).run(snapshot, registry, reports_dir=tmp_path)

    assert record.status == "failed"
    assert record.failing_modules == ["assembly"]
    payload = json.loads((tmp_path / f"{record.run_id}.json").read_text())
    assert payload["status"] == "failed"
    assert payload["failing_modules"] == ["assembly"]


def test_invalid_failed_smoke_result_reason_is_not_swallowed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    order: list[str] = []
    _install_hook_module(
        monkeypatch,
        "fake_invalid_public",
        {
            "module_id": "assembly",
            "hook_name": "smoke",
            "passed": False,
            "duration_ms": 0.0,
            "failure_reason": None,
        },
        order,
    )
    snapshot = _snapshot(["assembly"])
    registry = _registry(
        [_entry("assembly", IntegrationStatus.partial, "fake_invalid_public:smoke_hook")]
    )

    with pytest.raises(ValidationError):
        SmokeSuite(health_runner=FakeHealthRunner([_health("assembly")], order)).run(
            snapshot,
            registry,
            reports_dir=tmp_path,
        )


def _install_hook_module(
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
    result: SmokeResult | dict[str, object],
    order: list[str],
) -> None:
    module = types.ModuleType(module_name)

    class Hook:
        def run(self, *, profile_id: str) -> SmokeResult | dict[str, object]:
            order.append(f"smoke:{profile_id}")
            return result

    module.smoke_hook = Hook()
    monkeypatch.setitem(sys.modules, module_name, module)


def _health(
    module_id: str,
    *,
    status: HealthStatus = HealthStatus.healthy,
) -> HealthResult:
    return HealthResult(
        module_id=module_id,
        probe_name="health",
        status=status,
        latency_ms=0.0,
        message=f"{module_id} {status.value}",
    )


def _snapshot(enabled_modules: list[str]) -> ResolvedConfigSnapshot:
    return render_profile(
        "lite-local",
        profiles_root=PROFILES_ROOT,
        bundles_root=BUNDLES_ROOT,
        env=_env(),
    ).model_copy(update={"enabled_modules": enabled_modules, "service_bundles": []})


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


def _registry(entries: list[ModuleRegistryEntry]) -> Registry:
    return Registry(root=PROJECT_ROOT, modules=entries, compatibility_matrix=[])


def _entry(
    module_id: str,
    integration_status: IntegrationStatus,
    reference: str,
) -> ModuleRegistryEntry:
    return ModuleRegistryEntry(
        module_id=module_id,
        module_version="0.0.0" if module_id != "assembly" else "0.1.0",
        contract_version="v0.0.0",
        owner="test",
        upstream_modules=[],
        downstream_modules=[],
        public_entrypoints=[
            {
                "name": "smoke",
                "kind": "smoke_hook",
                "reference": reference,
            }
        ],
        depends_on=[],
        supported_profiles=["lite-local"],
        integration_status=integration_status,
        last_smoke_result=None,
        notes="test entry",
    )

