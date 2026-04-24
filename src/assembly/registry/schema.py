"""Pydantic schemas for the assembly module registry."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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

    @field_validator("extra_bundles", mode="before")
    @classmethod
    def _normalize_extra_bundles(cls, value: object) -> list[str]:
        """Normalize ``extra_bundles`` into a sorted, deduplicated list.

        Codex P2 follow-up on the MinIO pilot: matrix row identity is
        ``(profile_id, tuple(extra_bundles))`` across selectors, digests,
        and the release freezer. To keep that tuple a canonical key we
        normalize the input at schema level:

        * ``None`` is treated as empty (same as the field default).
        * Entries must be strings.
        * Leading / trailing whitespace is stripped.
        * Empty strings are rejected — they create silent key collisions.
        * Duplicates (post-strip) are rejected — same reason. If the
          caller wants to express "default", they should pass ``[]``.
        * The returned list is sorted, so two YAML authors who list
          ``[minio, grafana]`` vs ``[grafana, minio]`` produce the same
          matrix row identity and the same
          ``compatibility_context_artifact`` digest.
        """
        if value is None:
            return []
        if not isinstance(value, (list, tuple)):
            raise ValueError(
                f"extra_bundles must be a list, got {type(value).__name__}"
            )

        normalized: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError(
                    f"extra_bundles entries must be strings, got "
                    f"{type(item).__name__}: {item!r}"
                )
            stripped = item.strip()
            if not stripped:
                raise ValueError(
                    "extra_bundles entries must be non-empty strings"
                )
            normalized.append(stripped)

        if len(set(normalized)) != len(normalized):
            duplicates = sorted({x for x in normalized if normalized.count(x) > 1})
            raise ValueError(
                f"extra_bundles must not contain duplicates; got {duplicates}"
            )

        return sorted(normalized)

    @model_validator(mode="after")
    def enforce_status_fields(self) -> CompatibilityMatrixEntry:
        if self.status == "verified" and self.verified_at is None:
            raise ValueError("verified compatibility entries require verified_at")

        return self


def matrix_entry_key(
    entry: CompatibilityMatrixEntry,
) -> tuple[str, tuple[str, ...]]:
    """Canonical matrix-row identity: ``(profile_id, sorted(extra_bundles))``.

    Use this wherever you need to deduplicate / look up / key by matrix
    row. The field validator on ``extra_bundles`` already sorts on load
    so ``tuple(entry.extra_bundles)`` is stable across YAML authors.

    Codex P2 follow-up (MinIO pilot): before this helper, selectors
    across e2e / smoke / compat / release-freezer keyed only on
    ``profile_id`` and silently collided when two verified rows shared
    a profile with different opt-in bundles (default full-dev vs
    full-dev + minio). Every selector now imports this function so
    there is one source of truth for row identity.
    """
    return (entry.profile_id, tuple(entry.extra_bundles))
