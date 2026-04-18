from __future__ import annotations

import re
from pathlib import Path

import pytest

try:
    import click  # noqa: F401

    from assembly.cli.main import entrypoint

    CLICK_AVAILABLE = True
except ModuleNotFoundError:
    CLICK_AVAILABLE = False
    entrypoint = None  # type: ignore[assignment]


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = PROJECT_ROOT / "docs"
DOC_NAMES = (
    "STARTUP_GUIDE.md",
    "TROUBLESHOOTING.md",
    "PROFILE_COMPARISON.md",
    "VERSION_LOCK.md",
)


def test_release_docs_exist_with_key_titles() -> None:
    expected_titles = {
        "STARTUP_GUIDE.md": "# Startup Guide",
        "TROUBLESHOOTING.md": "# Troubleshooting",
        "PROFILE_COMPARISON.md": "# Profile Comparison",
        "VERSION_LOCK.md": "# Version Lock",
    }

    for doc_name, title in expected_titles.items():
        text = (DOCS_ROOT / doc_name).read_text(encoding="utf-8")
        assert text.startswith(title)

    startup = (DOCS_ROOT / "STARTUP_GUIDE.md").read_text(encoding="utf-8")
    for command in (
        "list-profiles",
        "render-profile",
        "bootstrap",
        "shutdown",
        "healthcheck",
        "smoke",
        "contract-suite",
        "e2e",
        "export-registry",
        "release-freeze",
    ):
        assert command in startup


def test_docs_internal_relative_links_resolve() -> None:
    for doc_name in DOC_NAMES:
        path = DOCS_ROOT / doc_name
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            if "://" in target or target.startswith("#"):
                continue
            relative_path = target.split("#", 1)[0]
            if not relative_path:
                continue
            assert (path.parent / relative_path).exists(), target


def test_startup_full_dev_default_does_not_enable_optional_bundles() -> None:
    text = (DOCS_ROOT / "STARTUP_GUIDE.md").read_text(encoding="utf-8")
    default_section = text.split("## Full Dev", 1)[1].split(
        "Optional service bundles are enabled only when explicitly requested",
        1,
    )[0]

    assert "--profile full-dev" in default_section
    assert "--extra-bundles" not in default_section


def test_profile_comparison_requires_explicit_optional_bundles() -> None:
    text = (DOCS_ROOT / "PROFILE_COMPARISON.md").read_text(encoding="utf-8")

    assert "Default `full-dev` only includes the core service bundles" in text
    assert "MinIO, Grafana, Superset" in text
    assert "`full-dev --extra-bundles=...`" in text
    for bundle in ("minio", "grafana", "superset", "temporal", "feast", "kafka-flink"):
        assert f"`{bundle}`" in text


def test_troubleshooting_distinguishes_host_probe_and_container_healthcheck() -> None:
    text = (DOCS_ROOT / "TROUBLESHOOTING.md").read_text(encoding="utf-8")

    assert "host-level probes" in text
    assert "Docker container healthchecks run inside the container" in text
    assert "host port override" in text
    for topic in (
        "Missing Environment",
        "PostgreSQL Unhealthy",
        "Neo4j Unhealthy",
        "Dagster Webserver Unhealthy",
        "Orchestrator Entrypoint",
        "Contract Mismatch",
        "Optional Bundle Credentials",
    ):
        assert f"## {topic}" in text


@pytest.mark.skipif(
    not CLICK_AVAILABLE,
    reason="click is not installed in the sandbox interpreter",
)
def test_documented_cli_commands_exist() -> None:
    command_names = set(entrypoint.commands)
    documented: set[str] = set()
    for doc_name in DOC_NAMES:
        text = (DOCS_ROOT / doc_name).read_text(encoding="utf-8")
        documented.update(re.findall(r"assembly\.cli\.main\s+([a-z][a-z-]+)", text))

    assert documented
    assert documented <= command_names
