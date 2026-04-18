"""Shared compatibility check helpers."""

from __future__ import annotations

import importlib
from typing import Any, Protocol

from assembly.compat.schema import CompatibilityCheckContext, CompatibilityCheckResult
from assembly.registry.schema import PublicEntrypoint


class CompatibilityCheck(Protocol):
    """Protocol implemented by contract compatibility checks."""

    def run(
        self,
        context: CompatibilityCheckContext,
    ) -> list[CompatibilityCheckResult]:
        """Run the check and return module-level results."""
        ...


PUBLIC_COMPAT_IMPORT_KINDS = frozenset(
    {
        "version_declaration",
        "smoke_hook",
        "health_probe",
        "cli",
    }
)


def load_public_entrypoint(
    public_entrypoint: PublicEntrypoint,
    *,
    allowed_kinds: frozenset[str] = PUBLIC_COMPAT_IMPORT_KINDS,
) -> Any:
    """Import a registered public entrypoint by ``module.path:symbol`` reference."""

    if public_entrypoint.kind not in allowed_kinds:
        raise ValueError(
            f"Unsupported compatibility entrypoint kind: {public_entrypoint.kind}"
        )

    module_name, _, symbol_name = public_entrypoint.reference.partition(":")
    if not module_name or not symbol_name:
        raise ValueError(
            f"Invalid public entrypoint reference: {public_entrypoint.reference}"
        )

    module = importlib.import_module(module_name)
    return getattr(module, symbol_name)
