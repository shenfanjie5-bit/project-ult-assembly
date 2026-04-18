from __future__ import annotations

from pathlib import Path

import yaml

from assembly.profiles import list_profiles, load_bundle, load_profile, render_profile
from assembly.profiles.schema import ProfileMode

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROFILES_ROOT = PROJECT_ROOT / "profiles"
BUNDLES_ROOT = PROJECT_ROOT / "bundles"
COMPOSE_FILE = PROJECT_ROOT / "compose" / "full-dev.yaml"

OPTIONAL_BUNDLES = [
    "minio",
    "grafana",
    "superset",
    "temporal",
    "feast",
    "kafka-flink",
]
OPTIONAL_SERVICES = {
    "minio",
    "grafana",
    "superset",
    "temporal",
    "temporal-ui",
    "feast",
    "kafka",
    "flink-jobmanager",
    "flink-taskmanager",
}


def test_full_dev_profile_is_registered_with_core_bundles_only() -> None:
    profiles = {
        profile.profile_id: profile for profile in list_profiles(PROFILES_ROOT)
    }

    assert set(profiles) >= {"lite-local", "full-dev"}
    profile = profiles["full-dev"]
    assert profile.mode == ProfileMode.full
    assert profile.enabled_service_bundles == ["postgres", "neo4j", "dagster"]
    assert profile.max_long_running_daemons > 4
    assert set(OPTIONAL_BUNDLES).isdisjoint(profile.enabled_service_bundles)


def test_full_dev_default_render_resolves_only_core_bundles() -> None:
    profile = load_profile(PROFILES_ROOT / "full-dev.yaml")

    snapshot = render_profile(
        "full-dev",
        profiles_root=PROFILES_ROOT,
        bundles_root=BUNDLES_ROOT,
        env=_required_env(profile.required_env_keys),
    )

    assert snapshot.enabled_service_bundles == ["postgres", "neo4j", "dagster"]
    assert [bundle.bundle_name for bundle in snapshot.service_bundles] == [
        "postgres",
        "neo4j",
        "dagster",
    ]
    assert set(snapshot.storage_backends) == {
        "postgres",
        "neo4j",
        "dagster_home",
    }
    assert "minio" not in snapshot.storage_backends


def test_full_dev_minio_backend_requires_selected_bundle() -> None:
    profile = load_profile(PROFILES_ROOT / "full-dev.yaml")
    env = _required_env(profile.required_env_keys)
    env.update(
        {
            "MINIO_ROOT_USER": "assembly-minio-user",
            "MINIO_ROOT_PASSWORD": "assembly-minio-password",
        }
    )

    snapshot = render_profile(
        "full-dev",
        profiles_root=PROFILES_ROOT,
        bundles_root=BUNDLES_ROOT,
        env=env,
        extra_bundles=["minio"],
    )

    assert snapshot.enabled_service_bundles == [
        "postgres",
        "neo4j",
        "dagster",
        "minio",
    ]
    assert snapshot.storage_backends["minio"] == {
        "kind": "minio",
        "connection": {
            "endpoint_env": "MINIO_PORT",
            "root_user_env": "MINIO_ROOT_USER",
            "root_password_env": "MINIO_ROOT_PASSWORD",
        },
    }


def test_full_dev_optional_bundle_manifests_are_closed() -> None:
    for bundle_name in OPTIONAL_BUNDLES:
        bundle = load_bundle(BUNDLES_ROOT / f"{bundle_name}.yaml")
        service_names = [service.name for service in bundle.services]
        service_probes = [service.health_probe for service in bundle.services]

        assert bundle.bundle_name == bundle_name
        assert bundle.optional is True
        assert bundle.required_profiles == ["full-dev"]
        assert bundle.startup_order == service_names
        assert sorted(bundle.shutdown_order) == sorted(service_names)
        assert bundle.health_checks == service_probes


def test_full_dev_optional_secret_env_has_no_literal_fallbacks() -> None:
    forbidden_fallbacks = {
        ("MINIO_ROOT_USER", ":-"),
        ("MINIO_ROOT_PASSWORD", ":-"),
        ("GRAFANA_ADMIN_USER", ":-admin"),
        ("GRAFANA_ADMIN_PASSWORD", ":-admin"),
        ("SUPERSET_SECRET_KEY", ":-"),
    }
    checked_paths = [
        COMPOSE_FILE,
        BUNDLES_ROOT / "minio.yaml",
        BUNDLES_ROOT / "grafana.yaml",
        BUNDLES_ROOT / "superset.yaml",
    ]

    for path in checked_paths:
        text = path.read_text(encoding="utf-8")
        assert all(
            f"{key}{suffix}" not in text for key, suffix in forbidden_fallbacks
        )

    compose = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
    assert compose["services"]["minio"]["environment"] == {
        "MINIO_ROOT_USER": "${MINIO_ROOT_USER}",
        "MINIO_ROOT_PASSWORD": "${MINIO_ROOT_PASSWORD}",
    }
    assert compose["services"]["grafana"]["environment"] == {
        "GF_SECURITY_ADMIN_USER": "${GRAFANA_ADMIN_USER}",
        "GF_SECURITY_ADMIN_PASSWORD": "${GRAFANA_ADMIN_PASSWORD}",
    }
    assert compose["services"]["superset"]["environment"]["SUPERSET_SECRET_KEY"] == (
        "${SUPERSET_SECRET_KEY}"
    )


def test_full_dev_compose_contains_core_and_optional_services() -> None:
    raw = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
    services = set(raw["services"])

    assert {
        "postgres",
        "neo4j",
        "dagster-daemon",
        "dagster-webserver",
    } <= services
    assert OPTIONAL_SERVICES <= services
    assert {"duckdb", "dbt", "iceberg", "milvus"}.isdisjoint(services)


def _required_env(keys: list[str]) -> dict[str, str]:
    values = {key: f"value-for-{key.lower()}" for key in keys}
    values.update(
        {
            "POSTGRES_HOST": "127.0.0.1",
            "POSTGRES_PORT": "5432",
            "NEO4J_URI": "bolt://127.0.0.1:7687",
            "DAGSTER_HOST": "127.0.0.1",
            "DAGSTER_PORT": "3000",
        }
    )
    return values
