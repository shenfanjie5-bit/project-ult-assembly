from __future__ import annotations

import json
from pathlib import Path

from assembly.registry import export_module_registry, load_all


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_export_module_registry_writes_json_and_markdown(tmp_path: Path) -> None:
    export = export_module_registry(load_all(PROJECT_ROOT), tmp_path)

    assert export.out_dir == tmp_path
    assert export.registry_json == tmp_path / "registry.json"
    assert export.matrix_json == tmp_path / "matrix.json"
    assert export.registry_md == tmp_path / "MODULE_REGISTRY.md"
    assert export.module_count == 14
    # Stage 5 + MinIO pilot: 3 = (full-dev default, lite-local default,
    # full-dev + extra_bundles=[minio]). Future optional-bundle pilots
    # add their own rows.
    assert export.matrix_count == 3

    registry_payload = json.loads(export.registry_json.read_text(encoding="utf-8"))
    matrix_payload = json.loads(export.matrix_json.read_text(encoding="utf-8"))

    assert len(registry_payload) == 14
    assert len(matrix_payload) == 3
    assert export.registry_md.read_text(encoding="utf-8") == (
        PROJECT_ROOT / "MODULE_REGISTRY.md"
    ).read_text(encoding="utf-8")


def test_export_module_registry_can_load_registry_when_not_provided(
    tmp_path: Path,
) -> None:
    export = export_module_registry(None, tmp_path, root=PROJECT_ROOT)

    assert export.module_count == 14
    assert json.loads((tmp_path / "registry.json").read_text(encoding="utf-8"))
