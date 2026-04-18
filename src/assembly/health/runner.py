"""Healthcheck convergence runner."""

from __future__ import annotations

import importlib
import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter, sleep
from typing import Any, Mapping

from assembly.bootstrap.service_handle import CommandRunner
from assembly.contracts.models import HealthResult, HealthStatus
from assembly.contracts.protocols import HealthProbe
from assembly.health.probes_builtin import (
    BUILTIN_PROBE_BY_SERVICE,
    build_builtin_probes,
)
from assembly.profiles.resolver import ResolvedConfigSnapshot
from assembly.registry import IntegrationStatus, ModuleRegistryEntry, Registry
from assembly.registry.schema import PublicEntrypoint


_RETRY_BACKOFF_SEC = 0.05


@dataclass(frozen=True)
class _BuiltinProbeSpec:
    service_name: str
    probe_name: str
    optional: bool


class HealthcheckRunner:
    """Run built-in service probes and available public module probes."""

    def __init__(
        self,
        *,
        builtin_probes: Mapping[str, HealthProbe] | None = None,
        compose_file: Path = Path("compose/lite-local.yaml"),
        env_file: Path | None = None,
        command_runner: CommandRunner | None = None,
    ) -> None:
        self._builtin_probes = (
            dict(builtin_probes) if builtin_probes is not None else None
        )
        self._compose_file = Path(compose_file)
        self._env_file = Path(env_file) if env_file is not None else None
        self._command_runner = command_runner

    def run(
        self,
        snapshot: ResolvedConfigSnapshot,
        registry: Registry | None = None,
        *,
        timeout_sec: float = 30.0,
    ) -> list[HealthResult]:
        """Run health probes in resolved Lite service order, then registry order."""

        results: list[HealthResult] = []
        builtin_plan = _builtin_probe_plan(snapshot)
        probes = self._builtin_probes
        if probes is None and builtin_plan:
            probes = build_builtin_probes(
                snapshot,
                compose_file=self._compose_file,
                env_file=self._env_file,
                command_runner=self._command_runner,
            )

        convergence_deadline_sec = max(timeout_sec, 0.0)
        deadline_at = perf_counter() + convergence_deadline_sec
        for spec in builtin_plan:
            probe = probes.get(spec.probe_name)
            if probe is None:
                result = _builtin_missing_result(spec)
            elif spec.optional:
                result = _run_optional_builtin_probe(
                    probe,
                    spec,
                    deadline_at=deadline_at,
                    deadline_sec=convergence_deadline_sec,
                )
            else:
                result = _run_required_builtin_probe_until_healthy(
                    probe,
                    spec,
                    deadline_at=deadline_at,
                    deadline_sec=convergence_deadline_sec,
                )
            results.append(_classify_builtin_result(result, spec))

        if registry is not None:
            results.extend(
                _run_registry_health_probes(
                    snapshot,
                    registry,
                    timeout_sec=timeout_sec,
                )
            )

        return results


def _builtin_probe_plan(snapshot: ResolvedConfigSnapshot) -> list[_BuiltinProbeSpec]:
    specs: list[_BuiltinProbeSpec] = []
    for bundle in snapshot.service_bundles:
        for service_name in bundle.startup_order:
            probe_name = BUILTIN_PROBE_BY_SERVICE.get(service_name)
            if probe_name is None:
                probe_name = f"{service_name}-ready"
            specs.append(
                _BuiltinProbeSpec(
                    service_name=service_name,
                    probe_name=probe_name,
                    optional=bundle.optional,
                )
            )

    return specs


def _run_required_builtin_probe_until_healthy(
    probe: HealthProbe,
    spec: _BuiltinProbeSpec,
    *,
    deadline_at: float,
    deadline_sec: float,
) -> HealthResult:
    started_at = perf_counter()
    attempts = 0
    last_result: HealthResult | None = None
    last_failure: HealthResult | None = None

    while True:
        remaining_sec = _remaining_sec(deadline_at)
        if remaining_sec <= 0:
            if last_result is None:
                last_result = _deadline_expired_result(spec, started_at=started_at)

            return _with_convergence_details(
                last_result,
                started_at=started_at,
                attempts=attempts,
                deadline_sec=deadline_sec,
                deadline_exceeded=True,
                last_failure=last_failure,
            )

        result = _run_health_probe(
            probe,
            module_id=spec.service_name,
            probe_name=spec.probe_name,
            timeout_sec=remaining_sec,
        )
        attempts += 1
        last_result = result

        if result.status == HealthStatus.healthy:
            return _with_convergence_details(
                result,
                started_at=started_at,
                attempts=attempts,
                deadline_sec=deadline_sec,
                deadline_exceeded=False,
                last_failure=last_failure,
            )

        last_failure = result
        if _remaining_sec(deadline_at) <= 0:
            return _with_convergence_details(
                result,
                started_at=started_at,
                attempts=attempts,
                deadline_sec=deadline_sec,
                deadline_exceeded=True,
            )

        _sleep_before_retry(deadline_at)


def _run_optional_builtin_probe(
    probe: HealthProbe,
    spec: _BuiltinProbeSpec,
    *,
    deadline_at: float,
    deadline_sec: float,
) -> HealthResult:
    started_at = perf_counter()
    remaining_sec = _remaining_sec(deadline_at)
    if remaining_sec <= 0:
        return _with_convergence_details(
            _deadline_expired_result(spec, started_at=started_at),
            started_at=started_at,
            attempts=0,
            deadline_sec=deadline_sec,
            deadline_exceeded=True,
        )

    result = _run_health_probe(
        probe,
        module_id=spec.service_name,
        probe_name=spec.probe_name,
        timeout_sec=remaining_sec,
    )
    return _with_convergence_details(
        result,
        started_at=started_at,
        attempts=1,
        deadline_sec=deadline_sec,
        deadline_exceeded=(
            result.status != HealthStatus.healthy and _remaining_sec(deadline_at) <= 0
        ),
    )


def _classify_builtin_result(
    result: HealthResult,
    spec: _BuiltinProbeSpec,
) -> HealthResult:
    if result.status == HealthStatus.healthy:
        return result

    details = dict(result.details)
    details["optional"] = spec.optional
    if spec.optional:
        return result.model_copy(
            update={
                "status": HealthStatus.degraded,
                "message": result.message or f"{spec.service_name} is degraded",
                "details": details,
            }
        )

    return result.model_copy(
        update={
            "status": HealthStatus.blocked,
            "message": result.message or f"{spec.service_name} is blocked",
            "details": details,
        }
    )


def _with_convergence_details(
    result: HealthResult,
    *,
    started_at: float,
    attempts: int,
    deadline_sec: float,
    deadline_exceeded: bool,
    last_failure: HealthResult | None = None,
) -> HealthResult:
    elapsed_ms = max((perf_counter() - started_at) * 1000, 0.0)
    details = dict(result.details)
    details.update(
        {
            "convergence_attempts": attempts,
            "convergence_elapsed_ms": elapsed_ms,
            "convergence_deadline_sec": deadline_sec,
            "deadline_exceeded": deadline_exceeded,
        }
    )
    if last_failure is not None:
        details["last_failure_status"] = last_failure.status.value
        details["last_failure_message"] = last_failure.message

    return result.model_copy(
        update={
            "latency_ms": elapsed_ms,
            "details": details,
        }
    )


def _remaining_sec(deadline_at: float) -> float:
    return max(deadline_at - perf_counter(), 0.0)


def _sleep_before_retry(deadline_at: float) -> None:
    remaining_sec = _remaining_sec(deadline_at)
    if remaining_sec <= 0:
        return

    sleep(min(_RETRY_BACKOFF_SEC, remaining_sec))


def _run_registry_health_probes(
    snapshot: ResolvedConfigSnapshot,
    registry: Registry,
    *,
    timeout_sec: float,
) -> list[HealthResult]:
    results: list[HealthResult] = []
    entries_by_id = {entry.module_id: entry for entry in registry.modules}

    for module_id in snapshot.enabled_modules:
        entry = entries_by_id.get(module_id)
        if entry is None:
            results.append(
                _unavailable_health_result(
                    module_id,
                    "unregistered",
                    status=HealthStatus.blocked,
                )
            )
            continue

        health_entrypoints = [
            entrypoint
            for entrypoint in entry.public_entrypoints
            if entrypoint.kind == "health_probe"
        ]
        if entry.integration_status == IntegrationStatus.not_started:
            probe_name = health_entrypoints[0].name if health_entrypoints else "health"
            results.append(
                _unavailable_health_result(
                    module_id,
                    entry.integration_status.value,
                    status=HealthStatus.degraded,
                    probe_name=probe_name,
                )
            )
            continue

        if not health_entrypoints:
            results.append(
                _unavailable_health_result(
                    module_id,
                    "missing_health_probe",
                    status=HealthStatus.blocked,
                )
            )
            continue

        for entrypoint in health_entrypoints:
            results.append(
                _run_registry_health_probe(
                    entry,
                    entrypoint,
                    timeout_sec=timeout_sec,
                )
            )

    return results


def _run_registry_health_probe(
    entry: ModuleRegistryEntry,
    public_entrypoint: PublicEntrypoint,
    *,
    timeout_sec: float,
) -> HealthResult:
    started_at = perf_counter()
    try:
        entrypoint = _load_reference(public_entrypoint.reference)
    except Exception as exc:
        return _blocked_result(
            module_id=entry.module_id,
            probe_name=public_entrypoint.name,
            started_at=started_at,
            message=f"{entry.module_id} health_probe could not be imported",
            details={
                "reference": public_entrypoint.reference,
                "failure_reason": str(exc),
            },
        )

    return _run_health_probe(
        entrypoint,
        module_id=entry.module_id,
        probe_name=public_entrypoint.name,
        timeout_sec=timeout_sec,
    )


def _run_health_probe(
    entrypoint: Any,
    *,
    module_id: str,
    probe_name: str,
    timeout_sec: float,
) -> HealthResult:
    result_queue: queue.Queue[tuple[str, object]] = queue.Queue(maxsize=1)
    started_at = perf_counter()

    def target() -> None:
        try:
            result_queue.put(
                ("ok", _invoke_health_probe(entrypoint, timeout_sec=timeout_sec))
            )
        except Exception as exc:
            result_queue.put(("error", exc))

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    try:
        kind, payload = result_queue.get(timeout=max(timeout_sec, 0.0))
    except queue.Empty:
        return _blocked_result(
            module_id=module_id,
            probe_name=probe_name,
            started_at=started_at,
            message=f"{module_id} health_probe timed out",
            details={"timeout_sec": str(timeout_sec), "timeout": "true"},
        )

    if kind == "ok":
        return HealthResult.model_validate(payload)

    exc = payload
    if isinstance(exc, BaseException):
        return _blocked_result(
            module_id=module_id,
            probe_name=probe_name,
            started_at=started_at,
            message=f"{module_id} health_probe failed",
            details={"failure_reason": str(exc)},
        )

    return _blocked_result(
        module_id=module_id,
        probe_name=probe_name,
        started_at=started_at,
        message=f"{module_id} health_probe failed",
        details={"failure_reason": str(exc)},
    )


def _invoke_health_probe(entrypoint: Any, *, timeout_sec: float) -> HealthResult:
    if hasattr(entrypoint, "check"):
        return HealthResult.model_validate(entrypoint.check(timeout_sec=timeout_sec))

    if callable(entrypoint):
        try:
            raw_result = entrypoint(timeout_sec=timeout_sec)
        except TypeError:
            raw_result = entrypoint()

        if hasattr(raw_result, "check"):
            raw_result = raw_result.check(timeout_sec=timeout_sec)

        return HealthResult.model_validate(raw_result)

    raise TypeError("health_probe entrypoint is not callable")


def _load_reference(reference: str) -> Any:
    module_name, _, symbol_name = reference.partition(":")
    if not module_name or not symbol_name:
        raise ValueError(f"Invalid public entrypoint reference: {reference}")

    module = importlib.import_module(module_name)
    return getattr(module, symbol_name)


def _builtin_missing_result(spec: _BuiltinProbeSpec) -> HealthResult:
    return HealthResult(
        module_id=spec.service_name,
        probe_name=spec.probe_name,
        status=HealthStatus.blocked,
        latency_ms=0.0,
        message=f"No built-in health probe registered for {spec.service_name}",
        details={"service": spec.service_name},
    )


def _deadline_expired_result(
    spec: _BuiltinProbeSpec,
    *,
    started_at: float,
) -> HealthResult:
    return _blocked_result(
        module_id=spec.service_name,
        probe_name=spec.probe_name,
        started_at=started_at,
        message=f"{spec.service_name} health_probe did not run before deadline",
        details={"timeout": "true", "timeout_sec": "0.0"},
    )


def _unavailable_health_result(
    module_id: str,
    reason: str,
    *,
    status: HealthStatus,
    probe_name: str = "health",
) -> HealthResult:
    return HealthResult(
        module_id=module_id,
        probe_name=probe_name,
        status=status,
        latency_ms=0.0,
        message=f"{module_id} health_probe unavailable: {reason}",
        details={
            "registry_reason": reason,
        },
    )


def _blocked_result(
    *,
    module_id: str,
    probe_name: str,
    started_at: float,
    message: str,
    details: dict[str, Any],
) -> HealthResult:
    return HealthResult(
        module_id=module_id,
        probe_name=probe_name,
        status=HealthStatus.blocked,
        latency_ms=max((perf_counter() - started_at) * 1000, 0.0),
        message=message,
        details=details,
    )
