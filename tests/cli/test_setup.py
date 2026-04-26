from __future__ import annotations

from pathlib import Path

import pytest

try:
    import click  # noqa: F401
    from click.testing import CliRunner

    from assembly.cli.main import entrypoint

    CLICK_AVAILABLE = True
except ModuleNotFoundError:
    CLICK_AVAILABLE = False
    CliRunner = None  # type: ignore[assignment]
    entrypoint = None  # type: ignore[assignment]

pytestmark = pytest.mark.skipif(
    not CLICK_AVAILABLE,
    reason="click is not installed in the sandbox interpreter",
)


def test_setup_help_is_registered() -> None:
    result = CliRunner().invoke(entrypoint, ["--help"])

    assert result.exit_code == 0
    assert "setup" in result.output


def test_setup_minimax_writes_key_and_clears_other_backend_gates(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "POSTGRES_DB=assembly",
                "MINIMAX_API_KEY=old-key",
                "MINIMAX_API_BASE=https://old.example/v1",
                "REASONER_RUNTIME_ENABLE_CODEX_OAUTH=1",
                "REASONER_RUNTIME_ENABLE_CLAUDE_CODE_CLI=1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        entrypoint,
        [
            "setup",
            "--env-file",
            str(env_file),
            "--backend",
            "minimax",
            "--minimax-api-key",
            "sk-xxx",
            "--minimax-api-base",
            "https://api.minimax.chat/v1",
        ],
    )

    assert result.exit_code == 0, result.output
    values = _read_env(env_file)
    assert values["POSTGRES_DB"] == "assembly"
    assert values["MINIMAX_API_KEY"] == "sk-xxx"
    assert values["MINIMAX_API_BASE"] == "https://api.minimax.chat/v1"
    assert values["REASONER_RUNTIME_ENABLE_CODEX_OAUTH"] == ""
    assert values["REASONER_RUNTIME_ENABLE_CLAUDE_CODE_CLI"] == ""


def test_setup_codex_requires_auth_and_clears_non_selected_backend_values(
    tmp_path: Path,
) -> None:
    env_file = _write_llm_env(tmp_path / ".env")
    home = tmp_path / "home"
    auth_path = home / ".codex" / "auth.json"
    auth_path.parent.mkdir(parents=True)
    auth_path.write_text('{"access_token":"token"}\n', encoding="utf-8")

    result = CliRunner().invoke(
        entrypoint,
        ["setup", "--env-file", str(env_file), "--backend", "codex"],
        env={"HOME": str(home)},
    )

    assert result.exit_code == 0, result.output
    values = _read_env(env_file)
    assert values["MINIMAX_API_KEY"] == ""
    assert values["MINIMAX_API_BASE"] == ""
    assert values["REASONER_RUNTIME_ENABLE_CODEX_OAUTH"] == "1"
    assert values["REASONER_RUNTIME_ENABLE_CLAUDE_CODE_CLI"] == ""
    assert "host-managed/runtime-only" in result.output
    assert "container-not-ready" in result.output
    assert "does not install the codex CLI" in result.output


def test_setup_codex_missing_auth_fails_without_rewriting_env(
    tmp_path: Path,
) -> None:
    env_file = _write_llm_env(tmp_path / ".env")
    before = env_file.read_text(encoding="utf-8")

    result = CliRunner().invoke(
        entrypoint,
        ["setup", "--env-file", str(env_file), "--backend", "codex"],
        env={"HOME": str(tmp_path / "empty-home")},
    )

    assert result.exit_code != 0
    assert "codex auth not found" in result.output
    assert env_file.read_text(encoding="utf-8") == before


def test_setup_claude_code_requires_path_and_clears_other_backend_values(
    tmp_path: Path,
) -> None:
    env_file = _write_llm_env(tmp_path / ".env")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    claude = bin_dir / "claude"
    claude.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    claude.chmod(0o755)

    result = CliRunner().invoke(
        entrypoint,
        ["setup", "--env-file", str(env_file), "--backend", "claude-code"],
        env={"PATH": str(bin_dir)},
    )

    assert result.exit_code == 0, result.output
    values = _read_env(env_file)
    assert values["MINIMAX_API_KEY"] == ""
    assert values["MINIMAX_API_BASE"] == ""
    assert values["REASONER_RUNTIME_ENABLE_CODEX_OAUTH"] == ""
    assert values["REASONER_RUNTIME_ENABLE_CLAUDE_CODE_CLI"] == "1"
    assert "host-managed/runtime-only" in result.output
    assert "container-not-ready" in result.output
    assert "does not install the claude CLI" in result.output


def test_setup_without_backend_prompts_for_backend(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    home = tmp_path / "home"
    auth_path = home / ".codex" / "auth.json"
    auth_path.parent.mkdir(parents=True)
    auth_path.write_text('{"access_token":"token"}\n', encoding="utf-8")

    result = CliRunner().invoke(
        entrypoint,
        ["setup", "--env-file", str(env_file)],
        input="codex\n",
        env={"HOME": str(home)},
    )

    assert result.exit_code == 0, result.output
    values = _read_env(env_file)
    assert values["REASONER_RUNTIME_ENABLE_CODEX_OAUTH"] == "1"
    assert values["MINIMAX_API_KEY"] == ""
    assert values["REASONER_RUNTIME_ENABLE_CLAUDE_CODE_CLI"] == ""
    assert "host-managed/runtime-only" in result.output
    assert "container-not-ready" in result.output


def _write_llm_env(path: Path) -> Path:
    path.write_text(
        "\n".join(
            [
                "# preserved comment",
                "MINIMAX_API_KEY=old-key",
                "MINIMAX_API_BASE=https://old.example/v1",
                "REASONER_RUNTIME_ENABLE_CODEX_OAUTH=",
                "REASONER_RUNTIME_ENABLE_CLAUDE_CODE_CLI=1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        if stripped.startswith("export "):
            stripped = stripped.removeprefix("export ").strip()
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip()
    return values
