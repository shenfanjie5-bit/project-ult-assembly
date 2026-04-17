"""Bootstrap planning and docker compose execution APIs."""

from __future__ import annotations

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
from assembly.profiles.loader import load_profile
from assembly.profiles.resolver import render_profile


def bootstrap(
    profile_id: str,
    *,
    profiles_root: Path = Path("profiles"),
    bundle_root: Path = Path("bundles"),
    compose_file: Path = Path("compose/lite-local.yaml"),
) -> BootstrapResult:
    """Resolve a profile fail-fast, build a plan, and start it."""

    render_profile(profile_id, profiles_root=profiles_root, bundles_root=bundle_root)
    profile = load_profile(Path(profiles_root) / f"{profile_id}.yaml")
    plan = build_plan(profile, bundle_root=bundle_root, compose_file=compose_file)
    return Runner().start(plan)


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
