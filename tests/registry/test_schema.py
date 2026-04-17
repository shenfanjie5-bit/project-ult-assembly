from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from assembly.registry import (
    CompatibilityMatrixEntry,
    IntegrationStatus,
    ModuleRegistryEntry,
    PublicEntrypoint,
)


def valid_registry_entry(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "module_id": "assembly",
        "module_version": "0.1.0",
        "contract_version": "v0.0.0",
        "owner": "assembly",
        "upstream_modules": [],
        "downstream_modules": [],
        "public_entrypoints": [],
        "depends_on": [],
        "supported_profiles": ["lite-local"],
        "integration_status": "partial",
        "last_smoke_result": None,
        "notes": "schema test entry",
    }
    data.update(overrides)
    return data


def valid_matrix_entry(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "matrix_version": "0.1.0",
        "profile_id": "lite-local",
        "module_set": [
            {
                "module_id": "assembly",
                "module_version": "0.1.0",
            }
        ],
        "contract_version": "v0.0.0",
        "required_tests": ["contract-suite"],
        "status": "draft",
        "verified_at": None,
    }
    data.update(overrides)
    return data


def test_integration_status_values_are_frozen() -> None:
    assert {status.value for status in IntegrationStatus} == {
        "not_started",
        "partial",
        "ready",
        "verified",
        "blocked",
    }


def test_public_entrypoint_accepts_registered_kind_and_reference() -> None:
    entrypoint = PublicEntrypoint.model_validate(
        {
            "name": "health",
            "kind": "health_probe",
            "reference": "assembly.health:probe",
        }
    )

    assert entrypoint.kind == "health_probe"


def test_public_entrypoint_rejects_unknown_kind() -> None:
    with pytest.raises(ValidationError):
        PublicEntrypoint.model_validate(
            {
                "name": "private",
                "kind": "private_hook",
                "reference": "assembly.private:probe",
            }
        )


def test_module_registry_entry_accepts_required_fields() -> None:
    entry = ModuleRegistryEntry.model_validate(valid_registry_entry())

    assert entry.module_id == "assembly"
    assert entry.integration_status == IntegrationStatus.partial


@pytest.mark.parametrize("module_id", ["M01", "N02", "P03"])
def test_module_id_rejects_alias_forms(module_id: str) -> None:
    with pytest.raises(ValidationError):
        ModuleRegistryEntry.model_validate(valid_registry_entry(module_id=module_id))


def test_module_id_rejects_underscore() -> None:
    with pytest.raises(ValidationError):
        ModuleRegistryEntry.model_validate(
            valid_registry_entry(module_id="entity_registry")
        )


def test_module_version_requires_semver() -> None:
    with pytest.raises(ValidationError):
        ModuleRegistryEntry.model_validate(
            valid_registry_entry(module_version="0.1")
        )


def test_contract_version_requires_v_prefixed_semver() -> None:
    with pytest.raises(ValidationError):
        ModuleRegistryEntry.model_validate(
            valid_registry_entry(contract_version="0.0.0")
        )


def test_compatibility_matrix_accepts_draft_entry() -> None:
    entry = CompatibilityMatrixEntry.model_validate(valid_matrix_entry())

    assert entry.status == "draft"
    assert entry.verified_at is None


def test_verified_matrix_entry_requires_verified_at() -> None:
    with pytest.raises(ValidationError, match="verified_at"):
        CompatibilityMatrixEntry.model_validate(
            valid_matrix_entry(status="verified", verified_at=None)
        )


def test_phase_zero_rejects_verified_matrix_entry_even_with_timestamp() -> None:
    with pytest.raises(ValidationError, match="Phase 0"):
        CompatibilityMatrixEntry.model_validate(
            valid_matrix_entry(
                status="verified",
                verified_at=datetime(2026, 4, 18, tzinfo=timezone.utc),
            )
        )
