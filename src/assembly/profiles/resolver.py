"""Resolve environment profiles into concrete configuration snapshots."""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict

from assembly.profiles.errors import (
    ProfileConstraintError,
    ProfileEnvMissingError,
    ProfileSchemaError,
)
from assembly.profiles.loader import list_profiles, load_bundle
from assembly.profiles.schema import (
    EnvironmentProfile,
    ProfileMode,
    ServiceBundleManifest,
)

_REDACTED_VALUE = "<redacted>"
_SENSITIVE_KEY_PARTS = ("PASSWORD", "SECRET", "TOKEN")


class ResolvedConfigSnapshot(BaseModel):
    """Fully resolved profile configuration safe to pass to bootstrap."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str
    mode: str
    enabled_modules: list[str]
    enabled_service_bundles: list[str]
    required_env: dict[str, str]
    optional_env: dict[str, str | None]
    storage_backends: dict[str, Any]
    resource_expectation: dict[str, Any]
    max_long_running_daemons: int
    service_bundles: list[ServiceBundleManifest]
    resolved_at: datetime

    def dump(self, path: Path) -> None:
        """Write a redacted UTF-8 JSON representation of the snapshot."""

        payload = _redact_sensitive_values(self.model_dump(mode="json"))
        Path(path).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def resolve(
    profile: EnvironmentProfile,
    env: Mapping[str, str],
    *,
    bundle_root: Path = Path("bundles"),
) -> ResolvedConfigSnapshot:
    """Resolve a loaded profile against env and referenced service bundles."""

    missing_keys = [key for key in profile.required_env_keys if key not in env]
    if missing_keys:
        raise ProfileEnvMissingError(
            "Missing required environment keys for "
            f"{profile.profile_id}: {', '.join(missing_keys)}"
        )

    service_bundles = [
        _load_profile_bundle(profile, bundle_name, bundle_root)
        for bundle_name in profile.enabled_service_bundles
    ]
    _enforce_lite_service_count(profile, service_bundles)

    return ResolvedConfigSnapshot(
        profile_id=profile.profile_id,
        mode=profile.mode.value,
        enabled_modules=list(profile.enabled_modules),
        enabled_service_bundles=list(profile.enabled_service_bundles),
        required_env={key: env[key] for key in profile.required_env_keys},
        optional_env={key: env.get(key) for key in profile.optional_env_keys},
        storage_backends={
            name: backend.model_dump(mode="json")
            for name, backend in profile.storage_backends.items()
        },
        resource_expectation=profile.resource_expectation.model_dump(mode="json"),
        max_long_running_daemons=profile.max_long_running_daemons,
        service_bundles=service_bundles,
        resolved_at=datetime.now(timezone.utc),
    )


def render_profile(
    profile_id: str,
    *,
    profiles_root: Path = Path("profiles"),
    bundles_root: Path = Path("bundles"),
    env: Mapping[str, str] | None = None,
) -> ResolvedConfigSnapshot:
    """Load a named profile artifact and resolve it against an environment."""

    profile = _find_profile(profile_id, profiles_root)
    return resolve(profile, os.environ if env is None else env, bundle_root=bundles_root)


def _find_profile(profile_id: str, profiles_root: Path) -> EnvironmentProfile:
    for profile in list_profiles(profiles_root):
        if profile.profile_id == profile_id:
            return profile

    from assembly.profiles.loader import load_profile

    return load_profile(Path(profiles_root) / f"{profile_id}.yaml")


def _load_profile_bundle(
    profile: EnvironmentProfile,
    bundle_name: str,
    bundle_root: Path,
) -> ServiceBundleManifest:
    bundle = load_bundle(Path(bundle_root) / f"{bundle_name}.yaml")
    if bundle.bundle_name != bundle_name:
        raise ProfileSchemaError(
            f"Bundle manifest {bundle_name!r} declares bundle_name "
            f"{bundle.bundle_name!r}"
        )

    if profile.profile_id not in bundle.required_profiles:
        raise ProfileConstraintError(
            f"Bundle {bundle.bundle_name} is not declared for profile "
            f"{profile.profile_id}"
        )

    return bundle


def _enforce_lite_service_count(
    profile: EnvironmentProfile,
    service_bundles: list[ServiceBundleManifest],
) -> None:
    if profile.mode != ProfileMode.lite:
        return

    service_names = [
        service.name for bundle in service_bundles for service in bundle.services
    ]
    duplicate_names = sorted(
        name for name, count in Counter(service_names).items() if count > 1
    )
    if duplicate_names:
        raise ProfileConstraintError(
            f"Duplicate service names for {profile.profile_id}: {duplicate_names}"
        )

    if len(service_names) != profile.max_long_running_daemons:
        raise ProfileConstraintError(
            f"Lite profile {profile.profile_id} resolves {len(service_names)} "
            "long-running services; expected "
            f"{profile.max_long_running_daemons}"
        )


def _redact_sensitive_values(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, child in value.items():
            if _is_sensitive_key(str(key)):
                redacted[key] = _REDACTED_VALUE
            else:
                redacted[key] = _redact_sensitive_values(child)
        return redacted

    if isinstance(value, list):
        return [_redact_sensitive_values(child) for child in value]

    return value


def _is_sensitive_key(key: str) -> bool:
    upper_key = key.upper()
    return any(part in upper_key for part in _SENSITIVE_KEY_PARTS)
