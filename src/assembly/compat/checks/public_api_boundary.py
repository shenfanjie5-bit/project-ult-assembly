"""Public API boundary protocol checks."""

from __future__ import annotations

from assembly.compat.checks.base import load_public_entrypoint
from assembly.compat.schema import (
    CompatibilityCheckContext,
    CompatibilityCheckResult,
    CompatibilityCheckStatus,
)
from assembly.contracts import ENTRYPOINT_KIND_TO_PROTOCOL
from assembly.registry import IntegrationStatus, ModuleRegistryEntry

_FOCUS_MODULE_IDS = {"main-core", "graph-engine", "audit-eval"}
_ALL_PROTOCOL_KINDS = frozenset(ENTRYPOINT_KIND_TO_PROTOCOL)


class PublicApiBoundaryCheck:
    """Validate registered public entrypoints against contract protocols."""

    check_name = "public_api_boundary"

    def run(
        self,
        context: CompatibilityCheckContext,
    ) -> list[CompatibilityCheckResult]:
        """Run boundary checks for focus modules and integrated modules."""

        results: list[CompatibilityCheckResult] = []
        for entry in context.resolved_entries:
            if entry.integration_status == IntegrationStatus.not_started:
                if entry.module_id in _FOCUS_MODULE_IDS:
                    results.append(
                        CompatibilityCheckResult(
                            check_name=self.check_name,
                            module_id=entry.module_id,
                            status=CompatibilityCheckStatus.not_started,
                            message=f"{entry.module_id} integration has not started",
                            details={
                                "integration_status": entry.integration_status.value
                            },
                        )
                    )
                continue

            results.append(self._check_entry(entry))

        return results

    def _check_entry(self, entry: ModuleRegistryEntry) -> CompatibilityCheckResult:
        if not entry.public_entrypoints:
            return _failed(
                self.check_name,
                entry.module_id,
                f"{entry.module_id} has no registered public entrypoints",
            )

        references: dict[str, str] = {}
        for public_entrypoint in entry.public_entrypoints:
            protocol = ENTRYPOINT_KIND_TO_PROTOCOL.get(public_entrypoint.kind)
            if protocol is None:
                return _failed(
                    self.check_name,
                    entry.module_id,
                    f"{entry.module_id} has unsupported public entrypoint kind",
                    {"kind": public_entrypoint.kind},
                )

            try:
                loaded = load_public_entrypoint(
                    public_entrypoint,
                    allowed_kinds=_ALL_PROTOCOL_KINDS,
                )
            except Exception as exc:
                return _failed(
                    self.check_name,
                    entry.module_id,
                    f"{entry.module_id} {public_entrypoint.kind} could not be imported",
                    {
                        "reference": public_entrypoint.reference,
                        "failure_reason": str(exc),
                    },
                )

            if not isinstance(loaded, protocol):
                return _failed(
                    self.check_name,
                    entry.module_id,
                    (
                        f"{entry.module_id} {public_entrypoint.kind} "
                        "does not satisfy protocol"
                    ),
                    {"reference": public_entrypoint.reference},
                )

            references[public_entrypoint.kind] = public_entrypoint.reference

        return CompatibilityCheckResult(
            check_name=self.check_name,
            module_id=entry.module_id,
            status=CompatibilityCheckStatus.success,
            message=f"{entry.module_id} public entrypoints satisfy protocols",
            details={"references": references},
        )


def _failed(
    check_name: str,
    module_id: str,
    message: str,
    details: dict[str, object] | None = None,
) -> CompatibilityCheckResult:
    return CompatibilityCheckResult(
        check_name=check_name,
        module_id=module_id,
        status=CompatibilityCheckStatus.failed,
        message=message,
        details={} if details is None else details,
    )
