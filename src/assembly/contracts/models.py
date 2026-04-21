"""Data models for module public entrypoint contracts."""

from __future__ import annotations

import re
import warnings
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from assembly.contracts.primitives import ContractVersion, ModuleId, Semver


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
    """Module version and compatible contract version declaration.

    The four core fields — ``module_id`` / ``module_version`` /
    ``contract_version`` / ``compatible_contract_range`` — are the baseline
    contract. The remaining fields are **typed optional structural
    markers** that specific modules publish to declare semantic invariants
    (see master plan §4.1.5). They are intentionally modeled here (not
    stored in an opaque ``metadata`` dict and not ignored via
    ``extra="allow"``) so the assembly contract stays strict:
    ``extra="forbid"`` still rejects unknown fields, but marker fields
    declared below are first-class introspectable attributes.

    Marker field usage (as of Stage 4 §4.1.5):

    * ``supported_ex_types`` — set by ``subsystem-sdk``, ``subsystem-
      announcement``, ``subsystem-news`` (Ex-1/2/3 producer surface; SDK
      adds Ex-0 heartbeat).
    * ``consumed_ex_types`` — set by ``graph-engine`` (Ex-3 consumer
      surface; semantic distinction from producer modules).
    * ``backend_kinds`` — set by ``subsystem-sdk`` (Lite/Full/mock backend
      kinds supported by the SDK dispatch layer).
    * ``sdk_envelope_fields`` — set by ``subsystem-announcement`` /
      ``subsystem-news`` (declares which envelope keys the module strips
      before dispatch — iron rule #7 wire-shape boundary documentation).
    * ``ex0_semantic`` — set by ``subsystem-sdk`` (Ex-0 heartbeat semantic
      marker).
    * ``ex3_high_threshold_marker`` — set by ``subsystem-announcement`` /
      ``subsystem-news`` (CLAUDE.md §10 Ex-3 high-threshold guard marker).
    * ``neo4j_status_enum_values`` — set by ``graph-engine`` (3-state
      ``Neo4jGraphStatus.graph_status`` Literal values).
    * ``canonical_truth_layer`` — set by ``graph-engine`` (CLAUDE.md §10
      #1 truth-before-mirror invariant marker — must equal ``"iceberg"``).

    Modules that do not publish a given marker leave the corresponding
    field at ``None``. Each marker is optional to avoid forcing unrelated
    modules to populate fields they have no semantic stake in.
    """

    model_config = ConfigDict(extra="forbid")

    module_id: ModuleId
    module_version: Semver
    contract_version: ContractVersion
    compatible_contract_range: str

    supported_ex_types: list[str] | None = None
    consumed_ex_types: list[str] | None = None
    backend_kinds: list[str] | None = None
    sdk_envelope_fields: list[str] | None = None
    ex0_semantic: str | None = None
    ex3_high_threshold_marker: bool | None = None
    neo4j_status_enum_values: list[str] | None = None
    canonical_truth_layer: str | None = None

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
