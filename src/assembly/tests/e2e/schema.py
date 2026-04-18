"""Schemas for minimal-cycle e2e fixtures and reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MinimalCycleFixture(BaseModel):
    """Manifest describing the minimal daily-cycle e2e scenario."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(min_length=1)
    expected_phases: list[str] = Field(min_length=1)
    required_artifacts: list[str] = Field(default_factory=list)
    orchestrator_args: list[str] = Field(min_length=1)
    manifest_path: Path = Path("src/assembly/tests/e2e/fixtures/minimal_cycle/manifest.yaml")

    @field_validator("expected_phases", "required_artifacts", "orchestrator_args")
    @classmethod
    def require_non_empty_items(cls, values: list[str]) -> list[str]:
        empty_indexes = [index for index, value in enumerate(values) if not value.strip()]
        if empty_indexes:
            raise ValueError(f"items must be non-empty strings: {empty_indexes}")

        return values


class OrchestratorCycleReport(BaseModel):
    """Report emitted by the orchestrator public CLI for one minimal cycle."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str
    phases: list[str]
    artifacts: dict[str, str] = Field(default_factory=dict)
    status: Literal["success", "failed", "partial"]
    failure_reason: str | None = None


class E2EAssertionResult(BaseModel):
    """Single assertion result in the persisted minimal-cycle e2e report."""

    model_config = ConfigDict(extra="forbid")

    assertion_name: str
    status: Literal["passed", "failed"]
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
