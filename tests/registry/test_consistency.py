from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from assembly.registry import (
    CompatibilityMatrixEntry,
    IntegrationStatus,
    ModuleRegistryEntry,
    RegistryInconsistentError,
    assert_md_yaml_consistent,
    load_registry_yaml,
    parse_registry_md,
)


EXPECTED_MODULE_IDS = {
    "contracts",
    "data-platform",
    "entity-registry",
    "reasoner-runtime",
    "graph-engine",
    "main-core",
    "audit-eval",
    "subsystem-sdk",
    "orchestrator",
    "assembly",
    "feature-store",
    "stream-layer",
    "subsystem-announcement",
    "subsystem-news",
}


def test_seed_markdown_and_yaml_are_consistent() -> None:
    assert_md_yaml_consistent(Path("MODULE_REGISTRY.md"), Path("module-registry.yaml"))


def test_public_registry_api_imports_and_loads_seed_yaml() -> None:
    entries = load_registry_yaml(Path("module-registry.yaml"))

    assert all(isinstance(entry, ModuleRegistryEntry) for entry in entries)


def test_parse_registry_md_extracts_fourteen_rows() -> None:
    rows = parse_registry_md(Path("MODULE_REGISTRY.md"))

    assert len(rows) == 14


def test_markdown_yaml_integration_status_drift_is_rejected(
    tmp_path: Path,
) -> None:
    original = Path("MODULE_REGISTRY.md").read_text(encoding="utf-8")
    changed = original.replace(
        "| contracts | 0.0.0 | v0.0.0 | unassigned | not_started |",
        "| contracts | 0.0.0 | v0.0.0 | unassigned | verified |",
        1,
    )
    md_path = tmp_path / "MODULE_REGISTRY.md"
    md_path.write_text(changed, encoding="utf-8")

    with pytest.raises(RegistryInconsistentError):
        assert_md_yaml_consistent(md_path, Path("module-registry.yaml"))


def test_seed_registry_covers_all_fourteen_modules() -> None:
    entries = load_registry_yaml(Path("module-registry.yaml"))

    assert {entry.module_id for entry in entries} == EXPECTED_MODULE_IDS


def test_unstarted_seed_modules_have_default_versions_and_empty_entrypoints() -> None:
    entries = load_registry_yaml(Path("module-registry.yaml"))
    unstarted_entries = [
        entry for entry in entries if entry.module_id != "assembly"
    ]

    assert len(unstarted_entries) == 13
    assert all(entry.module_version == "0.0.0" for entry in unstarted_entries)
    assert all(entry.contract_version == "v0.0.0" for entry in unstarted_entries)
    assert all(
        entry.integration_status == IntegrationStatus.not_started
        for entry in unstarted_entries
    )
    assert all(entry.public_entrypoints == [] for entry in unstarted_entries)
    assert all(entry.supported_profiles == ["lite-local"] for entry in unstarted_entries)


def test_seed_assembly_entry_is_partial() -> None:
    entries = load_registry_yaml(Path("module-registry.yaml"))
    assembly_entry = next(entry for entry in entries if entry.module_id == "assembly")

    assert assembly_entry.module_version == "0.1.0"
    assert assembly_entry.integration_status == IntegrationStatus.partial


def test_compatibility_matrix_seed_is_draft_only() -> None:
    data = yaml.safe_load(Path("compatibility-matrix.yaml").read_text(encoding="utf-8"))
    entries = [CompatibilityMatrixEntry.model_validate(item) for item in data]

    assert len(entries) == 1
    assert entries[0].profile_id == "lite-local"
    assert entries[0].status == "draft"
    assert {item.module_id for item in entries[0].module_set} == EXPECTED_MODULE_IDS


def test_phase_zero_matrix_rejects_non_draft_status_from_yaml(
    tmp_path: Path,
) -> None:
    data = yaml.safe_load(Path("compatibility-matrix.yaml").read_text(encoding="utf-8"))
    data[0]["status"] = "deprecated"
    path = tmp_path / "compatibility-matrix.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    reloaded = yaml.safe_load(path.read_text(encoding="utf-8"))

    with pytest.raises(ValidationError, match="Phase 0"):
        CompatibilityMatrixEntry.model_validate(reloaded[0])
