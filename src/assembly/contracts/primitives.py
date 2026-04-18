"""Shared schema primitives for assembly contracts and artifacts."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

PROFILE_ID_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"
MODULE_ID_PATTERN = PROFILE_ID_PATTERN
SEMVER_PATTERN = r"^\d+\.\d+\.\d+$"
CONTRACT_VERSION_PATTERN = r"^v\d+\.\d+\.\d+$"

ProfileId = Annotated[str, Field(pattern=PROFILE_ID_PATTERN)]
ModuleId = Annotated[str, Field(pattern=MODULE_ID_PATTERN)]
Semver = Annotated[str, Field(pattern=SEMVER_PATTERN)]
ContractVersion = Annotated[str, Field(pattern=CONTRACT_VERSION_PATTERN)]
EntrypointKind = Literal[
    "health_probe",
    "smoke_hook",
    "init_hook",
    "version_declaration",
    "cli",
]

__all__ = [
    "CONTRACT_VERSION_PATTERN",
    "ContractVersion",
    "EntrypointKind",
    "MODULE_ID_PATTERN",
    "ModuleId",
    "PROFILE_ID_PATTERN",
    "ProfileId",
    "SEMVER_PATTERN",
    "Semver",
]
