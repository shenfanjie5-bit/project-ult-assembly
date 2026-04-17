"""Assembly public entrypoint contract namespace."""

from __future__ import annotations

from assembly.contracts.models import (
    HealthResult,
    HealthStatus,
    SmokeResult,
    VersionInfo,
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
    "ENTRYPOINT_KIND_TO_PROTOCOL",
    "HealthProbe",
    "HealthResult",
    "HealthStatus",
    "InitHook",
    "SmokeHook",
    "SmokeResult",
    "VersionDeclaration",
    "VersionInfo",
]
