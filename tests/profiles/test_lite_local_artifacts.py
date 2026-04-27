from __future__ import annotations

from pathlib import Path

import yaml

from assembly.profiles import list_profiles, load_bundle, load_profile
from assembly.profiles.schema import ProfileMode
from assembly.registry import CompatibilityMatrixEntry, load_registry_yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = PROJECT_ROOT / "profiles" / "lite-local.yaml"
READONLY_UI_PROFILE_PATH = PROJECT_ROOT / "profiles" / "lite-local-readonly-ui.yaml"
BUNDLES_ROOT = PROJECT_ROOT / "bundles"
ENV_EXAMPLE = PROJECT_ROOT / ".env.example"
REGISTRY_YAML = PROJECT_ROOT / "module-registry.yaml"
MATRIX_YAML = PROJECT_ROOT / "compatibility-matrix.yaml"

FORBIDDEN_LITE_BUNDLES = {
    "minio",
    "grafana",
    "superset",
    "temporal",
    "feast",
    "milvus",
    "kafka",
    "flink",
    "kafka-flink",
}
OPTIONAL_FULL_BUNDLES = {
    "minio",
    "grafana",
    "superset",
    "temporal",
    "feast",
    "kafka-flink",
}


def test_lite_local_profile_artifact_is_complete() -> None:
    profile = load_profile(PROFILE_PATH)

    assert profile.profile_id == "lite-local"
    assert profile.mode == ProfileMode.lite
    assert profile.max_long_running_daemons == 4
    assert profile.enabled_service_bundles == ["postgres", "neo4j", "dagster"]
    assert FORBIDDEN_LITE_BUNDLES.isdisjoint(profile.enabled_service_bundles)


def test_lite_local_readonly_ui_profile_only_adds_frontend_api() -> None:
    base = load_profile(PROFILE_PATH)
    readonly_ui = load_profile(READONLY_UI_PROFILE_PATH)

    assert readonly_ui.profile_id == "lite-local-readonly-ui"
    assert readonly_ui.mode == base.mode
    assert readonly_ui.enabled_service_bundles == base.enabled_service_bundles
    assert readonly_ui.required_env_keys == base.required_env_keys
    assert readonly_ui.optional_env_keys == base.optional_env_keys
    assert readonly_ui.storage_backends == base.storage_backends
    assert readonly_ui.resource_expectation == base.resource_expectation
    assert readonly_ui.max_long_running_daemons == base.max_long_running_daemons
    assert set(readonly_ui.enabled_modules) == {
        *base.enabled_modules,
        "frontend-api",
    }
    assert len(readonly_ui.enabled_modules) == len(base.enabled_modules) + 1
    assert {"feature-store", "stream-layer"}.isdisjoint(
        readonly_ui.enabled_modules
    )
    assert "base lite-local unchanged" in readonly_ui.notes


def test_lite_local_bundle_manifests_have_exact_four_services() -> None:
    bundles = [
        load_bundle(BUNDLES_ROOT / "postgres.yaml"),
        load_bundle(BUNDLES_ROOT / "neo4j.yaml"),
        load_bundle(BUNDLES_ROOT / "dagster.yaml"),
    ]
    service_names = [
        service.name for bundle in bundles for service in bundle.services
    ]

    assert service_names == [
        "postgres",
        "neo4j",
        "dagster-daemon",
        "dagster-webserver",
    ]
    assert len(service_names) == len(set(service_names))
    assert sum(len(bundle.services) for bundle in bundles) == 4
    assert all(not bundle.optional for bundle in bundles)


def test_lite_local_profile_bundle_references_are_closed() -> None:
    profile = load_profile(PROFILE_PATH)

    for bundle_name in profile.enabled_service_bundles:
        bundle = load_bundle(BUNDLES_ROOT / f"{bundle_name}.yaml")
        assert bundle.bundle_name == bundle_name
        assert profile.profile_id in bundle.required_profiles


def test_lite_local_readonly_ui_profile_bundle_references_are_closed() -> None:
    profile = load_profile(READONLY_UI_PROFILE_PATH)

    for bundle_name in profile.enabled_service_bundles:
        bundle = load_bundle(BUNDLES_ROOT / f"{bundle_name}.yaml")
        assert bundle.bundle_name == bundle_name
        assert profile.profile_id in bundle.required_profiles


def test_optional_bundles_are_not_declared_for_lite_local() -> None:
    for bundle_name in OPTIONAL_FULL_BUNDLES:
        bundle = load_bundle(BUNDLES_ROOT / f"{bundle_name}.yaml")

        assert bundle.optional is True
        assert bundle.required_profiles == ["full-dev"]
        assert "lite-local" not in bundle.required_profiles
        assert "lite-local-readonly-ui" not in bundle.required_profiles


def test_lite_local_modules_cover_registry_supported_modules() -> None:
    """Lite profile's ``enabled_modules`` equals the set of registry modules
    whose ``supported_profiles`` declares ``lite-local``, minus the frozen
    slots that are declared-but-not-runnable this round.

    Per master plan §1.1, ``feature-store`` (P7 Feast enablement) and
    ``stream-layer`` (P11 Kafka/Flink enablement) keep
    ``supported_profiles: [lite-local, full-dev]`` in the registry as a
    forward declaration of compatibility, but they are **not** enabled in
    the Lite/Full profile ``enabled_modules`` list at Stage 4 §4.1.5 —
    per-module ``integration_status`` stays at ``not_started`` to
    explicitly reflect the freeze. Dropping them from
    ``enabled_modules`` prevents ``ContractsVersionCheck`` from returning
    ``not_started`` rows that would silently degrade the contract suite
    to ``partial``; Stage 3/4 contract suite runs ``success`` as a result.
    """
    profile = load_profile(PROFILE_PATH)
    registry_entries = load_registry_yaml(REGISTRY_YAML)
    registry_module_ids = {entry.module_id for entry in registry_entries}
    lite_supported_module_ids = {
        entry.module_id
        for entry in registry_entries
        if profile.profile_id in entry.supported_profiles
    }
    #: Slots declared in the registry but not enabled by the runtime profile
    #: in this round:
    #:
    #: * feature-store / stream-layer are frozen future modules.
    #: * frontend-api is registered with public smoke evidence, but it stays
    #:   outside the existing verified compatibility rows until fresh
    #:   contract/smoke/e2e evidence exists for a matrix identity that includes
    #:   it.
    registry_only_slots = {"feature-store", "stream-layer", "frontend-api"}

    assert set(profile.enabled_modules) <= registry_module_ids
    assert (
        set(profile.enabled_modules)
        == lite_supported_module_ids - registry_only_slots
    )
    assert len(profile.enabled_modules) == 12


def test_env_example_contains_lite_keys_and_empty_full_secret_placeholders() -> None:
    profile = load_profile(PROFILE_PATH)
    entries = _env_example_entries(ENV_EXAMPLE)
    lite_keys = [
        *profile.required_env_keys,
        *profile.optional_env_keys,
    ]
    full_secret_placeholders = [
        "MINIO_ROOT_USER",
        "MINIO_ROOT_PASSWORD",
        "GRAFANA_ADMIN_USER",
        "GRAFANA_ADMIN_PASSWORD",
        "SUPERSET_SECRET_KEY",
    ]

    env_keys = [key for key, _ in entries]
    assert env_keys[: len(profile.required_env_keys)] == profile.required_env_keys
    assert set(lite_keys) <= set(env_keys)
    assert all(key in env_keys for key in full_secret_placeholders)
    assert all(value == "" for _, value in entries)


def test_registry_and_matrix_profile_references_are_publicly_loadable() -> None:
    registry_entries = load_registry_yaml(REGISTRY_YAML)
    matrix_entries = [
        CompatibilityMatrixEntry.model_validate(item)
        for item in yaml.safe_load(MATRIX_YAML.read_text(encoding="utf-8"))
    ]
    profiles_by_id = {
        profile.profile_id: profile
        for profile in list_profiles(PROJECT_ROOT / "profiles")
    }

    referenced_profile_ids = {
        profile_id
        for entry in registry_entries
        for profile_id in entry.supported_profiles
    }
    referenced_profile_ids.update(entry.profile_id for entry in matrix_entries)

    assert referenced_profile_ids <= set(profiles_by_id)


def _env_example_entries(path: Path) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        key, separator, value = stripped.partition("=")
        assert separator == "="
        entries.append((key, value))

    return entries
