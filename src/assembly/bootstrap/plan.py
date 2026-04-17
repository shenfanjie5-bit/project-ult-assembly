"""Bootstrap plan construction from profile and service bundle artifacts."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
import re
import shlex
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from assembly.profiles.errors import ProfileError
from assembly.profiles.loader import load_bundle
from assembly.profiles.schema import (
    EnvironmentProfile,
    ProfileMode,
    ServiceBundleManifest,
    ServiceSpec,
)


_ENV_REF_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::?[-?=+][^}]*)?\}")


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

    compose_services = _load_compose_services(compose_file)
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

        _validate_bundle_health_checks(bundle)
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

            service_spec = service_specs[service_name]
            _validate_compose_service_matches_bundle(
                service=service_spec,
                compose_service=compose_services[service_name],
                previous_services=set(startup_order),
                profile=profile,
                compose_file=compose_file,
            )
            service = _bootstrap_service(
                bundle_name=bundle.bundle_name,
                service=service_spec,
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
    _validate_shutdown_respects_dependencies(
        shutdown_order,
        compose_services,
        compose_file,
    )
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


def _load_compose_services(compose_file: Path) -> dict[str, dict[str, object]]:
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

    normalized: dict[str, dict[str, object]] = {}
    for name, service_config in services.items():
        if not isinstance(service_config, dict):
            raise BootstrapPlanError(
                f"Compose service {name!r} in {compose_file} must be a mapping"
            )
        normalized[str(name)] = service_config

    return normalized


def _validate_bundle_health_checks(bundle: ServiceBundleManifest) -> None:
    service_probes = Counter(service.health_probe for service in bundle.services)
    bundle_probes = Counter(bundle.health_checks)
    if service_probes != bundle_probes:
        raise BootstrapPlanError(
            f"Bundle {bundle.bundle_name} health_checks must contain each "
            "service health_probe exactly once"
        )


def _validate_compose_service_matches_bundle(
    *,
    service: ServiceSpec,
    compose_service: dict[str, object],
    previous_services: set[str],
    profile: EnvironmentProfile,
    compose_file: Path,
) -> None:
    _validate_image_or_command(service, compose_service, compose_file)
    _validate_environment(service, compose_service, profile, compose_file)
    _validate_health_probe(service, compose_service, compose_file)
    _validate_startup_dependencies(
        service.name,
        compose_service,
        previous_services,
        compose_file,
    )


def _validate_image_or_command(
    service: ServiceSpec,
    compose_service: dict[str, object],
    compose_file: Path,
) -> None:
    compose_image = compose_service.get("image")
    command_name = _compose_command_name(compose_service.get("command"))
    matches_image = (
        isinstance(compose_image, str) and compose_image == service.image_or_cmd
    )
    matches_command = command_name == service.image_or_cmd
    if matches_image or matches_command:
        return

    raise BootstrapPlanError(
        f"Compose service {service.name!r} in {compose_file} does not match "
        f"bundle image_or_cmd {service.image_or_cmd!r}"
    )


def _validate_environment(
    service: ServiceSpec,
    compose_service: dict[str, object],
    profile: EnvironmentProfile,
    compose_file: Path,
) -> None:
    compose_env = _compose_environment(
        compose_service.get("environment"),
        service.name,
    )
    if compose_env != service.env:
        raise BootstrapPlanError(
            f"Compose service {service.name!r} in {compose_file} environment "
            "does not match bundle env"
        )

    profile_env_keys = set(profile.required_env_keys) | set(profile.optional_env_keys)
    unknown_refs = sorted(_env_refs(service.env.values()) - profile_env_keys)
    if unknown_refs:
        raise BootstrapPlanError(
            f"Bundle service {service.name!r} references env keys not declared "
            f"by profile {profile.profile_id}: {', '.join(unknown_refs)}"
        )


def _validate_health_probe(
    service: ServiceSpec,
    compose_service: dict[str, object],
    compose_file: Path,
) -> None:
    compose_probe = _compose_health_probe(compose_service, service.name)
    if compose_probe == service.health_probe:
        return

    raise BootstrapPlanError(
        f"Compose service {service.name!r} in {compose_file} healthcheck does "
        "not match bundle health_probe"
    )


def _validate_startup_dependencies(
    service_name: str,
    compose_service: dict[str, object],
    previous_services: set[str],
    compose_file: Path,
) -> None:
    dependencies = _compose_dependencies(compose_service, service_name, compose_file)
    invalid_dependencies = sorted(set(dependencies) - previous_services)
    if invalid_dependencies:
        raise BootstrapPlanError(
            f"Compose service {service_name!r} in {compose_file} depends on "
            "services that are not earlier in startup_order: "
            f"{', '.join(invalid_dependencies)}"
        )


def _compose_command_name(command: object) -> str | None:
    if command is None:
        return None

    if isinstance(command, str):
        try:
            parts = shlex.split(command)
        except ValueError:
            parts = command.split()
        return parts[0] if parts else None

    if isinstance(command, Sequence) and not isinstance(command, (str, bytes)):
        return str(command[0]) if command else None

    return None


def _compose_environment(environment: object, service_name: str) -> dict[str, str]:
    if environment is None:
        return {}

    if isinstance(environment, Mapping):
        return {
            str(key): "" if value is None else str(value)
            for key, value in environment.items()
        }

    if isinstance(environment, Sequence) and not isinstance(environment, (str, bytes)):
        values: dict[str, str] = {}
        for entry in environment:
            key, separator, value = str(entry).partition("=")
            values[key] = value if separator else ""
        return values

    raise BootstrapPlanError(
        f"Compose service {service_name!r} environment must be a mapping or list"
    )


def _compose_health_probe(
    compose_service: dict[str, object],
    service_name: str,
) -> str:
    healthcheck = compose_service.get("healthcheck")
    if not isinstance(healthcheck, Mapping):
        raise BootstrapPlanError(
            f"Compose service {service_name!r} must define a healthcheck mapping"
        )

    test = healthcheck.get("test")
    if isinstance(test, str):
        return test

    if isinstance(test, Sequence) and not isinstance(test, (str, bytes)):
        parts = [str(part) for part in test]
        if not parts:
            raise BootstrapPlanError(
                f"Compose service {service_name!r} healthcheck test cannot be empty"
            )
        if parts[0] in {"CMD", "CMD-SHELL"}:
            return " ".join(parts[1:])
        return " ".join(parts)

    raise BootstrapPlanError(
        f"Compose service {service_name!r} healthcheck test must be a string or list"
    )


def _compose_dependencies(
    compose_service: dict[str, object],
    service_name: str,
    compose_file: Path,
) -> list[str]:
    depends_on = compose_service.get("depends_on")
    if depends_on is None:
        return []

    if isinstance(depends_on, Sequence) and not isinstance(depends_on, (str, bytes)):
        return [str(dependency) for dependency in depends_on]

    if not isinstance(depends_on, Mapping):
        raise BootstrapPlanError(
            f"Compose service {service_name!r} in {compose_file} depends_on "
            "must be a mapping or list"
        )

    dependencies: list[str] = []
    for dependency, condition_config in depends_on.items():
        dependencies.append(str(dependency))
        if isinstance(condition_config, Mapping):
            condition = condition_config.get("condition")
            if condition != "service_healthy":
                raise BootstrapPlanError(
                    f"Compose service {service_name!r} in {compose_file} "
                    f"depends on {dependency!r} without service_healthy"
                )

    return dependencies


def _env_refs(values: object) -> set[str]:
    refs: set[str] = set()
    if isinstance(values, str):
        refs.update(match.group(1) for match in _ENV_REF_PATTERN.finditer(values))
    elif isinstance(values, Mapping):
        for value in values.values():
            refs.update(_env_refs(value))
    elif isinstance(values, Sequence) and not isinstance(values, (str, bytes)):
        for value in values:
            refs.update(_env_refs(value))
    return refs


def _validate_shutdown_order(startup_order: list[str], shutdown_order: list[str]) -> None:
    if Counter(startup_order) != Counter(shutdown_order):
        raise BootstrapPlanError(
            "Bootstrap shutdown_order must contain the same services as startup_order"
        )


def _validate_shutdown_respects_dependencies(
    shutdown_order: list[str],
    compose_services: dict[str, dict[str, object]],
    compose_file: Path,
) -> None:
    shutdown_position = {
        service_name: index for index, service_name in enumerate(shutdown_order)
    }
    for service_name in shutdown_order:
        dependencies = _compose_dependencies(
            compose_services[service_name],
            service_name,
            compose_file,
        )
        for dependency in dependencies:
            if dependency not in shutdown_position:
                continue
            if shutdown_position[service_name] > shutdown_position[dependency]:
                raise BootstrapPlanError(
                    f"Bootstrap shutdown_order must stop {service_name!r} "
                    f"before dependency {dependency!r}"
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
