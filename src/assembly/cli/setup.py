"""LLM backend setup command for assembly."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import click

_BACKENDS = ("minimax", "codex", "claude-code")
_MANAGED_KEYS = (
    "MINIMAX_API_KEY",
    "MINIMAX_API_BASE",
    "REASONER_RUNTIME_ENABLE_CODEX_OAUTH",
    "REASONER_RUNTIME_ENABLE_CLAUDE_CODE_CLI",
)
_ASSIGNMENT_RE = re.compile(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")


def make_setup_command() -> click.Command:
    @click.command("setup")
    @click.option(
        "--backend",
        type=click.Choice(_BACKENDS, case_sensitive=False),
        default=None,
        help="LLM backend to enable.",
    )
    @click.option(
        "--minimax-api-key",
        default=None,
        help="MiniMax API key to write when --backend=minimax.",
    )
    @click.option(
        "--minimax-api-base",
        default=None,
        help="Optional MiniMax API base URL to write when --backend=minimax.",
    )
    @click.option(
        "--env-file",
        type=click.Path(path_type=Path, dir_okay=False),
        default=Path(".env"),
        show_default=True,
        help="Env file to read and update.",
    )
    def setup_command(
        backend: str | None,
        minimax_api_key: str | None,
        minimax_api_base: str | None,
        env_file: Path,
    ) -> None:
        """Select one LLM backend and write the corresponding .env values."""

        try:
            current_values = _read_env_values(env_file)
            selected_backend = backend or _prompt_backend(current_values)
            updates = _backend_updates(
                selected_backend,
                current_values=current_values,
                minimax_api_key=minimax_api_key,
                minimax_api_base=minimax_api_base,
            )
            _write_env_values(env_file, updates)
        except (OSError, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc

        click.echo(f"configured {selected_backend} backend in {env_file}")
        runtime_note = _runtime_boundary_note(selected_backend)
        if runtime_note:
            click.echo(runtime_note)

    return setup_command


def _prompt_backend(current_values: dict[str, str]) -> str:
    default_backend = _detect_backend(current_values) or "minimax"
    return click.prompt(
        "LLM backend",
        type=click.Choice(_BACKENDS, case_sensitive=False),
        default=default_backend,
        show_choices=True,
    )


def _backend_updates(
    backend: str,
    *,
    current_values: dict[str, str],
    minimax_api_key: str | None,
    minimax_api_base: str | None,
) -> dict[str, str]:
    normalized = backend.lower()
    if normalized == "minimax":
        selected_key = minimax_api_key or current_values.get("MINIMAX_API_KEY", "")
        if not selected_key:
            selected_key = click.prompt("MiniMax API key", hide_input=True)
        return {
            "MINIMAX_API_KEY": selected_key,
            "MINIMAX_API_BASE": (
                minimax_api_base
                if minimax_api_base is not None
                else current_values.get("MINIMAX_API_BASE", "")
            ),
            "REASONER_RUNTIME_ENABLE_CODEX_OAUTH": "",
            "REASONER_RUNTIME_ENABLE_CLAUDE_CODE_CLI": "",
        }

    if normalized == "codex":
        auth_path = Path("~/.codex/auth.json").expanduser()
        if not auth_path.is_file():
            raise ValueError(
                f"codex auth not found at {auth_path}; run `codex login` first"
            )
        return {
            "MINIMAX_API_KEY": "",
            "MINIMAX_API_BASE": "",
            "REASONER_RUNTIME_ENABLE_CODEX_OAUTH": "1",
            "REASONER_RUNTIME_ENABLE_CLAUDE_CODE_CLI": "",
        }

    if normalized == "claude-code":
        if shutil.which("claude") is None:
            raise ValueError(
                "claude executable not found on PATH; install Claude Code first"
            )
        return {
            "MINIMAX_API_KEY": "",
            "MINIMAX_API_BASE": "",
            "REASONER_RUNTIME_ENABLE_CODEX_OAUTH": "",
            "REASONER_RUNTIME_ENABLE_CLAUDE_CODE_CLI": "1",
        }

    raise ValueError(f"unsupported backend: {backend}")


def _detect_backend(values: dict[str, str]) -> str | None:
    if values.get("REASONER_RUNTIME_ENABLE_CODEX_OAUTH") == "1":
        return "codex"
    if values.get("REASONER_RUNTIME_ENABLE_CLAUDE_CODE_CLI") == "1":
        return "claude-code"
    if values.get("MINIMAX_API_KEY"):
        return "minimax"
    return None


def _runtime_boundary_note(backend: str) -> str:
    normalized = backend.lower()
    if normalized == "codex":
        return (
            "codex is host-managed/runtime-only: compose pass-through makes the "
            "gate visible, but the Dagster container is container-not-ready "
            "because it does not install the codex CLI or mount host auth/keychain."
        )
    if normalized == "claude-code":
        return (
            "claude-code is host-managed/runtime-only: compose pass-through makes "
            "the gate visible, but the Dagster container is container-not-ready "
            "because it does not install the claude CLI or mount host auth/keychain."
        )
    return ""


def _read_env_values(env_file: Path) -> dict[str, str]:
    path = Path(env_file)
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key = _assignment_key(line)
        if key is None:
            continue
        _, _, raw_value = line.partition("=")
        values[key] = _unquote_env_value(raw_value.strip())
    return values


def _write_env_values(env_file: Path, updates: dict[str, str]) -> None:
    path = Path(env_file)
    original_lines = (
        path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    )
    output_lines: list[str] = []
    emitted_keys: set[str] = set()

    for line in original_lines:
        key = _assignment_key(line)
        if key in _MANAGED_KEYS:
            if key not in emitted_keys:
                output_lines.append(f"{key}={_format_env_value(updates[key])}")
                emitted_keys.add(key)
            continue
        output_lines.append(line)

    missing_keys = [key for key in _MANAGED_KEYS if key not in emitted_keys]
    if missing_keys:
        if output_lines and output_lines[-1].strip():
            output_lines.append("")
        output_lines.append("# === LLM backend (managed by `assembly setup`) ===")
        for key in missing_keys:
            output_lines.append(f"{key}={_format_env_value(updates[key])}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(output_lines) + "\n", encoding="utf-8")


def _assignment_key(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    match = _ASSIGNMENT_RE.match(stripped)
    if match is None:
        return None
    return match.group(1)


def _unquote_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _format_env_value(value: str) -> str:
    if "\n" in value or "\r" in value:
        raise ValueError("env values cannot contain newlines")
    return value
