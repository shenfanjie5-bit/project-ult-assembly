from __future__ import annotations

import json
from pathlib import Path

import pytest

from assembly.profiles import (
    ProfileConstraintError,
    ProfileEnvMissingError,
    render_profile,
    resolve,
    with_extra_bundles,
)
from assembly.profiles.loader import load_profile

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROFILES_ROOT = PROJECT_ROOT / "profiles"
BUNDLES_ROOT = PROJECT_ROOT / "bundles"
PROFILE_PATH = PROFILES_ROOT / "lite-local.yaml"


def test_resolve_lite_local_profile_successfully_loads_bundles() -> None:
    profile = load_profile(PROFILE_PATH)
    env = _required_env(profile.required_env_keys)

    snapshot = resolve(profile, env, bundle_root=BUNDLES_ROOT)

    assert snapshot.profile_id == "lite-local"
    assert snapshot.mode == "lite"
    assert snapshot.required_env == env
    assert snapshot.optional_env == {
        key: None for key in profile.optional_env_keys
    }
    assert [bundle.bundle_name for bundle in snapshot.service_bundles] == [
        "postgres",
        "neo4j",
        "dagster",
    ]
    assert sum(len(bundle.services) for bundle in snapshot.service_bundles) == 4


def test_render_profile_loads_profile_by_public_id() -> None:
    profile = load_profile(PROFILE_PATH)
    env = _required_env(profile.required_env_keys)

    snapshot = render_profile(
        "lite-local",
        profiles_root=PROFILES_ROOT,
        bundles_root=BUNDLES_ROOT,
        env=env,
    )

    assert snapshot.profile_id == profile.profile_id
    assert snapshot.enabled_service_bundles == ["postgres", "neo4j", "dagster"]


def test_render_profile_merges_full_extra_bundles_in_order() -> None:
    profile = load_profile(PROFILES_ROOT / "full-dev.yaml")
    env = _required_env(profile.required_env_keys)

    snapshot = render_profile(
        "full-dev",
        profiles_root=PROFILES_ROOT,
        bundles_root=BUNDLES_ROOT,
        env=env,
        extra_bundles=["grafana", "superset"],
    )

    assert snapshot.enabled_service_bundles == [
        "postgres",
        "neo4j",
        "dagster",
        "grafana",
        "superset",
    ]
    assert [bundle.bundle_name for bundle in snapshot.service_bundles] == [
        "postgres",
        "neo4j",
        "dagster",
        "grafana",
        "superset",
    ]


def test_with_extra_bundles_returns_copy_without_mutating_profile() -> None:
    profile = load_profile(PROFILES_ROOT / "full-dev.yaml")

    updated = with_extra_bundles(
        profile,
        ["grafana"],
        bundle_root=BUNDLES_ROOT,
    )

    assert updated is not profile
    assert profile.enabled_service_bundles == ["postgres", "neo4j", "dagster"]
    assert updated.enabled_service_bundles == [
        "postgres",
        "neo4j",
        "dagster",
        "grafana",
    ]


def test_with_extra_bundles_rejects_duplicate_and_unknown_bundles() -> None:
    profile = load_profile(PROFILES_ROOT / "full-dev.yaml")

    with pytest.raises(ProfileConstraintError, match="Duplicate"):
        with_extra_bundles(profile, ["grafana", "grafana"], bundle_root=BUNDLES_ROOT)

    with pytest.raises(ProfileConstraintError, match="Unknown extra bundle"):
        with_extra_bundles(profile, ["missing"], bundle_root=BUNDLES_ROOT)


def test_lite_profile_rejects_optional_extra_bundle() -> None:
    profile = load_profile(PROFILE_PATH)

    with pytest.raises(ProfileConstraintError, match="Lite profile.*optional"):
        with_extra_bundles(profile, ["grafana"], bundle_root=BUNDLES_ROOT)


def test_resolve_missing_required_env_fails_fast_with_all_missing_keys() -> None:
    profile = load_profile(PROFILE_PATH)
    env = _required_env(profile.required_env_keys)
    env.pop("POSTGRES_PASSWORD")
    env.pop("NEO4J_PASSWORD")

    with pytest.raises(ProfileEnvMissingError) as exc_info:
        resolve(profile, env, bundle_root=BUNDLES_ROOT)

    message = str(exc_info.value)
    assert "POSTGRES_PASSWORD" in message
    assert "NEO4J_PASSWORD" in message


def test_resolve_preserves_optional_env_values_when_present() -> None:
    profile = load_profile(PROFILE_PATH)
    env = _required_env(profile.required_env_keys)
    env["ASSEMBLY_LOG_LEVEL"] = "debug"
    env["ASSEMBLY_SERVICE_TOKEN"] = "service-token"

    snapshot = resolve(profile, env, bundle_root=BUNDLES_ROOT)

    assert snapshot.optional_env == {
        "ASSEMBLY_LOG_LEVEL": "debug",
        "ASSEMBLY_SERVICE_TOKEN": "service-token",
    }


def test_snapshot_dump_writes_redacted_utf8_json(tmp_path: Path) -> None:
    profile = load_profile(PROFILE_PATH)
    env = _required_env(profile.required_env_keys)
    env["POSTGRES_PASSWORD"] = "plain-postgres-password"
    env["NEO4J_PASSWORD"] = "plain-neo4j-password"
    env["ASSEMBLY_SERVICE_TOKEN"] = "plain-service-token"
    snapshot = resolve(profile, env, bundle_root=BUNDLES_ROOT)
    out = tmp_path / "lite-local-resolved-config.json"

    snapshot.dump(out)

    text = out.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert payload["profile_id"] == "lite-local"
    assert "POSTGRES_PASSWORD" in payload["required_env"]
    assert payload["required_env"]["POSTGRES_PASSWORD"] == "<redacted>"
    assert payload["required_env"]["NEO4J_PASSWORD"] == "<redacted>"
    assert payload["optional_env"]["ASSEMBLY_SERVICE_TOKEN"] == "<redacted>"
    assert "plain-postgres-password" not in text
    assert "plain-neo4j-password" not in text
    assert "plain-service-token" not in text


def _required_env(keys: list[str]) -> dict[str, str]:
    return {key: f"value-for-{key.lower()}" for key in keys}
