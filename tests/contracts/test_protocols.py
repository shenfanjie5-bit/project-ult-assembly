from __future__ import annotations

from pathlib import Path
from typing import get_args

from assembly.contracts import (
    ENTRYPOINT_KIND_TO_PROTOCOL,
    CliEntrypoint,
    HealthProbe,
    HealthResult,
    HealthStatus,
    InitHook,
    SmokeHook,
    SmokeResult,
    VersionDeclaration,
    VersionInfo,
)
from assembly.registry.schema import PublicEntrypoint


class DummyHealthProbe:
    def check(self, *, timeout_sec: float) -> HealthResult:
        return HealthResult(
            module_id="assembly",
            probe_name="dummy",
            status=HealthStatus.healthy,
            latency_ms=0.0,
            message="ready",
        )


class DummySmokeHook:
    def run(self, *, profile_id: str) -> SmokeResult:
        return SmokeResult(
            module_id="assembly",
            hook_name=f"{profile_id}-dummy",
            passed=True,
            duration_ms=0.0,
        )


class DummyInitHook:
    def initialize(self, *, resolved_env: dict[str, str]) -> None:
        return None


class DummyVersionDeclaration:
    def declare(self) -> VersionInfo:
        return VersionInfo(
            module_id="assembly",
            module_version="1.0.0",
            contract_version="v1.0.0",
            compatible_contract_range=">=1.0.0 <2.0.0",
        )


class DummyCliEntrypoint:
    def invoke(self, argv: list[str]) -> int:
        return 0


def public_entrypoint_kind_values() -> set[str]:
    annotation = PublicEntrypoint.model_fields["kind"].annotation
    return set(get_args(annotation))


def test_health_probe_is_runtime_checkable() -> None:
    assert isinstance(DummyHealthProbe(), HealthProbe)


def test_smoke_hook_is_runtime_checkable() -> None:
    assert isinstance(DummySmokeHook(), SmokeHook)


def test_init_hook_is_runtime_checkable() -> None:
    assert isinstance(DummyInitHook(), InitHook)


def test_version_declaration_is_runtime_checkable() -> None:
    assert isinstance(DummyVersionDeclaration(), VersionDeclaration)


def test_cli_entrypoint_is_runtime_checkable() -> None:
    assert isinstance(DummyCliEntrypoint(), CliEntrypoint)


def test_entrypoint_kind_mapping_matches_registry_schema() -> None:
    assert set(ENTRYPOINT_KIND_TO_PROTOCOL) == public_entrypoint_kind_values()


def test_entrypoint_kind_mapping_points_to_protocols() -> None:
    assert ENTRYPOINT_KIND_TO_PROTOCOL == {
        "health_probe": HealthProbe,
        "smoke_hook": SmokeHook,
        "init_hook": InitHook,
        "version_declaration": VersionDeclaration,
        "cli": CliEntrypoint,
    }


def test_contracts_namespace_does_not_import_external_contracts_source() -> None:
    contracts_init = Path("src/assembly/contracts/__init__.py").read_text()

    assert "from contracts" not in contracts_init
    assert "import contracts" not in contracts_init
