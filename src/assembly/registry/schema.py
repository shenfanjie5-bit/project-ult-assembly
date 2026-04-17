"""Pydantic schemas for the assembly module registry."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PublicEntrypoint(BaseModel):
    """Public entrypoint registered for a module."""

    model_config = ConfigDict(extra="forbid")

    name: str
    kind: Literal[
        "health_probe",
        "smoke_hook",
        "init_hook",
        "version_declaration",
        "cli",
    ]
    reference: str = Field(pattern=r"^[A-Za-z_][\w.]*:[A-Za-z_]\w*$")
