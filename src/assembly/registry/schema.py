"""Pydantic schemas for the assembly module registry."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    field_validator,
    model_validator,
)


MODULE_ID_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"
PROFILE_ID_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"
ENTRYPOINT_REFERENCE_PATTERN = (
    r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*$"
)

ModuleId = Annotated[str, Field(pattern=MODULE_ID_PATTERN)]
ProfileId = Annotated[str, Field(pattern=PROFILE_ID_PATTERN)]
VersionString = Annotated[str, Field(min_length=1)]
ContractVersion = Annotated[str, Field(pattern=r"^v\d+\.\d+\.\d+$")]


class IntegrationStatus(str, Enum):
    """Supported module integration states."""

    not_started = "not_started"
    partial = "partial"
    ready = "ready"
    verified = "verified"
    blocked = "blocked"


class PublicEntrypoint(BaseModel):
    """Public integration entrypoint exposed by a registered module."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    kind: Literal[
        "health_probe",
        "init_hook",
        "smoke_hook",
        "version_declaration",
        "cli",
    ]
    reference: str = Field(pattern=ENTRYPOINT_REFERENCE_PATTERN)


class ModuleRegistryEntry(BaseModel):
    """Schema for one module row in the assembly registry."""

    model_config = ConfigDict(extra="forbid")

    module_id: ModuleId
    module_version: VersionString
    contract_version: ContractVersion
    owner: str = Field(min_length=1)
    upstream_modules: list[ModuleId]
    downstream_modules: list[ModuleId]
    public_entrypoints: list[PublicEntrypoint]
    depends_on: list[ModuleId]
    supported_profiles: list[ProfileId]
    integration_status: IntegrationStatus
    last_smoke_result: str | None
    notes: str

    @field_validator("module_id")
    @classmethod
    def reject_module_aliases(cls, value: str) -> str:
        if len(value) >= 2 and value[0].upper() in {"M", "N", "P"}:
            if value[1:].isdigit():
                raise ValueError("module_id must use kebab-case, not M##/N##/P## alias")

        return value


class CompatibilityModuleVersion(BaseModel):
    """Module version entry inside a compatibility matrix row."""

    model_config = ConfigDict(extra="forbid")

    module_id: ModuleId
    module_version: VersionString


class CompatibilityMatrixEntry(BaseModel):
    """Schema for one compatibility matrix declaration."""

    model_config = ConfigDict(extra="forbid")

    matrix_version: VersionString
    profile_id: ProfileId
    module_set: list[CompatibilityModuleVersion]
    contract_version: ContractVersion
    required_tests: list[str]
    status: Literal["draft", "verified", "deprecated"]
    verified_at: datetime | None

    @model_validator(mode="after")
    def enforce_verified_metadata_and_phase_zero_status(
        self,
    ) -> CompatibilityMatrixEntry:
        if self.status == "verified" and self.verified_at is None:
            raise ValueError("verified compatibility entries require verified_at")

        if self.status != "draft":
            raise ValueError("Phase 0 compatibility matrix entries must remain draft")

        return self


class CompatibilityMatrix(RootModel[list[CompatibilityMatrixEntry]]):
    """Root schema for the phase 0 compatibility matrix artifact."""
