"""Lightweight handles for compose-managed bootstrap services."""

from __future__ import annotations

import subprocess
from pathlib import Path
from subprocess import CompletedProcess
from typing import Callable, Sequence

from pydantic import BaseModel, ConfigDict, Field


CommandRunner = Callable[[Sequence[str]], CompletedProcess[str]]


class ServiceHandle(BaseModel):
    """Handle for a service managed through docker compose."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    name: str
    bundle_name: str
    compose_service: str
    compose_file: Path
    command_runner: CommandRunner | None = Field(default=None, exclude=True, repr=False)

    def poll(self) -> int | None:
        """Return None while the compose service is running, otherwise an exit code."""

        result = self._run(
            [
                "docker",
                "compose",
                "-f",
                str(self.compose_file),
                "ps",
                "--status",
                "running",
                "-q",
                self.compose_service,
            ]
        )
        if result.returncode != 0:
            return result.returncode

        if result.stdout.strip():
            return None

        return 1

    def terminate(self) -> None:
        """Ask docker compose to stop the managed service."""

        self._run(
            [
                "docker",
                "compose",
                "-f",
                str(self.compose_file),
                "stop",
                self.compose_service,
            ]
        )

    def _run(self, command: Sequence[str]) -> CompletedProcess[str]:
        if self.command_runner is not None:
            return self.command_runner(command)

        return subprocess.run(
            list(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
