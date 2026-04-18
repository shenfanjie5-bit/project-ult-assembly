"""Version declaration compatibility checks."""

from __future__ import annotations

from pydantic import ValidationError

from assembly.compat.checks.base import load_public_entrypoint
from assembly.compat.schema import (
    CompatibilityCheckContext,
    CompatibilityCheckResult,
    CompatibilityCheckStatus,
)
from assembly.contracts import VersionDeclaration, VersionInfo
from assembly.registry import IntegrationStatus, ModuleRegistryEntry
from assembly.registry.schema import PublicEntrypoint


class ContractsVersionCheck:
    """Validate registered version declarations against registry and matrix facts."""

    check_name = "contracts_version"

    def run(
        self,
        context: CompatibilityCheckContext,
    ) -> list[CompatibilityCheckResult]:
        """Run version checks in resolved dependency order."""

        matrix_versions = {
            module.module_id: module.module_version
            for module in context.matrix_entry.module_set
        }
        return [
            self._check_entry(context, entry, matrix_versions)
            for entry in context.resolved_entries
        ]

    def _check_entry(
        self,
        context: CompatibilityCheckContext,
        entry: ModuleRegistryEntry,
        matrix_versions: dict[str, str],
    ) -> CompatibilityCheckResult:
        if entry.integration_status == IntegrationStatus.not_started:
            return CompatibilityCheckResult(
                check_name=self.check_name,
                module_id=entry.module_id,
                status=CompatibilityCheckStatus.not_started,
                message=f"{entry.module_id} has not started integration",
                details={"integration_status": entry.integration_status.value},
            )

        public_entrypoint = _single_entrypoint(entry, "version_declaration")
        if public_entrypoint is None:
            return _failed(
                self.check_name,
                entry.module_id,
                f"{entry.module_id} has no version_declaration public entrypoint",
            )

        try:
            loaded = load_public_entrypoint(public_entrypoint)
        except Exception as exc:
            return _failed(
                self.check_name,
                entry.module_id,
                f"{entry.module_id} version_declaration could not be imported",
                {"reference": public_entrypoint.reference, "failure_reason": str(exc)},
            )

        if not isinstance(loaded, VersionDeclaration):
            return _failed(
                self.check_name,
                entry.module_id,
                f"{entry.module_id} version_declaration does not satisfy protocol",
                {"reference": public_entrypoint.reference},
            )

        try:
            declared = VersionInfo.model_validate(loaded.declare())
        except ValidationError as exc:
            return _failed(
                self.check_name,
                entry.module_id,
                f"{entry.module_id} version declaration returned invalid data",
                {"failure_reason": str(exc)},
            )
        except Exception as exc:
            return _failed(
                self.check_name,
                entry.module_id,
                f"{entry.module_id} version declaration failed",
                {"failure_reason": str(exc)},
            )

        mismatches = _version_mismatches(
            declared,
            entry,
            matrix_module_version=matrix_versions.get(entry.module_id),
            matrix_contract_version=context.matrix_entry.contract_version,
        )
        if mismatches:
            return _failed(
                self.check_name,
                entry.module_id,
                f"{entry.module_id} version declaration does not match registry",
                {"mismatches": mismatches, "declared": declared.model_dump(mode="json")},
            )

        return CompatibilityCheckResult(
            check_name=self.check_name,
            module_id=entry.module_id,
            status=CompatibilityCheckStatus.success,
            message=f"{entry.module_id} version declaration matches registry",
            details={
                "reference": public_entrypoint.reference,
                "module_version": declared.module_version,
                "contract_version": declared.contract_version,
            },
        )


def _single_entrypoint(
    entry: ModuleRegistryEntry,
    kind: str,
) -> PublicEntrypoint | None:
    matches = [
        public_entrypoint
        for public_entrypoint in entry.public_entrypoints
        if public_entrypoint.kind == kind
    ]
    if not matches:
        return None

    return matches[0]


def _version_mismatches(
    declared: VersionInfo,
    entry: ModuleRegistryEntry,
    *,
    matrix_module_version: str | None,
    matrix_contract_version: str,
) -> dict[str, dict[str, str | None]]:
    expected = {
        "module_id": entry.module_id,
        "module_version": entry.module_version,
        "contract_version": entry.contract_version,
        "matrix_module_version": matrix_module_version,
        "matrix_contract_version": matrix_contract_version,
    }
    actual = {
        "module_id": declared.module_id,
        "module_version": declared.module_version,
        "contract_version": declared.contract_version,
        "matrix_module_version": declared.module_version,
        "matrix_contract_version": declared.contract_version,
    }

    mismatches: dict[str, dict[str, str | None]] = {}
    for field, expected_value in expected.items():
        actual_value = actual[field]
        if actual_value != expected_value:
            mismatches[field] = {
                "expected": expected_value,
                "actual": actual_value,
            }

    return mismatches


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
