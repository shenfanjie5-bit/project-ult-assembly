"""Validation helpers for the human and machine-readable module registry."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from assembly.registry.schema import ModuleRegistryEntry


class RegistryError(Exception):
    """Base error for registry loading and consistency checks."""


class RegistryInconsistentError(RegistryError):
    """Raised when Markdown and YAML registry artifacts diverge."""


def load_registry_yaml(path: Path) -> list[ModuleRegistryEntry]:
    """Load and validate the machine-readable module registry."""

    path = Path(path)
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except OSError as exc:
        raise RegistryError(f"Registry YAML not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise RegistryError(f"Invalid YAML in {path}: {exc}") from exc

    if data is None:
        data = []

    if not isinstance(data, list):
        raise RegistryError(f"Invalid registry in {path}: YAML root must be a list")

    try:
        return [ModuleRegistryEntry.model_validate(item) for item in data]
    except ValidationError as exc:
        raise RegistryError(f"Invalid registry schema in {path}: {exc}") from exc


def parse_registry_md(path: Path) -> list[dict[str, str]]:
    """Extract module registry rows from the Markdown table."""

    path = Path(path)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise RegistryError(f"Registry Markdown not found: {path}") from exc

    rows: list[dict[str, str]] = []
    headers: list[str] | None = None

    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue

        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if headers is None:
            if "module_id" not in cells:
                continue
            headers = cells
            continue

        if _is_markdown_separator(cells):
            continue

        if len(cells) != len(headers):
            raise RegistryError(f"Malformed registry table row in {path}: {line}")

        rows.append(dict(zip(headers, cells, strict=True)))

    if headers is None:
        raise RegistryError(f"Registry table not found in {path}")

    return rows


def assert_md_yaml_consistent(md_path: Path, yaml_path: Path) -> None:
    """Assert that Markdown and YAML registry artifacts share key facts."""

    md_rows = parse_registry_md(md_path)
    yaml_entries = load_registry_yaml(yaml_path)

    md_by_id = {row["module_id"]: row for row in md_rows}
    yaml_by_id = {entry.module_id: entry for entry in yaml_entries}

    if set(md_by_id) != set(yaml_by_id):
        missing_in_md = sorted(set(yaml_by_id) - set(md_by_id))
        missing_in_yaml = sorted(set(md_by_id) - set(yaml_by_id))
        raise RegistryInconsistentError(
            "Registry module_id sets differ: "
            f"missing_in_md={missing_in_md}, missing_in_yaml={missing_in_yaml}"
        )

    for module_id, entry in yaml_by_id.items():
        row = md_by_id[module_id]
        expected = {
            "module_id": entry.module_id,
            "integration_status": entry.integration_status.value,
            "contract_version": entry.contract_version,
        }
        for field, yaml_value in expected.items():
            md_value = row.get(field)
            if md_value != yaml_value:
                raise RegistryInconsistentError(
                    f"Registry mismatch for {module_id}.{field}: "
                    f"md={md_value!r}, yaml={yaml_value!r}"
                )


def _is_markdown_separator(cells: list[str]) -> bool:
    return all(cell and set(cell) <= {"-", ":"} for cell in cells)
