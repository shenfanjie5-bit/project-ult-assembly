"""Shared compatibility check helpers."""

from __future__ import annotations

from typing import Protocol

from assembly.compat.schema import CompatibilityCheckContext, CompatibilityCheckResult
from assembly.contracts.entrypoints import (
    PUBLIC_COMPAT_IMPORT_KINDS,
    load_public_entrypoint,
)


class CompatibilityCheck(Protocol):
    """Protocol implemented by contract compatibility checks."""

    def run(
        self,
        context: CompatibilityCheckContext,
    ) -> list[CompatibilityCheckResult]:
        """Run the check and return module-level results."""
        ...
