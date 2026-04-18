"""Public contract compatibility suite API."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from assembly.compat.errors import CompatibilityError, CompatibilityPromotionError
from assembly.compat.runner import CompatRunner, promote_matrix_entry
from assembly.compat.schema import (
    CompatibilityCheckContext,
    CompatibilityCheckResult,
    CompatibilityCheckStatus,
    CompatibilityReport,
)


def run_contract_suite(
    profile_id: str,
    *,
    profiles_root: Path = Path("profiles"),
    bundles_root: Path = Path("bundles"),
    registry_root: Path = Path("."),
    reports_dir: Path = Path("reports/contract"),
    env: Mapping[str, str] | None = None,
    timeout_sec: float = 30.0,
    promote: bool = False,
) -> CompatibilityReport:
    """Resolve a profile and run the contract compatibility suite."""

    return CompatRunner().run(
        profile_id,
        profiles_root=profiles_root,
        bundles_root=bundles_root,
        registry_root=registry_root,
        reports_dir=reports_dir,
        env=env,
        timeout_sec=timeout_sec,
        promote=promote,
    )


__all__ = [
    "CompatRunner",
    "CompatibilityCheckContext",
    "CompatibilityCheckResult",
    "CompatibilityCheckStatus",
    "CompatibilityError",
    "CompatibilityPromotionError",
    "CompatibilityReport",
    "promote_matrix_entry",
    "run_contract_suite",
]
