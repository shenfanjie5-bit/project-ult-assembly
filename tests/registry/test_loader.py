from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest
import yaml

from assembly.registry import (
    RegistryError,
    RegistryInconsistentError,
    load_all,
    load_compatibility_matrix,
)
from assembly.registry import loader


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_NAMES = (
    "MODULE_REGISTRY.md",
    "module-registry.yaml",
    "compatibility-matrix.yaml",
)


def test_load_all_loads_real_project_registry() -> None:
    registry = load_all(PROJECT_ROOT)

    assert registry.root == PROJECT_ROOT
    assert len(registry.modules) == 15
    # Stage 5 + MinIO pilot added a 3rd row for
    # (profile=full-dev, extra_bundles=[minio]).
    assert len(registry.compatibility_matrix) == 3


def test_load_all_runs_consistency_check_before_yaml_load(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    for name in ARTIFACT_NAMES:
        (tmp_path / name).write_text("[]\n", encoding="utf-8")
    calls: list[str] = []

    def fake_consistency(md_path: Path, yaml_path: Path) -> None:
        calls.append(f"consistent:{md_path.name}:{yaml_path.name}")

    def fake_registry_yaml(path: Path) -> list[object]:
        calls.append(f"registry:{path.name}")
        return []

    def fake_matrix(path: Path) -> list[object]:
        calls.append(f"matrix:{path.name}")
        return []

    monkeypatch.setattr(loader, "assert_md_yaml_consistent", fake_consistency)
    monkeypatch.setattr(loader, "load_registry_yaml", fake_registry_yaml)
    monkeypatch.setattr(loader, "load_compatibility_matrix", fake_matrix)

    load_all(tmp_path)

    assert calls == [
        "consistent:MODULE_REGISTRY.md:module-registry.yaml",
        "registry:module-registry.yaml",
        "matrix:compatibility-matrix.yaml",
    ]


@pytest.mark.parametrize("missing_name", ARTIFACT_NAMES)
def test_load_all_missing_artifacts_raise_registry_error(
    tmp_path: Path,
    missing_name: str,
) -> None:
    _copy_project_artifacts(tmp_path, skip=missing_name)

    with pytest.raises(RegistryError, match=re.escape(str(tmp_path / missing_name))):
        load_all(tmp_path)


def test_load_all_registry_consistency_errors_are_preserved(tmp_path: Path) -> None:
    _copy_project_artifacts(tmp_path)
    registry_md = tmp_path / "MODULE_REGISTRY.md"
    # Target the assembly row's ``notes`` cell — at Stage 4 §4.1 this row
    # carries the post-§4.1 status string ``Stage 4 §4.1 done (11 active
    # subsystem modules verified); pending §4.2 e2e runner extension + §4.3
    # self-verify upgrade.``. Replacing the leading sentinel with a different
    # string introduces drift between MD and YAML, which ``load_all`` must
    # surface via ``RegistryInconsistentError`` with the offending column
    # ``notes`` referenced. (Pre-§4.1 this targeted the Stage 0 sentinel
    # ``"Stage 0 registry implementation is partial"``; that string was
    # removed when the assembly row was updated by Stage 4 §4.1.)
    # Stage 4 §4.3 promotion updated the assembly row's notes to start
    # with ``Stage 4 §4.0 + §4.1 + §4.1.5 + §4.2 + §4.3 done`` (full
    # promotion-chain attribution). Stage 5 extended that to
    # ``Stage 4 §4.0 + §4.1 + §4.1.5 + §4.2 + §4.3 + Stage 5 done``
    # — the sentinel below tracks the current MD content; pre-Stage-5
    # it ended at ``§4.3 done`` which no longer appears verbatim.
    registry_md.write_text(
        registry_md.read_text(encoding="utf-8").replace(
            "Stage 4 §4.0 + §4.1 + §4.1.5 + §4.2 + §4.3 + Stage 5 done",
            "Drifted registry note",
            1,
        ),
        encoding="utf-8",
    )

    with pytest.raises(RegistryInconsistentError, match="notes"):
        load_all(tmp_path)


def test_load_compatibility_matrix_wraps_invalid_yaml(tmp_path: Path) -> None:
    matrix_path = tmp_path / "compatibility-matrix.yaml"
    matrix_path.write_text("- [\n", encoding="utf-8")

    with pytest.raises(RegistryError, match="Invalid YAML"):
        load_compatibility_matrix(matrix_path)


def test_load_compatibility_matrix_wraps_schema_errors(tmp_path: Path) -> None:
    matrix_path = tmp_path / "compatibility-matrix.yaml"
    matrix_path.write_text(
        yaml.safe_dump(
            [
                {
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
                    "status": "verified",
                    "verified_at": None,
                }
            ],
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(RegistryError, match="verified_at"):
        load_compatibility_matrix(matrix_path)


def test_load_compatibility_matrix_missing_file_mentions_path(tmp_path: Path) -> None:
    matrix_path = tmp_path / "compatibility-matrix.yaml"

    with pytest.raises(RegistryError, match=re.escape(str(matrix_path))):
        load_compatibility_matrix(matrix_path)


def _copy_project_artifacts(root: Path, *, skip: str | None = None) -> None:
    for name in ARTIFACT_NAMES:
        if name == skip:
            continue
        shutil.copy2(PROJECT_ROOT / name, root / name)
