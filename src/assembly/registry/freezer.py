"""Release-freeze lockfile generation for verified compatibility baselines."""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Literal, Sequence

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from assembly.contracts.models import IntegrationRunRecord
from assembly.contracts.reporting import record_matches_matrix_context
from assembly.registry.loader import Registry, load_all
from assembly.registry.resolver import resolve_for_profile
from assembly.registry.schema import (
    CompatibilityMatrixEntry,
    IntegrationStatus,
)
from assembly.registry.validator import RegistryError


class ReleaseFreezeError(Exception):
    """Raised when a verified compatibility baseline cannot be frozen."""


class VersionLockModule(BaseModel):
    """Frozen module/version tuple for a release baseline."""

    model_config = ConfigDict(extra="forbid")

    module_id: str
    module_version: str
    contract_version: str
    integration_status: IntegrationStatus


class VersionLockRunRef(BaseModel):
    """Reference to a successful integration run supporting a lockfile."""

    model_config = ConfigDict(extra="forbid")

    run_type: Literal["smoke", "contract", "e2e"]
    run_id: str
    status: Literal["success"]
    path: Path | None


class VersionLock(BaseModel):
    """Auditable release-freeze lockfile."""

    model_config = ConfigDict(extra="forbid")

    lock_version: str
    profile_id: str
    matrix_version: str
    contract_version: str
    matrix_verified_at: datetime
    frozen_at: datetime
    required_tests: list[str]
    modules: list[VersionLockModule]
    supporting_runs: list[VersionLockRunRef]
    source_artifacts: dict[str, str]
    lock_file: Path


def find_verified_matrix_entry(
    registry: Registry,
    profile_id: str,
    *,
    profiles_root: Path = Path("profiles"),
) -> CompatibilityMatrixEntry:
    """Return the unique verified matrix entry matching a resolved profile."""

    verified_entries = [
        entry
        for entry in registry.compatibility_matrix
        if entry.profile_id == profile_id and entry.status == "verified"
    ]
    if not verified_entries:
        raise ReleaseFreezeError(
            f"No verified compatibility matrix entry found for profile {profile_id}"
        )
    if len(verified_entries) > 1:
        versions = ", ".join(entry.matrix_version for entry in verified_entries)
        raise ReleaseFreezeError(
            "Multiple verified compatibility matrix entries found for profile "
            f"{profile_id}: {versions}"
        )

    matrix_entry = verified_entries[0]
    try:
        resolved_entries = resolve_for_profile(
            registry,
            profile_id,
            profiles_root=profiles_root,
        )
    except RegistryError as exc:
        if "Compatibility matrix does not cover resolved modules" in str(exc):
            raise ReleaseFreezeError(
                "Verified compatibility matrix module_set does not match "
                f"resolved profile modules for {profile_id}"
            ) from exc
        raise ReleaseFreezeError(str(exc)) from exc
    expected = sorted(
        (entry.module_id, entry.module_version) for entry in resolved_entries
    )
    actual = sorted(
        (module.module_id, module.module_version)
        for module in matrix_entry.module_set
    )
    if actual != expected:
        raise ReleaseFreezeError(
            "Verified compatibility matrix module_set does not match resolved "
            f"profile modules for {profile_id}"
        )

    return matrix_entry


def collect_supporting_run_records(
    matrix_entry: CompatibilityMatrixEntry,
    *,
    reports_root: Path,
    profile_id: str,
) -> list[VersionLockRunRef]:
    """Collect successful run records required by a matrix entry."""

    run_types = _required_run_types(matrix_entry.required_tests)
    refs: list[VersionLockRunRef] = []
    missing: list[str] = []
    for run_type in run_types:
        ref = _find_successful_run_record(
            reports_root,
            profile_id=profile_id,
            run_type=run_type,
            matrix_entry=matrix_entry,
        )
        if ref is None:
            missing.append(run_type)
            continue

        refs.append(ref)

    if missing:
        raise ReleaseFreezeError(
            "Missing successful supporting run records for profile "
            f"{profile_id}: {', '.join(missing)}"
        )

    return refs


def freeze(
    registry: Registry,
    matrix_entry: CompatibilityMatrixEntry,
    out_dir: Path,
    *,
    reports_root: Path = Path("reports"),
    now: datetime | None = None,
) -> VersionLock:
    """Write a release lockfile for an already verified matrix entry."""

    if matrix_entry.status != "verified":
        raise ReleaseFreezeError(
            "Only verified compatibility matrix entries can be frozen; "
            f"got {matrix_entry.status}"
        )
    if matrix_entry.verified_at is None:
        raise ReleaseFreezeError(
            "Verified compatibility matrix entry is missing verified_at"
        )

    modules = _version_lock_modules(registry, matrix_entry)
    supporting_runs = collect_supporting_run_records(
        matrix_entry,
        reports_root=reports_root,
        profile_id=matrix_entry.profile_id,
    )
    frozen_at = _utc_datetime(now)
    lock_file = Path(out_dir) / (
        f"{frozen_at.date().isoformat()}-{matrix_entry.profile_id}.yaml"
    )
    lock = VersionLock(
        lock_version="1",
        profile_id=matrix_entry.profile_id,
        matrix_version=matrix_entry.matrix_version,
        contract_version=matrix_entry.contract_version,
        matrix_verified_at=matrix_entry.verified_at,
        frozen_at=frozen_at,
        required_tests=list(matrix_entry.required_tests),
        modules=modules,
        supporting_runs=supporting_runs,
        source_artifacts=_source_artifacts(registry),
        lock_file=lock_file,
    )
    _write_lock(lock, lock_file)
    return lock


def freeze_profile(
    profile_id: str,
    *,
    registry_root: Path = Path("."),
    profiles_root: Path = Path("profiles"),
    reports_root: Path = Path("reports"),
    out_dir: Path = Path("version-lock"),
    now: datetime | None = None,
) -> VersionLock:
    """Load registry artifacts and freeze the verified entry for a profile."""

    try:
        registry = load_all(registry_root)
    except RegistryError as exc:
        raise ReleaseFreezeError(str(exc)) from exc
    matrix_entry = find_verified_matrix_entry(
        registry,
        profile_id,
        profiles_root=profiles_root,
    )
    return freeze(
        registry,
        matrix_entry,
        out_dir,
        reports_root=reports_root,
        now=now,
    )


def _version_lock_modules(
    registry: Registry,
    matrix_entry: CompatibilityMatrixEntry,
) -> list[VersionLockModule]:
    registry_by_id = {entry.module_id: entry for entry in registry.modules}
    modules: list[VersionLockModule] = []
    not_verified: list[str] = []
    missing: list[str] = []

    for module_ref in matrix_entry.module_set:
        entry = registry_by_id.get(module_ref.module_id)
        if entry is None:
            missing.append(module_ref.module_id)
            continue
        if entry.integration_status != IntegrationStatus.verified:
            not_verified.append(entry.module_id)

        modules.append(
            VersionLockModule(
                module_id=entry.module_id,
                module_version=entry.module_version,
                contract_version=entry.contract_version,
                integration_status=entry.integration_status,
            )
        )

    if missing:
        raise ReleaseFreezeError(
            "Compatibility matrix references unregistered modules: "
            + ", ".join(sorted(missing))
        )
    if not_verified:
        raise ReleaseFreezeError(
            "Cannot freeze profile with non-verified registry modules: "
            + ", ".join(sorted(not_verified))
        )

    return modules


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
            raise ReleaseFreezeError(
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
) -> VersionLockRunRef | None:
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
            and record_matches_matrix_context(record, matrix_entry)
        ):
            return VersionLockRunRef(
                run_type=record.run_type,
                run_id=record.run_id,
                status="success",
                path=path,
            )

    return None


def _load_run_record(path: Path) -> IntegrationRunRecord | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "run_record" in payload:
            payload = payload["run_record"]
        return IntegrationRunRecord.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError):
        return None


def _source_artifacts(registry: Registry) -> dict[str, str]:
    root = Path(registry.root)
    return {
        "module_registry_md": str(root / "MODULE_REGISTRY.md"),
        "module_registry_yaml": str(root / "module-registry.yaml"),
        "compatibility_matrix_yaml": str(root / "compatibility-matrix.yaml"),
    }


def _write_lock(lock: VersionLock, lock_file: Path) -> None:
    payload = lock.model_dump(mode="json")
    serialized = yaml.safe_dump(payload, sort_keys=False)
    with _lockfile_write_lock(lock_file):
        _atomic_write_text(lock_file, serialized)


@contextmanager
def _lockfile_write_lock(lock_file: Path) -> Iterator[None]:
    lock_path = lock_file.with_name(f"{lock_file.name}.lock")
    try:
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_handle = lock_path.open("a", encoding="utf-8")
    except OSError as exc:
        raise ReleaseFreezeError(
            f"Could not prepare version lockfile lock {lock_path}: {exc}"
        ) from exc

    with lock_handle:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        except OSError as exc:
            raise ReleaseFreezeError(
                f"Could not lock version lockfile {lock_file}: {exc}"
            ) from exc

        try:
            yield
        finally:
            try:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass


def _atomic_write_text(path: Path, content: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
    except OSError as exc:
        raise ReleaseFreezeError(
            f"Could not prepare atomic write for version lockfile {path}: {exc}"
        ) from exc

    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            fd = -1
            tmp_file.write(content)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())

        os.replace(tmp_path, path)
        _fsync_directory(path.parent)
    except OSError as exc:
        if fd != -1:
            os.close(fd)
        tmp_path.unlink(missing_ok=True)
        raise ReleaseFreezeError(
            f"Could not atomically write version lockfile {path}: {exc}"
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


def _utc_datetime(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)
