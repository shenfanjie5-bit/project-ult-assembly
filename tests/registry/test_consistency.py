from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from assembly.registry import (
    CompatibilityMatrixEntry,
    IntegrationStatus,
    RegistryInconsistentError,
    assert_md_yaml_consistent,
    load_registry_yaml,
    parse_registry_md,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_MD = PROJECT_ROOT / "MODULE_REGISTRY.md"
REGISTRY_YAML = PROJECT_ROOT / "module-registry.yaml"
MATRIX_YAML = PROJECT_ROOT / "compatibility-matrix.yaml"

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

MD_COLUMNS = [
    "module_id",
    "module_version",
    "contract_version",
    "owner",
    "integration_status",
    "supported_profiles",
    "notes",
]


def write_registry_md(path: Path, rows: list[dict[str, str]]) -> Path:
    table = [
        "# MODULE_REGISTRY",
        "",
        "| " + " | ".join(MD_COLUMNS) + " |",
        "|---|---|---|---|---|---|---|",
    ]
    table.extend(
        "| " + " | ".join(row[column] for column in MD_COLUMNS) + " |"
        for row in rows
    )
    path.write_text("\n".join(table) + "\n", encoding="utf-8")
    return path


def write_yaml(path: Path, data: object) -> Path:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def test_registry_md_and_yaml_are_consistent() -> None:
    assert_md_yaml_consistent(REGISTRY_MD, REGISTRY_YAML)


def test_registry_artifacts_cover_expected_fourteen_modules() -> None:
    rows = parse_registry_md(REGISTRY_MD)
    entries = load_registry_yaml(REGISTRY_YAML)

    assert len(rows) == 14
    assert {entry.module_id for entry in entries} == EXPECTED_MODULE_IDS

    unstarted_entries = [
        entry for entry in entries if entry.module_id != "assembly"
    ]
    assert all(
        entry.integration_status == IntegrationStatus.not_started
        for entry in unstarted_entries
    )
    assert all(
        entry.module_version == "0.0.0"
        and entry.contract_version == "v0.0.0"
        and entry.public_entrypoints == []
        and entry.supported_profiles == ["lite-local"]
        for entry in unstarted_entries
    )

    assembly = next(entry for entry in entries if entry.module_id == "assembly")
    assert assembly.module_version == "0.1.0"
    assert assembly.integration_status == IntegrationStatus.partial


def test_markdown_status_drift_raises_inconsistent_error(tmp_path: Path) -> None:
    rows = parse_registry_md(REGISTRY_MD)
    rows[0] = {**rows[0], "integration_status": "verified"}
    drifted_md = write_registry_md(tmp_path / "MODULE_REGISTRY.md", rows)

    with pytest.raises(RegistryInconsistentError, match="integration_status"):
        assert_md_yaml_consistent(drifted_md, REGISTRY_YAML)


@pytest.mark.parametrize(
    ("column", "drifted_value"),
    [
        ("module_version", "9.9.9"),
        ("owner", "platform-team"),
        ("supported_profiles", "full-dev"),
        ("notes", "Drifted Markdown note."),
    ],
)
def test_markdown_registry_field_drift_raises_inconsistent_error(
    tmp_path: Path,
    column: str,
    drifted_value: str,
) -> None:
    rows = parse_registry_md(REGISTRY_MD)
    rows[0] = {**rows[0], column: drifted_value}
    drifted_md = write_registry_md(tmp_path / "MODULE_REGISTRY.md", rows)

    with pytest.raises(RegistryInconsistentError, match=column):
        assert_md_yaml_consistent(drifted_md, REGISTRY_YAML)


def test_phase_zero_rejects_non_draft_matrix_status() -> None:
    raw = yaml.safe_load(MATRIX_YAML.read_text(encoding="utf-8"))
    raw[0]["status"] = "deprecated"

    with pytest.raises(ValidationError, match="Phase 0"):
        CompatibilityMatrixEntry.model_validate(raw[0])


def test_compatibility_matrix_is_draft_and_covers_registry_modules() -> None:
    raw = yaml.safe_load(MATRIX_YAML.read_text(encoding="utf-8"))
    entries = [CompatibilityMatrixEntry.model_validate(item) for item in raw]

    assert len(entries) == 1
    assert entries[0].profile_id == "lite-local"
    assert entries[0].status == "draft"
    assert entries[0].verified_at is None
    assert {
        module.module_id for module in entries[0].module_set
    } == EXPECTED_MODULE_IDS


def test_duplicate_module_id_in_markdown_is_rejected(tmp_path: Path) -> None:
    rows = parse_registry_md(REGISTRY_MD)
    duplicated_md = write_registry_md(
        tmp_path / "MODULE_REGISTRY.md",
        [*rows, rows[0]],
    )

    with pytest.raises(RegistryInconsistentError, match="Duplicate module_id"):
        assert_md_yaml_consistent(duplicated_md, REGISTRY_YAML)


def test_duplicate_module_id_in_yaml_is_rejected_before_set_comparison(
    tmp_path: Path,
) -> None:
    raw = yaml.safe_load(REGISTRY_YAML.read_text(encoding="utf-8"))
    duplicated_yaml = write_yaml(
        tmp_path / "module-registry.yaml",
        [*raw, raw[0]],
    )

    with pytest.raises(RegistryInconsistentError, match="Duplicate module_id"):
        assert_md_yaml_consistent(REGISTRY_MD, duplicated_yaml)
