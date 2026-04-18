"""Contract compatibility suite runner."""

from __future__ import annotations

import json
import fcntl
import hashlib
import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Mapping, Sequence

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


@dataclass(frozen=True)
class _RunRecordRef:
    record: IntegrationRunRecord
    path: Path | None


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
                _compatibility_context_artifact(matrix_entry),
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
            promoted_entry, supporting_records = _promote_matrix_entry(
                profile_id,
                registry_root=registry_root,
                reports_root=_reports_root(Path(reports_dir)),
                matrix_entry=matrix_entry,
                contract_run_record=record,
            )
            promoted_record = record.model_copy(
                update={
                    "artifacts": [
                        *record.artifacts,
                        *_promotion_support_artifacts(supporting_records),
                    ]
                }
            )
            report = report.model_copy(
                update={
                    "run_record": promoted_record,
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

    promoted_entry, _supporting_records = _promote_matrix_entry(
        profile_id,
        registry_root=registry_root,
        reports_root=reports_root,
        matrix_entry=matrix_entry,
        contract_run_record=contract_run_record,
        now=now,
    )
    return promoted_entry


def _promote_matrix_entry(
    profile_id: str,
    *,
    registry_root: Path = Path("."),
    reports_root: Path = Path("reports"),
    matrix_entry: CompatibilityMatrixEntry,
    contract_run_record: IntegrationRunRecord,
    now: datetime | None = None,
) -> tuple[CompatibilityMatrixEntry, list[_RunRecordRef]]:
    """Promote a matrix entry while holding the matrix file lock."""

    matrix_path = Path(registry_root) / "compatibility-matrix.yaml"
    with _matrix_promotion_lock(matrix_path):
        raw = _load_raw_matrix(matrix_path)
        target_index = _find_raw_matrix_entry(raw, matrix_entry)
        if target_index is None:
            raise CompatibilityPromotionError(
                "Compatibility matrix entry could not be found for promotion"
            )

        locked_entry = CompatibilityMatrixEntry.model_validate(raw[target_index])
        _validate_promotable_matrix_entry(locked_entry)
        contract_ref = _validate_current_contract_run(
            contract_run_record,
            profile_id=profile_id,
            matrix_entry=locked_entry,
        )

        supporting_records = _validated_supporting_run_records(
            reports_root,
            profile_id=profile_id,
            matrix_entry=locked_entry,
            contract_ref=contract_ref,
        )

        verified_at = now or datetime.now(timezone.utc)
        updated_item = dict(raw[target_index])
        updated_item["status"] = "verified"
        updated_item["verified_at"] = _isoformat_utc(verified_at)
        promoted_entry = CompatibilityMatrixEntry.model_validate(updated_item)
        raw[target_index] = promoted_entry.model_dump(mode="json")
        _atomic_write_yaml(matrix_path, raw)
        return promoted_entry, supporting_records


def _validate_promotable_matrix_entry(
    matrix_entry: CompatibilityMatrixEntry,
) -> None:
    if matrix_entry.status == "deprecated":
        raise CompatibilityPromotionError(
            "Deprecated compatibility matrix entries cannot be promoted"
        )
    if matrix_entry.status != "draft":
        raise CompatibilityPromotionError(
            f"Only draft compatibility matrix entries can be promoted; "
            f"got {matrix_entry.status}"
        )


def _validate_current_contract_run(
    contract_run_record: IntegrationRunRecord,
    *,
    profile_id: str,
    matrix_entry: CompatibilityMatrixEntry,
) -> _RunRecordRef:
    if contract_run_record.profile_id != profile_id:
        raise CompatibilityPromotionError(
            "Contract run profile does not match matrix entry profile"
        )
    if contract_run_record.run_type != "contract":
        raise CompatibilityPromotionError(
            "Promotion requires a contract IntegrationRunRecord"
        )
    if contract_run_record.status != "success":
        raise CompatibilityPromotionError(
            "Cannot promote compatibility matrix entry without a successful "
            "contract run"
        )
    if not _record_matches_matrix_context(contract_run_record, matrix_entry):
        raise CompatibilityPromotionError(
            "Contract run record does not match compatibility matrix context"
        )

    path = _current_run_record_path(contract_run_record)
    if path is None:
        raise CompatibilityPromotionError(
            "Contract run record artifact must be persisted before promotion"
        )

    return _RunRecordRef(record=contract_run_record, path=path)


def _validated_supporting_run_records(
    reports_root: Path,
    *,
    profile_id: str,
    matrix_entry: CompatibilityMatrixEntry,
    contract_ref: _RunRecordRef,
) -> list[_RunRecordRef]:
    required_run_types = _required_run_types(matrix_entry.required_tests)
    refs: list[_RunRecordRef] = []
    missing: list[str] = []
    for run_type in required_run_types:
        ref = _find_successful_run_record(
            reports_root,
            profile_id=profile_id,
            run_type=run_type,
            matrix_entry=matrix_entry,
            current_contract_ref=contract_ref,
        )
        if ref is None:
            missing.append(run_type)
        else:
            refs.append(ref)

    if missing:
        raise CompatibilityPromotionError(
            "Cannot promote compatibility matrix entry; missing successful "
            f"run records for: {', '.join(missing)}"
        )

    if not any(ref.record.run_type == "contract" for ref in refs):
        refs.insert(0, contract_ref)

    return _dedupe_run_refs(refs)


@contextmanager
def _matrix_promotion_lock(matrix_path: Path) -> Iterator[None]:
    lock_path = matrix_path.with_name(f"{matrix_path.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _load_raw_matrix(matrix_path: Path) -> list[object]:
    raw = yaml.safe_load(matrix_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise CompatibilityPromotionError(
            f"Invalid compatibility matrix in {matrix_path}: YAML root must be a list"
        )

    return raw


def _atomic_write_yaml(matrix_path: Path, raw: Sequence[object]) -> None:
    serialized = yaml.safe_dump(list(raw), sort_keys=False)
    matrix_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{matrix_path.name}.",
        suffix=".tmp",
        dir=matrix_path.parent,
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            fd = -1
            tmp_file.write(serialized)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())

        os.replace(tmp_path, matrix_path)
        _fsync_directory(matrix_path.parent)
    except OSError as exc:
        if fd != -1:
            os.close(fd)
        tmp_path.unlink(missing_ok=True)
        raise CompatibilityPromotionError(
            f"Could not atomically write compatibility matrix {matrix_path}: {exc}"
        ) from exc


def _fsync_directory(directory: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY

    dir_fd = os.open(directory, flags)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


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


def _find_successful_run_record(
    reports_root: Path,
    *,
    profile_id: str,
    run_type: str,
    matrix_entry: CompatibilityMatrixEntry,
    current_contract_ref: _RunRecordRef,
) -> _RunRecordRef | None:
    if run_type == "contract":
        if (
            current_contract_ref.record.profile_id == profile_id
            and current_contract_ref.record.status == "success"
            and _record_matches_matrix_context(current_contract_ref.record, matrix_entry)
        ):
            return current_contract_ref

        return None

    run_dir = Path(reports_root) / run_type
    if not run_dir.exists():
        return None

    for path in sorted(run_dir.glob("*.json")):
        record = _load_run_record(path)
        if record is None:
            continue

        if (
            record.profile_id == profile_id
            and record.run_type == run_type
            and record.status == "success"
            and _record_matches_matrix_context(record, matrix_entry)
        ):
            return _RunRecordRef(record=record, path=path)

    return None


def _load_run_record(path: Path) -> IntegrationRunRecord | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "run_record" in payload:
            payload = payload["run_record"]
        return IntegrationRunRecord.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError):
        return None


def _current_run_record_path(record: IntegrationRunRecord) -> Path | None:
    for artifact in record.artifacts:
        if artifact.get("kind") != "contract_report":
            continue

        artifact_path = artifact.get("path")
        if artifact_path and Path(artifact_path).exists():
            return Path(artifact_path)

    return None


def _record_matches_matrix_context(
    record: IntegrationRunRecord,
    matrix_entry: CompatibilityMatrixEntry,
) -> bool:
    expected = _compatibility_context_artifact(matrix_entry)
    for artifact in record.artifacts:
        if artifact.get("kind") != expected["kind"]:
            continue

        return all(artifact.get(key) == value for key, value in expected.items())

    return False


def _compatibility_context_artifact(
    matrix_entry: CompatibilityMatrixEntry,
) -> dict[str, str]:
    module_set = sorted(
        (
            {
                "module_id": module.module_id,
                "module_version": module.module_version,
            }
            for module in matrix_entry.module_set
        ),
        key=lambda item: (item["module_id"], item["module_version"]),
    )
    matrix_context = {
        "profile_id": matrix_entry.profile_id,
        "matrix_version": matrix_entry.matrix_version,
        "contract_version": matrix_entry.contract_version,
        "module_set": module_set,
    }
    return {
        "kind": "compatibility_context",
        "profile_id": matrix_entry.profile_id,
        "matrix_version": matrix_entry.matrix_version,
        "contract_version": matrix_entry.contract_version,
        "module_set_digest": _stable_digest(module_set),
        "matrix_digest": _stable_digest(matrix_context),
    }


def _stable_digest(payload: object) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _promotion_support_artifacts(
    supporting_records: Sequence[_RunRecordRef],
) -> list[dict[str, str]]:
    artifacts: list[dict[str, str]] = []
    for ref in supporting_records:
        artifact = {
            "kind": "promotion_supporting_run",
            "run_id": ref.record.run_id,
            "run_type": ref.record.run_type,
        }
        if ref.path is not None:
            artifact["path"] = str(ref.path)

        artifacts.append(artifact)

    return artifacts


def _dedupe_run_refs(refs: Sequence[_RunRecordRef]) -> list[_RunRecordRef]:
    seen: set[tuple[str, str]] = set()
    deduped: list[_RunRecordRef] = []
    for ref in refs:
        key = (ref.record.run_type, ref.record.run_id)
        if key in seen:
            continue

        seen.add(key)
        deduped.append(ref)

    return deduped


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
