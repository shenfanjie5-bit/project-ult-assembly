from __future__ import annotations

import json
import re
import sys
import time
import types
from pathlib import Path

import pytest
import yaml

from assembly.contracts import HealthResult, HealthStatus, VersionInfo
from assembly.registry import IntegrationStatus, ModuleRegistryEntry
from assembly.tests.e2e import E2ERunner, run_min_cycle_e2e
from assembly.tests.e2e.runner import E2EBlocker, load_orchestrator_cli


def test_public_api_exports_runner_and_run_function() -> None:
    assert E2ERunner is not None
    assert callable(run_min_cycle_e2e)


def test_fake_orchestrator_success_writes_required_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = {
        "phases": ["phase-a", "phase-b"],
        "required_artifact": "custom_artifact",
        "artifact_path": "custom-artifact.json",
        "invoked": False,
    }
    _install_public_module(monkeypatch, module_name="e2e_orchestrator_public", state=state)
    project = _write_project(
        tmp_path,
        modules=[_module_data("orchestrator", "e2e_orchestrator_public")],
        profile_modules=["orchestrator"],
        matrix_modules=[{"module_id": "orchestrator", "module_version": "0.1.0"}],
    )
    fixture_dir = _write_fixture(
        tmp_path,
        expected_phases=["phase-a", "phase-b"],
        required_artifacts=["custom_artifact"],
    )

    record = run_min_cycle_e2e(
        "full-local",
        profiles_root=project / "profiles",
        bundles_root=project / "bundles",
        registry_root=project,
        fixture_dir=fixture_dir,
        reports_dir=project / "reports/e2e",
        env={},
        timeout_sec=1.0,
        bootstrap_if_needed=False,
    )

    assert state["invoked"] is True
    assert record.run_type == "e2e"
    assert record.status == "success"
    assert record.failing_modules == []
    artifact_kinds = {artifact["kind"] for artifact in record.artifacts}
    assert {
        "e2e_report",
        "orchestrator_report",
        "fixture_manifest",
        "resolved_config_snapshot",
        "assertion_results",
        "compatibility_context",
    }.issubset(artifact_kinds)
    report_path = _artifact_path(record, "e2e_report")
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["run_record"]["run_id"] == record.run_id
    assert payload["scenario_id"] == "test-minimal-cycle"
    assert all(
        assertion["status"] == "passed"
        for assertion in payload["assertion_results"]
    )
    assert _artifact_path(record, "orchestrator_report").exists()
    assert _artifact_path(record, "resolved_config_snapshot").exists()
    assert _artifact_path(record, "assertion_results").exists()


def test_phase_order_failure_marks_e2e_failed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = {
        "phases": ["phase-b", "phase-a"],
        "required_artifact": "cycle_summary",
        "artifact_path": "cycle-summary.json",
    }
    _install_public_module(monkeypatch, module_name="e2e_orchestrator_public", state=state)
    project = _write_project(
        tmp_path,
        modules=[_module_data("orchestrator", "e2e_orchestrator_public")],
        profile_modules=["orchestrator"],
        matrix_modules=[{"module_id": "orchestrator", "module_version": "0.1.0"}],
    )
    fixture_dir = _write_fixture(
        tmp_path,
        expected_phases=["phase-a", "phase-b"],
        required_artifacts=["cycle_summary"],
    )

    record = E2ERunner().run(
        "full-local",
        profiles_root=project / "profiles",
        bundles_root=project / "bundles",
        registry_root=project,
        fixture_dir=fixture_dir,
        reports_dir=project / "reports/e2e",
        env={},
        timeout_sec=1.0,
        bootstrap_if_needed=False,
    )

    assert record.status == "failed"
    assertions = _assertion_payload(record)
    assert any(
        assertion["assertion_name"] == "phase_order"
        and assertion["status"] == "failed"
        for assertion in assertions
    )


def test_required_artifact_missing_reports_key_path_and_scenario(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = {
        "phases": ["phase-a"],
        "required_artifact": "cycle_summary",
        "artifact_path": "missing-summary.json",
        "skip_artifact_write": True,
    }
    _install_public_module(monkeypatch, module_name="e2e_orchestrator_public", state=state)
    project = _write_project(
        tmp_path,
        modules=[_module_data("orchestrator", "e2e_orchestrator_public")],
        profile_modules=["orchestrator"],
        matrix_modules=[{"module_id": "orchestrator", "module_version": "0.1.0"}],
    )
    fixture_dir = _write_fixture(
        tmp_path,
        expected_phases=["phase-a"],
        required_artifacts=["cycle_summary"],
    )

    record = run_min_cycle_e2e(
        "full-local",
        profiles_root=project / "profiles",
        bundles_root=project / "bundles",
        registry_root=project,
        fixture_dir=fixture_dir,
        reports_dir=project / "reports/e2e",
        env={},
        timeout_sec=1.0,
        bootstrap_if_needed=False,
    )

    assert record.status == "failed"
    failed_artifact_assertion = next(
        assertion
        for assertion in _assertion_payload(record)
        if assertion["assertion_name"] == "required_artifact"
        and assertion["status"] == "failed"
    )
    details = failed_artifact_assertion["details"]
    assert details["artifact_key"] == "cycle_summary"
    assert details["expected_path"].endswith("missing-summary.json")
    assert details["scenario_id"] == "test-minimal-cycle"


def test_orchestrator_not_resolved_fails_without_invoking_cli(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = {
        "phases": ["phase-a"],
        "required_artifact": "cycle_summary",
        "artifact_path": "cycle-summary.json",
        "invoked": False,
    }
    _install_public_module(monkeypatch, module_name="e2e_app_public", state=state)
    project = _write_project(
        tmp_path,
        modules=[_module_data("app", "e2e_app_public")],
        profile_modules=["app"],
        matrix_modules=[{"module_id": "app", "module_version": "0.1.0"}],
    )
    fixture_dir = _write_fixture(tmp_path)

    record = run_min_cycle_e2e(
        "full-local",
        profiles_root=project / "profiles",
        bundles_root=project / "bundles",
        registry_root=project,
        fixture_dir=fixture_dir,
        reports_dir=project / "reports/e2e",
        env={},
        timeout_sec=1.0,
        bootstrap_if_needed=False,
    )

    assert state["invoked"] is False
    assert record.status == "failed"
    assert "Blocker" in record.summary
    assert record.failing_modules == ["orchestrator"]


def test_load_orchestrator_cli_rejects_not_started_import_failure_and_protocol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_cli = _entry(
        "orchestrator",
        IntegrationStatus.partial,
        public_entrypoints=[],
    )
    not_started = _entry(
        "orchestrator",
        IntegrationStatus.not_started,
        public_entrypoints=[
            {
                "name": "cli",
                "kind": "cli",
                "reference": "e2e_bad_public:cli",
            }
        ],
    )
    import_failure = _entry(
        "orchestrator",
        IntegrationStatus.partial,
        public_entrypoints=[
            {
                "name": "cli",
                "kind": "cli",
                "reference": "missing_public_module:cli",
            }
        ],
    )
    bad_module = types.ModuleType("e2e_bad_public")
    bad_module.cli = object()
    monkeypatch.setitem(sys.modules, "e2e_bad_public", bad_module)
    protocol_failure = _entry(
        "orchestrator",
        IntegrationStatus.partial,
        public_entrypoints=[
            {
                "name": "cli",
                "kind": "cli",
                "reference": "e2e_bad_public:cli",
            }
        ],
    )

    for entry, expected in (
        (missing_cli, "does not register"),
        (not_started, "not_started"),
        (import_failure, "could not be imported"),
        (protocol_failure, "does not satisfy"),
    ):
        with pytest.raises(E2EBlocker, match=expected):
            load_orchestrator_cli([entry])


def test_orchestrator_cli_timeout_writes_failed_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = {
        "phases": ["phase-a"],
        "required_artifact": "cycle_summary",
        "artifact_path": "cycle-summary.json",
        "sleep_sec": 0.2,
    }
    _install_public_module(monkeypatch, module_name="e2e_orchestrator_public", state=state)
    project = _write_project(
        tmp_path,
        modules=[_module_data("orchestrator", "e2e_orchestrator_public")],
        profile_modules=["orchestrator"],
        matrix_modules=[{"module_id": "orchestrator", "module_version": "0.1.0"}],
    )
    fixture_dir = _write_fixture(
        tmp_path,
        expected_phases=["phase-a"],
        required_artifacts=["cycle_summary"],
    )

    record = run_min_cycle_e2e(
        "full-local",
        profiles_root=project / "profiles",
        bundles_root=project / "bundles",
        registry_root=project,
        fixture_dir=fixture_dir,
        reports_dir=project / "reports/e2e",
        env={},
        timeout_sec=0.01,
        bootstrap_if_needed=False,
    )

    assert record.status == "failed"
    report_payload = json.loads(_artifact_path(record, "e2e_report").read_text())
    timeout_assertion = next(
        assertion
        for assertion in report_payload["assertion_results"]
        if assertion["assertion_name"] == "orchestrator_cli_timeout"
    )
    assert timeout_assertion["details"]["timeout_sec"] == "0.01"


def test_registry_matrix_drift_fails_before_orchestrator_call(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = {
        "phases": ["phase-a"],
        "required_artifact": "cycle_summary",
        "artifact_path": "cycle-summary.json",
        "invoked": False,
    }
    _install_public_module(monkeypatch, module_name="e2e_orchestrator_public", state=state)
    project = _write_project(
        tmp_path,
        modules=[_module_data("orchestrator", "e2e_orchestrator_public")],
        profile_modules=["orchestrator"],
        matrix_modules=[{"module_id": "orchestrator", "module_version": "9.9.9"}],
    )
    fixture_dir = _write_fixture(tmp_path)

    record = run_min_cycle_e2e(
        "full-local",
        profiles_root=project / "profiles",
        bundles_root=project / "bundles",
        registry_root=project,
        fixture_dir=fixture_dir,
        reports_dir=project / "reports/e2e",
        env={},
        timeout_sec=1.0,
        bootstrap_if_needed=False,
    )

    assert state["invoked"] is False
    assert record.status == "failed"
    assert "registry/profile preflight" in record.summary


def test_blocked_health_without_bootstrap_is_not_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = {
        "phases": ["phase-a"],
        "required_artifact": "cycle_summary",
        "artifact_path": "cycle-summary.json",
        "invoked": False,
    }
    _install_public_module(monkeypatch, module_name="e2e_orchestrator_public", state=state)
    project = _write_project(
        tmp_path,
        modules=[_module_data("orchestrator", "e2e_orchestrator_public")],
        profile_modules=["orchestrator"],
        matrix_modules=[{"module_id": "orchestrator", "module_version": "0.1.0"}],
    )
    fixture_dir = _write_fixture(tmp_path)

    def blocked_healthcheck(profile_id: str, **kwargs: object) -> list[HealthResult]:
        return [
            HealthResult(
                module_id="postgres",
                probe_name="postgres-ready",
                status=HealthStatus.blocked,
                latency_ms=0.0,
                message="blocked",
            )
        ]

    import assembly.tests.e2e.runner as e2e_runner

    monkeypatch.setattr(e2e_runner, "healthcheck", blocked_healthcheck)

    record = run_min_cycle_e2e(
        "full-local",
        profiles_root=project / "profiles",
        bundles_root=project / "bundles",
        registry_root=project,
        fixture_dir=fixture_dir,
        reports_dir=project / "reports/e2e",
        env={},
        timeout_sec=1.0,
        bootstrap_if_needed=False,
    )

    assert state["invoked"] is False
    assert record.status == "failed"
    assert record.failing_modules == ["postgres"]


def test_blocked_health_bootstraps_and_requires_second_convergence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = {
        "phases": ["phase-a"],
        "required_artifact": "cycle_summary",
        "artifact_path": "cycle-summary.json",
        "invoked": False,
    }
    _install_public_module(monkeypatch, module_name="e2e_orchestrator_public", state=state)
    project = _write_project(
        tmp_path,
        modules=[_module_data("orchestrator", "e2e_orchestrator_public")],
        profile_modules=["orchestrator"],
        matrix_modules=[{"module_id": "orchestrator", "module_version": "0.1.0"}],
    )
    fixture_dir = _write_fixture(tmp_path)
    health_calls: list[str] = []
    bootstrap_calls: list[str] = []

    def converging_healthcheck(profile_id: str, **kwargs: object) -> list[HealthResult]:
        health_calls.append(profile_id)
        status = HealthStatus.blocked if len(health_calls) == 1 else HealthStatus.healthy
        return [
            HealthResult(
                module_id="postgres",
                probe_name="postgres-ready",
                status=status,
                latency_ms=0.0,
                message=status.value,
            )
        ]

    def fake_bootstrap(profile_id: str, **kwargs: object) -> object:
        bootstrap_calls.append(profile_id)
        return object()

    import assembly.tests.e2e.runner as e2e_runner

    monkeypatch.setattr(e2e_runner, "healthcheck", converging_healthcheck)
    monkeypatch.setattr(e2e_runner, "bootstrap", fake_bootstrap)

    record = run_min_cycle_e2e(
        "full-local",
        profiles_root=project / "profiles",
        bundles_root=project / "bundles",
        registry_root=project,
        fixture_dir=fixture_dir,
        reports_dir=project / "reports/e2e",
        env={},
        timeout_sec=1.0,
        bootstrap_if_needed=True,
    )

    assert health_calls == ["full-local", "full-local"]
    assert bootstrap_calls == ["full-local"]
    assert state["invoked"] is True
    assert record.status == "success"


def test_e2e_package_does_not_directly_import_orchestrator_private_modules() -> None:
    package_root = Path(__file__).resolve().parents[2] / "src/assembly/tests/e2e"
    private_import = re.compile(r"^\s*(import|from)\s+orchestrator\b", re.MULTILINE)
    for path in package_root.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert private_import.search(text) is None


class FakeVersionDeclaration:
    def __init__(self, module_id: str) -> None:
        self.module_id = module_id

    def declare(self) -> VersionInfo:
        return VersionInfo(
            module_id=self.module_id,
            module_version="0.1.0",
            contract_version="v0.0.0",
            compatible_contract_range=">=0.0.0 <1.0.0",
        )


class FakeHealthProbe:
    def __init__(self, module_id: str) -> None:
        self.module_id = module_id

    def check(self, *, timeout_sec: float) -> HealthResult:
        return HealthResult(
            module_id=self.module_id,
            probe_name="health",
            status=HealthStatus.healthy,
            latency_ms=0.0,
            message="healthy",
            details={"timeout_sec": str(timeout_sec)},
        )


class FakeCliEntrypoint:
    def __init__(self, state: dict[str, object]) -> None:
        self.state = state

    def invoke(self, argv: list[str]) -> int:
        self.state["invoked"] = True
        sleep_sec = float(self.state.get("sleep_sec", 0.0))
        if sleep_sec:
            time.sleep(sleep_sec)

        report_path = Path(argv[argv.index("--report") + 1])
        run_dir = Path(argv[argv.index("--run-artifacts-dir") + 1])
        artifact_key = str(self.state["required_artifact"])
        artifact_path = str(self.state["artifact_path"])
        if not self.state.get("skip_artifact_write", False):
            (run_dir / artifact_path).write_text(
                json.dumps({"ok": True}) + "\n",
                encoding="utf-8",
            )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(
                {
                    "profile_id": argv[argv.index("--profile") + 1],
                    "phases": self.state["phases"],
                    "artifacts": {artifact_key: artifact_path},
                    "status": self.state.get("status", "success"),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return int(self.state.get("exit_code", 0))


def _install_public_module(
    monkeypatch: pytest.MonkeyPatch,
    *,
    module_name: str,
    state: dict[str, object],
) -> None:
    module = types.ModuleType(module_name)
    module_id = "orchestrator" if "orchestrator" in module_name else "app"
    module.health_probe = FakeHealthProbe(module_id)
    module.version_declaration = FakeVersionDeclaration(module_id)
    module.cli = FakeCliEntrypoint(state)
    monkeypatch.setitem(sys.modules, module_name, module)


def _write_project(
    root: Path,
    *,
    modules: list[dict[str, object]],
    profile_modules: list[str],
    matrix_modules: list[dict[str, str]],
) -> Path:
    (root / "profiles").mkdir(parents=True)
    (root / "bundles").mkdir()
    (root / "profiles/full-local.yaml").write_text(
        yaml.safe_dump(
            {
                "profile_id": "full-local",
                "mode": "full",
                "enabled_modules": profile_modules,
                "enabled_service_bundles": [],
                "required_env_keys": [],
                "optional_env_keys": [],
                "storage_backends": {},
                "resource_expectation": {
                    "cpu_cores": 1,
                    "memory_gb": 1,
                    "disk_gb": 1,
                },
                "max_long_running_daemons": 1,
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
    (root / "compatibility-matrix.yaml").write_text(
        yaml.safe_dump(
            [
                {
                    "matrix_version": "0.1.0",
                    "profile_id": "full-local",
                    "module_set": matrix_modules,
                    "contract_version": "v0.0.0",
                    "required_tests": ["contract-suite", "smoke", "min-cycle-e2e"],
                    "status": "draft",
                    "verified_at": None,
                }
            ],
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return root


def _write_fixture(
    root: Path,
    *,
    expected_phases: list[str] | None = None,
    required_artifacts: list[str] | None = None,
) -> Path:
    fixture_dir = root / "fixture"
    fixture_dir.mkdir(exist_ok=True)
    (fixture_dir / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "scenario_id": "test-minimal-cycle",
                "expected_phases": expected_phases or ["phase-a"],
                "required_artifacts": required_artifacts or ["cycle_summary"],
                "orchestrator_args": [
                    "min-cycle",
                    "--profile",
                    "{profile_id}",
                    "--fixture",
                    "{fixture_manifest}",
                    "--run-artifacts-dir",
                    "{run_dir}",
                    "--report",
                    "{orchestrator_report_path}",
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return fixture_dir


def _module_data(module_id: str, public_module: str) -> dict[str, object]:
    return {
        "module_id": module_id,
        "module_version": "0.1.0",
        "contract_version": "v0.0.0",
        "owner": "test",
        "upstream_modules": [],
        "downstream_modules": [],
        "public_entrypoints": [
            {
                "name": "health",
                "kind": "health_probe",
                "reference": f"{public_module}:health_probe",
            },
            {
                "name": "version",
                "kind": "version_declaration",
                "reference": f"{public_module}:version_declaration",
            },
            {
                "name": "cli",
                "kind": "cli",
                "reference": f"{public_module}:cli",
            },
        ],
        "depends_on": [],
        "supported_profiles": ["full-local"],
        "integration_status": "partial",
        "last_smoke_result": None,
        "notes": "test module",
    }


def _entry(
    module_id: str,
    integration_status: IntegrationStatus,
    *,
    public_entrypoints: list[dict[str, str]],
) -> ModuleRegistryEntry:
    return ModuleRegistryEntry(
        module_id=module_id,
        module_version="0.1.0",
        contract_version="v0.0.0",
        owner="test",
        upstream_modules=[],
        downstream_modules=[],
        public_entrypoints=public_entrypoints,
        depends_on=[],
        supported_profiles=["full-local"],
        integration_status=integration_status,
        last_smoke_result=None,
        notes="test module",
    )


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
        row = {column: _markdown_value(column, module[column]) for column in columns}
        lines.append("| " + " | ".join(row[column] for column in columns) + " |")
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
        return "; ".join(
            f"{entry['name']}:{entry['kind']}={entry['reference']}"
            for entry in value  # type: ignore[union-attr]
        )
    if column == "last_smoke_result" and value is None:
        return "null"
    return str(value)


def _artifact_path(record: object, kind: str) -> Path:
    artifacts = getattr(record, "artifacts")
    return Path(next(artifact["path"] for artifact in artifacts if artifact["kind"] == kind))


def _assertion_payload(record: object) -> list[dict[str, object]]:
    payload = json.loads(_artifact_path(record, "assertion_results").read_text())
    assert isinstance(payload, list)
    return payload
