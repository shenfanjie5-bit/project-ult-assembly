"""Bootstrap plan construction from profile and service bundle artifacts."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from assembly.profiles.errors import ProfileError
from assembly.profiles.loader import load_bundle
from assembly.profiles.schema import EnvironmentProfile, ProfileMode, ServiceSpec


class BootstrapPlanError(Exception):
    """Raised when bootstrap artifacts cannot produce a valid plan."""


class BootstrapService(BaseModel):
    """Single long-running service included in a bootstrap plan."""

    model_config = ConfigDict(extra="forbid")

    name: str
    bundle_name: str
    compose_service: str
    image_or_cmd: str
    health_probe: str


class BootstrapPlan(BaseModel):
    """Ordered service plan for docker compose bootstrap and shutdown."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str
    mode: str
    compose_file: Path
    services: list[BootstrapService]
    startup_order: list[str]
    shutdown_order: list[str]


def build_plan(
    profile: EnvironmentProfile,
    *,
    bundle_root: Path = Path("bundles"),
    compose_file: Path = Path("compose/lite-local.yaml"),
) -> BootstrapPlan:
    """Build an ordered bootstrap plan from enabled service bundles."""

    compose_services = _load_compose_service_names(compose_file)
    services_by_name: dict[str, BootstrapService] = {}
    startup_order: list[str] = []
    shutdown_order: list[str] = []

    for bundle_name in profile.enabled_service_bundles:
        bundle_path = Path(bundle_root) / f"{bundle_name}.yaml"
        try:
            bundle = load_bundle(bundle_path)
        except ProfileError as exc:
            raise BootstrapPlanError(
                f"Unable to load bundle {bundle_name!r} from {bundle_path}: {exc}"
            ) from exc

        if bundle.bundle_name != bundle_name:
            raise BootstrapPlanError(
                f"Bundle artifact {bundle_path} declares bundle_name "
                f"{bundle.bundle_name!r}, expected {bundle_name!r}"
            )

        if profile.profile_id not in bundle.required_profiles:
            raise BootstrapPlanError(
                f"Bundle {bundle.bundle_name} is not required by profile "
                f"{profile.profile_id}"
            )

        if bundle.optional:
            raise BootstrapPlanError(
                f"Bundle {bundle.bundle_name} is optional and cannot be part of "
                f"the {profile.profile_id} bootstrap plan"
            )

        service_specs = {service.name: service for service in bundle.services}
        for service_name in bundle.startup_order:
            if service_name in services_by_name:
                raise BootstrapPlanError(
                    f"Duplicate bootstrap service name {service_name!r}"
                )
            if service_name not in compose_services:
                raise BootstrapPlanError(
                    f"Compose file {compose_file} does not define service "
                    f"{service_name!r}"
                )

            service = _bootstrap_service(
                bundle_name=bundle.bundle_name,
                service=service_specs[service_name],
            )
            services_by_name[service.name] = service
            startup_order.append(service.name)

    for bundle_name in reversed(profile.enabled_service_bundles):
        bundle_path = Path(bundle_root) / f"{bundle_name}.yaml"
        try:
            bundle = load_bundle(bundle_path)
        except ProfileError as exc:
            raise BootstrapPlanError(
                f"Unable to load bundle {bundle_name!r} from {bundle_path}: {exc}"
            ) from exc

        shutdown_order.extend(bundle.shutdown_order)

    _validate_shutdown_order(startup_order, shutdown_order)
    _validate_lite_service_count(profile, startup_order)

    return BootstrapPlan(
        profile_id=profile.profile_id,
        mode=profile.mode.value,
        compose_file=Path(compose_file),
        services=[services_by_name[name] for name in startup_order],
        startup_order=startup_order,
        shutdown_order=shutdown_order,
    )


def _bootstrap_service(
    *,
    bundle_name: str,
    service: ServiceSpec,
) -> BootstrapService:
    return BootstrapService(
        name=service.name,
        bundle_name=bundle_name,
        compose_service=service.name,
        image_or_cmd=service.image_or_cmd,
        health_probe=service.health_probe,
    )


def _load_compose_service_names(compose_file: Path) -> set[str]:
    compose_file = Path(compose_file)
    if not compose_file.exists():
        raise BootstrapPlanError(f"Compose artifact not found: {compose_file}")

    try:
        raw = yaml.safe_load(compose_file.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise BootstrapPlanError(f"Invalid compose YAML in {compose_file}: {exc}") from exc

    if not isinstance(raw, dict):
        raise BootstrapPlanError(
            f"Compose artifact {compose_file} must have a mapping root"
        )

    services = raw.get("services")
    if not isinstance(services, dict):
        raise BootstrapPlanError(
            f"Compose artifact {compose_file} must define a services mapping"
        )

    return {str(name) for name in services}


def _validate_shutdown_order(startup_order: list[str], shutdown_order: list[str]) -> None:
    if Counter(startup_order) != Counter(shutdown_order):
        raise BootstrapPlanError(
            "Bootstrap shutdown_order must contain the same services as startup_order"
        )


def _validate_lite_service_count(
    profile: EnvironmentProfile,
    startup_order: list[str],
) -> None:
    if profile.mode != ProfileMode.lite:
        return

    if len(startup_order) != profile.max_long_running_daemons:
        raise BootstrapPlanError(
            f"Lite profile {profile.profile_id} plans {len(startup_order)} "
            "long-running services; expected "
            f"{profile.max_long_running_daemons}"
        )
