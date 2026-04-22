"""Public minimal-cycle e2e API."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from assembly.contracts.models import IntegrationRunRecord
from assembly.tests.e2e.assertions import (
    assert_artifact_payload_invariants,
    assert_orchestrator_report,
    assert_phase_order,
    assert_required_artifacts,
)
from assembly.tests.e2e.runner import (
    E2EBlocker,
    E2ERunner,
    build_orchestrator_argv,
    load_minimal_cycle_fixture,
    load_orchestrator_cli,
)
from assembly.tests.e2e.schema import (
    E2EAssertionResult,
    MinimalCycleFixture,
    OrchestratorCycleReport,
)


def run_min_cycle_e2e(
    profile_id: str,
    *,
    profiles_root: Path = Path("profiles"),
    bundles_root: Path = Path("bundles"),
    registry_root: Path = Path("."),
    fixture_dir: Path = Path("src/assembly/tests/e2e/fixtures/minimal_cycle"),
    reports_dir: Path = Path("reports/e2e"),
    env: Mapping[str, str] | None = None,
    timeout_sec: float = 600.0,
    bootstrap_if_needed: bool = True,
) -> IntegrationRunRecord:
    """Run the minimal daily-cycle e2e through orchestrator's public CLI."""

    return E2ERunner().run(
        profile_id,
        profiles_root=profiles_root,
        bundles_root=bundles_root,
        registry_root=registry_root,
        fixture_dir=fixture_dir,
        reports_dir=reports_dir,
        env=env,
        timeout_sec=timeout_sec,
        bootstrap_if_needed=bootstrap_if_needed,
    )


__all__ = [
    "E2EAssertionResult",
    "E2EBlocker",
    "E2ERunner",
    "MinimalCycleFixture",
    "OrchestratorCycleReport",
    "assert_artifact_payload_invariants",
    "assert_orchestrator_report",
    "assert_phase_order",
    "assert_required_artifacts",
    "build_orchestrator_argv",
    "load_minimal_cycle_fixture",
    "load_orchestrator_cli",
    "run_min_cycle_e2e",
]
