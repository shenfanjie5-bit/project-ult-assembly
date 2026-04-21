from __future__ import annotations

import json
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from assembly.compat import CompatibilityPromotionError, run_contract_suite
import assembly.compat.runner as compat_runner
from assembly.compat.runner import promote_matrix_entry
from assembly.contracts import VersionInfo
from assembly.contracts.models import IntegrationRunRecord
from assembly.contracts.reporting import compatibility_context_artifact
from assembly.registry import CompatibilityMatrixEntry, RegistryResolutionError, load_all

PROJECT_ROOT = Path(__file__).resolve().parents[2]


#: 11 cross-repo subsystem modules that must be resolvable (via PYTHONPATH
#: or a full-system venv) for the contract suite to exercise the real
#: resolved-module path. Each name is the ``module:symbol`` reference used
#: by ``assembly.contracts.entrypoints.load_reference`` — we check
#: importability of just the ``.public`` module surface here; the check
#: itself later does the full ``module:symbol`` resolution per entry.
_CROSS_REPO_PUBLIC_MODULES = (
    "contracts.public",
    "audit_eval.public",
    "reasoner_runtime.public",
    "main_core.public",
    "data_platform.public",
    "orchestrator.public",
    "entity_registry.public",
    "subsystem_sdk.public",
    "subsystem_announcement.public",
    "subsystem_news.public",
    "graph_engine.public",
)


def test_run_contract_suite_succeeds_in_resolved_module_env(
    tmp_path: Path,
) -> None:
    """Stage 4 §4.1.5 positive regression: when every cross-repo subsystem
    module is resolvable (either via PYTHONPATH covering the 11 sibling
    repos, or a full-system venv with all of them editable-installed),
    the full contract suite against ``lite-local`` must pass with
    ``status == "success"`` and ``failing_modules == []``.

    This is the **real** gate codex review #6 asked for: after §4.1.5
    baseline alignment (registry contract_version v0.1.3 for 11 active
    modules + matrix top-level contract_version v0.1.3 + VersionInfo
    typed optional marker fields + frozen slots removed from profiles),
    the resolved-module path must be green. The alternative "stub
    everything with monkeypatch" approach was explicitly rejected
    because it would bypass the real registry/profile/matrix semantics
    that this test needs to verify.

    If the cross-repo modules are NOT importable (e.g., running against
    an assembly-only venv with no PYTHONPATH), the test SKIPS gracefully
    via ``pytest.importorskip`` with a clear setup-required message. The
    companion test ``test_run_contract_suite_fails_gracefully_without_
    cross_repo_install`` locks in the legitimate degraded behavior
    (``status == "failed"`` with ``ModuleNotFoundError``-shaped
    failure_reasons) for the no-PYTHONPATH case.
    """
    # Gate: require every cross-repo public module to be importable. If
    # any is not, skip with the canonical importorskip message.
    for module_name in _CROSS_REPO_PUBLIC_MODULES:
        pytest.importorskip(
            module_name,
            reason=(
                f"Stage 4 §4.1.5 positive regression requires {module_name} "
                "to be resolvable. Run with PYTHONPATH covering the 11 "
                "sibling repos' src/root dirs, or with a full-system venv "
                "that has them editable-installed. The Stage 3 cross-project "
                "compat audit script (scripts/stage_3_compat_audit.py) "
                "documents the canonical PYTHONPATH setup."
            ),
        )

    reports_dir = tmp_path / "reports/contract"
    report = run_contract_suite(
        "lite-local",
        profiles_root=PROJECT_ROOT / "profiles",
        bundles_root=PROJECT_ROOT / "bundles",
        registry_root=PROJECT_ROOT,
        reports_dir=reports_dir,
        env=_env_from_example(),
        timeout_sec=5.0,
    )

    assert report.run_record.status == "success", (
        f"contract suite did not reach success in resolved-module env; "
        f"status={report.run_record.status!r}, "
        f"failing_modules={report.run_record.failing_modules}. "
        "See the check details in the persisted report for root cause."
    )
    assert report.run_record.failing_modules == []
    assert report.run_record.run_type == "contract"
    assert report.matrix_version == "0.1.0"
    assert report.report_path.exists()

    payload = json.loads(report.report_path.read_text(encoding="utf-8"))
    assert payload["run_record"]["run_type"] == "contract"
    assert payload["run_record"]["status"] == "success"
    assert payload["run_record"]["failing_modules"] == []
    assert payload["matrix_version"] == "0.1.0"

    # Every check on every active module must be ``success`` — the full
    # positive regression that codex review #6 demanded.
    non_success = [
        c
        for c in payload["checks"]
        if c["status"] != "success"
    ]
    assert non_success == [], (
        "Every check on every active module must be ``success`` in the "
        f"resolved-module env; got non-success checks: {non_success}"
    )

    # Smoke-test the context artifact so consumers downstream (Stage 4
    # §4.3 matrix promotion) have the matrix_digest available.
    context_artifact = next(
        artifact
        for artifact in payload["run_record"]["artifacts"]
        if artifact["kind"] == "compatibility_context"
    )
    assert context_artifact["matrix_version"] == "0.1.0"
    assert context_artifact["matrix_digest"]


def test_run_contract_suite_fails_gracefully_without_cross_repo_install(
    tmp_path: Path,
) -> None:
    """Stage 4 §4.1.5 degraded-baseline regression: in an environment
    where cross-repo subsystem modules are NOT importable (assembly's
    own venv with no PYTHONPATH), the contract suite must fail
    gracefully with ``status == "failed"`` and every missing module in
    ``failing_modules`` carrying an ``ImportError``-shaped
    ``failure_reason`` in its check ``details``.

    Pre-§4.1 the registry held all 11 active modules at ``not_started``,
    so ``PublicApiBoundaryCheck`` early-exited (only the focus subset
    ``{main-core, graph-engine, audit-eval}`` even returned a
    ``not_started`` row), and the overall record status was ``partial``.

    Post-§4.1 the 11 active modules are at ``verified`` per Stage 3
    cross-project compat audit evidence (see ``Stage 4 §4.1`` rollout in
    the master plan). ``_check_entry`` now actually runs for every
    promoted module and tries ``importlib.import_module(...)`` on its
    public entrypoint reference. In assembly's own venv that import
    fails for every cross-repo module, ``_check_entry`` returns
    ``CompatibilityCheckStatus.failed`` with ``failure_reason`` carrying
    the ``ModuleNotFoundError`` text, and the overall record status
    becomes ``failed`` (per ``_record_status``: any failed → failed).

    This test pins that **honest** baseline: without a full-system venv
    or PYTHONPATH covering the 11 sibling repos, the contract suite
    correctly reports ``failed`` and surfaces every cross-repo module in
    ``failing_modules`` with the import error in ``checks[*].details``.
    The Stage 3 cross-project compat audit
    (``scripts/stage_3_compat_audit.py``) is the proper venue for
    running this suite against installed/PYTHONPATH-resolvable modules.

    Gate: if the cross-repo modules ARE importable (i.e., PYTHONPATH
    covers the 11 sibling repos OR a full-system venv has them editable-
    installed), this degraded-baseline test is irrelevant and gets
    skipped — the companion
    ``test_run_contract_suite_succeeds_in_resolved_module_env`` covers
    the positive-regression case in that environment.
    """

    import importlib.util

    cross_repo_importable = all(
        importlib.util.find_spec(module_name) is not None
        for module_name in _CROSS_REPO_PUBLIC_MODULES
    )
    if cross_repo_importable:
        pytest.skip(
            "Cross-repo public modules are importable (PYTHONPATH set or "
            "full-system venv); resolved-module positive regression covers "
            "this environment. This degraded-baseline test only applies "
            "when cross-repo modules are NOT importable."
        )

    reports_dir = tmp_path / "reports/contract"

    report = run_contract_suite(
        "lite-local",
        profiles_root=PROJECT_ROOT / "profiles",
        bundles_root=PROJECT_ROOT / "bundles",
        registry_root=PROJECT_ROOT,
        reports_dir=reports_dir,
        env=_env_from_example(),
        timeout_sec=1.0,
    )

    assert report.run_record.run_type == "contract"
    assert report.run_record.status == "failed"
    assert report.matrix_version == "0.1.0"
    assert report.report_path.exists()
    payload = json.loads(report.report_path.read_text(encoding="utf-8"))
    assert payload["run_record"]["run_type"] == "contract"
    assert payload["run_record"]["failing_modules"]
    # At least one of the 11 active subsystem modules must show up in
    # failing_modules (the cross-repo import failure surface).
    assert set(payload["run_record"]["failing_modules"]) & {
        "contracts",
        "data-platform",
        "entity-registry",
        "reasoner-runtime",
        "graph-engine",
        "main-core",
        "audit-eval",
        "subsystem-sdk",
        "orchestrator",
        "subsystem-announcement",
        "subsystem-news",
    }, (
        "Expected at least one cross-repo subsystem module in failing_modules; "
        f"got {payload['run_record']['failing_modules']}"
    )
    assert payload["checks"]
    # Every check failure for a cross-repo module should carry an
    # ``import`` failure_reason (the legitimate "module not pip-installed
    # in assembly's venv" surface). Stage 3 audit script runs the same
    # check stack against a PYTHONPATH-covered context where these
    # imports succeed.
    cross_repo_failure_messages = [
        check["details"].get("failure_reason", "")
        for check in payload["checks"]
        if check["status"] == "failed"
        and check.get("details", {}).get("failure_reason")
    ]
    assert any(
        "No module named" in reason for reason in cross_repo_failure_messages
    ), (
        "Expected at least one ModuleNotFoundError-shaped failure_reason; got "
        f"{cross_repo_failure_messages}"
    )
    assert payload["matrix_version"] == "0.1.0"
    context_artifact = next(
        artifact
        for artifact in payload["run_record"]["artifacts"]
        if artifact["kind"] == "compatibility_context"
    )
    assert context_artifact["matrix_version"] == "0.1.0"
    assert context_artifact["matrix_digest"]


def test_runner_fails_fast_on_matrix_extra_modules(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_app_module(monkeypatch)
    project = _write_project(
        tmp_path,
        modules=[_module_data("app"), _module_data("extra")],
        profile_modules=["app"],
        matrix_modules=[
            {"module_id": "app", "module_version": "0.1.0"},
            {"module_id": "extra", "module_version": "0.1.0"},
        ],
    )

    with pytest.raises(RegistryResolutionError, match="extra"):
        run_contract_suite(
            "full-local",
            profiles_root=project / "profiles",
            bundles_root=project / "bundles",
            registry_root=project,
            reports_dir=project / "reports/contract",
            env={},
        )


def test_promote_rejects_missing_smoke_e2e_records_and_preserves_matrix(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_app_module(monkeypatch)
    project = _write_project(
        tmp_path,
        modules=[_module_data("app")],
        profile_modules=["app"],
        matrix_modules=[{"module_id": "app", "module_version": "0.1.0"}],
        required_tests=["contract-suite", "smoke", "min-cycle-e2e"],
    )

    with pytest.raises(CompatibilityPromotionError, match="missing successful"):
        run_contract_suite(
            "full-local",
            profiles_root=project / "profiles",
            bundles_root=project / "bundles",
            registry_root=project,
            reports_dir=project / "reports/contract",
            env={},
            promote=True,
        )

    matrix = yaml.safe_load((project / "compatibility-matrix.yaml").read_text())
    assert matrix[0]["status"] == "draft"
    assert matrix[0]["verified_at"] is None


def test_promote_updates_matrix_when_required_runs_succeeded(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_app_module(monkeypatch)
    project = _write_project(
        tmp_path,
        modules=[_module_data("app")],
        profile_modules=["app"],
        matrix_modules=[{"module_id": "app", "module_version": "0.1.0"}],
        required_tests=["contract-suite", "smoke", "min-cycle-e2e"],
    )
    matrix_entry = _matrix_entry(project)
    _write_run_record(
        project / "reports/smoke/smoke-success.json",
        "smoke",
        matrix_entry,
    )
    _write_run_record(
        project / "reports/e2e/e2e-success.json",
        "e2e",
        matrix_entry,
    )

    report = run_contract_suite(
        "full-local",
        profiles_root=project / "profiles",
        bundles_root=project / "bundles",
        registry_root=project,
        reports_dir=project / "reports/contract",
        env={},
        promote=True,
    )

    assert report.run_record.status == "success"
    assert report.promoted is True
    support_artifacts = [
        artifact
        for artifact in report.run_record.artifacts
        if artifact["kind"] == "promotion_supporting_run"
    ]
    assert {artifact["run_type"] for artifact in support_artifacts} == {
        "contract",
        "smoke",
        "e2e",
    }
    assert all(artifact["run_id"] for artifact in support_artifacts)
    reloaded = load_all(project)
    assert reloaded.compatibility_matrix[0].status == "verified"
    assert reloaded.compatibility_matrix[0].verified_at is not None


def test_promote_rejects_stale_records_from_different_matrix_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_app_module(monkeypatch)
    project = _write_project(
        tmp_path,
        modules=[_module_data("app")],
        profile_modules=["app"],
        matrix_modules=[{"module_id": "app", "module_version": "0.1.0"}],
        required_tests=["contract-suite", "smoke", "min-cycle-e2e"],
    )
    matrix_entry = _matrix_entry(project)
    stale_data = matrix_entry.model_dump(mode="json")
    stale_data["matrix_version"] = "9.9.9"
    stale_entry = CompatibilityMatrixEntry.model_validate(stale_data)
    _write_run_record(
        project / "reports/smoke/smoke-success.json",
        "smoke",
        stale_entry,
    )
    _write_run_record(
        project / "reports/e2e/e2e-success.json",
        "e2e",
        matrix_entry,
    )

    with pytest.raises(CompatibilityPromotionError, match="smoke"):
        run_contract_suite(
            "full-local",
            profiles_root=project / "profiles",
            bundles_root=project / "bundles",
            registry_root=project,
            reports_dir=project / "reports/contract",
            env={},
            promote=True,
        )

    matrix = yaml.safe_load((project / "compatibility-matrix.yaml").read_text())
    assert matrix[0]["status"] == "draft"
    assert matrix[0]["verified_at"] is None


def test_promote_atomic_write_failure_preserves_matrix(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_app_module(monkeypatch)
    project = _write_project(
        tmp_path,
        modules=[_module_data("app")],
        profile_modules=["app"],
        matrix_modules=[{"module_id": "app", "module_version": "0.1.0"}],
        required_tests=["contract-suite", "smoke", "min-cycle-e2e"],
    )
    matrix_entry = _matrix_entry(project)
    _write_run_record(
        project / "reports/smoke/smoke-success.json",
        "smoke",
        matrix_entry,
    )
    _write_run_record(
        project / "reports/e2e/e2e-success.json",
        "e2e",
        matrix_entry,
    )

    def fail_replace(src: object, dst: object) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(compat_runner.os, "replace", fail_replace)

    with pytest.raises(CompatibilityPromotionError, match="atomically write"):
        run_contract_suite(
            "full-local",
            profiles_root=project / "profiles",
            bundles_root=project / "bundles",
            registry_root=project,
            reports_dir=project / "reports/contract",
            env={},
            promote=True,
        )

    matrix = yaml.safe_load((project / "compatibility-matrix.yaml").read_text())
    assert matrix[0]["status"] == "draft"
    assert matrix[0]["verified_at"] is None
    assert load_all(project).compatibility_matrix[0].status == "draft"


def test_promote_directory_fsync_failure_keeps_matrix_and_report_consistent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_app_module(monkeypatch)
    project = _write_project(
        tmp_path,
        modules=[_module_data("app")],
        profile_modules=["app"],
        matrix_modules=[{"module_id": "app", "module_version": "0.1.0"}],
        required_tests=["contract-suite", "smoke", "min-cycle-e2e"],
    )
    matrix_entry = _matrix_entry(project)
    _write_run_record(
        project / "reports/smoke/smoke-success.json",
        "smoke",
        matrix_entry,
    )
    _write_run_record(
        project / "reports/e2e/e2e-success.json",
        "e2e",
        matrix_entry,
    )

    def fail_directory_fsync(directory: Path) -> None:
        raise OSError(f"simulated fsync failure for {directory}")

    monkeypatch.setattr(compat_runner, "_fsync_directory", fail_directory_fsync)

    report = run_contract_suite(
        "full-local",
        profiles_root=project / "profiles",
        bundles_root=project / "bundles",
        registry_root=project,
        reports_dir=project / "reports/contract",
        env={},
        promote=True,
    )

    assert report.run_record.status == "success"
    assert report.promoted is True
    assert load_all(project).compatibility_matrix[0].status == "verified"

    payload = json.loads(report.report_path.read_text(encoding="utf-8"))
    assert payload["promoted"] is True
    assert payload["run_record"]["status"] == "success"
    warning_artifacts = [
        artifact
        for artifact in payload["run_record"]["artifacts"]
        if artifact["kind"] == "promotion_warning"
    ]
    assert len(warning_artifacts) == 1
    assert "directory fsync failed" in warning_artifacts[0]["message"]


def test_promote_rejects_deprecated_matrix_entry(tmp_path: Path) -> None:
    project = _write_project(
        tmp_path,
        modules=[_module_data("app")],
        profile_modules=["app"],
        matrix_modules=[{"module_id": "app", "module_version": "0.1.0"}],
        matrix_status="deprecated",
    )
    matrix_entry = CompatibilityMatrixEntry.model_validate(
        yaml.safe_load((project / "compatibility-matrix.yaml").read_text())[0]
    )

    with pytest.raises(CompatibilityPromotionError, match="Deprecated"):
        promote_matrix_entry(
            "full-local",
            registry_root=project,
            reports_root=project / "reports",
            matrix_entry=matrix_entry,
            contract_run_record=_run_record("contract"),
        )


def _env_from_example() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator:
            values[key] = value
    return values


class FakeVersionDeclaration:
    def declare(self) -> VersionInfo:
        return VersionInfo(
            module_id="app",
            module_version="0.1.0",
            contract_version="v0.0.0",
            compatible_contract_range=">=0.0.0 <1.0.0",
        )


class FakeCliEntrypoint:
    def invoke(self, argv: list[str]) -> int:
        return 0


def _install_app_module(monkeypatch: pytest.MonkeyPatch) -> None:
    module = types.ModuleType("compat_app_public")
    module.version_declaration = FakeVersionDeclaration()
    module.cli = FakeCliEntrypoint()
    monkeypatch.setitem(sys.modules, "compat_app_public", module)


def _write_project(
    root: Path,
    *,
    modules: list[dict[str, object]],
    profile_modules: list[str],
    matrix_modules: list[dict[str, str]],
    required_tests: list[str] | None = None,
    matrix_status: str = "draft",
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
                    "required_tests": required_tests or ["contract-suite"],
                    "status": matrix_status,
                    "verified_at": None,
                }
            ],
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return root


def _module_data(module_id: str) -> dict[str, object]:
    return {
        "module_id": module_id,
        "module_version": "0.1.0",
        "contract_version": "v0.0.0",
        "owner": "test",
        "upstream_modules": [],
        "downstream_modules": [],
        "public_entrypoints": [
            {
                "name": "version",
                "kind": "version_declaration",
                "reference": "compat_app_public:version_declaration",
            },
            {
                "name": "cli",
                "kind": "cli",
                "reference": "compat_app_public:cli",
            },
        ],
        "depends_on": [],
        "supported_profiles": ["full-local"],
        "integration_status": "partial",
        "last_smoke_result": None,
        "notes": "test module",
    }


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


def _matrix_entry(project: Path) -> CompatibilityMatrixEntry:
    return CompatibilityMatrixEntry.model_validate(
        yaml.safe_load((project / "compatibility-matrix.yaml").read_text())[0]
    )


def _write_run_record(
    path: Path,
    run_type: str,
    matrix_entry: CompatibilityMatrixEntry,
) -> None:
    record = _run_record(run_type, matrix_entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(record.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )


def _run_record(
    run_type: str,
    matrix_entry: CompatibilityMatrixEntry | None = None,
) -> IntegrationRunRecord:
    now = datetime.now(timezone.utc)
    artifacts = [{"kind": f"{run_type}_report", "path": f"reports/{run_type}.json"}]
    if matrix_entry is not None:
        artifacts.append(compatibility_context_artifact(matrix_entry))

    return IntegrationRunRecord(
        run_id=f"{run_type}-success",
        profile_id="full-local",
        run_type=run_type,  # type: ignore[arg-type]
        started_at=now,
        finished_at=now,
        status="success",
        artifacts=artifacts,
        failing_modules=[],
        summary=f"{run_type} succeeded",
    )
