"""Pydantic schemas for assembly environment profiles and service bundles."""

from __future__ import annotations

from collections import Counter
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from assembly.profiles.errors import ProfileConstraintError


class ProfileMode(str, Enum):
    """Supported environment profile modes."""

    lite = "lite"
    full = "full"


class ResourceExpectation(BaseModel):
    """Baseline local resources expected by a profile."""

    model_config = ConfigDict(extra="forbid")

    cpu_cores: float = Field(ge=0)
    memory_gb: float = Field(ge=0)
    disk_gb: float = Field(ge=0)


class StorageBackend(BaseModel):
    """Storage backend declaration for a profile."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["postgres", "neo4j", "local_fs", "minio", "iceberg"]
    connection: dict[str, str]


class ServiceSpec(BaseModel):
    """Service entry inside a bundle manifest."""

    model_config = ConfigDict(extra="forbid")

    name: str
    image_or_cmd: str
    health_probe: str
    env: dict[str, str] = Field(default_factory=dict)


class ServiceBundleManifest(BaseModel):
    """Schema for a reusable service bundle manifest."""

    model_config = ConfigDict(extra="forbid")

    bundle_name: str
    services: list[ServiceSpec]
    startup_order: list[str]
    shutdown_order: list[str]
    health_checks: list[str]
    required_profiles: list[str]
    optional: bool

    @model_validator(mode="after")
    def enforce_service_order_matches_services(self) -> ServiceBundleManifest:
        service_names = [service.name for service in self.services]
        expected_names = Counter(service_names)
        startup_names = Counter(self.startup_order)
        shutdown_names = Counter(self.shutdown_order)

        if startup_names != expected_names or shutdown_names != expected_names:
            raise ValueError(
                "startup_order and shutdown_order must contain each service "
                "name exactly once"
            )

        return self


class EnvironmentProfile(BaseModel):
    """Schema for an assembly runtime profile."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    mode: ProfileMode
    enabled_modules: list[str]
    enabled_service_bundles: list[str]
    required_env_keys: list[str]
    optional_env_keys: list[str]
    storage_backends: dict[str, StorageBackend]
    resource_expectation: ResourceExpectation
    max_long_running_daemons: int = Field(ge=1)
    notes: str = ""

    @model_validator(mode="after")
    def enforce_lite_daemon_cap(self) -> EnvironmentProfile:
        if self.mode == ProfileMode.lite and self.max_long_running_daemons != 4:
            raise ProfileConstraintError(
                "Lite profiles must set max_long_running_daemons to 4"
            )

        return self

