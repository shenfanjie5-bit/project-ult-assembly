"""Bootstrap planning and docker compose execution APIs."""

from __future__ import annotations

import os
from pathlib import Path

from assembly.bootstrap.plan import (
    BootstrapPlan,
    BootstrapPlanError,
    BootstrapService,
    build_plan,
)
from assembly.bootstrap.runner import (
    BootstrapResult,
    ComposeCommandError,
    DockerComposeUnavailableError,
    Runner,
)
from assembly.bootstrap.service_handle import ServiceHandle
from assembly.profiles.errors import ProfileNotFoundError
from assembly.profiles.loader import list_profiles
from assembly.profiles.resolver import resolve
from assembly.profiles.schema import EnvironmentProfile


def bootstrap(
    profile_id: str,
    *,
    profiles_root: Path = Path("profiles"),
    bundle_root: Path = Path("bundles"),
    compose_file: Path = Path("compose/lite-local.yaml"),
) -> BootstrapResult:
    """Resolve a profile fail-fast, build a plan, and start it."""

    profile = _load_profile_by_id(profile_id, profiles_root)
    resolve(profile, os.environ, bundle_root=bundle_root)
    plan = build_plan(profile, bundle_root=bundle_root, compose_file=compose_file)
    return Runner().start(plan)


def _load_profile_by_id(profile_id: str, profiles_root: Path) -> EnvironmentProfile:
    for profile in list_profiles(profiles_root):
        if profile.profile_id == profile_id:
            return profile

    raise ProfileNotFoundError(f"Profile id not found in {profiles_root}: {profile_id}")


__all__ = [
    "BootstrapPlan",
    "BootstrapPlanError",
    "BootstrapResult",
    "BootstrapService",
    "ComposeCommandError",
    "DockerComposeUnavailableError",
    "Runner",
    "ServiceHandle",
    "bootstrap",
    "build_plan",
]
