"""Pydantic schemas for the assembly module registry."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PROFILE_ID_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"
MODULE_ID_PATTERN = PROFILE_ID_PATTERN
SEMVER_PATTERN = r"^\d+\.\d+\.\d+$"
CONTRACT_VERSION_PATTERN = r"^v\d+\.\d+\.\d+$"

ProfileId = Annotated[str, Field(pattern=PROFILE_ID_PATTERN)]
ModuleId = Annotated[str, Field(pattern=MODULE_ID_PATTERN)]
Semver = Annotated[str, Field(pattern=SEMVER_PATTERN)]
ContractVersion = Annotated[str, Field(pattern=CONTRACT_VERSION_PATTERN)]


class IntegrationStatus(str, Enum):
    """Allowed registry integration states."""

    not_started = "not_started"
    partial = "partial"
    ready = "ready"
    verified = "verified"
    blocked = "blocked"


class PublicEntrypoint(BaseModel):
    """Public entrypoint registered for a module."""

    model_config = ConfigDict(extra="forbid")

    name: str
    kind: Literal[
        "health_probe",
        "smoke_hook",
        "init_hook",
        "version_declaration",
        "cli",
    ]
    reference: str = Field(pattern=r"^[A-Za-z_][\w.]*:[A-Za-z_]\w*$")


class ModuleRegistryEntry(BaseModel):
    """Single module entry in the assembly registry."""

    model_config = ConfigDict(extra="forbid")

    module_id: ModuleId
    module_version: Semver
    contract_version: ContractVersion
    owner: str
    upstream_modules: list[ModuleId]
    downstream_modules: list[ModuleId]
    public_entrypoints: list[PublicEntrypoint]
    depends_on: list[ModuleId]
    supported_profiles: list[ProfileId]
    integration_status: IntegrationStatus
    last_smoke_result: str | None
    notes: str


class CompatibilityModuleRef(BaseModel):
    """Module/version pair declared in a compatibility matrix entry."""

    model_config = ConfigDict(extra="forbid")

    module_id: ModuleId
    module_version: Semver


class CompatibilityMatrixEntry(BaseModel):
    """Compatibility matrix row for a profile and module set."""

    model_config = ConfigDict(extra="forbid")

    matrix_version: Semver
    profile_id: ProfileId
    module_set: list[CompatibilityModuleRef]
    contract_version: ContractVersion
    required_tests: list[str]
    status: Literal["draft", "verified", "deprecated"]
    verified_at: datetime | None

    @model_validator(mode="after")
    def enforce_phase_zero_status(self) -> CompatibilityMatrixEntry:
        if self.status == "verified" and self.verified_at is None:
            raise ValueError("verified compatibility entries require verified_at")

        if self.status != "draft":
            raise ValueError("Phase 0 compatibility matrix entries must be draft")

        return self
