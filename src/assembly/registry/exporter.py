"""Export runtime registry artifacts for reports."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from assembly.registry.loader import Registry, load_all
from assembly.registry.validator import RegistryError


class RegistryExport(BaseModel):
    """Paths and counts produced by a registry export."""

    model_config = ConfigDict(extra="forbid")

    out_dir: Path
    registry_json: Path
    matrix_json: Path
    registry_md: Path
    module_count: int = Field(ge=0)
    matrix_count: int = Field(ge=0)


def export_module_registry(
    registry: Registry | None = None,
    out_dir: Path = Path("reports/registry"),
    *,
    root: Path = Path("."),
) -> RegistryExport:
    """Export registry and matrix facts to a report directory."""

    registry = load_all(root) if registry is None else registry
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    registry_json = out_dir / "registry.json"
    matrix_json = out_dir / "matrix.json"
    registry_md = out_dir / "MODULE_REGISTRY.md"

    registry_json.write_text(
        json.dumps(
            [entry.model_dump(mode="json") for entry in registry.modules],
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    matrix_json.write_text(
        json.dumps(
            [entry.model_dump(mode="json") for entry in registry.compatibility_matrix],
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    source_md = registry.root / "MODULE_REGISTRY.md"
    if not source_md.exists():
        raise RegistryError(f"Registry Markdown artifact not found: {source_md}")
    shutil.copy2(source_md, registry_md)

    return RegistryExport(
        out_dir=out_dir,
        registry_json=registry_json,
        matrix_json=matrix_json,
        registry_md=registry_md,
        module_count=len(registry.modules),
        matrix_count=len(registry.compatibility_matrix),
    )
