"""Orchestrator public entrypoint loadability check."""

from __future__ import annotations

from assembly.compat.checks.base import load_public_entrypoint
from assembly.compat.schema import (
    CompatibilityCheckContext,
    CompatibilityCheckResult,
    CompatibilityCheckStatus,
)
from assembly.contracts import ENTRYPOINT_KIND_TO_PROTOCOL
from assembly.registry import IntegrationStatus, ModuleRegistryEntry

_ORCHESTRATOR_MODULE_ID = "orchestrator"
_REQUIRED_KINDS = ("cli", "version_declaration")


class OrchestratorLoadabilityCheck:
    """Validate orchestrator public CLI/version entrypoints without running cycles."""

    check_name = "orchestrator_loadability"

    def run(
        self,
        context: CompatibilityCheckContext,
    ) -> list[CompatibilityCheckResult]:
        """Run loadability checks if orchestrator is resolved."""

        entry = next(
            (
                resolved_entry
                for resolved_entry in context.resolved_entries
                if resolved_entry.module_id == _ORCHESTRATOR_MODULE_ID
            ),
            None,
        )
        if entry is None:
            return []

        if entry.integration_status == IntegrationStatus.not_started:
            return [
                CompatibilityCheckResult(
                    check_name=self.check_name,
                    module_id=entry.module_id,
                    status=CompatibilityCheckStatus.not_started,
                    message="orchestrator integration has not started",
                    details={"integration_status": entry.integration_status.value},
                )
            ]

        return [self._check_entry(entry)]

    def _check_entry(self, entry: ModuleRegistryEntry) -> CompatibilityCheckResult:
        entrypoints_by_kind = {
            public_entrypoint.kind: public_entrypoint
            for public_entrypoint in entry.public_entrypoints
        }
        missing_kinds = [
            kind for kind in _REQUIRED_KINDS if kind not in entrypoints_by_kind
        ]
        if missing_kinds:
            return _failed(
                self.check_name,
                entry.module_id,
                "orchestrator is missing required public entrypoints",
                {"missing_kinds": missing_kinds},
            )

        loaded_references: dict[str, str] = {}
        for kind in _REQUIRED_KINDS:
            public_entrypoint = entrypoints_by_kind[kind]
            try:
                loaded = load_public_entrypoint(public_entrypoint)
            except Exception as exc:
                return _failed(
                    self.check_name,
                    entry.module_id,
                    f"orchestrator {kind} entrypoint could not be imported",
                    {
                        "reference": public_entrypoint.reference,
                        "failure_reason": str(exc),
                    },
                )

            protocol = ENTRYPOINT_KIND_TO_PROTOCOL[kind]
            if not isinstance(loaded, protocol):
                return _failed(
                    self.check_name,
                    entry.module_id,
                    f"orchestrator {kind} entrypoint does not satisfy protocol",
                    {"reference": public_entrypoint.reference},
                )
            loaded_references[kind] = public_entrypoint.reference

        return CompatibilityCheckResult(
            check_name=self.check_name,
            module_id=entry.module_id,
            status=CompatibilityCheckStatus.success,
            message="orchestrator public CLI and version entrypoints are loadable",
            details={"references": loaded_references},
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
