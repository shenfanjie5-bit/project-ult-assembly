"""Minimal-cycle e2e runner."""

from __future__ import annotations

import json
import multiprocessing
import queue
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml
from pydantic import ValidationError

from assembly.bootstrap import bootstrap
from assembly.compat import (
    CompatibilityCheckStatus,
    CompatibilityReport,
    run_contract_suite,
)
from assembly.contracts.models import HealthResult, HealthStatus, IntegrationRunRecord
from assembly.contracts.entrypoints import load_reference
from assembly.contracts.protocols import CliEntrypoint
from assembly.contracts.reporting import record_matches_matrix_context
from assembly.health import healthcheck
from assembly.profiles.resolver import render_profile
from assembly.registry import (
    CompatibilityMatrixEntry,
    IntegrationStatus,
    ModuleRegistryEntry,
    Registry,
    load_all,
    resolve_for_profile,
)
from assembly.tests.e2e.assertions import (
    assert_orchestrator_report,
    assert_phase_order,
    assert_required_artifacts,
)
from assembly.tests.e2e.schema import (
    E2EAssertionResult,
    MinimalCycleFixture,
    OrchestratorCycleReport,
)

_ORCHESTRATOR_MODULE_ID = "orchestrator"
_MINIMAL_CYCLE_MODULE_IDS = frozenset({_ORCHESTRATOR_MODULE_ID})
_DEFAULT_FIXTURE_DIR = Path("src/assembly/tests/e2e/fixtures/minimal_cycle")


class E2EBlocker(Exception):
    """Raised when minimal-cycle e2e cannot safely invoke orchestrator."""


@dataclass(frozen=True)
class _RunPaths:
    reports_dir: Path
    run_dir: Path
    e2e_report: Path
    orchestrator_report: Path
    resolved_config_snapshot: Path
    assertion_results: Path


@dataclass(frozen=True)
class _CliInvocationResult:
    exit_code: int | None = None
    timed_out: bool = False
    exception: BaseException | None = None
    process_exitcode: int | None = None


class E2ERunner:
    """Run the minimal daily-cycle e2e through orchestrator's public CLI."""

    def run(
        self,
        profile_id: str,
        *,
        profiles_root: Path = Path("profiles"),
        bundles_root: Path = Path("bundles"),
        registry_root: Path = Path("."),
        fixture_dir: Path = _DEFAULT_FIXTURE_DIR,
        reports_dir: Path = Path("reports/e2e"),
        env: Mapping[str, str] | None = None,
        timeout_sec: float = 600.0,
        bootstrap_if_needed: bool = True,
    ) -> IntegrationRunRecord:
        """Run preflight checks, invoke orchestrator, assert outputs, and persist."""

        started_at = datetime.now(timezone.utc)
        run_id = _run_id(profile_id, started_at)
        paths = _run_paths(reports_dir, run_id)
        paths.run_dir.mkdir(parents=True, exist_ok=True)
        fixture_manifest_path = _fixture_manifest_path(fixture_dir)
        artifacts = _base_artifacts(paths, fixture_manifest_path)
        assertion_results: list[E2EAssertionResult] = []
        health_results: list[HealthResult] = []
        orchestrator_argv: list[str] = []
        contract_report_path: Path | None = None
        scenario_id: str | None = None

        try:
            fixture = load_minimal_cycle_fixture(fixture_dir)
            scenario_id = fixture.scenario_id
        except Exception as exc:
            assertion_results.append(_failed_assertion("fixture_manifest", str(exc)))
            _write_orchestrator_failure_report(paths.orchestrator_report, profile_id, str(exc))
            return _finish_run(
                profile_id,
                started_at,
                paths,
                artifacts,
                assertion_results,
                status="failed",
                failing_modules=["assembly"],
                summary=f"E2E blocked: fixture manifest invalid; Blocker: {exc}",
                scenario_id=scenario_id,
                health_results=health_results,
                orchestrator_argv=orchestrator_argv,
                contract_report_path=contract_report_path,
            )

        try:
            snapshot = render_profile(
                profile_id,
                profiles_root=profiles_root,
                bundles_root=bundles_root,
                env=env,
            )
            registry = load_all(registry_root)
            resolved_entries = resolve_for_profile(
                registry,
                profile_id,
                profiles_root=profiles_root,
            )
            matrix_entry = _select_matrix_entry(registry, profile_id, resolved_entries)
            snapshot = snapshot.model_copy(
                update={"enabled_modules": [entry.module_id for entry in resolved_entries]}
            )
            snapshot.dump(paths.resolved_config_snapshot)
        except Exception as exc:
            assertion_results.append(_failed_assertion("registry_preflight", str(exc)))
            _write_orchestrator_failure_report(paths.orchestrator_report, profile_id, str(exc))
            return _finish_run(
                profile_id,
                started_at,
                paths,
                artifacts,
                assertion_results,
                status="failed",
                failing_modules=["assembly"],
                summary=f"E2E blocked: registry/profile preflight failed; Blocker: {exc}",
                scenario_id=scenario_id,
                health_results=health_results,
                orchestrator_argv=orchestrator_argv,
                contract_report_path=contract_report_path,
            )

        try:
            contract_report = run_contract_suite(
                profile_id,
                profiles_root=profiles_root,
                bundles_root=bundles_root,
                registry_root=registry_root,
                reports_dir=_contract_reports_dir(paths.reports_dir),
                env=env,
                timeout_sec=timeout_sec,
                promote=False,
            )
            contract_report_path = contract_report.report_path
            artifacts.append({"kind": "contract_report", "path": str(contract_report_path)})
            artifacts.append(_contract_compatibility_context_artifact(contract_report))
        except Exception as exc:
            assertion_results.append(_failed_assertion("contract_preflight", str(exc)))
            _write_orchestrator_failure_report(paths.orchestrator_report, profile_id, str(exc))
            return _finish_run(
                profile_id,
                started_at,
                paths,
                artifacts,
                assertion_results,
                status="failed",
                failing_modules=["assembly"],
                summary=f"E2E blocked: contract preflight failed; Blocker: {exc}",
                scenario_id=scenario_id,
                health_results=health_results,
                orchestrator_argv=orchestrator_argv,
                contract_report_path=contract_report_path,
            )

        if not record_matches_matrix_context(contract_report.run_record, matrix_entry):
            details = {
                "e2e_matrix_version": matrix_entry.matrix_version,
                "contract_matrix_version": contract_report.matrix_version
                or "unknown",
                "contract_report_path": str(contract_report_path),
            }
            assertion_results.append(
                _failed_assertion(
                    "contract_preflight_matrix_context",
                    "Contract preflight compatibility context changed during e2e setup",
                    details,
                )
            )
            _write_orchestrator_failure_report(
                paths.orchestrator_report,
                profile_id,
                "contract preflight compatibility context changed during e2e setup",
            )
            return _finish_run(
                profile_id,
                started_at,
                paths,
                artifacts,
                assertion_results,
                status="failed",
                failing_modules=["assembly"],
                summary=(
                    "E2E blocked: contract preflight compatibility context changed; "
                    f"Blocker: {details}"
                ),
                scenario_id=scenario_id,
                health_results=health_results,
                orchestrator_argv=orchestrator_argv,
                contract_report_path=contract_report_path,
            )

        contract_preflight_blocker = _contract_preflight_blocker(contract_report)
        if contract_preflight_blocker is not None:
            failing_modules, message, details = contract_preflight_blocker
            assertion_results.append(
                _failed_assertion(
                    "contract_preflight",
                    message,
                    details,
                )
            )
            _write_orchestrator_failure_report(
                paths.orchestrator_report,
                profile_id,
                contract_report.run_record.summary,
            )
            return _finish_run(
                profile_id,
                started_at,
                paths,
                artifacts,
                assertion_results,
                status="failed",
                failing_modules=failing_modules,
                summary=(
                    "E2E blocked: contract preflight was not successful; "
                    f"Blocker: {contract_report.run_record.summary}"
                ),
                scenario_id=scenario_id,
                health_results=health_results,
                orchestrator_argv=orchestrator_argv,
                contract_report_path=contract_report_path,
            )

        try:
            health_results = healthcheck(
                profile_id,
                profiles_root=profiles_root,
                bundles_root=bundles_root,
                registry_root=registry_root,
                env=env,
                timeout_sec=timeout_sec,
            )
        except Exception as exc:
            assertion_results.append(_failed_assertion("health_preflight", str(exc)))
            _write_orchestrator_failure_report(paths.orchestrator_report, profile_id, str(exc))
            return _finish_run(
                profile_id,
                started_at,
                paths,
                artifacts,
                assertion_results,
                status="failed",
                failing_modules=["assembly"],
                summary=f"E2E blocked: health preflight failed; Blocker: {exc}",
                scenario_id=scenario_id,
                health_results=health_results,
                orchestrator_argv=orchestrator_argv,
                contract_report_path=contract_report_path,
            )

        blocked_modules = _modules_with_status(health_results, HealthStatus.blocked)
        if blocked_modules and bootstrap_if_needed:
            try:
                bootstrap(
                    profile_id,
                    profiles_root=profiles_root,
                    bundle_root=bundles_root,
                    registry_path=Path(registry_root) / "module-registry.yaml",
                    env=env,
                )
                health_results = healthcheck(
                    profile_id,
                    profiles_root=profiles_root,
                    bundles_root=bundles_root,
                    registry_root=registry_root,
                    env=env,
                    timeout_sec=timeout_sec,
                )
            except Exception as exc:
                assertion_results.append(_failed_assertion("bootstrap_preflight", str(exc)))
                _write_orchestrator_failure_report(paths.orchestrator_report, profile_id, str(exc))
                return _finish_run(
                    profile_id,
                    started_at,
                    paths,
                    artifacts,
                    assertion_results,
                    status="failed",
                    failing_modules=blocked_modules or ["assembly"],
                    summary=f"E2E blocked: bootstrap failed; Blocker: {exc}",
                    scenario_id=scenario_id,
                    health_results=health_results,
                    orchestrator_argv=orchestrator_argv,
                    contract_report_path=contract_report_path,
                )

        blocked_modules = _modules_with_status(health_results, HealthStatus.blocked)
        if blocked_modules:
            assertion_results.append(
                _failed_assertion(
                    "health_preflight",
                    "Healthcheck still has blocked modules",
                    {"blocked_modules": blocked_modules},
                )
            )
            _write_orchestrator_failure_report(
                paths.orchestrator_report,
                profile_id,
                f"blocked health modules: {blocked_modules}",
            )
            return _finish_run(
                profile_id,
                started_at,
                paths,
                artifacts,
                assertion_results,
                status="failed",
                failing_modules=blocked_modules,
                summary=(
                    "E2E blocked: health preflight did not converge; "
                    f"Blocker: blocked_modules={blocked_modules}"
                ),
                scenario_id=scenario_id,
                health_results=health_results,
                orchestrator_argv=orchestrator_argv,
                contract_report_path=contract_report_path,
            )

        try:
            orchestrator_cli = load_orchestrator_cli(resolved_entries)
            orchestrator_argv = build_orchestrator_argv(
                profile_id,
                fixture,
                paths.run_dir,
                paths.orchestrator_report,
            )
        except Exception as exc:
            assertion_results.append(_failed_assertion("orchestrator_entrypoint", str(exc)))
            _write_orchestrator_failure_report(paths.orchestrator_report, profile_id, str(exc))
            return _finish_run(
                profile_id,
                started_at,
                paths,
                artifacts,
                assertion_results,
                status="failed",
                failing_modules=[_ORCHESTRATOR_MODULE_ID],
                summary=f"E2E blocked: orchestrator entrypoint unavailable; Blocker: {exc}",
                scenario_id=scenario_id,
                health_results=health_results,
                orchestrator_argv=orchestrator_argv,
                contract_report_path=contract_report_path,
            )

        invocation = _invoke_cli_with_timeout(
            orchestrator_cli,
            orchestrator_argv,
            timeout_sec=timeout_sec,
        )
        assertion_results.extend(
            _assert_cli_invocation(
                invocation,
                paths.orchestrator_report,
                profile_id,
                timeout_sec=timeout_sec,
            )
        )
        if invocation.timed_out:
            _write_orchestrator_failure_report(
                paths.orchestrator_report,
                profile_id,
                f"orchestrator CLI timed out after timeout_sec={timeout_sec}",
                overwrite=True,
            )
        if invocation.exception is not None and not paths.orchestrator_report.exists():
            _write_orchestrator_failure_report(
                paths.orchestrator_report,
                profile_id,
                str(invocation.exception),
            )

        cycle_report = _load_orchestrator_report(paths.orchestrator_report)
        if cycle_report is None:
            assertion_results.append(
                _failed_assertion(
                    "orchestrator_report",
                    "Orchestrator report could not be loaded",
                    {"path": str(paths.orchestrator_report)},
                )
            )
        else:
            assertion_results.extend(
                assert_orchestrator_report(cycle_report, profile_id=profile_id)
            )
            assertion_results.extend(
                assert_phase_order(cycle_report.phases, fixture.expected_phases)
            )
            assertion_results.extend(
                _with_scenario_id(
                    assert_required_artifacts(
                        cycle_report.artifacts,
                        fixture.required_artifacts,
                        base_dir=paths.run_dir,
                    ),
                    fixture.scenario_id,
                )
            )

        failed_assertions = [
            result for result in assertion_results if result.status == "failed"
        ]
        degraded_modules = _modules_with_status(health_results, HealthStatus.degraded)
        if failed_assertions:
            status = "failed"
            failing_modules = [_ORCHESTRATOR_MODULE_ID]
            summary = (
                "E2E failed; failed_assertions="
                f"{[result.assertion_name for result in failed_assertions]}"
            )
        elif degraded_modules:
            status = "partial"
            failing_modules = []
            summary = f"E2E partially passed; degraded={degraded_modules}"
        else:
            status = "success"
            failing_modules = []
            summary = "E2E succeeded through orchestrator public CLI"

        return _finish_run(
            profile_id,
            started_at,
            paths,
            artifacts,
            assertion_results,
            status=status,
            failing_modules=failing_modules,
            summary=summary,
            scenario_id=scenario_id,
            health_results=health_results,
            orchestrator_argv=orchestrator_argv,
            contract_report_path=contract_report_path,
        )


def load_minimal_cycle_fixture(fixture_dir: Path) -> MinimalCycleFixture:
    """Load a minimal-cycle fixture manifest from a fixture directory or file."""

    manifest_path = _fixture_manifest_path(fixture_dir)
    if not manifest_path.exists():
        raise E2EBlocker(f"Fixture manifest not found: {manifest_path}")

    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise E2EBlocker(f"Invalid YAML in {manifest_path}: {exc}") from exc

    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise E2EBlocker(
            f"Invalid fixture manifest in {manifest_path}: YAML root must be a mapping"
        )

    try:
        return MinimalCycleFixture.model_validate(raw).model_copy(
            update={"manifest_path": manifest_path}
        )
    except ValidationError as exc:
        raise E2EBlocker(f"Invalid fixture manifest in {manifest_path}: {exc}") from exc


def build_orchestrator_argv(
    profile_id: str,
    fixture: MinimalCycleFixture,
    run_dir: Path,
    report_path: Path,
) -> list[str]:
    """Build the argv vector passed to orchestrator's public CLI."""

    values = {
        "profile_id": profile_id,
        "scenario_id": fixture.scenario_id,
        "fixture_manifest": str(fixture.manifest_path),
        "fixture_dir": str(fixture.manifest_path.parent),
        "run_dir": str(run_dir),
        "orchestrator_report_path": str(report_path),
        "report_path": str(report_path),
    }
    argv: list[str] = []
    for template in fixture.orchestrator_args:
        try:
            argv.append(template.format(**values))
        except KeyError as exc:
            raise E2EBlocker(f"Unknown orchestrator argv template key: {exc}") from exc

    return argv


def load_orchestrator_cli(
    resolved_entries: Sequence[ModuleRegistryEntry],
) -> CliEntrypoint:
    """Load the resolved orchestrator CLI entrypoint from registry facts."""

    entry = next(
        (
            resolved_entry
            for resolved_entry in resolved_entries
            if resolved_entry.module_id == _ORCHESTRATOR_MODULE_ID
        ),
        None,
    )
    if entry is None:
        raise E2EBlocker(
            "Blocker: profile does not resolve module_id='orchestrator'"
        )

    if entry.integration_status == IntegrationStatus.not_started:
        raise E2EBlocker(
            "Blocker: orchestrator integration_status is not_started"
        )
    if entry.integration_status == IntegrationStatus.blocked:
        raise E2EBlocker("Blocker: orchestrator integration_status is blocked")

    cli_entrypoints = [
        public_entrypoint
        for public_entrypoint in entry.public_entrypoints
        if public_entrypoint.kind == "cli"
    ]
    if not cli_entrypoints:
        raise E2EBlocker("Blocker: orchestrator does not register a cli entrypoint")

    public_entrypoint = cli_entrypoints[0]
    try:
        loaded = load_reference(public_entrypoint.reference)
    except Exception as exc:
        raise E2EBlocker(
            "Blocker: orchestrator cli entrypoint could not be imported: "
            f"{public_entrypoint.reference}: {exc}"
        ) from exc

    if not isinstance(loaded, CliEntrypoint):
        raise E2EBlocker(
            "Blocker: orchestrator cli entrypoint does not satisfy CliEntrypoint"
        )

    return loaded


def _fixture_manifest_path(fixture_dir: Path) -> Path:
    path = Path(fixture_dir)
    if path.suffix in {".yaml", ".yml"}:
        return path

    return path / "manifest.yaml"


def _run_paths(reports_dir: Path, run_id: str) -> _RunPaths:
    reports_dir = Path(reports_dir)
    run_dir = reports_dir / run_id
    return _RunPaths(
        reports_dir=reports_dir,
        run_dir=run_dir,
        e2e_report=reports_dir / f"{run_id}.json",
        orchestrator_report=run_dir / "orchestrator-report.json",
        resolved_config_snapshot=run_dir / "resolved-config-snapshot.json",
        assertion_results=run_dir / "assertion-results.json",
    )


def _base_artifacts(paths: _RunPaths, fixture_manifest_path: Path) -> list[dict[str, str]]:
    return [
        {"kind": "e2e_report", "path": str(paths.e2e_report)},
        {"kind": "orchestrator_report", "path": str(paths.orchestrator_report)},
        {"kind": "fixture_manifest", "path": str(fixture_manifest_path)},
        {
            "kind": "resolved_config_snapshot",
            "path": str(paths.resolved_config_snapshot),
        },
        {"kind": "assertion_results", "path": str(paths.assertion_results)},
    ]


def _contract_reports_dir(e2e_reports_dir: Path) -> Path:
    return Path(e2e_reports_dir).parent / "contract"


def _select_matrix_entry(
    registry: Registry,
    profile_id: str,
    resolved_entries: Sequence[ModuleRegistryEntry],
) -> CompatibilityMatrixEntry:
    expected_versions = {
        entry.module_id: entry.module_version for entry in resolved_entries
    }
    for matrix_entry in registry.compatibility_matrix:
        if matrix_entry.profile_id != profile_id or matrix_entry.status == "deprecated":
            continue

        matrix_versions = {
            module.module_id: module.module_version
            for module in matrix_entry.module_set
        }
        if matrix_versions == expected_versions:
            return matrix_entry

    raise E2EBlocker(
        f"Blocker: no active compatibility matrix entry matches profile {profile_id}"
    )


def _contract_compatibility_context_artifact(
    contract_report: CompatibilityReport,
) -> dict[str, str]:
    context_artifacts = [
        dict(artifact)
        for artifact in contract_report.run_record.artifacts
        if artifact.get("kind") == "compatibility_context"
    ]
    if not context_artifacts:
        raise E2EBlocker(
            "Blocker: contract preflight run record is missing compatibility_context"
        )
    if len(context_artifacts) > 1:
        raise E2EBlocker(
            "Blocker: contract preflight run record has multiple compatibility_context artifacts"
        )

    return context_artifacts[0]


def _contract_preflight_blocker(
    contract_report: CompatibilityReport,
) -> tuple[list[str], str, dict[str, Any]] | None:
    record = contract_report.run_record
    if record.status == "success":
        return None

    cycle_checks = [
        check
        for check in contract_report.checks
        if check.module_id in _MINIMAL_CYCLE_MODULE_IDS
        and check.status != CompatibilityCheckStatus.success
    ]
    if record.status == "partial" and not cycle_checks:
        return None

    cycle_modules = sorted({check.module_id for check in cycle_checks})
    details: dict[str, Any] = {
        "contract_status": record.status,
        "contract_summary": record.summary,
        "minimal_cycle_modules": sorted(_MINIMAL_CYCLE_MODULE_IDS),
    }
    if cycle_checks:
        details["minimal_cycle_non_success_checks"] = [
            {
                "check_name": check.check_name,
                "module_id": check.module_id,
                "status": check.status.value,
                "message": check.message,
            }
            for check in cycle_checks
        ]

    return (
        cycle_modules or record.failing_modules or ["assembly"],
        f"Contract suite did not satisfy minimal-cycle preflight: {record.status}",
        details,
    )


def _invoke_cli_with_timeout(
    entrypoint: CliEntrypoint,
    argv: list[str],
    *,
    timeout_sec: float,
) -> _CliInvocationResult:
    ctx = _process_context()
    result_queue = ctx.Queue(maxsize=1)
    process = ctx.Process(
        target=_invoke_cli_process,
        args=(entrypoint, list(argv), result_queue),
    )
    try:
        process.start()
    except BaseException as exc:
        _close_process_queue(result_queue)
        _close_process(process)
        return _CliInvocationResult(exception=exc)

    process.join(timeout=max(timeout_sec, 0.0))

    if process.is_alive():
        process.terminate()
        process.join(timeout=1.0)
        if process.is_alive():
            process.kill()
            process.join()

        process_exitcode = process.exitcode
        _close_process_queue(result_queue)
        _close_process(process)
        return _CliInvocationResult(
            timed_out=True,
            process_exitcode=process_exitcode,
        )

    process_exitcode = process.exitcode
    try:
        kind, payload = result_queue.get(timeout=1.0)
    except queue.Empty:
        return _CliInvocationResult(
            exception=RuntimeError(
                "Orchestrator CLI subprocess exited without an invocation result; "
                f"exitcode={process_exitcode}"
            ),
            process_exitcode=process_exitcode,
        )
    finally:
        if not process.is_alive():
            _close_process_queue(result_queue)
            _close_process(process)

    if kind == "ok":
        try:
            return _CliInvocationResult(
                exit_code=int(payload),
                process_exitcode=process_exitcode,
            )
        except (TypeError, ValueError) as exc:
            return _CliInvocationResult(
                exception=exc,
                process_exitcode=process_exitcode,
            )

    if kind == "error" and isinstance(payload, dict):
        return _CliInvocationResult(
            exception=RuntimeError(_format_child_exception(payload)),
            process_exitcode=process_exitcode,
        )

    return _CliInvocationResult(
        exception=RuntimeError(str(payload)),
        process_exitcode=process_exitcode,
    )


def _process_context() -> multiprocessing.context.BaseContext:
    try:
        return multiprocessing.get_context("fork")
    except ValueError:
        return multiprocessing.get_context()


def _invoke_cli_process(
    entrypoint: CliEntrypoint,
    argv: list[str],
    result_queue: multiprocessing.Queue,
) -> None:
    try:
        result_queue.put(("ok", entrypoint.invoke(argv)))
    except BaseException as exc:
        result_queue.put(
            (
                "error",
                {
                    "type": exc.__class__.__name__,
                    "message": str(exc),
                    "traceback": "".join(
                        traceback.format_exception(
                            exc.__class__,
                            exc,
                            exc.__traceback__,
                        )
                    ),
                },
            )
        )


def _format_child_exception(payload: dict[str, object]) -> str:
    error_type = str(payload.get("type", "Exception"))
    message = str(payload.get("message", ""))
    child_traceback = str(payload.get("traceback", ""))
    if child_traceback:
        return f"{error_type}: {message}\n{child_traceback}"

    return f"{error_type}: {message}"


def _close_process_queue(result_queue: multiprocessing.Queue) -> None:
    result_queue.close()
    result_queue.join_thread()


def _close_process(process: multiprocessing.Process) -> None:
    try:
        process.close()
    except ValueError:
        pass


def _assert_cli_invocation(
    invocation: _CliInvocationResult,
    report_path: Path,
    profile_id: str,
    *,
    timeout_sec: float,
) -> list[E2EAssertionResult]:
    if invocation.timed_out:
        return [
            _failed_assertion(
                "orchestrator_cli_timeout",
                "Orchestrator CLI timed out",
                {
                    "profile_id": profile_id,
                    "report_path": str(report_path),
                    "timeout_sec": str(timeout_sec),
                    "process_exitcode": invocation.process_exitcode,
                },
            )
        ]

    if invocation.exception is not None:
        return [
            _failed_assertion(
                "orchestrator_cli",
                "Orchestrator CLI raised an exception",
                {
                    "profile_id": profile_id,
                    "report_path": str(report_path),
                    "failure_reason": str(invocation.exception),
                },
            )
        ]

    if invocation.exit_code != 0:
        return [
            _failed_assertion(
                "orchestrator_cli",
                "Orchestrator CLI returned a non-zero exit code",
                {
                    "profile_id": profile_id,
                    "report_path": str(report_path),
                    "exit_code": invocation.exit_code,
                },
            )
        ]

    return [
        E2EAssertionResult(
            assertion_name="orchestrator_cli",
            status="passed",
            message="Orchestrator CLI returned zero",
            details={"profile_id": profile_id, "report_path": str(report_path)},
        )
    ]


def _load_orchestrator_report(path: Path) -> OrchestratorCycleReport | None:
    try:
        return OrchestratorCycleReport.model_validate_json(
            Path(path).read_text(encoding="utf-8")
        )
    except (OSError, ValidationError, json.JSONDecodeError):
        return None


def _write_orchestrator_failure_report(
    path: Path,
    profile_id: str,
    failure_reason: str,
    *,
    overwrite: bool = False,
) -> None:
    if path.exists() and not overwrite:
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    report = OrchestratorCycleReport(
        profile_id=profile_id,
        phases=[],
        artifacts={},
        status="failed",
        failure_reason=failure_reason,
    )
    path.write_text(
        json.dumps(
            report.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _finish_run(
    profile_id: str,
    started_at: datetime,
    paths: _RunPaths,
    artifacts: list[dict[str, str]],
    assertion_results: list[E2EAssertionResult],
    *,
    status: str,
    failing_modules: list[str],
    summary: str,
    scenario_id: str | None,
    health_results: list[HealthResult],
    orchestrator_argv: list[str],
    contract_report_path: Path | None,
) -> IntegrationRunRecord:
    finished_at = datetime.now(timezone.utc)
    record = IntegrationRunRecord(
        run_id=paths.e2e_report.stem,
        profile_id=profile_id,
        run_type="e2e",
        started_at=started_at,
        finished_at=finished_at,
        status=status,  # type: ignore[arg-type]
        artifacts=_dedupe_artifacts(artifacts),
        failing_modules=sorted(set(failing_modules)),
        summary=summary,
    )
    _persist_assertion_results(paths.assertion_results, assertion_results)
    _persist_e2e_report(
        record,
        paths.e2e_report,
        scenario_id=scenario_id,
        health_results=health_results,
        assertion_results=assertion_results,
        orchestrator_argv=orchestrator_argv,
        contract_report_path=contract_report_path,
    )
    return record


def _persist_assertion_results(
    path: Path,
    assertion_results: list[E2EAssertionResult],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            [result.model_dump(mode="json") for result in assertion_results],
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _persist_e2e_report(
    record: IntegrationRunRecord,
    report_path: Path,
    *,
    scenario_id: str | None,
    health_results: list[HealthResult],
    assertion_results: list[E2EAssertionResult],
    orchestrator_argv: list[str],
    contract_report_path: Path | None,
) -> None:
    payload = {
        "run_record": record.model_dump(mode="json"),
        "scenario_id": scenario_id,
        "health_results": [
            result.model_dump(mode="json") for result in health_results
        ],
        "assertion_results": [
            result.model_dump(mode="json") for result in assertion_results
        ],
        "orchestrator_argv": orchestrator_argv,
        "contract_report_path": (
            None if contract_report_path is None else str(contract_report_path)
        ),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _dedupe_artifacts(artifacts: Sequence[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[tuple[str, str], ...]] = set()
    for artifact in artifacts:
        key = tuple(sorted(artifact.items()))
        if key in seen:
            continue

        seen.add(key)
        deduped.append(dict(artifact))

    return deduped


def _modules_with_status(
    health_results: Sequence[HealthResult],
    status: HealthStatus,
) -> list[str]:
    return sorted(
        {
            result.module_id
            for result in health_results
            if result.status == status
        }
    )


def _with_scenario_id(
    results: list[E2EAssertionResult],
    scenario_id: str,
) -> list[E2EAssertionResult]:
    updated: list[E2EAssertionResult] = []
    for result in results:
        details = dict(result.details)
        details["scenario_id"] = scenario_id
        updated.append(result.model_copy(update={"details": details}))

    return updated


def _failed_assertion(
    assertion_name: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> E2EAssertionResult:
    return E2EAssertionResult(
        assertion_name=assertion_name,
        status="failed",
        message=message,
        details={} if details is None else details,
    )


def _run_id(profile_id: str, started_at: datetime) -> str:
    timestamp = started_at.strftime("%Y%m%dT%H%M%S%fZ")
    return f"e2e-{profile_id}-{timestamp}"
