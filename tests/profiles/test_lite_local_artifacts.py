from __future__ import annotations

from pathlib import Path

import yaml

from assembly.profiles import list_profiles, load_bundle, load_profile
from assembly.profiles.schema import ProfileMode
from assembly.registry import CompatibilityMatrixEntry, load_registry_yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = PROJECT_ROOT / "profiles" / "lite-local.yaml"
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


def test_optional_bundles_are_not_declared_for_lite_local() -> None:
    for bundle_name in OPTIONAL_FULL_BUNDLES:
        bundle = load_bundle(BUNDLES_ROOT / f"{bundle_name}.yaml")

        assert bundle.optional is True
        assert bundle.required_profiles == ["full-dev"]
        assert "lite-local" not in bundle.required_profiles


def test_lite_local_modules_cover_registry_supported_modules() -> None:
    profile = load_profile(PROFILE_PATH)
    registry_entries = load_registry_yaml(REGISTRY_YAML)
    registry_module_ids = {entry.module_id for entry in registry_entries}
    lite_module_ids = {
        entry.module_id
        for entry in registry_entries
        if profile.profile_id in entry.supported_profiles
    }

    assert set(profile.enabled_modules) <= registry_module_ids
    assert set(profile.enabled_modules) == lite_module_ids
    assert len(profile.enabled_modules) == 14


def test_env_example_matches_lite_local_env_keys_exactly() -> None:
    profile = load_profile(PROFILE_PATH)

    assert _env_example_keys(ENV_EXAMPLE) == [
        *profile.required_env_keys,
        *profile.optional_env_keys,
    ]


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


def _env_example_keys(path: Path) -> list[str]:
    keys: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        key, separator, _ = stripped.partition("=")
        assert separator == "="
        keys.append(key)

    return keys
