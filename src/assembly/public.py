"""Assembly-owned public entrypoints registered in module-registry.yaml."""

from __future__ import annotations

from assembly.contracts.models import HealthResult, HealthStatus, SmokeResult


class _AssemblyHealthProbe:
    def check(self, *, timeout_sec: float) -> HealthResult:
        return HealthResult(
            module_id="assembly",
            probe_name="health",
            status=HealthStatus.healthy,
            latency_ms=0.0,
            message="assembly public health entrypoint is available",
            details={"timeout_sec": str(timeout_sec)},
        )


class _AssemblySmokeHook:
    def run(self, *, profile_id: str) -> SmokeResult:
        return SmokeResult(
            module_id="assembly",
            hook_name="smoke",
            passed=True,
            duration_ms=0.0,
            failure_reason=None,
        )


health_probe = _AssemblyHealthProbe()
smoke_hook = _AssemblySmokeHook()

