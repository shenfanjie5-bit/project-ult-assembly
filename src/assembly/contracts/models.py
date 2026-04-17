"""Data models for module public entrypoint contracts."""

from __future__ import annotations

import re
import warnings
from enum import Enum
from typing import Any

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
    latency_ms: float
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
    duration_ms: float
    failure_reason: str | None = None


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
