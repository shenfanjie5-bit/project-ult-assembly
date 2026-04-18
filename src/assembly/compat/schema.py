"""Pydantic schemas for contract compatibility reports."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from assembly.contracts.models import IntegrationRunRecord
from assembly.profiles.resolver import ResolvedConfigSnapshot
from assembly.registry.loader import Registry
from assembly.registry.schema import CompatibilityMatrixEntry, ModuleRegistryEntry


class CompatibilityCheckStatus(str, Enum):
    """Outcome for a single contract compatibility check."""

    success = "success"
    failed = "failed"
    not_started = "not_started"
    skipped = "skipped"


class CompatibilityCheckResult(BaseModel):
    """Single module-level compatibility check result."""

    model_config = ConfigDict(extra="forbid")

    check_name: str
    module_id: str
    status: CompatibilityCheckStatus
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class CompatibilityCheckContext(BaseModel):
    """Shared context passed to compatibility checks."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str
    snapshot: ResolvedConfigSnapshot
    registry: Registry
    resolved_entries: list[ModuleRegistryEntry]
    matrix_entry: CompatibilityMatrixEntry
    timeout_sec: float = Field(default=30.0, ge=0)


class CompatibilityReport(BaseModel):
    """Persisted contract compatibility suite report."""

    model_config = ConfigDict(extra="forbid")

    run_record: IntegrationRunRecord
    checks: list[CompatibilityCheckResult]
    matrix_version: str | None
    promoted: bool
    report_path: Path
