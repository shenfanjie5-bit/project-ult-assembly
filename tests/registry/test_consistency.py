from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from assembly.profiles import list_profiles
from assembly.registry import (
    CompatibilityMatrixEntry,
    IntegrationStatus,
    RegistryInconsistentError,
    assert_md_yaml_consistent,
    load_registry_yaml,
    parse_registry_md,
)
from assembly.registry.schema import ModuleRegistryEntry
from assembly.registry.validator import REGISTRY_MD_COLUMNS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_MD = PROJECT_ROOT / "MODULE_REGISTRY.md"
REGISTRY_YAML = PROJECT_ROOT / "module-registry.yaml"
MATRIX_YAML = PROJECT_ROOT / "compatibility-matrix.yaml"
PROFILES_DIR = PROJECT_ROOT / "profiles"

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

MD_COLUMNS = REGISTRY_MD_COLUMNS
PHASE_ZERO_ENTRYPOINTS = {
    "health_probe": ("health", "health_probe"),
    "smoke_hook": ("smoke", "smoke_hook"),
    "init_hook": ("init", "init_hook"),
    "version_declaration": ("version", "version_declaration"),
    "cli": ("cli", "cli"),
}


def write_registry_md(path: Path, rows: list[dict[str, str]]) -> Path:
    table = [
        "# MODULE_REGISTRY",
        "",
        "| " + " | ".join(MD_COLUMNS) + " |",
        "|" + "|".join("---" for _ in MD_COLUMNS) + "|",
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


#: Stage 4 §4.1 baseline (Stage 3 cross-project compat audit code-confirmed).
#: 11 active subsystem modules promoted from ``not_started`` → ``verified``;
#: ``assembly`` stays ``partial`` (pending §4.2 e2e runner extension + §4.3
#: self-verify upgrade); ``feature-store`` + ``stream-layer`` stay
#: ``not_started`` (frozen slots per master plan §1.1).
STAGE_4_VERIFIED_MODULE_IDS = {
    "contracts",
    "data-platform",
    "entity-registry",
    "reasoner-runtime",
    "graph-engine",
    "main-core",
    "audit-eval",
    "subsystem-sdk",
    "orchestrator",
    "subsystem-announcement",
    "subsystem-news",
    # Stage 4 §4.3 promotion: assembly moves from `partial` to `verified`
    # after the real Lite-stack PASS of test_e2e_runner_consumes_audit_
    # eval_fixtures_minimal_cycle is recorded (codex review #8 strict
    # call). All 4 §4.3 gates met: profile resolve ✓ + public smoke
    # probes ✓ + contract suite ✓ + minimal-cycle e2e real PASS ✓.
    "assembly",
}
STAGE_4_PARTIAL_MODULE_IDS: set[str] = set()
STAGE_4_NOT_STARTED_MODULE_IDS = {"feature-store", "stream-layer"}

#: Per-module ``module_version`` baseline at Stage 4 §4.1 — sourced from each
#: module's ``version_declaration.declare()`` after the §4.0 source drift
#: fixes (audit-eval 0.2.1→0.2.2; graph-engine ``_safe_contract_version``
#: now adds ``v`` prefix). Frozen slots stay at ``0.0.0``.
STAGE_4_MODULE_VERSIONS = {
    "contracts": "0.1.3",
    "data-platform": "0.1.1",
    "entity-registry": "0.1.1",
    "reasoner-runtime": "0.1.1",
    "graph-engine": "0.1.1",
    "main-core": "0.1.1",
    "audit-eval": "0.2.2",
    "subsystem-sdk": "0.1.2",
    "orchestrator": "0.1.1",
    "assembly": "0.1.0",
    "feature-store": "0.0.0",
    "stream-layer": "0.0.0",
    "subsystem-announcement": "0.1.1",
    "subsystem-news": "0.1.1",
}

#: Per-module ``contract_version`` baseline. Per master plan §4.1 rule:
#: ``contract_version`` is bumped only when the module's
#: ``version_declaration.declare()`` returns a well-formed ``v\d+\.\d+\.\d+``
#: value. Modules that return ``"unknown"`` (the SDK/announcement/news
#: subsystem trio — they consume the contracts schema, they don't own one)
#: stay at ``v0.0.0``. ``graph-engine`` re-exports ``contracts.__version__``
#: with the canonical ``v`` prefix added by ``_safe_contract_version`` per
#: §4.0 Op-2.
#: Per Stage 4 §4.1.5, all 11 active subsystem modules align to the canonical
#: contracts schema version (``v0.1.3``) — this is what each module's
#: ``public.py`` hardcodes in its ``_CONTRACT_VERSION`` constant (or
#: ``graph-engine`` dynamically computes via ``f"v{contracts.__version__}"``
#: in ``_safe_contract_version``). This is NOT the module's own
#: ``module_version``; it's the canonical contracts schema version the
#: module declares compatibility with. Assembly stays at ``v0.0.0`` (meta-
#: orchestration module — owns no contracts schema); frozen slots stay at
#: ``v0.0.0`` per master plan §1.1 freeze.
STAGE_4_CONTRACT_VERSIONS = {
    "contracts": "v0.1.3",
    "data-platform": "v0.1.3",
    "entity-registry": "v0.1.3",
    "reasoner-runtime": "v0.1.3",
    "graph-engine": "v0.1.3",
    "main-core": "v0.1.3",
    "audit-eval": "v0.1.3",
    "subsystem-sdk": "v0.1.3",
    "orchestrator": "v0.1.3",
    "assembly": "v0.0.0",
    "feature-store": "v0.0.0",
    "stream-layer": "v0.0.0",
    "subsystem-announcement": "v0.1.3",
    "subsystem-news": "v0.1.3",
}


def test_registry_artifacts_cover_expected_fourteen_modules() -> None:
    rows = parse_registry_md(REGISTRY_MD)
    entries = load_registry_yaml(REGISTRY_YAML)

    assert len(rows) == 14
    assert {entry.module_id for entry in entries} == EXPECTED_MODULE_IDS
    assert (
        STAGE_4_VERIFIED_MODULE_IDS
        | STAGE_4_PARTIAL_MODULE_IDS
        | STAGE_4_NOT_STARTED_MODULE_IDS
        == EXPECTED_MODULE_IDS
    ), "Stage 4 §4.1 baseline groups must cover all 14 modules disjointly"

    by_id = {entry.module_id: entry for entry in entries}

    # Stage 4 §4.1 integration_status invariants.
    for module_id in STAGE_4_VERIFIED_MODULE_IDS:
        assert (
            by_id[module_id].integration_status == IntegrationStatus.verified
        ), f"{module_id} should be verified at Stage 4 §4.1"
    for module_id in STAGE_4_PARTIAL_MODULE_IDS:
        assert (
            by_id[module_id].integration_status == IntegrationStatus.partial
        ), f"{module_id} should remain partial pending Stage 4 §4.3"
    for module_id in STAGE_4_NOT_STARTED_MODULE_IDS:
        assert (
            by_id[module_id].integration_status == IntegrationStatus.not_started
        ), (
            f"{module_id} is a frozen slot per master plan §1.1; must stay "
            "not_started at Stage 4 §4.1"
        )

    # Stage 4 §4.1 module_version + contract_version + supported_profiles
    # per-module evidence.
    for module_id, expected_module_version in STAGE_4_MODULE_VERSIONS.items():
        assert by_id[module_id].module_version == expected_module_version, (
            f"{module_id} module_version should be {expected_module_version} "
            f"per Stage 4 §4.1 evidence; got {by_id[module_id].module_version}"
        )
    for module_id, expected_contract_version in STAGE_4_CONTRACT_VERSIONS.items():
        assert (
            by_id[module_id].contract_version == expected_contract_version
        ), (
            f"{module_id} contract_version should be {expected_contract_version} "
            f"per Stage 4 §4.1 evidence; got "
            f"{by_id[module_id].contract_version}"
        )

    # All 14 modules expose the same canonical 5-entrypoint surface +
    # supported_profiles set; this part is invariant across Stage 0/4.
    for entry in entries:
        assert_phase_zero_public_entrypoints(entry)
        assert entry.supported_profiles == ["lite-local", "full-dev"]


def test_markdown_status_drift_raises_inconsistent_error(tmp_path: Path) -> None:
    # Pick a module currently at ``not_started`` (not the verified Stage 4
    # §4.1 set) so flipping its MD value to ``verified`` actually creates
    # drift vs the YAML. ``rows[0]`` was the Stage 0 default but post-§4.1
    # it is ``contracts`` which is already ``verified``; the drift would be
    # zero and the test would silently pass. ``feature-store`` is a
    # frozen-slot ``not_started`` module per master plan §1.1.
    rows = parse_registry_md(REGISTRY_MD)
    target_index = next(
        index
        for index, row in enumerate(rows)
        if row["module_id"] == "feature-store"
    )
    rows[target_index] = {
        **rows[target_index],
        "integration_status": "verified",
    }
    drifted_md = write_registry_md(tmp_path / "MODULE_REGISTRY.md", rows)

    with pytest.raises(RegistryInconsistentError, match="integration_status"):
        assert_md_yaml_consistent(drifted_md, REGISTRY_YAML)


@pytest.mark.parametrize(
    ("column", "drifted_value"),
    [
        ("module_version", "9.9.9"),
        ("owner", "platform-team"),
        ("upstream_modules", "assembly"),
        ("downstream_modules", "assembly"),
        (
            "public_entrypoints",
            "health:health_probe=example.public:health_probe",
        ),
        ("depends_on", "assembly"),
        ("supported_profiles", "full-dev"),
        ("last_smoke_result", "reports/smoke/manual.json"),
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


def assert_phase_zero_public_entrypoints(entry: ModuleRegistryEntry) -> None:
    package_name = entry.module_id.replace("-", "_")

    assert {
        entrypoint.kind: (entrypoint.name, entrypoint.reference)
        for entrypoint in entry.public_entrypoints
    } == {
        kind: (name, f"{package_name}.public:{symbol}")
        for kind, (name, symbol) in PHASE_ZERO_ENTRYPOINTS.items()
    }


def test_deprecated_matrix_status_is_valid_but_not_current() -> None:
    raw = yaml.safe_load(MATRIX_YAML.read_text(encoding="utf-8"))
    raw[0]["status"] = "deprecated"

    entry = CompatibilityMatrixEntry.model_validate(raw[0])

    assert entry.status == "deprecated"


def test_compatibility_matrix_lite_local_verified_full_dev_still_draft() -> None:
    """Stage 4 §4.3 promotion is **per-profile** (codex review #10 strict
    call): only `lite-local` moves to `verified` with a non-None
    ``verified_at`` ISO timestamp because the recorded real e2e PASS
    evidence (``test_e2e_runner_consumes_audit_eval_fixtures_minimal_
    cycle``) invokes ``run_min_cycle_e2e("lite-local", ...)`` and
    therefore only covers the `lite-local` profile. `full-dev` stays
    `draft` until a separate ``run_min_cycle_e2e("full-dev", ...)``
    PASS is recorded; promoting it now would over-promote the
    matrix's evidence surface.
    """
    raw = yaml.safe_load(MATRIX_YAML.read_text(encoding="utf-8"))
    entries = [CompatibilityMatrixEntry.model_validate(item) for item in raw]
    entries_by_profile = {entry.profile_id: entry for entry in entries}

    assert set(entries_by_profile) == {"lite-local", "full-dev"}

    lite_local = entries_by_profile["lite-local"]
    assert lite_local.status == "verified"
    assert lite_local.verified_at is not None

    full_dev = entries_by_profile["full-dev"]
    assert full_dev.status == "draft"
    assert full_dev.verified_at is None
    #: At Stage 4 §4.1.5 the matrix ``module_set`` drops the two frozen slots
    #: (``feature-store``, ``stream-layer``) from both profile entries.
    #: Those modules remain declared in the registry with
    #: ``supported_profiles=[lite-local, full-dev]`` as a forward declaration
    #: of compatibility for their future P7/P11 enablement, but are not
    #: part of the verified combination this round. See master plan §1.1
    #: frozen slots + ``profiles/lite-local.yaml`` + ``profiles/full-dev.yaml``
    #: where their ``enabled_modules`` entries were also removed.
    frozen_slots = {"feature-store", "stream-layer"}
    assert {
        module.module_id for module in entries_by_profile["lite-local"].module_set
    } == EXPECTED_MODULE_IDS - frozen_slots
    assert {
        module.module_id for module in entries_by_profile["full-dev"].module_set
    } == EXPECTED_MODULE_IDS - frozen_slots


def test_full_dev_supported_profiles_are_explicit_for_feature_and_stream() -> None:
    entries_by_id = {
        entry.module_id: entry for entry in load_registry_yaml(REGISTRY_YAML)
    }

    assert entries_by_id["feature-store"].supported_profiles == [
        "lite-local",
        "full-dev",
    ]
    assert entries_by_id["stream-layer"].supported_profiles == [
        "lite-local",
        "full-dev",
    ]


def test_registry_and_matrix_profile_references_are_loadable() -> None:
    registry_entries = load_registry_yaml(REGISTRY_YAML)
    matrix_entries = [
        CompatibilityMatrixEntry.model_validate(item)
        for item in yaml.safe_load(MATRIX_YAML.read_text(encoding="utf-8"))
    ]
    profiles_by_id = {
        profile.profile_id: profile for profile in list_profiles(PROFILES_DIR)
    }

    referenced_profile_ids = {
        profile_id
        for entry in registry_entries
        for profile_id in entry.supported_profiles
    }
    referenced_profile_ids.update(entry.profile_id for entry in matrix_entries)

    assert referenced_profile_ids <= set(profiles_by_id)


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
