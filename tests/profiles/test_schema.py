from __future__ import annotations

import pytest
from pydantic import ValidationError

from assembly.profiles.errors import ProfileConstraintError
from assembly.profiles.schema import EnvironmentProfile, ServiceBundleManifest


def valid_profile_data(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "profile_id": "lite-local",
        "mode": "lite",
        "enabled_modules": ["assembly"],
        "enabled_service_bundles": ["core-services"],
        "required_env_keys": ["DATABASE_URL"],
        "optional_env_keys": ["LOG_LEVEL"],
        "storage_backends": {
            "primary": {
                "kind": "postgres",
                "connection": {"dsn_env": "DATABASE_URL"},
            }
        },
        "resource_expectation": {
            "cpu_cores": 2,
            "memory_gb": 4,
            "disk_gb": 20,
        },
        "max_long_running_daemons": 4,
        "notes": "schema test profile",
    }
    data.update(overrides)
    return data


def valid_bundle_data(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "bundle_name": "core-services",
        "services": [
            {
                "name": "postgres",
                "image_or_cmd": "postgres:16",
                "health_probe": "pg_isready",
            },
            {
                "name": "neo4j",
                "image_or_cmd": "neo4j:5",
                "health_probe": "cypher-shell RETURN 1",
                "env": {"NEO4J_AUTH": "none"},
            },
        ],
        "startup_order": ["postgres", "neo4j"],
        "shutdown_order": ["neo4j", "postgres"],
        "health_checks": ["pg_isready", "cypher-shell RETURN 1"],
        "required_profiles": ["lite-local"],
        "optional": False,
    }
    data.update(overrides)
    return data


def test_valid_lite_profile_validates() -> None:
    profile = EnvironmentProfile.model_validate(valid_profile_data())

    assert profile.profile_id == "lite-local"
    assert profile.max_long_running_daemons == 4


def test_lite_profile_requires_exactly_four_long_running_daemons() -> None:
    with pytest.raises(ProfileConstraintError):
        EnvironmentProfile.model_validate(
            valid_profile_data(max_long_running_daemons=5)
        )


def test_full_profile_can_use_different_daemon_cap() -> None:
    profile = EnvironmentProfile.model_validate(
        valid_profile_data(
            profile_id="full-dev",
            mode="full",
            max_long_running_daemons=8,
        )
    )

    assert profile.max_long_running_daemons == 8


def test_profile_id_rejects_uppercase() -> None:
    with pytest.raises(ValidationError):
        EnvironmentProfile.model_validate(valid_profile_data(profile_id="Lite-Local"))


def test_profile_id_rejects_leading_dash() -> None:
    with pytest.raises(ValidationError):
        EnvironmentProfile.model_validate(valid_profile_data(profile_id="-lite-local"))


def test_missing_required_profile_field_fails_validation() -> None:
    data = valid_profile_data()
    data.pop("enabled_service_bundles")

    with pytest.raises(ValidationError):
        EnvironmentProfile.model_validate(data)


def test_negative_resource_expectation_fails_validation() -> None:
    with pytest.raises(ValidationError):
        EnvironmentProfile.model_validate(
            valid_profile_data(
                resource_expectation={
                    "cpu_cores": -1,
                    "memory_gb": 4,
                    "disk_gb": 20,
                }
            )
        )


def test_storage_backend_kind_is_limited_to_known_values() -> None:
    with pytest.raises(ValidationError):
        EnvironmentProfile.model_validate(
            valid_profile_data(
                storage_backends={
                    "warehouse": {
                        "kind": "duckdb",
                        "connection": {"path": "local.duckdb"},
                    }
                }
            )
        )


def test_extra_profile_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EnvironmentProfile.model_validate(valid_profile_data(unexpected=True))


def test_valid_service_bundle_manifest_validates() -> None:
    bundle = ServiceBundleManifest.model_validate(valid_bundle_data())

    assert bundle.bundle_name == "core-services"
    assert [service.name for service in bundle.services] == ["postgres", "neo4j"]


def test_service_bundle_startup_order_must_match_service_names() -> None:
    with pytest.raises(ValidationError):
        ServiceBundleManifest.model_validate(
            valid_bundle_data(startup_order=["postgres", "dagster"])
        )


def test_service_bundle_rejects_duplicate_service_names_even_when_orders_match() -> None:
    data = valid_bundle_data(
        services=[
            {
                "name": "postgres",
                "image_or_cmd": "postgres:16",
                "health_probe": "pg_isready",
            },
            {
                "name": "postgres",
                "image_or_cmd": "postgres:16-replica",
                "health_probe": "pg_isready replica",
            },
        ],
        startup_order=["postgres", "postgres"],
        shutdown_order=["postgres", "postgres"],
        health_checks=["pg_isready", "pg_isready replica"],
    )

    with pytest.raises(ValidationError, match="unique service names"):
        ServiceBundleManifest.model_validate(data)


def test_service_bundle_shutdown_order_must_match_service_names() -> None:
    with pytest.raises(ValidationError):
        ServiceBundleManifest.model_validate(
            valid_bundle_data(shutdown_order=["neo4j"])
        )


def test_missing_required_bundle_field_fails_validation() -> None:
    data = valid_bundle_data()
    data.pop("health_checks")

    with pytest.raises(ValidationError):
        ServiceBundleManifest.model_validate(data)
