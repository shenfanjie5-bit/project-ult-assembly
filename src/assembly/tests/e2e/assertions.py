"""Assertions for minimal-cycle e2e reports."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Mapping, Sequence

from assembly.tests.e2e.schema import E2EAssertionResult, OrchestratorCycleReport


def assert_phase_order(
    observed: Sequence[str],
    expected: Sequence[str],
) -> list[E2EAssertionResult]:
    """Assert that observed phases exactly match the manifest-declared order."""

    observed_list = list(observed)
    expected_list = list(expected)
    results: list[E2EAssertionResult] = []

    duplicate_phases = sorted(
        phase for phase, count in Counter(observed_list).items() if count > 1
    )
    if duplicate_phases:
        results.append(
            _failed(
                "phase_order",
                "Observed phases contain duplicates",
                {
                    "duplicates": duplicate_phases,
                    "observed": observed_list,
                    "expected": expected_list,
                },
            )
        )

    missing_phases = [phase for phase in expected_list if phase not in observed_list]
    if missing_phases:
        results.append(
            _failed(
                "phase_order",
                "Observed phases are missing manifest-declared phases",
                {
                    "missing": missing_phases,
                    "observed": observed_list,
                    "expected": expected_list,
                },
            )
        )

    unexpected_phases = [phase for phase in observed_list if phase not in expected_list]
    if unexpected_phases:
        results.append(
            _failed(
                "phase_order",
                "Observed phases contain unexpected phases",
                {
                    "unexpected": unexpected_phases,
                    "observed": observed_list,
                    "expected": expected_list,
                },
            )
        )

    if observed_list != expected_list:
        results.append(
            _failed(
                "phase_order",
                "Observed phases do not match manifest-declared order",
                {"observed": observed_list, "expected": expected_list},
            )
        )

    if results:
        return results

    return [
        E2EAssertionResult(
            assertion_name="phase_order",
            status="passed",
            message="Observed phases match manifest-declared order",
            details={"observed": observed_list, "expected": expected_list},
        )
    ]


def assert_required_artifacts(
    artifacts: Mapping[str, str],
    required: Sequence[str],
    *,
    base_dir: Path,
) -> list[E2EAssertionResult]:
    """Assert that every manifest-required artifact exists on disk."""

    results: list[E2EAssertionResult] = []
    base_dir = Path(base_dir).resolve(strict=False)
    for artifact_key in required:
        raw_path = artifacts.get(artifact_key)
        if raw_path is None:
            results.append(
                _failed(
                    "required_artifact",
                    "Required artifact key is missing from orchestrator report",
                    {
                        "artifact_key": artifact_key,
                        "expected_path": str(base_dir / artifact_key),
                    },
                )
            )
            continue

        artifact_path = Path(raw_path)
        if artifact_path.is_absolute():
            normalized_path = artifact_path.resolve(strict=False)
            results.append(
                _failed(
                    "required_artifact",
                    "Required artifact path must be relative to the run artifact directory",
                    {
                        "artifact_key": artifact_key,
                        "expected_path": str(base_dir / artifact_key),
                        "raw_reported_path": raw_path,
                        "normalized_path": str(normalized_path),
                    },
                )
            )
            continue

        artifact_path = (base_dir / artifact_path).resolve(strict=False)
        if not artifact_path.is_relative_to(base_dir):
            results.append(
                _failed(
                    "required_artifact",
                    "Required artifact path escapes the run artifact directory",
                    {
                        "artifact_key": artifact_key,
                        "expected_path": str(base_dir / artifact_key),
                        "raw_reported_path": raw_path,
                        "normalized_path": str(artifact_path),
                    },
                )
            )
            continue

        if not artifact_path.exists():
            results.append(
                _failed(
                    "required_artifact",
                    "Required artifact path does not exist",
                    {
                        "artifact_key": artifact_key,
                        "expected_path": str(artifact_path),
                        "raw_reported_path": raw_path,
                        "normalized_path": str(artifact_path),
                    },
                )
            )
            continue

        results.append(
            E2EAssertionResult(
                assertion_name="required_artifact",
                status="passed",
                message="Required artifact exists",
                details={
                    "artifact_key": artifact_key,
                    "path": str(artifact_path),
                },
            )
        )

    if not required:
        results.append(
            E2EAssertionResult(
                assertion_name="required_artifact",
                status="passed",
                message="Fixture declares no required artifacts",
            )
        )

    return results


def assert_orchestrator_report(
    report: OrchestratorCycleReport,
    *,
    profile_id: str | None = None,
) -> list[E2EAssertionResult]:
    """Assert terminal status and optional profile identity for a cycle report."""

    results: list[E2EAssertionResult] = []
    if profile_id is not None and report.profile_id != profile_id:
        results.append(
            _failed(
                "orchestrator_report",
                "Orchestrator report profile_id does not match the requested profile",
                {"expected": profile_id, "actual": report.profile_id},
            )
        )

    if report.status != "success":
        results.append(
            _failed(
                "orchestrator_report",
                "Orchestrator report terminal status is not success",
                {"status": report.status},
            )
        )

    if results:
        return results

    return [
        E2EAssertionResult(
            assertion_name="orchestrator_report",
            status="passed",
            message="Orchestrator report terminal status is success",
            details={"profile_id": report.profile_id, "status": report.status},
        )
    ]


def _failed(
    assertion_name: str,
    message: str,
    details: dict[str, object],
) -> E2EAssertionResult:
    return E2EAssertionResult(
        assertion_name=assertion_name,
        status="failed",
        message=message,
        details=details,
    )
