"""Bootstrap planning, staged execution, and docker compose APIs."""

from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from assembly.bootstrap.plan import (
    BootstrapPlan,
    BootstrapPlanError,
    BootstrapService,
    BootstrapStageName,
    BootstrapStageResult,
    BootstrapStageSpec,
    BootstrapStageStatus,
    build_plan,
)
from assembly.bootstrap.runner import (
    BootstrapResult,
    ComposeCommandError,
    DockerComposeUnavailableError,
    Runner,
)
from assembly.bootstrap.service_handle import ServiceHandle
from assembly.contracts.models import HealthResult, HealthStatus, SmokeResult
from assembly.profiles.errors import ProfileError, ProfileNotFoundError
from assembly.profiles.loader import list_profiles
from assembly.profiles.resolver import resolve, with_extra_bundles
from assembly.profiles.schema import EnvironmentProfile
from assembly.registry import (
    ModuleRegistryEntry,
    PublicEntrypoint,
    load_registry_yaml,
)

_DEFAULT_BOOTSTRAP_REPORT_ROOT = Path("reports/bootstrap")
_DEFAULT_ENTRYPOINT_TIMEOUT_SEC = 5.0


class BootstrapStageError(Exception):
    """Raised when a post-compose bootstrap boundary fails."""

    def __init__(
        self,
        stage: BootstrapStageName,
        message: str,
        result: BootstrapResult,
    ) -> None:
        self.stage = stage
        self.result = result
        super().__init__(message)


class BootstrapEntrypointError(Exception):
    """Raised when a registered public entrypoint cannot be exercised."""


def bootstrap(
    profile_id: str,
    *,
    profiles_root: Path = Path("profiles"),
    bundle_root: Path = Path("bundles"),
    compose_file: Path | None = None,
    registry_path: Path = Path("module-registry.yaml"),
    env: Mapping[str, str] | None = None,
    env_file: Path | None = None,
    extra_bundles: Sequence[str] | None = None,
    runner: Runner | None = None,
    dry_run: bool = False,
    reports_root: Path = _DEFAULT_BOOTSTRAP_REPORT_ROOT,
    report_path: Path | None = None,
    orchestrator_entrypoint: Any | None = None,
    smoke_hooks: Sequence[Any] | None = None,
    entrypoint_timeout_sec: float = _DEFAULT_ENTRYPOINT_TIMEOUT_SEC,
) -> BootstrapResult:
    """Resolve a profile, execute the Lite stages in order, and write a report."""

    action = "plan" if dry_run else "start"
    profile = _load_profile_by_id(profile_id, profiles_root)
    resolved_report_path = _resolve_report_path(
        report_path=report_path,
        reports_root=reports_root,
        profile_id=profile_id,
        action=action,
    )
    stage_results: list[BootstrapStageResult] = []

    try:
        profile = with_extra_bundles(
            profile,
            extra_bundles,
            bundle_root=bundle_root,
        )
        resolved_compose_file = compose_file or _default_compose_file(
            profile.profile_id
        )
        resolve(profile, os.environ if env is None else env, bundle_root=bundle_root)
        plan = build_plan(
            profile,
            bundle_root=bundle_root,
            compose_file=resolved_compose_file,
        )
    except (BootstrapPlanError, ProfileError, OSError) as exc:
        result = BootstrapResult(
            profile_id=profile_id,
            action=action,
            command=[],
            service_order=[],
            returncode=1,
            dry_run=dry_run,
            stage_results=[
                _stage_result(
                    "env_filesystem_readiness",
                    "failed",
                    str(exc),
                )
            ],
            report_path=resolved_report_path,
        )
        _persist_report(result, None)
        raise

    stage_results.append(
        _stage_result(
            "env_filesystem_readiness",
            "passed",
            "Profile env, bundle, compose, and report paths resolved.",
            {
                "compose_file": str(plan.compose_file),
                "enabled_service_bundles": list(profile.enabled_service_bundles),
            },
        )
    )

    if dry_run:
        stage_results.extend(
            _planned_stage_results(
                plan,
                completed_stage_names={"env_filesystem_readiness"},
            )
        )
        result = BootstrapResult(
            profile_id=profile_id,
            action="plan",
            command=_start_command(plan, env_file),
            service_order=list(plan.startup_order),
            returncode=0,
            dry_run=True,
            stage_results=stage_results,
            report_path=resolved_report_path,
        )
        _persist_report(result, plan)
        return result

    active_runner = runner or Runner(env_file=env_file)
    try:
        result = active_runner.start(plan)
    except ComposeCommandError as exc:
        result = BootstrapResult(
            profile_id=profile_id,
            action="start",
            command=list(exc.command),
            service_order=list(plan.startup_order),
            returncode=exc.returncode,
            stdout=exc.stdout,
            stderr=exc.stderr,
            stage_results=stage_results
            + [
                _stage_result(
                    "service_startup",
                    "failed",
                    str(exc),
                    {"service_order": list(plan.startup_order)},
                )
            ],
            report_path=resolved_report_path,
        )
        _persist_report(result, plan)
        raise

    stage_results.append(
        _stage_result(
            "service_startup",
            "passed",
            "Compose services started in profile startup order.",
            {
                "command": list(result.command),
                "service_order": list(result.service_order),
            },
        )
    )
    result = result.model_copy(
        update={
            "dry_run": False,
            "stage_results": list(stage_results),
            "report_path": resolved_report_path,
        }
    )

    try:
        orchestrator_details = _exercise_orchestrator_entrypoint(
            profile=profile,
            registry_path=registry_path,
            orchestrator_entrypoint=orchestrator_entrypoint,
            timeout_sec=entrypoint_timeout_sec,
        )
        stage_results.append(
            _stage_result(
                "orchestrator_entrypoint_readiness",
                "passed",
                "Orchestrator public readiness entrypoint passed.",
                orchestrator_details,
            )
        )
        result = result.model_copy(update={"stage_results": list(stage_results)})

        smoke_details = _exercise_smoke_hooks(
            profile=profile,
            registry_path=registry_path,
            smoke_hooks=smoke_hooks,
        )
        stage_results.append(
            _stage_result(
                "public_smoke_probes",
                "passed",
                "Enabled module public smoke hooks passed.",
                smoke_details,
            )
        )
        result = result.model_copy(update={"stage_results": list(stage_results)})
    except Exception as exc:
        failed_stage = _next_unfinished_stage(plan, stage_results)
        result = result.model_copy(
            update={
                "returncode": 1,
                "stage_results": stage_results
                + [
                    _stage_result(
                        failed_stage,
                        "failed",
                        str(exc),
                    )
                ],
            }
        )
        _persist_report(result, plan)
        raise BootstrapStageError(failed_stage, str(exc), result) from exc

    _persist_report(result, plan)
    return result


def _load_profile_by_id(profile_id: str, profiles_root: Path) -> EnvironmentProfile:
    for profile in list_profiles(profiles_root):
        if profile.profile_id == profile_id:
            return profile

    raise ProfileNotFoundError(f"Profile id not found in {profiles_root}: {profile_id}")


def _default_compose_file(profile_id: str) -> Path:
    if profile_id == "full-dev":
        return Path("compose/full-dev.yaml")

    return Path("compose/lite-local.yaml")


def _exercise_orchestrator_entrypoint(
    *,
    profile: EnvironmentProfile,
    registry_path: Path,
    orchestrator_entrypoint: Any | None,
    timeout_sec: float,
) -> dict[str, Any]:
    entrypoint = orchestrator_entrypoint
    if entrypoint is None:
        registry = load_registry_yaml(registry_path)
        public_entrypoint = _find_public_entrypoint(
            registry,
            module_id="orchestrator",
            profile_id=profile.profile_id,
            kind="health_probe",
        )
        entrypoint = _load_reference(public_entrypoint.reference)

    health = _invoke_health_probe(entrypoint, timeout_sec=timeout_sec)
    if health.status != HealthStatus.healthy:
        raise BootstrapEntrypointError(
            "orchestrator health_probe returned "
            f"{health.status.value}: {health.message}"
        )

    return {
        "module_id": health.module_id,
        "probe_name": health.probe_name,
        "status": health.status.value,
        "latency_ms": health.latency_ms,
    }


def _exercise_smoke_hooks(
    *,
    profile: EnvironmentProfile,
    registry_path: Path,
    smoke_hooks: Sequence[Any] | None,
) -> dict[str, Any]:
    hooks = list(smoke_hooks) if smoke_hooks is not None else _load_smoke_hooks(
        profile,
        registry_path,
    )
    if not hooks:
        raise BootstrapEntrypointError(
            f"No public smoke hooks are registered for profile {profile.profile_id}"
        )

    smoke_results = [
        _invoke_smoke_hook(hook, profile_id=profile.profile_id) for hook in hooks
    ]
    failures = [
        result
        for result in smoke_results
        if not result.passed
    ]
    if failures:
        failure_details = ", ".join(
            f"{result.module_id}:{result.hook_name}: "
            f"{result.failure_reason or 'failed without reason'}"
            for result in failures
        )
        raise BootstrapEntrypointError(
            f"Public smoke hooks failed: {failure_details}"
        )

    return {
        "smoke_results": [
            {
                "module_id": result.module_id,
                "hook_name": result.hook_name,
                "passed": result.passed,
                "duration_ms": result.duration_ms,
            }
            for result in smoke_results
        ]
    }


def _load_smoke_hooks(
    profile: EnvironmentProfile,
    registry_path: Path,
) -> list[Any]:
    registry = load_registry_yaml(registry_path)
    hooks: list[Any] = []
    for module_id in profile.enabled_modules:
        public_entrypoint = _find_public_entrypoint(
            registry,
            module_id=module_id,
            profile_id=profile.profile_id,
            kind="smoke_hook",
        )
        hooks.append(_load_reference(public_entrypoint.reference))

    return hooks


def _find_public_entrypoint(
    registry: Sequence[ModuleRegistryEntry],
    *,
    module_id: str,
    profile_id: str,
    kind: str,
) -> PublicEntrypoint:
    for entry in registry:
        if entry.module_id != module_id or profile_id not in entry.supported_profiles:
            continue

        for public_entrypoint in entry.public_entrypoints:
            if public_entrypoint.kind == kind:
                return public_entrypoint

    raise BootstrapEntrypointError(
        f"Module {module_id!r} does not register a {kind!r} entrypoint "
        f"for profile {profile_id!r}"
    )


def _load_reference(reference: str) -> Any:
    module_name, _, symbol_name = reference.partition(":")
    if not module_name or not symbol_name:
        raise BootstrapEntrypointError(
            f"Invalid public entrypoint reference: {reference}"
        )

    module = importlib.import_module(module_name)
    return getattr(module, symbol_name)


def _invoke_health_probe(entrypoint: Any, *, timeout_sec: float) -> HealthResult:
    if hasattr(entrypoint, "check"):
        raw_result = entrypoint.check(timeout_sec=timeout_sec)
        return HealthResult.model_validate(raw_result)

    if callable(entrypoint):
        try:
            raw_result = entrypoint(timeout_sec=timeout_sec)
        except TypeError:
            raw_result = entrypoint()

        if hasattr(raw_result, "check"):
            raw_result = raw_result.check(timeout_sec=timeout_sec)

        return HealthResult.model_validate(raw_result)

    raise BootstrapEntrypointError("health_probe entrypoint is not callable")


def _invoke_smoke_hook(entrypoint: Any, *, profile_id: str) -> SmokeResult:
    if hasattr(entrypoint, "run"):
        raw_result = entrypoint.run(profile_id=profile_id)
        return SmokeResult.model_validate(raw_result)

    if callable(entrypoint):
        try:
            raw_result = entrypoint(profile_id=profile_id)
        except TypeError:
            raw_result = entrypoint()

        if hasattr(raw_result, "run"):
            raw_result = raw_result.run(profile_id=profile_id)

        return SmokeResult.model_validate(raw_result)

    raise BootstrapEntrypointError("smoke_hook entrypoint is not callable")


def _stage_result(
    name: BootstrapStageName,
    status: BootstrapStageStatus,
    message: str,
    details: dict[str, Any] | None = None,
) -> BootstrapStageResult:
    return BootstrapStageResult(
        name=name,
        status=status,
        message=message,
        details={} if details is None else details,
    )


def _planned_stage_results(
    plan: BootstrapPlan,
    *,
    completed_stage_names: set[BootstrapStageName],
) -> list[BootstrapStageResult]:
    return [
        _stage_result(stage.name, "planned", stage.description)
        for stage in plan.stages
        if stage.name not in completed_stage_names
    ]


def _next_unfinished_stage(
    plan: BootstrapPlan,
    stage_results: Sequence[BootstrapStageResult],
) -> BootstrapStageName:
    finished_names = {result.name for result in stage_results}
    for stage in plan.stages:
        if stage.name not in finished_names:
            return stage.name

    return "public_smoke_probes"


def _resolve_report_path(
    *,
    report_path: Path | None,
    reports_root: Path,
    profile_id: str,
    action: str,
) -> Path:
    if report_path is not None:
        path = Path(report_path)
        if path.suffix:
            return path

        return path / _report_filename(profile_id, action)

    return Path(reports_root) / _report_filename(profile_id, action)


def _report_filename(profile_id: str, action: str) -> str:
    return f"{profile_id}-bootstrap-{action}.json"


def _persist_report(result: BootstrapResult, plan: BootstrapPlan | None) -> None:
    if result.report_path is None:
        return

    payload = result.model_dump(mode="json", exclude={"handles"})
    payload["stages"] = payload.pop("stage_results")
    if plan is not None:
        payload["stage_contract"] = [
            stage.model_dump(mode="json") for stage in plan.stages
        ]
        payload["compose_file"] = str(plan.compose_file)

    path = Path(result.report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _start_command(plan: BootstrapPlan, env_file: Path | None) -> list[str]:
    command = ["docker", "compose"]
    if env_file is not None:
        command.extend(["--env-file", str(env_file)])
    command.extend(
        [
            "-f",
            str(plan.compose_file),
            "up",
            "-d",
            "--wait",
            *plan.startup_order,
        ]
    )
    return command


__all__ = [
    "BootstrapPlan",
    "BootstrapPlanError",
    "BootstrapResult",
    "BootstrapService",
    "BootstrapStageError",
    "BootstrapStageResult",
    "BootstrapStageSpec",
    "BootstrapStageStatus",
    "ComposeCommandError",
    "DockerComposeUnavailableError",
    "Runner",
    "ServiceHandle",
    "bootstrap",
    "build_plan",
]
