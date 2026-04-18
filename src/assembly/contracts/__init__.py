"""Assembly public entrypoint contract namespace."""

from __future__ import annotations

from assembly.contracts.models import (
    HealthResult,
    HealthStatus,
    IntegrationRunRecord,
    SmokeResult,
    VersionInfo,
)
from assembly.contracts.primitives import (
    ContractVersion,
    EntrypointKind,
    ModuleId,
    ProfileId,
    Semver,
)
from assembly.contracts.protocols import (
    CliEntrypoint,
    HealthProbe,
    InitHook,
    SmokeHook,
    VersionDeclaration,
)

ENTRYPOINT_KIND_TO_PROTOCOL: dict[str, type] = {
    "health_probe": HealthProbe,
    "smoke_hook": SmokeHook,
    "init_hook": InitHook,
    "version_declaration": VersionDeclaration,
    "cli": CliEntrypoint,
}

__all__ = [
    "CliEntrypoint",
    "ContractVersion",
    "ENTRYPOINT_KIND_TO_PROTOCOL",
    "EntrypointKind",
    "HealthProbe",
    "HealthResult",
    "HealthStatus",
    "IntegrationRunRecord",
    "InitHook",
    "ModuleId",
    "ProfileId",
    "SmokeHook",
    "SmokeResult",
    "Semver",
    "VersionDeclaration",
    "VersionInfo",
]
