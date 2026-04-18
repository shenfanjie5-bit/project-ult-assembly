"""Contract compatibility suite runner."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

import yaml
from pydantic import ValidationError

from assembly.compat.checks import (
    CompatibilityCheck,
    ContractsVersionCheck,
    OrchestratorLoadabilityCheck,
    PublicApiBoundaryCheck,
    SdkBoundaryCheck,
)
from assembly.compat.errors import CompatibilityError, CompatibilityPromotionError
from assembly.compat.schema import (
    CompatibilityCheckContext,
    CompatibilityCheckResult,
    CompatibilityCheckStatus,
    CompatibilityReport,
)
from assembly.contracts.models import IntegrationRunRecord
from assembly.profiles.resolver import render_profile
from assembly.registry import (
    CompatibilityMatrixEntry,
    ModuleRegistryEntry,
    Registry,
    load_all,
    resolve_for_profile,
)


class CompatRunner:
    """Run contract compatibility checks for a resolved profile."""

    def __init__(self, checks: Sequence[CompatibilityCheck] | None = None) -> None:
        self._checks = list(checks) if checks is not None else _default_checks()

    def run(
        self,
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
        """Resolve registry/profile facts, run checks, and persist a report."""

        started_at = datetime.now(timezone.utc)
        registry = load_all(registry_root)
        resolved_entries = resolve_for_profile(
            registry,
            profile_id,
            profiles_root=profiles_root,
        )
        snapshot = render_profile(
            profile_id,
            profiles_root=profiles_root,
            bundles_root=bundles_root,
            env=env,
        ).model_copy(
            update={"enabled_modules": [entry.module_id for entry in resolved_entries]}
        )
        matrix_entry = _select_matrix_entry(registry, profile_id, resolved_entries)
        context = CompatibilityCheckContext(
            profile_id=profile_id,
            snapshot=snapshot,
            registry=registry,
            resolved_entries=resolved_entries,
            matrix_entry=matrix_entry,
            timeout_sec=timeout_sec,
        )
        checks = self._run_checks(context)
        finished_at = datetime.now(timezone.utc)
        run_id = _run_id(profile_id, started_at)
        report_path = Path(reports_dir) / f"{run_id}.json"
        record = IntegrationRunRecord(
            run_id=run_id,
            profile_id=profile_id,
            run_type="contract",
            started_at=started_at,
            finished_at=finished_at,
            status=_record_status(checks),
            artifacts=[
                {"kind": "contract_report", "path": str(report_path)},
                {"kind": "compatibility_matrix", "version": matrix_entry.matrix_version},
            ],
            failing_modules=_non_success_modules(checks),
            summary=_summary(checks),
        )
        report = CompatibilityReport(
            run_record=record,
            checks=checks,
            matrix_version=matrix_entry.matrix_version,
            promoted=False,
            report_path=report_path,
        )
        _persist_report(report)

        if promote:
            promoted_entry = promote_matrix_entry(
                profile_id,
                registry_root=registry_root,
                reports_root=_reports_root(Path(reports_dir)),
                matrix_entry=matrix_entry,
                contract_run_record=record,
            )
            report = report.model_copy(
                update={
                    "promoted": True,
                    "matrix_version": promoted_entry.matrix_version,
                }
            )
            _persist_report(report)

        return report

    def _run_checks(
        self,
        context: CompatibilityCheckContext,
    ) -> list[CompatibilityCheckResult]:
        results: list[CompatibilityCheckResult] = []
        for check in self._checks:
            try:
                results.extend(check.run(context))
            except Exception as exc:
                results.append(
                    CompatibilityCheckResult(
                        check_name=check.__class__.__name__,
                        module_id="assembly",
                        status=CompatibilityCheckStatus.failed,
                        message="compatibility check raised unexpectedly",
                        details={"failure_reason": str(exc)},
                    )
                )

        return results


def promote_matrix_entry(
    profile_id: str,
    *,
    registry_root: Path = Path("."),
    reports_root: Path = Path("reports"),
    matrix_entry: CompatibilityMatrixEntry,
    contract_run_record: IntegrationRunRecord,
    now: datetime | None = None,
) -> CompatibilityMatrixEntry:
    """Promote a draft matrix entry after all required run records are successful."""

    if matrix_entry.status == "deprecated":
        raise CompatibilityPromotionError(
            "Deprecated compatibility matrix entries cannot be promoted"
        )
    if matrix_entry.status != "draft":
        raise CompatibilityPromotionError(
            f"Only draft compatibility matrix entries can be promoted; "
            f"got {matrix_entry.status}"
        )
    if contract_run_record.profile_id != profile_id:
        raise CompatibilityPromotionError(
            "Contract run profile does not match matrix entry profile"
        )
    if contract_run_record.status != "success":
        raise CompatibilityPromotionError(
            "Cannot promote compatibility matrix entry without a successful "
            "contract run"
        )

    required_run_types = _required_run_types(matrix_entry.required_tests)
    missing = [
        run_type
        for run_type in required_run_types
        if not _has_successful_run_record(
            reports_root,
            profile_id=profile_id,
            run_type=run_type,
            current_contract_run=contract_run_record,
        )
    ]
    if missing:
        raise CompatibilityPromotionError(
            "Cannot promote compatibility matrix entry; missing successful "
            f"run records for: {', '.join(missing)}"
        )

    matrix_path = Path(registry_root) / "compatibility-matrix.yaml"
    raw = yaml.safe_load(matrix_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise CompatibilityPromotionError(
            f"Invalid compatibility matrix in {matrix_path}: YAML root must be a list"
        )

    target_index = _find_raw_matrix_entry(raw, matrix_entry)
    if target_index is None:
        raise CompatibilityPromotionError(
            "Compatibility matrix entry could not be found for promotion"
        )

    verified_at = now or datetime.now(timezone.utc)
    updated_item = dict(raw[target_index])
    updated_item["status"] = "verified"
    updated_item["verified_at"] = _isoformat_utc(verified_at)
    promoted_entry = CompatibilityMatrixEntry.model_validate(updated_item)
    raw[target_index] = promoted_entry.model_dump(mode="json")
    matrix_path.write_text(
        yaml.safe_dump(raw, sort_keys=False),
        encoding="utf-8",
    )
    return promoted_entry


def _default_checks() -> list[CompatibilityCheck]:
    return [
        ContractsVersionCheck(),
        SdkBoundaryCheck(),
        OrchestratorLoadabilityCheck(),
        PublicApiBoundaryCheck(),
    ]


def _select_matrix_entry(
    registry: Registry,
    profile_id: str,
    resolved_entries: Sequence[ModuleRegistryEntry],
) -> CompatibilityMatrixEntry:
    expected_versions = {
        entry.module_id: entry.module_version for entry in resolved_entries
    }
    for matrix_entry in registry.compatibility_matrix:
        if matrix_entry.profile_id != profile_id or matrix_entry.status == "deprecated":
            continue

        matrix_versions = {
            module.module_id: module.module_version
            for module in matrix_entry.module_set
        }
        if matrix_versions == expected_versions:
            return matrix_entry

    raise CompatibilityError(
        f"No active compatibility matrix entry matches profile {profile_id}"
    )


def _run_id(profile_id: str, started_at: datetime) -> str:
    timestamp = started_at.strftime("%Y%m%dT%H%M%S%fZ")
    return f"contract-{profile_id}-{timestamp}"


def _record_status(checks: Sequence[CompatibilityCheckResult]) -> str:
    if any(check.status == CompatibilityCheckStatus.failed for check in checks):
        return "failed"
    if any(check.status != CompatibilityCheckStatus.success for check in checks):
        return "partial"
    return "success"


def _non_success_modules(checks: Sequence[CompatibilityCheckResult]) -> list[str]:
    return sorted(
        {
            check.module_id
            for check in checks
            if check.status != CompatibilityCheckStatus.success
        }
    )


def _summary(checks: Sequence[CompatibilityCheckResult]) -> str:
    failed = [
        check.module_id
        for check in checks
        if check.status == CompatibilityCheckStatus.failed
    ]
    not_started = [
        check.module_id
        for check in checks
        if check.status == CompatibilityCheckStatus.not_started
    ]
    if failed:
        return f"Contract suite failed; failed_modules={sorted(set(failed))}"
    if not_started:
        return (
            "Contract suite partially passed; "
            f"not_started={sorted(set(not_started))}"
        )

    return "Contract suite succeeded"


def _persist_report(report: CompatibilityReport) -> None:
    report.report_path.parent.mkdir(parents=True, exist_ok=True)
    report.report_path.write_text(
        json.dumps(
            report.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _reports_root(reports_dir: Path) -> Path:
    return reports_dir.parent


def _required_run_types(required_tests: Sequence[str]) -> list[str]:
    mapping = {
        "contract-suite": "contract",
        "contract": "contract",
        "smoke": "smoke",
        "min-cycle-e2e": "e2e",
        "e2e": "e2e",
    }
    run_types: list[str] = []
    for required_test in required_tests:
        run_type = mapping.get(required_test)
        if run_type is None:
            raise CompatibilityPromotionError(
                f"Unknown required compatibility test: {required_test}"
            )
        if run_type not in run_types:
            run_types.append(run_type)

    return run_types


def _has_successful_run_record(
    reports_root: Path,
    *,
    profile_id: str,
    run_type: str,
    current_contract_run: IntegrationRunRecord,
) -> bool:
    if (
        run_type == "contract"
        and current_contract_run.profile_id == profile_id
        and current_contract_run.run_type == "contract"
        and current_contract_run.status == "success"
        and _current_run_record_is_persisted(current_contract_run)
    ):
        return True

    run_dir = Path(reports_root) / run_type
    if not run_dir.exists():
        return False

    for path in sorted(run_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if "run_record" in payload:
                payload = payload["run_record"]
            record = IntegrationRunRecord.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError):
            continue

        if (
            record.profile_id == profile_id
            and record.run_type == run_type
            and record.status == "success"
        ):
            return True

    return False


def _current_run_record_is_persisted(record: IntegrationRunRecord) -> bool:
    for artifact in record.artifacts:
        if artifact.get("kind") != "contract_report":
            continue

        artifact_path = artifact.get("path")
        if artifact_path and Path(artifact_path).exists():
            return True

    return False


def _find_raw_matrix_entry(
    raw: Sequence[object],
    matrix_entry: CompatibilityMatrixEntry,
) -> int | None:
    target_key = _matrix_entry_key(matrix_entry)
    for index, item in enumerate(raw):
        try:
            candidate = CompatibilityMatrixEntry.model_validate(item)
        except ValidationError:
            continue

        if _matrix_entry_key(candidate) == target_key:
            return index

    return None


def _matrix_entry_key(entry: CompatibilityMatrixEntry) -> tuple[object, ...]:
    return (
        entry.profile_id,
        entry.matrix_version,
        entry.contract_version,
        tuple((module.module_id, module.module_version) for module in entry.module_set),
    )


def _isoformat_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
