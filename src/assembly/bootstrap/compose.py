"""Compose artifact selection for bootstrap workflows."""

from __future__ import annotations

from pathlib import Path


def default_compose_file(profile_id: str) -> Path:
    """Return the default compose file for a profile id."""

    if profile_id == "full-dev":
        return Path("compose/full-dev.yaml")

    return Path("compose/lite-local.yaml")


def resolve_compose_file(profile_id: str, compose_file: Path | None = None) -> Path:
    """Return an explicit compose file or the profile-derived default."""

    if compose_file is not None:
        return Path(compose_file)

    return default_compose_file(profile_id)


__all__ = ["default_compose_file", "resolve_compose_file"]
