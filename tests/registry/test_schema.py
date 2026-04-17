from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from assembly.registry import (
    CompatibilityMatrix,
    CompatibilityMatrixEntry,
    IntegrationStatus,
    ModuleRegistryEntry,
    PublicEntrypoint,
)


def valid_registry_entry(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "module_id": "graph-engine",
        "module_version": "0.0.0",
        "contract_version": "v0.0.0",
        "owner": "unassigned",
        "upstream_modules": [],
        "downstream_modules": [],
        "public_entrypoints": [],
        "depends_on": [],
        "supported_profiles": ["lite-local"],
        "integration_status": "not_started",
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
                "module_id": "graph-engine",
                "module_version": "0.0.0",
            }
        ],
        "contract_version": "v0.0.0",
        "required_tests": [],
        "status": "draft",
        "verified_at": None,
    }
    data.update(overrides)
    return data


def test_integration_status_values_are_exact() -> None:
    assert {status.value for status in IntegrationStatus} == {
        "not_started",
        "partial",
        "ready",
        "verified",
        "blocked",
    }


def test_valid_public_entrypoint_validates() -> None:
    entrypoint = PublicEntrypoint.model_validate(
        {
            "name": "health",
            "kind": "health_probe",
            "reference": "assembly.health.public:probe",
        }
    )

    assert entrypoint.reference == "assembly.health.public:probe"


def test_public_entrypoint_kind_is_limited() -> None:
    with pytest.raises(ValidationError):
        PublicEntrypoint.model_validate(
            {
                "name": "private",
                "kind": "private_hook",
                "reference": "assembly.health.public:probe",
            }
        )


def test_public_entrypoint_rejects_empty_path_segments() -> None:
    with pytest.raises(ValidationError):
        PublicEntrypoint.model_validate(
            {
                "name": "health",
                "kind": "health_probe",
                "reference": "assembly..health:probe",
            }
        )


def test_public_entrypoint_rejects_trailing_dotted_path() -> None:
    with pytest.raises(ValidationError):
        PublicEntrypoint.model_validate(
            {
                "name": "health",
                "kind": "health_probe",
                "reference": "assembly.health.:probe",
            }
        )


def test_valid_module_registry_entry_validates() -> None:
    entry = ModuleRegistryEntry.model_validate(valid_registry_entry())

    assert entry.module_id == "graph-engine"
    assert entry.integration_status == IntegrationStatus.not_started


@pytest.mark.parametrize("module_id", ["M01", "N02", "P03", "m04"])
def test_module_id_rejects_shorthand_aliases(module_id: str) -> None:
    with pytest.raises(ValidationError):
        ModuleRegistryEntry.model_validate(valid_registry_entry(module_id=module_id))


def test_module_id_rejects_non_kebab_case() -> None:
    with pytest.raises(ValidationError):
        ModuleRegistryEntry.model_validate(
            valid_registry_entry(module_id="graph_engine")
        )


def test_missing_required_registry_field_fails_validation() -> None:
    data = valid_registry_entry()
    data.pop("contract_version")

    with pytest.raises(ValidationError):
        ModuleRegistryEntry.model_validate(data)


def test_verified_matrix_entry_requires_verified_at() -> None:
    with pytest.raises(ValidationError, match="verified_at"):
        CompatibilityMatrixEntry.model_validate(
            valid_matrix_entry(status="verified", verified_at=None)
        )


@pytest.mark.parametrize("status", ["verified", "deprecated"])
def test_phase_zero_matrix_rejects_non_draft_status(status: str) -> None:
    with pytest.raises(ValidationError, match="Phase 0"):
        CompatibilityMatrixEntry.model_validate(
            valid_matrix_entry(
                status=status,
                verified_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
        )


def test_compatibility_matrix_root_validates_entries() -> None:
    matrix = CompatibilityMatrix.model_validate([valid_matrix_entry()])

    assert matrix.root[0].profile_id == "lite-local"
