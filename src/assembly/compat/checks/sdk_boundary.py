"""Subsystem SDK public boundary compatibility check."""

from __future__ import annotations

from pydantic import ValidationError

from assembly.compat.checks.base import load_public_entrypoint
from assembly.compat.checks.contracts_version import _single_entrypoint
from assembly.compat.schema import (
    CompatibilityCheckContext,
    CompatibilityCheckResult,
    CompatibilityCheckStatus,
)
from assembly.contracts import VersionDeclaration, VersionInfo
from assembly.registry import IntegrationStatus, ModuleRegistryEntry

_SDK_MODULE_ID = "subsystem-sdk"


class SdkBoundaryCheck:
    """Validate the subsystem SDK boundary without importing private SDK models."""

    check_name = "sdk_boundary"

    def run(
        self,
        context: CompatibilityCheckContext,
    ) -> list[CompatibilityCheckResult]:
        """Run the SDK boundary check if the SDK is resolved for the profile."""

        entry = next(
            (
                resolved_entry
                for resolved_entry in context.resolved_entries
                if resolved_entry.module_id == _SDK_MODULE_ID
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
                    message="subsystem-sdk integration has not started",
                    details={
                        "integration_status": entry.integration_status.value,
                        "registered_entrypoint_kinds": _registered_kinds(entry),
                    },
                )
            ]

        return [self._check_version_boundary(context, entry)]

    def _check_version_boundary(
        self,
        context: CompatibilityCheckContext,
        entry: ModuleRegistryEntry,
    ) -> CompatibilityCheckResult:
        public_entrypoint = _single_entrypoint(entry, "version_declaration")
        if public_entrypoint is None:
            return _failed(
                self.check_name,
                entry.module_id,
                "subsystem-sdk has no version_declaration public entrypoint",
            )

        try:
            loaded = load_public_entrypoint(public_entrypoint)
        except Exception as exc:
            return _failed(
                self.check_name,
                entry.module_id,
                "subsystem-sdk version_declaration could not be imported",
                {"reference": public_entrypoint.reference, "failure_reason": str(exc)},
            )

        if not isinstance(loaded, VersionDeclaration):
            return _failed(
                self.check_name,
                entry.module_id,
                "subsystem-sdk version_declaration does not satisfy protocol",
                {"reference": public_entrypoint.reference},
            )

        try:
            declared = VersionInfo.model_validate(loaded.declare())
        except ValidationError as exc:
            return _failed(
                self.check_name,
                entry.module_id,
                "subsystem-sdk version declaration returned invalid data",
                {"failure_reason": str(exc)},
            )

        mismatches: dict[str, dict[str, str]] = {}
        if declared.module_id != entry.module_id:
            mismatches["module_id"] = {
                "expected": entry.module_id,
                "actual": declared.module_id,
            }
        if declared.module_version != entry.module_version:
            mismatches["module_version"] = {
                "expected": entry.module_version,
                "actual": declared.module_version,
            }
        if declared.contract_version != entry.contract_version:
            mismatches["contract_version"] = {
                "expected": entry.contract_version,
                "actual": declared.contract_version,
            }
        if declared.contract_version != context.matrix_entry.contract_version:
            mismatches["matrix_contract_version"] = {
                "expected": context.matrix_entry.contract_version,
                "actual": declared.contract_version,
            }

        if mismatches:
            return _failed(
                self.check_name,
                entry.module_id,
                "subsystem-sdk version declaration does not match registry",
                {"mismatches": mismatches},
            )

        return CompatibilityCheckResult(
            check_name=self.check_name,
            module_id=entry.module_id,
            status=CompatibilityCheckStatus.success,
            message="subsystem-sdk public version boundary is compatible",
            details={
                "reference": public_entrypoint.reference,
                "registered_entrypoint_kinds": _registered_kinds(entry),
            },
        )


def _registered_kinds(entry: ModuleRegistryEntry) -> list[str]:
    return sorted({public_entrypoint.kind for public_entrypoint in entry.public_entrypoints})


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
