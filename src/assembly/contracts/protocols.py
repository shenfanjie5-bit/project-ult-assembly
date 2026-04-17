"""Runtime-checkable Protocols for module public entrypoints."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from assembly.contracts.models import HealthResult, SmokeResult, VersionInfo


@runtime_checkable
class HealthProbe(Protocol):
    """Public health probe exposed by an integrated module."""

    def check(self, *, timeout_sec: float) -> HealthResult:
        """Return the current module health state within the requested timeout."""
        ...


@runtime_checkable
class SmokeHook(Protocol):
    """Public smoke hook exposed by an integrated module."""

    def run(self, *, profile_id: str) -> SmokeResult:
        """Run a fast module-level smoke check for a profile."""
        ...


@runtime_checkable
class InitHook(Protocol):
    """Public initialization hook exposed by an integrated module."""

    def initialize(self, *, resolved_env: dict[str, str]) -> None:
        """Initialize module resources from the resolved environment."""
        ...


@runtime_checkable
class VersionDeclaration(Protocol):
    """Public version declaration exposed by an integrated module."""

    def declare(self) -> VersionInfo:
        """Return the module and contract version declaration."""
        ...


@runtime_checkable
class CliEntrypoint(Protocol):
    """Public CLI entrypoint exposed by an integrated module."""

    def invoke(self, argv: list[str]) -> int:
        """Invoke the module CLI with an argv vector."""
        ...
