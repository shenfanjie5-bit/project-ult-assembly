"""Consistency checks for the human and machine-readable registries."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import yaml
from pydantic import ValidationError

from assembly.registry.schema import ModuleRegistryEntry, PublicEntrypoint

REGISTRY_MD_COLUMNS = [
    "module_id",
    "module_version",
    "contract_version",
    "owner",
    "upstream_modules",
    "downstream_modules",
    "public_entrypoints",
    "depends_on",
    "supported_profiles",
    "integration_status",
    "last_smoke_result",
    "notes",
]
CONSISTENCY_COLUMNS = tuple(REGISTRY_MD_COLUMNS)
LIST_COLUMNS = {
    "upstream_modules",
    "downstream_modules",
    "depends_on",
    "supported_profiles",
}


class RegistryError(Exception):
    """Base exception for registry parsing and validation errors."""


class RegistryInconsistentError(RegistryError):
    """Raised when registry artifacts disagree."""


def load_registry_yaml(path: Path) -> list[ModuleRegistryEntry]:
    """Load and validate the machine-readable module registry."""

    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RegistryError(f"Invalid YAML in {path}: {exc}") from exc

    if not isinstance(raw, list):
        raise RegistryError("module registry YAML root must be a list")

    entries: list[ModuleRegistryEntry] = []
    for index, item in enumerate(raw):
        try:
            entries.append(ModuleRegistryEntry.model_validate(item))
        except ValidationError as exc:
            raise RegistryError(
                f"Invalid registry entry at index {index}: {exc}"
            ) from exc

    return entries


def parse_registry_md(path: Path) -> list[dict[str, str]]:
    """Extract registry rows from the MODULE_REGISTRY Markdown table."""

    rows: list[dict[str, str]] = []
    in_registry_table = False

    for line in Path(path).read_text(encoding="utf-8").splitlines():
        cells = _split_markdown_row(line)
        if cells is None:
            if in_registry_table:
                break
            continue

        if cells == REGISTRY_MD_COLUMNS:
            in_registry_table = True
            continue

        if not in_registry_table:
            continue

        if _is_separator_row(cells):
            continue

        if len(cells) != len(REGISTRY_MD_COLUMNS):
            raise RegistryError("MODULE_REGISTRY.md table row has unexpected width")

        rows.append(dict(zip(REGISTRY_MD_COLUMNS, cells, strict=True)))

    if not in_registry_table:
        raise RegistryError("MODULE_REGISTRY.md registry table was not found")

    return rows


def assert_md_yaml_consistent(md_path: Path, yaml_path: Path) -> None:
    """Raise if MODULE_REGISTRY.md and module-registry.yaml disagree."""

    rows = parse_registry_md(md_path)
    entries = load_registry_yaml(yaml_path)

    _assert_unique_ids(
        [row["module_id"] for row in rows],
        "MODULE_REGISTRY.md",
    )
    _assert_unique_ids(
        [entry.module_id for entry in entries],
        "module-registry.yaml",
    )

    md_by_id = {row["module_id"]: row for row in rows}
    yaml_by_id = {entry.module_id: entry for entry in entries}

    md_ids = set(md_by_id)
    yaml_ids = set(yaml_by_id)
    if md_ids != yaml_ids:
        raise RegistryInconsistentError(
            "Registry module_id sets differ: "
            f"md_only={sorted(md_ids - yaml_ids)}, "
            f"yaml_only={sorted(yaml_ids - md_ids)}"
        )

    for module_id in sorted(md_ids):
        md_row = md_by_id[module_id]
        yaml_entry = yaml_by_id[module_id]
        yaml_values = _registry_md_values(yaml_entry)

        for column in CONSISTENCY_COLUMNS:
            md_value = _normalize_md_value(column, md_row[column])
            if md_value != yaml_values[column]:
                raise RegistryInconsistentError(
                    f"{module_id} has inconsistent {column}: "
                    f"md={md_row[column]!r}, yaml={yaml_values[column]!r}"
                )


def _split_markdown_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None

    row = stripped[1:]
    if row.endswith("|"):
        row = row[:-1]

    return [cell.strip() for cell in row.split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    return all(cell and set(cell) <= {"-", ":"} for cell in cells)


def _registry_md_values(entry: ModuleRegistryEntry) -> dict[str, str]:
    return {
        "module_id": entry.module_id,
        "module_version": entry.module_version,
        "contract_version": entry.contract_version,
        "owner": entry.owner,
        "upstream_modules": _format_list_cell(entry.upstream_modules),
        "downstream_modules": _format_list_cell(entry.downstream_modules),
        "public_entrypoints": _format_entrypoints_cell(entry.public_entrypoints),
        "depends_on": _format_list_cell(entry.depends_on),
        "supported_profiles": _format_list_cell(entry.supported_profiles),
        "integration_status": entry.integration_status.value,
        "last_smoke_result": _format_nullable_cell(entry.last_smoke_result),
        "notes": entry.notes,
    }


def _normalize_md_value(column: str, value: str) -> str:
    if column in LIST_COLUMNS:
        return _format_list_cell(_parse_list_cell(value))

    if column == "public_entrypoints":
        return _format_entrypoints_cell(_parse_entrypoints_cell(value))

    if column == "last_smoke_result":
        return _format_nullable_cell(_parse_nullable_cell(value))

    return value


def _parse_list_cell(value: str) -> list[str]:
    if not value:
        return []

    return [item.strip() for item in value.split(",") if item.strip()]


def _format_list_cell(values: list[str]) -> str:
    return ", ".join(values)


def _parse_entrypoints_cell(value: str) -> list[PublicEntrypoint]:
    if not value:
        return []

    entrypoints: list[PublicEntrypoint] = []
    for raw_item in value.split(";"):
        item = raw_item.strip()
        if not item:
            continue

        try:
            name_and_kind, reference = item.split("=", 1)
            name, kind = name_and_kind.split(":", 1)
        except ValueError as exc:
            raise RegistryError(
                "MODULE_REGISTRY.md public_entrypoints must use "
                "'name:kind=module.path:symbol' entries"
            ) from exc

        try:
            entrypoints.append(
                PublicEntrypoint.model_validate(
                    {
                        "name": name.strip(),
                        "kind": kind.strip(),
                        "reference": reference.strip(),
                    }
                )
            )
        except ValidationError as exc:
            raise RegistryError(
                f"Invalid public_entrypoints cell entry {item!r}: {exc}"
            ) from exc

    return entrypoints


def _format_entrypoints_cell(values: list[PublicEntrypoint]) -> str:
    return "; ".join(
        f"{entrypoint.name}:{entrypoint.kind}={entrypoint.reference}"
        for entrypoint in values
    )


def _parse_nullable_cell(value: str) -> str | None:
    if not value or value == "null":
        return None

    return value


def _format_nullable_cell(value: str | None) -> str:
    if value is None:
        return "null"

    return value


def _assert_unique_ids(module_ids: list[str], source_name: str) -> None:
    counts: Counter[str] = Counter(module_ids)
    duplicates = sorted(module_id for module_id, count in counts.items() if count > 1)
    if duplicates:
        raise RegistryInconsistentError(
            f"Duplicate module_id values in {source_name}: {duplicates}"
        )
