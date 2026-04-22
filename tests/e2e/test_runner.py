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
from assembly.tests.e2e.assertions import assert_required_artifacts
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
    contract_payload = json.loads(Path(payload["contract_report_path"]).read_text())
    assert _compatibility_context(payload["run_record"]) == _compatibility_context(
        contract_payload["run_record"]
    )
    assert all(
        assertion["status"] == "passed"
        for assertion in payload["assertion_results"]
    )
    assert _artifact_path(record, "orchestrator_report").exists()
    assert _artifact_path(record, "resolved_config_snapshot").exists()
    assert _artifact_path(record, "assertion_results").exists()


def test_contract_partial_outside_minimal_cycle_still_invokes_orchestrator(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = {
        "phases": ["phase-a"],
        "required_artifact": "cycle_summary",
        "artifact_path": "cycle-summary.json",
    }
    _install_public_module(monkeypatch, module_name="e2e_orchestrator_public", state=state)
    project = _write_project(
        tmp_path,
        modules=[
            _module_data("orchestrator", "e2e_orchestrator_public"),
            _not_started_module_data("main-core"),
        ],
        profile_modules=["orchestrator", "main-core"],
        matrix_modules=[
            {"module_id": "orchestrator", "module_version": "0.1.0"},
            {"module_id": "main-core", "module_version": "0.1.0"},
        ],
    )
    fixture_dir = _write_fixture(
        tmp_path,
        expected_phases=["phase-a"],
        required_artifacts=["cycle_summary"],
    )
    load_calls: list[list[str]] = []

    import assembly.tests.e2e.runner as e2e_runner

    original_load_orchestrator_cli = e2e_runner.load_orchestrator_cli

    def spy_load_orchestrator_cli(
        resolved_entries: list[ModuleRegistryEntry],
    ) -> object:
        load_calls.append([entry.module_id for entry in resolved_entries])
        return original_load_orchestrator_cli(resolved_entries)

    monkeypatch.setattr(e2e_runner, "load_orchestrator_cli", spy_load_orchestrator_cli)

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

    assert load_calls == [["orchestrator", "main-core"]]
    assert record.status == "partial"
    e2e_payload = json.loads(_artifact_path(record, "e2e_report").read_text())
    contract_payload = json.loads(Path(e2e_payload["contract_report_path"]).read_text())
    assert contract_payload["run_record"]["status"] == "partial"
    assert "main-core" in contract_payload["run_record"]["failing_modules"]
    assert "orchestrator" not in contract_payload["run_record"]["failing_modules"]
    orchestrator_report = json.loads(
        _artifact_path(record, "orchestrator_report").read_text()
    )
    assert orchestrator_report["status"] == "success"
    cycle_summary_path = (
        _artifact_path(record, "orchestrator_report").parent / "cycle-summary.json"
    )
    assert cycle_summary_path.exists()


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
    time.sleep(0.3)
    orchestrator_report = json.loads(
        _artifact_path(record, "orchestrator_report").read_text()
    )
    assert orchestrator_report["status"] == "failed"
    assert orchestrator_report["phases"] == []
    assert "timeout_sec=0.01" in orchestrator_report["failure_reason"]
    cycle_summary_path = (
        _artifact_path(record, "orchestrator_report").parent / "cycle-summary.json"
    )
    assert not cycle_summary_path.exists()


def test_required_artifact_rejects_absolute_and_escaping_paths(tmp_path: Path) -> None:
    base_dir = tmp_path / "run"
    base_dir.mkdir()
    outside_artifact = tmp_path / "outside.json"
    outside_artifact.write_text("{}\n", encoding="utf-8")

    results = assert_required_artifacts(
        {
            "absolute": str(outside_artifact),
            "escape": "../outside.json",
        },
        ["absolute", "escape"],
        base_dir=base_dir,
    )

    assert all(result.status == "failed" for result in results)
    absolute_details = results[0].details
    escape_details = results[1].details
    assert absolute_details["raw_reported_path"] == str(outside_artifact)
    assert absolute_details["normalized_path"] == str(outside_artifact.resolve())
    assert escape_details["raw_reported_path"] == "../outside.json"
    assert escape_details["normalized_path"] == str(outside_artifact.resolve())


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


def test_contract_context_drift_fails_before_orchestrator_call(
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

    import assembly.tests.e2e.runner as e2e_runner

    original_run_contract_suite = e2e_runner.run_contract_suite

    def drift_then_run_contract_suite(*args: object, **kwargs: object) -> object:
        matrix_path = project / "compatibility-matrix.yaml"
        matrix_payload = yaml.safe_load(matrix_path.read_text(encoding="utf-8"))
        matrix_payload[0]["matrix_version"] = "0.2.0"
        matrix_path.write_text(
            yaml.safe_dump(matrix_payload, sort_keys=False),
            encoding="utf-8",
        )
        return original_run_contract_suite(*args, **kwargs)

    monkeypatch.setattr(
        e2e_runner,
        "run_contract_suite",
        drift_then_run_contract_suite,
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

    assert state["invoked"] is False
    assert record.status == "failed"
    assert "compatibility context changed" in record.summary
    report_payload = json.loads(_artifact_path(record, "e2e_report").read_text())
    contract_payload = json.loads(
        Path(report_payload["contract_report_path"]).read_text()
    )
    assert _compatibility_context(
        report_payload["run_record"]
    ) == _compatibility_context(contract_payload["run_record"])
    assert (
        _compatibility_context(record.model_dump(mode="json"))["matrix_version"]
        == "0.2.0"
    )


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
            # Stage 4 §4.2 — fake CLI must mirror the real
            # ``orchestrator.cli.min_cycle._emit_runtime_artifacts`` payload
            # contract so the new ``assert_artifact_payload_invariants``
            # assertion in the runner sees a conformant JSON. Tests that
            # want to exercise specific failure modes can override these
            # fields via ``state["artifact_payload_overrides"]`` (a dict
            # merged on top of the defaults).
            scenario_id = str(
                self.state.get("scenario_id", "test-minimal-cycle")
            )
            sanitized = scenario_id.replace("-", "_").replace(".", "_")
            default_payload: dict[str, object] = {
                "kind": artifact_key,
                "scenario_id": scenario_id,
                "real_phase_execution": True,
                "assembled_job_names": ["fake_daily_cycle_job"],
                "assembly_error": None,
                "cycle_publish_manifest_id": f"MAN_{sanitized}_v0",
                "ok": True,
            }
            overrides = self.state.get("artifact_payload_overrides") or {}
            payload = {**default_payload, **overrides}
            (run_dir / artifact_path).write_text(
                json.dumps(payload) + "\n",
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


def _not_started_module_data(module_id: str) -> dict[str, object]:
    public_module = f"missing_{module_id.replace('-', '_')}_public"
    data = _module_data(module_id, public_module)
    data["integration_status"] = "not_started"
    return data


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


def _compatibility_context(record_payload: object) -> dict[str, str]:
    if not isinstance(record_payload, dict):
        artifacts = getattr(record_payload, "artifacts")
    else:
        artifacts = record_payload["artifacts"]
    return next(
        artifact for artifact in artifacts if artifact["kind"] == "compatibility_context"
    )


# ───────────────────────── Stage 4 §4.2 §4.2 ─────────────────────────


_PROJECT_ROOT = Path(__file__).resolve().parents[2]


_REQUIRED_ARTIFACT_PAYLOAD_KEYS_FOR_TEST = (
    "real_phase_execution",
    "assembled_job_names",
    "assembly_error",
    "cycle_publish_manifest_id",
)


def _conformant_artifact_payload(
    *,
    scenario_id: str,
    artifact_kind: str = "cycle_summary",
    overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build a conformant artifact payload for direct assertion testing.

    Mirrors the shape ``orchestrator.cli.min_cycle._emit_runtime_artifacts``
    writes per master plan §4.2 contract. Tests can pass ``overrides`` to
    flip individual invariants and exercise the failure path.
    """
    sanitized = scenario_id.replace("-", "_").replace(".", "_")
    payload: dict[str, object] = {
        "kind": artifact_kind,
        "scenario_id": scenario_id,
        "real_phase_execution": True,
        "assembled_job_names": ["daily_cycle_job"],
        "assembly_error": None,
        "cycle_publish_manifest_id": f"MAN_{sanitized}_v0",
        "phases_executed": ["resolve-profile", "execute-minimal-cycle"],
        "produced_by": "orchestrator.cli.min_cycle",
        "published_at": "2026-04-22T10:00:00+00:00",
    }
    if overrides:
        payload.update(overrides)
    return payload


def test_assert_artifact_payload_invariants_passes_on_conformant_payload(
    tmp_path: Path,
) -> None:
    """Direct unit test: conformant payload yields exactly one passed result."""
    from assembly.tests.e2e.assertions import assert_artifact_payload_invariants

    scenario_id = "shared-fixture-minimal-cycle-v1"
    artifact_kind = "cycle_summary"
    artifact_path = tmp_path / "cycle_summary.json"
    artifact_path.write_text(
        json.dumps(
            _conformant_artifact_payload(
                scenario_id=scenario_id,
                artifact_kind=artifact_kind,
            )
        )
        + "\n",
        encoding="utf-8",
    )

    results = assert_artifact_payload_invariants(
        artifacts={artifact_kind: "cycle_summary.json"},
        required_artifacts=[artifact_kind],
        base_dir=tmp_path,
        scenario_id=scenario_id,
    )

    assert len(results) == 1
    assert results[0].status == "passed"
    assert results[0].assertion_name == "artifact_payload_invariants"
    assert results[0].details["artifact_kind"] == artifact_kind
    assert results[0].details["assembled_job_count"] == 1
    assert results[0].details["cycle_publish_manifest_id"] == (
        f"MAN_{scenario_id.replace('-', '_').replace('.', '_')}_v0"
    )


@pytest.mark.parametrize(
    ("override_field", "override_value", "expected_violation_key"),
    [
        ("real_phase_execution", False, "real_phase_execution"),
        ("assembled_job_names", [], "assembled_job_names"),
        ("assembly_error", "Dagster import failed", "assembly_error"),
        (
            "cycle_publish_manifest_id",
            "MAN_someone_else_v0",
            "cycle_publish_manifest_id",
        ),
    ],
)
def test_assert_artifact_payload_invariants_fails_per_invariant(
    tmp_path: Path,
    override_field: str,
    override_value: object,
    expected_violation_key: str,
) -> None:
    """Each of the 4 invariants must be enforced individually."""
    from assembly.tests.e2e.assertions import assert_artifact_payload_invariants

    scenario_id = "shared-fixture-minimal-cycle-v1"
    artifact_kind = "cycle_summary"
    artifact_path = tmp_path / "cycle_summary.json"
    artifact_path.write_text(
        json.dumps(
            _conformant_artifact_payload(
                scenario_id=scenario_id,
                artifact_kind=artifact_kind,
                overrides={override_field: override_value},
            )
        )
        + "\n",
        encoding="utf-8",
    )

    results = assert_artifact_payload_invariants(
        artifacts={artifact_kind: "cycle_summary.json"},
        required_artifacts=[artifact_kind],
        base_dir=tmp_path,
        scenario_id=scenario_id,
    )

    assert len(results) == 1
    result = results[0]
    assert result.status == "failed"
    assert result.assertion_name == "artifact_payload_invariants"
    assert expected_violation_key in result.details["violations"]


def test_assert_artifact_payload_invariants_fails_on_missing_keys(
    tmp_path: Path,
) -> None:
    """Payload missing any of the 4 required keys should be flagged."""
    from assembly.tests.e2e.assertions import assert_artifact_payload_invariants

    artifact_path = tmp_path / "cycle_summary.json"
    artifact_path.write_text(json.dumps({"ok": True}) + "\n", encoding="utf-8")

    results = assert_artifact_payload_invariants(
        artifacts={"cycle_summary": "cycle_summary.json"},
        required_artifacts=["cycle_summary"],
        base_dir=tmp_path,
        scenario_id="shared-fixture-minimal-cycle-v1",
    )

    assert len(results) == 1
    assert results[0].status == "failed"
    assert results[0].details["missing_keys"] == list(
        _REQUIRED_ARTIFACT_PAYLOAD_KEYS_FOR_TEST
    )


_AUDIT_EVAL_FIXTURES_MINIMAL_CYCLE_CASE = "case_001_one_stock_one_cycle"

#: Cross-repo public modules required for the full Stage 4 §4.2 e2e
#: run-through. Same set as the contract-suite positive regression in
#: ``tests/compat/test_runner.py`` — gated by ``pytest.importorskip``
#: per module so the test SKIPs gracefully without PYTHONPATH coverage.
_E2E_CROSS_REPO_PUBLIC_MODULES = (
    "contracts.public",
    "audit_eval.public",
    "reasoner_runtime.public",
    "main_core.public",
    "data_platform.public",
    "orchestrator.public",
    "orchestrator.cli.min_cycle",
    "entity_registry.public",
    "subsystem_sdk.public",
    "subsystem_announcement.public",
    "subsystem_news.public",
    "graph_engine.public",
)


def test_e2e_runner_consumes_audit_eval_fixtures_minimal_cycle(
    tmp_path: Path,
) -> None:
    """Stage 4 §4.2 positive regression: drive the REAL e2e runner against
    a fixture manifest that anchors to the shared
    ``audit_eval_fixtures.minimal_cycle.case_001_one_stock_one_cycle``
    case identity, invoke the real ``orchestrator min-cycle`` CLI through
    assembly's e2e pipeline, and assert all 4 artifact-payload
    invariants land green.

    This is the test that locks in the master plan §4.2 contract:

    * The shared ``audit_eval_fixtures.minimal_cycle`` case is consumed
      via ``load_case``. Per the codex review #8 strict call (commit
      `92aac55`), the test consumes the case's **content** —
      ``input.json`` / ``expected.json`` / ``context.json`` /
      ``metadata.json`` — not just ``metadata.fixture_id``. Pre-flight
      asserts pin the canonical baseline shape (9 invariants), the e2e
      ``scenario_id`` is derived from ``case.input["cycle_id"]``
      (content, not metadata id), and the orchestrator-emitted
      ``cycle_publish_manifest_id`` is cross-checked against
      ``f"{case.metadata['manifest_cycle_id']}_v0"``. Any drift in the
      shared case content surfaces here loudly.
    * The real orchestrator ``min-cycle`` CLI runs through assembly's
      ``run_min_cycle_e2e``, which invokes the
      ``_emit_runtime_artifacts`` path that writes the 4 invariants per
      required artifact.
    * The new ``assert_artifact_payload_invariants`` assertion (added
      to the runner in this commit) reads each artifact JSON and pins
      the 4 fields green.

    Gates (codex review of `3d9c872` strict call):

    1. ``audit_eval_fixtures`` importable (importorskip).
    2. Each of the 11 cross-repo public modules importable (importorskip).
    3. **All 3 Lite-stack services reachable** (PostgreSQL + Neo4j +
       Dagster) — codex review #8 P3 fix. Probing only Postgres (the
       previous gate) let partially-started stacks slip through and
       fail noisily on Neo4j or Dagster instead of skipping cleanly.

    Shared-fixture consumption (codex review #8 P2 fix): the test
    consumes the case's ``input.json`` / ``expected.json`` / ``context
    .json`` / ``metadata.json`` content, NOT just ``metadata.fixture_id``.
    Pre-flight invariants pin the case to the canonical
    ``minimal_cycle_baseline`` shape (same fixture_kind, same
    object_ref, same replay_mode, same target profile, internal
    cycle_id consistency between input/expected, manifest formula
    match between metadata and input, non-empty candidate_universe,
    all phase_results=ok). The orchestrator scenario_id is derived
    from ``case.input["cycle_id"]`` (content, not metadata id), and
    the test cross-checks that the orchestrator-emitted
    ``cycle_publish_manifest_id`` equals
    ``f"{case.metadata['manifest_cycle_id']}_v0"`` — locking the
    orchestrator-side formula directly to the shared case's manifest
    id. Any drift in the shared case content surfaces here.
    """
    audit_eval_fixtures = pytest.importorskip(
        "audit_eval_fixtures",
        reason=(
            "Stage 4 §4.2 positive regression requires audit_eval_fixtures. "
            "Install via the [shared-fixtures] extra or PYTHONPATH cover "
            "audit-eval/src."
        ),
    )
    for module_name in _E2E_CROSS_REPO_PUBLIC_MODULES:
        pytest.importorskip(
            module_name,
            reason=(
                f"Stage 4 §4.2 positive regression requires {module_name}. "
                "Run with PYTHONPATH covering the 11 sibling repos' src/root "
                "dirs, or with a full-system venv."
            ),
        )

    # Infra-reachability gate (codex review #8 P3 fix): lite-local profile
    # health preflight needs PostgreSQL + Neo4j + Dagster (the 3 Lite
    # service bundles defined in ``profiles/lite-local.yaml`` /
    # ``bundles/{postgres,neo4j,dagster}.yaml``). The previous version
    # only probed Postgres, so a partially-started stack would run the
    # test and fail noisily on Neo4j or Dagster instead of skipping
    # cleanly. Probe each service explicitly; SKIP message names which
    # specific service is down so the user knows what to start.
    import socket

    def _service_reachable(host: str, port: int) -> bool:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except (OSError, ValueError):
            return False

    _LITE_STACK_SERVICES = (
        ("PostgreSQL", "localhost", 5432),
        ("Neo4j (Bolt)", "localhost", 7687),
        ("Dagster webserver", "localhost", 3000),
    )
    unreachable = [
        f"{name} on {host}:{port}"
        for name, host, port in _LITE_STACK_SERVICES
        if not _service_reachable(host, port)
    ]
    if unreachable:
        pytest.skip(
            "Stage 4 §4.2 positive regression requires the full Lite stack "
            f"to be running; unreachable: {unreachable}. Start the Lite "
            "stack via the project's docker-compose under "
            "``assembly/compose/`` or skip this test in CI envs that lack "
            "infra. Cross-repo PYTHONPATH alone is not sufficient."
        )

    # Codex review #8 P2 fix: actually consume the shared case's content.
    # The earlier version only read case.metadata["fixture_id"] which
    # let drift in input/expected/context payloads slip through. Now
    # the test pre-flights the case content shape, then derives
    # scenario_id from input.cycle_id, then cross-checks the
    # orchestrator-emitted cycle_publish_manifest_id against
    # case.metadata.manifest_cycle_id.
    case = audit_eval_fixtures.load_case(
        "minimal_cycle", _AUDIT_EVAL_FIXTURES_MINIMAL_CYCLE_CASE
    )
    case_metadata = case.metadata
    case_input = case.input
    case_expected = case.expected
    case_context = case.context

    # Pre-flight content-shape invariants on the shared case.
    # Each assertion explains what would break if the case drifted.
    assert case_metadata["fixture_kind"] == "minimal_cycle_baseline", (
        "shared case is no longer the canonical Stage 4 §4.2 baseline "
        "(metadata.fixture_kind drifted); audit-eval fixture replaced?"
    )
    assert case_metadata["object_ref"] == "cycle_publish_manifest", (
        "shared case object identity drifted (metadata.object_ref); "
        "expected cycle_publish_manifest"
    )
    assert case_metadata["replay_mode"] == "read_history", (
        "shared case replay_mode must be read_history per audit-eval "
        "CLAUDE.md C1 (replay = read_history only)"
    )
    assert case_context["active_profile"] == "lite-local", (
        "shared case targets lite-local profile; this test exercises "
        "the same — drift here would mismatch the Lite stack just "
        "verified above"
    )
    assert case_context["neo4j_graph_status"] == "ready", (
        "shared case assumes Neo4j is ready; drift here would invert "
        "the Lite-stack precondition this test gates on"
    )
    case_input_cycle_id = case_input["cycle_id"]
    case_expected_cycle_id = case_expected["cycle_publish_manifest"]["cycle_id"]
    assert case_input_cycle_id == case_expected_cycle_id, (
        f"shared case input/expected pair internally inconsistent: "
        f"input.cycle_id={case_input_cycle_id!r} vs "
        f"expected.cycle_publish_manifest.cycle_id="
        f"{case_expected_cycle_id!r}"
    )
    assert (
        case_metadata["manifest_cycle_id"] == f"MAN_{case_input_cycle_id}"
    ), (
        f"shared case manifest_cycle_id formula mismatch: "
        f"metadata.manifest_cycle_id="
        f"{case_metadata['manifest_cycle_id']!r} vs "
        f"f'MAN_{{input.cycle_id}}'='MAN_{case_input_cycle_id}'"
    )
    assert len(case_input["candidate_universe"]) >= 1, (
        "'one stock one cycle' case must have at least one candidate "
        "in input.candidate_universe; drift to empty universe breaks "
        "the case's own naming promise"
    )
    assert all(
        v == "ok" for v in case_expected["phase_results"].values()
    ), (
        "shared case expected phase_results must all be 'ok' (a "
        "regression baseline that fails phases is no longer a valid "
        "minimal_cycle_baseline); got "
        f"{case_expected['phase_results']}"
    )

    # Content-derived scenario_id: drives the orchestrator's
    # _derive_cycle_publish_manifest_id formula from the shared case's
    # input cycle_id. The orchestrator emits
    # f"MAN_{sanitized_scenario_id}_v0", which when fed
    # case_input_cycle_id="CYC_2025_01_03_DAILY" produces
    # "MAN_CYC_2025_01_03_DAILY_v0" — exactly
    # case_metadata["manifest_cycle_id"] + "_v0".
    scenario_id = case_input_cycle_id

    # Build a minimal-cycle manifest YAML in tmp_path that consumes the
    # shared fixture's content (scenario_id from input.cycle_id; the
    # orchestrator-emitted manifest id will then equal
    # f"{case_metadata['manifest_cycle_id']}_v0", asserted below).
    fixture_dir = tmp_path / "fixture"
    fixture_dir.mkdir()
    (fixture_dir / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "scenario_id": scenario_id,
                "expected_phases": [
                    "resolve-profile",
                    "load-fixture",
                    "execute-minimal-cycle",
                    "write-report",
                ],
                "required_artifacts": ["cycle_summary"],
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

    env = {
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "proj",
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "changeme",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "changeme",
        "DAGSTER_HOME": "/tmp",
        "DAGSTER_HOST": "localhost",
        "DAGSTER_PORT": "3000",
    }

    record = run_min_cycle_e2e(
        "lite-local",
        profiles_root=_PROJECT_ROOT / "profiles",
        bundles_root=_PROJECT_ROOT / "bundles",
        registry_root=_PROJECT_ROOT,
        fixture_dir=fixture_dir,
        reports_dir=tmp_path / "reports/e2e",
        env=env,
        timeout_sec=60.0,
        bootstrap_if_needed=False,
    )

    assert record.run_type == "e2e"
    assert record.status == "success", (
        f"e2e did not reach success; status={record.status!r}, "
        f"failing_modules={record.failing_modules}, summary={record.summary!r}"
    )
    assert record.failing_modules == []

    # Verify assertion_results in the persisted e2e report all passed
    # (including the new ``artifact_payload_invariants`` rows).
    e2e_report_path = _artifact_path(record, "e2e_report")
    payload = json.loads(e2e_report_path.read_text(encoding="utf-8"))
    failed_assertions = [
        result
        for result in payload["assertion_results"]
        if result["status"] != "passed"
    ]
    assert failed_assertions == [], (
        "e2e assertions had failures: "
        f"{[r['assertion_name'] for r in failed_assertions]}"
    )

    artifact_payload_assertions = [
        result
        for result in payload["assertion_results"]
        if result["assertion_name"] == "artifact_payload_invariants"
    ]
    assert artifact_payload_assertions, (
        "Stage 4 §4.2 requires at least one "
        "``artifact_payload_invariants`` assertion to be reported"
    )
    assert all(r["status"] == "passed" for r in artifact_payload_assertions)

    # Independent direct check: load each cycle_summary.json artifact and
    # verify the 4 invariants directly (belt-and-suspenders against the
    # in-runner assertion that already passed).
    orchestrator_report = json.loads(
        _artifact_path(record, "orchestrator_report").read_text(encoding="utf-8")
    )
    e2e_report_dir = e2e_report_path.parent
    # Cross-check (codex review #8 P2 fix): the orchestrator-emitted
    # cycle_publish_manifest_id MUST equal the shared case's
    # metadata.manifest_cycle_id with the orchestrator-side "_v0"
    # suffix appended. This locks the cross-module formula directly
    # against the shared fixture content — any drift in either the
    # orchestrator's _derive_cycle_publish_manifest_id formula OR
    # case.metadata.manifest_cycle_id surfaces here.
    expected_manifest_id_from_shared_case = (
        f"{case_metadata['manifest_cycle_id']}_v0"
    )
    sanitized = scenario_id.replace("-", "_").replace(".", "_")
    expected_manifest_id_from_formula = f"MAN_{sanitized}_v0"
    assert (
        expected_manifest_id_from_shared_case
        == expected_manifest_id_from_formula
    ), (
        "shared case + orchestrator formula mismatch (test setup bug, "
        "not a runtime drift): "
        f"case-derived={expected_manifest_id_from_shared_case!r} vs "
        f"formula-derived={expected_manifest_id_from_formula!r}"
    )

    for kind, rel_path in orchestrator_report["artifacts"].items():
        artifact_path = (e2e_report_dir / rel_path).resolve()
        artifact_payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        assert artifact_payload["real_phase_execution"] is True
        assert artifact_payload["assembled_job_names"]
        assert artifact_payload["assembly_error"] is None
        assert (
            artifact_payload["cycle_publish_manifest_id"]
            == expected_manifest_id_from_shared_case
        ), (
            f"orchestrator-emitted cycle_publish_manifest_id "
            f"{artifact_payload['cycle_publish_manifest_id']!r} does not "
            f"match the shared case's metadata.manifest_cycle_id + '_v0' "
            f"({expected_manifest_id_from_shared_case!r})"
        )
