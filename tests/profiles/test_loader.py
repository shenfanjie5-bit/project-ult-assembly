from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from assembly.profiles import (
    EnvironmentProfile,
    ServiceBundleManifest,
    list_bundles,
    list_profiles,
    load_bundle,
    load_profile,
)
from assembly.profiles.errors import ProfileNotFoundError, ProfileSchemaError


def valid_profile_data(profile_id: str = "lite-local") -> dict[str, object]:
    return {
        "profile_id": profile_id,
        "mode": "lite",
        "enabled_modules": ["assembly"],
        "enabled_service_bundles": ["core-services"],
        "required_env_keys": ["DATABASE_URL"],
        "optional_env_keys": [],
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
        "notes": "loader test profile",
    }


def valid_bundle_data(bundle_name: str = "core-services") -> dict[str, object]:
    return {
        "bundle_name": bundle_name,
        "services": [
            {
                "name": "postgres",
                "image_or_cmd": "postgres:16",
                "health_probe": "pg_isready",
                "env": {},
            }
        ],
        "startup_order": ["postgres"],
        "shutdown_order": ["postgres"],
        "health_checks": ["pg_isready"],
        "required_profiles": ["lite-local"],
        "optional": False,
    }


def write_yaml(path: Path, data: dict[str, object]) -> Path:
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_load_profile_reads_yaml_file(tmp_path: Path) -> None:
    path = write_yaml(tmp_path / "lite-local.yaml", valid_profile_data())

    profile = load_profile(path)

    assert isinstance(profile, EnvironmentProfile)
    assert profile.profile_id == "lite-local"


def test_load_profile_reads_yml_file(tmp_path: Path) -> None:
    path = write_yaml(tmp_path / "lite-local.yml", valid_profile_data())

    profile = load_profile(path)

    assert profile.profile_id == "lite-local"


def test_load_bundle_reads_yaml_file(tmp_path: Path) -> None:
    path = write_yaml(tmp_path / "core-services.yaml", valid_bundle_data())

    bundle = load_bundle(path)

    assert isinstance(bundle, ServiceBundleManifest)
    assert bundle.bundle_name == "core-services"


def test_load_bundle_reads_yml_file(tmp_path: Path) -> None:
    path = write_yaml(tmp_path / "core-services.yml", valid_bundle_data())

    bundle = load_bundle(path)

    assert bundle.services[0].name == "postgres"


def test_missing_profile_file_raises_profile_not_found(tmp_path: Path) -> None:
    with pytest.raises(ProfileNotFoundError):
        load_profile(tmp_path / "missing.yaml")


def test_yaml_syntax_error_raises_schema_error_with_line_number(
    tmp_path: Path,
) -> None:
    path = tmp_path / "broken.yaml"
    path.write_text("profile_id: lite-local\nmode: [lite\n", encoding="utf-8")

    with pytest.raises(ProfileSchemaError) as exc_info:
        load_profile(path)

    message = str(exc_info.value)
    assert "Invalid YAML" in message
    assert "line" in message


def test_schema_error_is_wrapped_as_profile_schema_error(tmp_path: Path) -> None:
    path = write_yaml(
        tmp_path / "bad-profile.yaml",
        valid_profile_data(profile_id="Lite-Local"),
    )

    with pytest.raises(ProfileSchemaError) as exc_info:
        load_profile(path)

    assert "profile_id" in str(exc_info.value)


def test_lite_daemon_constraint_error_is_wrapped_by_loader(tmp_path: Path) -> None:
    data = valid_profile_data()
    data["max_long_running_daemons"] = 5
    path = write_yaml(tmp_path / "bad-daemons.yaml", data)

    with pytest.raises(ProfileSchemaError) as exc_info:
        load_profile(path)

    assert "max_long_running_daemons" in str(exc_info.value)


def test_list_profiles_returns_empty_list_for_empty_directory(tmp_path: Path) -> None:
    assert list_profiles(tmp_path) == []


def test_list_profiles_loads_yaml_and_yml_files(tmp_path: Path) -> None:
    write_yaml(tmp_path / "b-profile.yml", valid_profile_data("lite-b"))
    write_yaml(tmp_path / "a-profile.yaml", valid_profile_data("lite-a"))
    (tmp_path / "README.md").write_text("ignored", encoding="utf-8")

    profiles = list_profiles(tmp_path)

    assert [profile.profile_id for profile in profiles] == ["lite-a", "lite-b"]


def test_list_bundles_returns_empty_list_for_empty_directory(tmp_path: Path) -> None:
    assert list_bundles(tmp_path) == []


def test_non_mapping_yaml_root_raises_schema_error(tmp_path: Path) -> None:
    path = tmp_path / "profile.yaml"
    path.write_text("- not\n- a\n- mapping\n", encoding="utf-8")

    with pytest.raises(ProfileSchemaError) as exc_info:
        load_profile(path)

    assert "YAML root must be a mapping" in str(exc_info.value)

