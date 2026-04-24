"""Public minimal-cycle e2e API."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

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
    extra_bundles: Sequence[str] | None = None,
) -> IntegrationRunRecord:
    """Run the minimal daily-cycle e2e through orchestrator's public CLI.

    ``extra_bundles`` opt-in to full-dev optional service bundles (MinIO,
    Grafana, Superset, Temporal, Feast, Kafka-Flink). The list is threaded
    through to ``render_profile`` / ``healthcheck`` / ``bootstrap`` so the
    resolver appends these bundles to ``enabled_service_bundles``,
    healthcheck aggregator sees their probes, and bootstrap plan includes
    them in startup_order. Only valid for profiles whose bundle declares
    ``required_profiles: [<this profile>]`` (currently ``full-dev`` only).
    ``run_contract_suite`` is intentionally NOT threaded — optional bundles
    are infra slots, not contract-surface changes.
    """

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
        extra_bundles=extra_bundles,
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
