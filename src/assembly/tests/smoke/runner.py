"""System-level smoke suite runner."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

from pydantic import ValidationError

from assembly.contracts.entrypoints import load_reference
from assembly.contracts.models import (
    HealthStatus,
    IntegrationRunRecord,
    SmokeResult,
)
from assembly.contracts.reporting import compatibility_context_artifact
from assembly.health.runner import HealthcheckRunner
from assembly.profiles.resolver import ResolvedConfigSnapshot
from assembly.registry import (
    CompatibilityMatrixEntry,
    IntegrationStatus,
    ModuleRegistryEntry,
    Registry,
)
from assembly.registry.schema import PublicEntrypoint


class SmokeSuite:
    """Run health convergence followed by available module smoke hooks."""

    def __init__(self, health_runner: HealthcheckRunner | None = None) -> None:
        self._health_runner = health_runner or HealthcheckRunner()

    def run(
        self,
        snapshot: ResolvedConfigSnapshot,
        registry: Registry,
        *,
        timeout_sec: float = 30.0,
        reports_dir: Path = Path("reports/smoke"),
        matrix_entry: CompatibilityMatrixEntry | None = None,
    ) -> IntegrationRunRecord:
        """Run the smoke suite and persist an integration run record."""

        started_at = datetime.now(timezone.utc)
        run_id = _run_id(snapshot.profile_id, started_at)
        report_path = Path(reports_dir) / f"{run_id}.json"
        artifacts: list[dict[str, str]] = [
            {"kind": "smoke_report", "path": str(report_path)}
        ]
        if matrix_entry is not None:
            artifacts.append(compatibility_context_artifact(matrix_entry))

        health_results = self._health_runner.run(
            snapshot,
            registry,
            timeout_sec=timeout_sec,
        )
        artifacts.extend(
            {
                "kind": "health_result",
                "module_id": result.module_id,
                "probe_name": result.probe_name,
                "status": result.status.value,
                "message": result.message,
            }
            for result in health_results
        )

        blocked_modules = [
            result.module_id
            for result in health_results
            if result.status == HealthStatus.blocked
        ]
        degraded_modules = [
            result.module_id
            for result in health_results
            if result.status == HealthStatus.degraded
        ]

        smoke_results: list[SmokeResult] = []
        skip_artifacts: list[dict[str, str]] = []
        if not blocked_modules:
            smoke_results, skip_artifacts = _run_smoke_hooks(snapshot, registry)
            artifacts.extend(skip_artifacts)
            artifacts.extend(_smoke_result_artifact(result) for result in smoke_results)

        failing_modules = sorted(
            {
                *blocked_modules,
                *(
                    result.module_id
                    for result in smoke_results
                    if not result.passed
                ),
            }
        )
        if failing_modules:
            status = "failed"
        elif degraded_modules or skip_artifacts:
            status = "partial"
        else:
            status = "success"

        finished_at = datetime.now(timezone.utc)
        record = IntegrationRunRecord(
            run_id=run_id,
            profile_id=snapshot.profile_id,
            run_type="smoke",
            started_at=started_at,
            finished_at=finished_at,
            status=status,
            artifacts=artifacts,
            failing_modules=failing_modules,
            summary=_summary(
                status=status,
                blocked_modules=blocked_modules,
                degraded_modules=degraded_modules,
                smoke_results=smoke_results,
                skip_count=len(skip_artifacts),
            ),
        )
        _persist_record(record, report_path)
        return record


def _run_smoke_hooks(
    snapshot: ResolvedConfigSnapshot,
    registry: Registry,
) -> tuple[list[SmokeResult], list[dict[str, str]]]:
    results: list[SmokeResult] = []
    artifacts: list[dict[str, str]] = []
    entries_by_id = {entry.module_id: entry for entry in registry.modules}

    for module_id in snapshot.enabled_modules:
        entry = entries_by_id.get(module_id)
        if entry is None:
            results.append(
                _failed_smoke_result(
                    module_id=module_id,
                    hook_name="smoke",
                    started_at=perf_counter(),
                    failure_reason=(
                        f"{module_id} is not registered in the module registry"
                    ),
                )
            )
            continue

        smoke_entrypoints = [
            entrypoint
            for entrypoint in entry.public_entrypoints
            if entrypoint.kind == "smoke_hook"
        ]
        if entry.integration_status == IntegrationStatus.not_started:
            artifacts.append(
                _skip_artifact(module_id, entry.integration_status.value)
            )
            continue

        if not smoke_entrypoints:
            results.append(
                _failed_smoke_result(
                    module_id=module_id,
                    hook_name="smoke",
                    started_at=perf_counter(),
                    failure_reason=(
                        f"{module_id} has no smoke_hook public entrypoint"
                    ),
                )
            )
            continue

        for entrypoint in smoke_entrypoints:
            results.append(
                _run_smoke_hook(
                    entry,
                    entrypoint,
                    profile_id=snapshot.profile_id,
                )
            )

    return results, artifacts


def _run_smoke_hook(
    entry: ModuleRegistryEntry,
    public_entrypoint: PublicEntrypoint,
    *,
    profile_id: str,
) -> SmokeResult:
    started_at = perf_counter()
    try:
        entrypoint = load_reference(public_entrypoint.reference)
    except Exception as exc:
        return _failed_smoke_result(
            module_id=entry.module_id,
            hook_name=public_entrypoint.name,
            started_at=started_at,
            failure_reason=(
                f"Could not import {public_entrypoint.reference}: {exc}"
            ),
        )

    try:
        return _invoke_smoke_hook(entrypoint, profile_id=profile_id)
    except ValidationError:
        raise
    except Exception as exc:
        return _failed_smoke_result(
            module_id=entry.module_id,
            hook_name=public_entrypoint.name,
            started_at=started_at,
            failure_reason=str(exc),
        )


def _invoke_smoke_hook(entrypoint: Any, *, profile_id: str) -> SmokeResult:
    if hasattr(entrypoint, "run"):
        return SmokeResult.model_validate(entrypoint.run(profile_id=profile_id))

    if callable(entrypoint):
        try:
            raw_result = entrypoint(profile_id=profile_id)
        except TypeError:
            raw_result = entrypoint()

        if hasattr(raw_result, "run"):
            raw_result = raw_result.run(profile_id=profile_id)

        return SmokeResult.model_validate(raw_result)

    raise TypeError("smoke_hook entrypoint is not callable")


def _failed_smoke_result(
    *,
    module_id: str,
    hook_name: str,
    started_at: float,
    failure_reason: str,
) -> SmokeResult:
    return SmokeResult(
        module_id=module_id,
        hook_name=hook_name,
        passed=False,
        duration_ms=max((perf_counter() - started_at) * 1000, 0.0),
        failure_reason=failure_reason,
    )


def _skip_artifact(module_id: str, integration_status: str) -> dict[str, str]:
    return {
        "kind": "smoke_skip",
        "module_id": module_id,
        "skipped": "true",
        "integration_status": integration_status,
    }


def _smoke_result_artifact(result: SmokeResult) -> dict[str, str]:
    artifact = {
        "kind": "smoke_result",
        "module_id": result.module_id,
        "hook_name": result.hook_name,
        "passed": str(result.passed).lower(),
    }
    if result.failure_reason:
        artifact["failure_reason"] = result.failure_reason

    return artifact


def _run_id(profile_id: str, started_at: datetime) -> str:
    timestamp = started_at.strftime("%Y%m%dT%H%M%S%fZ")
    return f"smoke-{profile_id}-{timestamp}"


def _summary(
    *,
    status: str,
    blocked_modules: list[str],
    degraded_modules: list[str],
    smoke_results: list[SmokeResult],
    skip_count: int,
) -> str:
    failed_hooks = [
        result.module_id
        for result in smoke_results
        if not result.passed
    ]
    if status == "failed":
        return (
            "Smoke failed; "
            f"blocked={blocked_modules}; failed_hooks={failed_hooks}; "
            f"skipped={skip_count}"
        )
    if status == "partial":
        return (
            "Smoke partially passed; "
            f"degraded={degraded_modules}; skipped={skip_count}"
        )

    return f"Smoke succeeded; skipped={skip_count}"


def _persist_record(record: IntegrationRunRecord, report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            record.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
