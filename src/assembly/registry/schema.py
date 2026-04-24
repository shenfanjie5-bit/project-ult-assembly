"""Pydantic schemas for the assembly module registry."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from assembly.contracts.primitives import (
    ContractVersion,
    EntrypointKind,
    ModuleId,
    ProfileId,
    Semver,
)


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
    kind: EntrypointKind
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
    """Compatibility matrix row for a profile and module set.

    ``extra_bundles`` (Stage 5 + MinIO pilot): the list of full-dev
    optional service bundles opted-in for THIS verified combination.
    Empty / absent = default profile (no extras). The unique evidence
    key for matrix rows is ``(profile_id, sorted(extra_bundles))`` —
    Stage 5 promoted ``(full-dev, [])``; MinIO pilot adds
    ``(full-dev, [minio])``; future optional-bundle pilots add their
    own rows. ``contract_version`` + ``module_set`` typically don't
    differ by extra_bundles (bundles are infra slots, not contract
    surface), but the schema doesn't forbid that.
    """

    model_config = ConfigDict(extra="forbid")

    matrix_version: Semver
    profile_id: ProfileId
    extra_bundles: list[str] = []
    module_set: list[CompatibilityModuleRef]
    contract_version: ContractVersion
    required_tests: list[str]
    status: Literal["draft", "verified", "deprecated"]
    verified_at: datetime | None

    @model_validator(mode="after")
    def enforce_status_fields(self) -> CompatibilityMatrixEntry:
        if self.status == "verified" and self.verified_at is None:
            raise ValueError("verified compatibility entries require verified_at")

        return self
