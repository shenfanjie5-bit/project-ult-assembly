"""Docker compose runner for bootstrap plans."""

from __future__ import annotations

import subprocess
from pathlib import Path
from subprocess import CompletedProcess
from typing import Literal, Sequence

from pydantic import BaseModel, ConfigDict, Field

from assembly.bootstrap.plan import BootstrapPlan
from assembly.bootstrap.service_handle import CommandRunner, ServiceHandle


class BootstrapResult(BaseModel):
    """Result of a bootstrap runner action."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str
    action: Literal["start", "stop"]
    command: list[str]
    service_order: list[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""
    handles: list[ServiceHandle] = Field(default_factory=list)


class ComposeCommandError(Exception):
    """Raised when docker compose returns a non-zero exit code."""

    def __init__(
        self,
        command: Sequence[str],
        returncode: int,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        self.command = list(command)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(
            f"Command failed with exit code {returncode}: {_format_command(command)}"
        )


class DockerComposeUnavailableError(ComposeCommandError):
    """Raised when the docker compose executable cannot be launched."""


class Runner:
    """Run bootstrap plans through docker compose."""

    def __init__(
        self,
        command_runner: CommandRunner | None = None,
        cwd: Path = Path.cwd(),
        env_file: Path | None = None,
    ) -> None:
        self.command_runner = command_runner
        self.cwd = Path(cwd)
        self.env_file = Path(env_file) if env_file is not None else None

    def start(self, plan: BootstrapPlan) -> BootstrapResult:
        """Start services in plan startup order and wait for compose readiness."""

        command = self._compose_prefix(plan) + [
            "up",
            "-d",
            "--wait",
            *plan.startup_order,
        ]
        result = self._run(command)
        return BootstrapResult(
            profile_id=plan.profile_id,
            action="start",
            command=command,
            service_order=list(plan.startup_order),
            returncode=result.returncode,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
            handles=[
                ServiceHandle(
                    name=service.name,
                    bundle_name=service.bundle_name,
                    compose_service=service.compose_service,
                    compose_file=plan.compose_file,
                    env_file=self.env_file,
                    command_runner=self.command_runner,
                )
                for service in plan.services
            ],
        )

    def stop(self, plan: BootstrapPlan) -> BootstrapResult:
        """Stop services in the plan shutdown order."""

        command = self._compose_prefix(plan) + [
            "stop",
            *plan.shutdown_order,
        ]
        result = self._run(command)
        return BootstrapResult(
            profile_id=plan.profile_id,
            action="stop",
            command=command,
            service_order=list(plan.shutdown_order),
            returncode=result.returncode,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
        )

    def _compose_prefix(self, plan: BootstrapPlan) -> list[str]:
        command = ["docker", "compose"]
        if self.env_file is not None:
            command.extend(["--env-file", str(self.env_file)])
        command.extend(["-f", str(plan.compose_file)])
        return command

    def _run(self, command: Sequence[str]) -> CompletedProcess[str]:
        try:
            if self.command_runner is not None:
                result = self.command_runner(command)
            else:
                result = subprocess.run(
                    list(command),
                    cwd=self.cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                )
        except FileNotFoundError as exc:
            raise DockerComposeUnavailableError(
                command,
                127,
                stderr=str(exc),
            ) from exc

        if result.returncode != 0:
            raise ComposeCommandError(
                command,
                result.returncode,
                stdout=result.stdout or "",
                stderr=result.stderr or "",
            )

        return result


def _format_command(command: Sequence[str]) -> str:
    return " ".join(str(part) for part in command)
