"""Assertions for minimal-cycle e2e reports."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Mapping, Sequence

from assembly.tests.e2e.schema import E2EAssertionResult, OrchestratorCycleReport

#: The 4 invariants Stage 4 §4.2 requires every required-artifact JSON to
#: carry, written by ``orchestrator.cli.min_cycle._emit_runtime_artifacts``
#: into ``<run_artifacts_dir>/<kind>.json`` for each declared
#: ``required_artifact``.
_REQUIRED_ARTIFACT_PAYLOAD_KEYS = (
    "real_phase_execution",
    "assembled_job_names",
    "assembly_error",
    "cycle_publish_manifest_id",
)


def _expected_cycle_publish_manifest_id(scenario_id: str) -> str:
    """Mirror ``orchestrator.cli.min_cycle._derive_cycle_publish_manifest_id``.

    Kept in lockstep here (not imported) so this assertion module does not
    cross the assembly→orchestrator import boundary. Anything here MUST
    track the orchestrator side; the contract is "derive a stable
    name-shaped synthetic id" — codified in
    ``orchestrator/src/orchestrator/cli/min_cycle.py:200`` as
    ``f"MAN_{scenario_id.replace('-','_').replace('.','_')}_v0"``.
    """
    sanitized = scenario_id.replace("-", "_").replace(".", "_")
    return f"MAN_{sanitized}_v0"


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


def assert_artifact_payload_invariants(
    *,
    artifacts: Mapping[str, str],
    required_artifacts: Sequence[str],
    base_dir: Path,
    scenario_id: str,
) -> list[E2EAssertionResult]:
    """Assert each required-artifact JSON satisfies the Stage 4 §4.2 contract.

    Master plan §4.2 requires the e2e runner to load each artifact JSON
    written by ``orchestrator.cli.min_cycle`` and assert the 4
    assembly-facing invariants live in the artifact **payload** (NOT in
    the report top-level — ``OrchestratorCycleReport`` is
    ``extra="forbid"`` and only carries 5 fields):

    * ``real_phase_execution: bool`` — must be ``True``. This is the
      observe-not-assert signal codex stage 2.5 review #1 locked in:
      ``True`` ONLY when ``build_daily_cycle_jobs(None)`` real-imports +
      returns a non-empty job tuple. ``False`` means the Dagster
      assembly probe failed (with a reason in ``assembly_error``).
    * ``assembled_job_names: list[str]`` — must be non-empty. Real
      Dagster Job names returned by the builder.
    * ``assembly_error: str | None`` — must be ``None``. Non-None iff
      assembly failed; surfaces the failure reason for diagnostics.
    * ``cycle_publish_manifest_id: str`` — must equal the stable
      derived synthetic id for ``scenario_id`` (caveat: this is a
      name-derived id, NOT a real Iceberg/PG manifest write — real
      persistence is a future stage's responsibility per the
      orchestrator min-cycle docstring at
      ``min_cycle.py:_emit_runtime_artifacts``).

    Resolves each artifact's filesystem path the same way
    ``assert_required_artifacts`` does — from ``cycle_report.artifacts``
    (orchestrator's report contract: kind → path, where path is
    relative to ``base_dir``). This deliberately does NOT hardcode the
    orchestrator-side ``<kind>.json`` naming convention so any
    test-side fake CLI that uses a different artifact_path (e.g.,
    ``"custom-artifact.json"`` for kind ``"custom_artifact"``) still
    works with this assertion.

    Raises no exceptions; non-conformant payloads produce ``failed``
    ``E2EAssertionResult`` rows that the caller persists to the
    structured e2e report.

    The function deliberately does NOT cross-validate
    ``assembled_job_names`` against orchestrator's current Dagster job
    set (master plan §4.2 mentions this as a "would be nice"); doing so
    would require importing orchestrator from assembly, breaking
    assembly CLAUDE.md constraint #1 (only via public entrypoints).
    Future work could surface that set via orchestrator's
    ``version_declaration`` if the cross-check is needed.
    """

    results: list[E2EAssertionResult] = []
    base_dir = Path(base_dir).resolve(strict=False)
    expected_manifest_id = _expected_cycle_publish_manifest_id(scenario_id)

    if not required_artifacts:
        results.append(
            E2EAssertionResult(
                assertion_name="artifact_payload_invariants",
                status="passed",
                message=(
                    "Fixture declares no required artifacts; "
                    "artifact-payload invariants vacuously hold"
                ),
            )
        )
        return results

    for artifact_kind in required_artifacts:
        raw_path = artifacts.get(artifact_kind)
        if raw_path is None:
            # Surfaced separately by ``assert_required_artifacts``; skip
            # here to avoid duplicate failures on the same root cause.
            continue

        artifact_path = Path(raw_path)
        if not artifact_path.is_absolute():
            artifact_path = (base_dir / artifact_path).resolve(strict=False)
        if not artifact_path.exists():
            # Same — file-existence failure is the
            # ``assert_required_artifacts`` responsibility; skip here.
            continue

        try:
            payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            results.append(
                _failed(
                    "artifact_payload_invariants",
                    "Required-artifact JSON could not be parsed",
                    {
                        "artifact_kind": artifact_kind,
                        "path": str(artifact_path),
                        "failure_reason": str(exc),
                    },
                )
            )
            continue

        missing_keys = [
            key
            for key in _REQUIRED_ARTIFACT_PAYLOAD_KEYS
            if key not in payload
        ]
        if missing_keys:
            results.append(
                _failed(
                    "artifact_payload_invariants",
                    "Required-artifact payload is missing assembly-facing keys",
                    {
                        "artifact_kind": artifact_kind,
                        "missing_keys": missing_keys,
                        "payload_keys": sorted(payload.keys()),
                    },
                )
            )
            continue

        violations: dict[str, object] = {}
        if payload["real_phase_execution"] is not True:
            violations["real_phase_execution"] = {
                "expected": True,
                "actual": payload["real_phase_execution"],
            }
        if not payload["assembled_job_names"]:
            violations["assembled_job_names"] = {
                "expected": "non-empty list",
                "actual": payload["assembled_job_names"],
            }
        if payload["assembly_error"] is not None:
            violations["assembly_error"] = {
                "expected": None,
                "actual": payload["assembly_error"],
            }
        if payload["cycle_publish_manifest_id"] != expected_manifest_id:
            violations["cycle_publish_manifest_id"] = {
                "expected": expected_manifest_id,
                "actual": payload["cycle_publish_manifest_id"],
            }

        if violations:
            results.append(
                _failed(
                    "artifact_payload_invariants",
                    "Required-artifact payload violates Stage 4 §4.2 invariants",
                    {
                        "artifact_kind": artifact_kind,
                        "path": str(artifact_path),
                        "violations": violations,
                    },
                )
            )
            continue

        results.append(
            E2EAssertionResult(
                assertion_name="artifact_payload_invariants",
                status="passed",
                message=(
                    "Required-artifact payload satisfies Stage 4 §4.2 "
                    "invariants (real_phase_execution / assembled_job_names "
                    "/ assembly_error / cycle_publish_manifest_id)"
                ),
                details={
                    "artifact_kind": artifact_kind,
                    "assembled_job_count": len(payload["assembled_job_names"]),
                    "cycle_publish_manifest_id": payload["cycle_publish_manifest_id"],
                },
            )
        )

    return results


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
