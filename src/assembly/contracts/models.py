"""Data models for module public entrypoint contracts."""

from __future__ import annotations

import re
import warnings
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_SEMVER_PATTERN = (
    r"v?(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)
_RANGE_TERM_RE = re.compile(
    rf"\s*,?\s*(?:(?:<=|>=|<|>|==|=|\^|~|~>)\s*)?{_SEMVER_PATTERN}\s*"
)


class HealthStatus(str, Enum):
    """Health states emitted by module health probes."""

    healthy = "healthy"
    degraded = "degraded"
    blocked = "blocked"


class HealthResult(BaseModel):
    """Result returned by a module health probe."""

    model_config = ConfigDict(extra="forbid")

    module_id: str
    probe_name: str
    status: HealthStatus
    latency_ms: float = Field(ge=0, allow_inf_nan=False)
    message: str
    details: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def warn_degraded_without_message(self) -> HealthResult:
        if self.status == HealthStatus.degraded and not self.message.strip():
            warnings.warn(
                "degraded HealthResult should include a non-empty message",
                UserWarning,
                stacklevel=2,
            )

        return self


class SmokeResult(BaseModel):
    """Result returned by a module smoke hook."""

    model_config = ConfigDict(extra="forbid")

    module_id: str
    hook_name: str
    passed: bool
    duration_ms: float = Field(ge=0, allow_inf_nan=False)
    failure_reason: str | None = None

    @model_validator(mode="after")
    def require_failure_reason_for_failures(self) -> SmokeResult:
        if not self.passed and not (self.failure_reason or "").strip():
            raise ValueError("failed SmokeResult requires a non-empty failure_reason")

        return self


class IntegrationRunRecord(BaseModel):
    """Persisted record for smoke, contract, and e2e integration runs."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    profile_id: str
    run_type: Literal["smoke", "contract", "e2e"]
    started_at: datetime
    finished_at: datetime
    status: Literal["success", "failed", "partial"]
    artifacts: list[dict[str, str]]
    failing_modules: list[str]
    summary: str


class VersionInfo(BaseModel):
    """Module version and compatible contract version declaration."""

    model_config = ConfigDict(extra="forbid")

    module_id: str
    module_version: str
    contract_version: str
    compatible_contract_range: str

    @field_validator("compatible_contract_range")
    @classmethod
    def validate_compatible_contract_range(cls, value: str) -> str:
        if not _is_semver_range(value):
            raise ValueError("compatible_contract_range must be a SemVer range")

        return value


def _is_semver_range(value: str) -> bool:
    if not value.strip():
        return False

    for alternative in value.split("||"):
        if not alternative.strip():
            return False

        position = 0
        matched_term = False
        while position < len(alternative):
            match = _RANGE_TERM_RE.match(alternative, position)
            if match is None or match.end() == position:
                return False

            matched_term = True
            position = match.end()

        if not matched_term:
            return False

    return True
