from __future__ import annotations

import sys
import types
from datetime import datetime, timezone
from pathlib import Path

import pytest

from assembly.compat import (
    CompatRunner,
    CompatibilityCheckStatus,
    CompatibilityReport,
    run_contract_suite,
)
from assembly.compat.checks.base import load_public_entrypoint
from assembly.compat.checks.contracts_version import ContractsVersionCheck
from assembly.compat.checks.orchestrator_loadability import (
    OrchestratorLoadabilityCheck,
)
from assembly.compat.checks.public_api_boundary import PublicApiBoundaryCheck
from assembly.compat.checks.sdk_boundary import SdkBoundaryCheck
from assembly.compat.schema import CompatibilityCheckContext
from assembly.contracts import (
    HealthResult,
    HealthStatus,
    SmokeResult,
    VersionInfo,
)
from assembly.profiles.resolver import ResolvedConfigSnapshot
from assembly.registry import CompatibilityMatrixEntry, ModuleRegistryEntry, Registry
from assembly.registry.schema import PublicEntrypoint


def test_public_compat_api_exports_runner_and_report() -> None:
    assert CompatRunner is not None
    assert CompatibilityReport is not None
    assert callable(run_contract_suite)


def test_contracts_version_check_detects_version_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "compat_fake_version_mismatch"
    _install_fake_public_module(
        monkeypatch,
        module_name,
        version=FakeVersionDeclaration(
            module_id="app",
            module_version="9.9.9",
            contract_version="v0.0.0",
        ),
    )
    entry = _module(
        "app",
        public_entrypoints=[
            _entrypoint("version", "version_declaration", f"{module_name}:version")
        ],
    )

    results = ContractsVersionCheck().run(_context([entry]))

    assert len(results) == 1
    assert results[0].status == CompatibilityCheckStatus.failed
    assert "module_version" in results[0].details["mismatches"]


def test_contracts_version_check_reports_not_started_without_importing() -> None:
    entry = _module(
        "app",
        integration_status="not_started",
        public_entrypoints=[
            _entrypoint("version", "version_declaration", "missing.module:version")
        ],
    )

    results = ContractsVersionCheck().run(_context([entry]))

    assert results[0].status == CompatibilityCheckStatus.not_started
    assert "missing.module" not in sys.modules


def test_sdk_boundary_reports_not_started_as_non_success() -> None:
    entry = _module(
        "subsystem-sdk",
        integration_status="not_started",
        public_entrypoints=[
            _entrypoint(
                "version",
                "version_declaration",
                "subsystem_sdk.public:version_declaration",
            )
        ],
    )

    results = SdkBoundaryCheck().run(_context([entry]))

    assert results[0].module_id == "subsystem-sdk"
    assert results[0].status == CompatibilityCheckStatus.not_started


def test_orchestrator_loadability_imports_without_invoking_cli(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "compat_fake_orchestrator"
    fake_cli = FakeCliEntrypoint()
    _install_fake_public_module(
        monkeypatch,
        module_name,
        version=FakeVersionDeclaration(module_id="orchestrator"),
        cli=fake_cli,
    )
    entry = _module(
        "orchestrator",
        public_entrypoints=[
            _entrypoint("version", "version_declaration", f"{module_name}:version"),
            _entrypoint("cli", "cli", f"{module_name}:cli"),
        ],
    )

    results = OrchestratorLoadabilityCheck().run(_context([entry]))

    assert results[0].status == CompatibilityCheckStatus.success
    assert fake_cli.invoked is False


def test_public_api_boundary_uses_registered_protocol_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "compat_fake_public_api"
    _install_fake_public_module(
        monkeypatch,
        module_name,
        version=FakeVersionDeclaration(module_id="app"),
        cli=FakeCliEntrypoint(),
        health=FakeHealthProbe(),
        smoke=FakeSmokeHook(),
        init=FakeInitHook(),
    )
    entry = _module(
        "app",
        public_entrypoints=[
            _entrypoint("health", "health_probe", f"{module_name}:health"),
            _entrypoint("smoke", "smoke_hook", f"{module_name}:smoke"),
            _entrypoint("init", "init_hook", f"{module_name}:init"),
            _entrypoint("version", "version_declaration", f"{module_name}:version"),
            _entrypoint("cli", "cli", f"{module_name}:cli"),
        ],
    )

    results = PublicApiBoundaryCheck().run(_context([entry]))

    assert results[0].status == CompatibilityCheckStatus.success
    assert set(results[0].details["references"]) == {
        "health_probe",
        "smoke_hook",
        "init_hook",
        "version_declaration",
        "cli",
    }


def test_base_loader_rejects_init_hook_by_default() -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        load_public_entrypoint(
            _entrypoint("init", "init_hook", "compat_fake_public_api:init")
        )


def test_compat_package_does_not_import_external_contracts_source() -> None:
    compat_root = Path("src/assembly/compat")
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in compat_root.rglob("*.py")
    )

    assert "from contracts" not in source
    assert "import contracts" not in source


class FakeVersionDeclaration:
    def __init__(
        self,
        *,
        module_id: str,
        module_version: str = "0.1.0",
        contract_version: str = "v0.0.0",
    ) -> None:
        self._module_id = module_id
        self._module_version = module_version
        self._contract_version = contract_version

    def declare(self) -> VersionInfo:
        return VersionInfo(
            module_id=self._module_id,
            module_version=self._module_version,
            contract_version=self._contract_version,
            compatible_contract_range=">=0.0.0 <1.0.0",
        )


class FakeCliEntrypoint:
    def __init__(self) -> None:
        self.invoked = False

    def invoke(self, argv: list[str]) -> int:
        self.invoked = True
        return 0


class FakeHealthProbe:
    def check(self, *, timeout_sec: float) -> HealthResult:
        return HealthResult(
            module_id="app",
            probe_name="health",
            status=HealthStatus.healthy,
            latency_ms=0.0,
            message="ok",
        )


class FakeSmokeHook:
    def run(self, *, profile_id: str) -> SmokeResult:
        return SmokeResult(
            module_id="app",
            hook_name="smoke",
            passed=True,
            duration_ms=0.0,
        )


class FakeInitHook:
    def initialize(self, *, resolved_env: dict[str, str]) -> None:
        return None


def _install_fake_public_module(
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
    *,
    version: object,
    cli: object | None = None,
    health: object | None = None,
    smoke: object | None = None,
    init: object | None = None,
) -> None:
    module = types.ModuleType(module_name)
    module.version = version
    if cli is not None:
        module.cli = cli
    if health is not None:
        module.health = health
    if smoke is not None:
        module.smoke = smoke
    if init is not None:
        module.init = init
    monkeypatch.setitem(sys.modules, module_name, module)


def _context(entries: list[ModuleRegistryEntry]) -> CompatibilityCheckContext:
    return CompatibilityCheckContext(
        profile_id="lite-local",
        snapshot=ResolvedConfigSnapshot(
            profile_id="lite-local",
            mode="lite",
            enabled_modules=[entry.module_id for entry in entries],
            enabled_service_bundles=[],
            required_env={},
            optional_env={},
            storage_backends={},
            resource_expectation={},
            max_long_running_daemons=4,
            service_bundles=[],
            resolved_at=datetime.now(timezone.utc),
        ),
        registry=Registry(
            root=Path("."),
            modules=entries,
            compatibility_matrix=[_matrix(entries)],
        ),
        resolved_entries=entries,
        matrix_entry=_matrix(entries),
        timeout_sec=1.0,
    )


def _module(
    module_id: str,
    *,
    module_version: str = "0.1.0",
    integration_status: str = "partial",
    public_entrypoints: list[PublicEntrypoint] | None = None,
) -> ModuleRegistryEntry:
    return ModuleRegistryEntry.model_validate(
        {
            "module_id": module_id,
            "module_version": module_version,
            "contract_version": "v0.0.0",
            "owner": "test",
            "upstream_modules": [],
            "downstream_modules": [],
            "public_entrypoints": public_entrypoints or [],
            "depends_on": [],
            "supported_profiles": ["lite-local"],
            "integration_status": integration_status,
            "last_smoke_result": None,
            "notes": "test",
        }
    )


def _entrypoint(name: str, kind: str, reference: str) -> PublicEntrypoint:
    return PublicEntrypoint.model_validate(
        {"name": name, "kind": kind, "reference": reference}
    )


def _matrix(entries: list[ModuleRegistryEntry]) -> CompatibilityMatrixEntry:
    return CompatibilityMatrixEntry.model_validate(
        {
            "matrix_version": "0.1.0",
            "profile_id": "lite-local",
            "module_set": [
                {"module_id": entry.module_id, "module_version": entry.module_version}
                for entry in entries
            ],
            "contract_version": "v0.0.0",
            "required_tests": ["contract-suite"],
            "status": "draft",
            "verified_at": None,
        }
    )
