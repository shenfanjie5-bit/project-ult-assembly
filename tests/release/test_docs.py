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
REPORTS_ROOT = PROJECT_ROOT / "reports"
DOC_NAMES = (
    "STARTUP_GUIDE.md",
    "TROUBLESHOOTING.md",
    "PROFILE_COMPARISON.md",
    "VERSION_LOCK.md",
)
POST_CANARY_RUNBOOK = DOCS_ROOT / "runbook/holdings-post-canary-production-rollout.md"
POST_CANARY_TEMPLATE = (
    REPORTS_ROOT
    / "stabilization/holdings-post-canary-rollout-evidence-template-20260508.md"
)
POST_CANARY_DOCS = (POST_CANARY_RUNBOOK, POST_CANARY_TEMPLATE)
POST_CANARY_FORBIDDEN_CLAIMS = (
    "Broad production rollout complete.",
    "Production rollout complete.",
    "Default/full propagation enabled.",
    "Default full-propagation rollout.",
    "`run_full_propagation` execution.",
    "M4.7 real-document completion.",
    "M4.7/financial-doc complete.",
    "Financial-doc scope.",
    "Contracts subtype changes.",
    "New relation types beyond `CO_HOLDING` and `NORTHBOUND_HOLD`.",
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


def _markdown_section(text: str, heading: str) -> str:
    _, _, tail = text.partition(f"{heading}\n")
    assert tail, heading
    next_heading = re.search(r"\n## ", tail)
    if next_heading is None:
        return tail
    return tail[: next_heading.start()]


def _contains_words(text: str, phrase: str) -> bool:
    pattern = r"\s+".join(re.escape(word) for word in phrase.split())
    return re.search(pattern, text) is not None


def _assert_boundary_mentions_are_negated(text: str, path: Path) -> None:
    protected_phrases = (
        "broad production rollout complete",
        "production rollout complete",
        "default/full propagation enabled",
        "default full-propagation rollout",
        "M4.7 real-doc",
        "M4.7 real-document completion",
        "M4.7/financial-doc complete",
        "financial-doc scope",
        "contracts subtype",
        "new relation",
    )
    negation_markers = (
        "not ",
        "no ",
        "does not",
        "do not",
        "outside",
        "remain outside",
        "remains outside",
        "closed / not planned",
        "不",
        "未",
        "仍",
        "不在",
    )

    lines = text.splitlines()
    for line_number, line in enumerate(lines, start=1):
        lower_line = line.lower()
        for phrase in protected_phrases:
            if phrase.lower() not in lower_line:
                continue
            context = " ".join(
                lines[max(0, line_number - 5) : min(len(lines), line_number + 2)],
            ).lower()
            assert any(marker in context for marker in negation_markers), (
                f"{path.name}:{line_number}: protected boundary phrase is not "
                f"clearly negated: {phrase!r}"
            )


def test_post_canary_rollout_runbook_locks_operator_gates() -> None:
    text = POST_CANARY_RUNBOOK.read_text(encoding="utf-8")

    assert text.startswith("# Holdings Post-Canary Production Rollout Runbook")
    assert "Status: `OPERATIONALIZATION_ONLY`" in text

    allowed_claims = _markdown_section(text, "## Allowed Current Claims")
    assert "Production hardening prerequisites and guards have landed." in allowed_claims
    assert "Bounded gated canary/live production evidence passed." in allowed_claims
    assert (
        "production rollout operationalization/runbook hardening" in allowed_claims
    )
    assert "controlled opt-in/default propagation canary" in allowed_claims

    operator_gates = _markdown_section(text, "## Operator Gates")
    for gate in (
        "Ownership and approval",
        "Scope lock",
        "Environment lock",
        "Execution lock",
        "Observability lock",
        "Rollback lock",
        "Evidence hygiene lock",
    ):
        assert gate in operator_gates

    rollback = _markdown_section(text, "## Rollback Checklist")
    for trigger in (
        "Worker rejected count is nonzero",
        "Frozen reader count diverges from accepted queue receipt count",
        "Graph readback count diverges from the approved expected count",
        "Missing edge ids are nonzero",
        "Disallowed relation count is nonzero",
    ):
        assert trigger in rollback


def test_post_canary_evidence_template_is_template_only() -> None:
    text = POST_CANARY_TEMPLATE.read_text(encoding="utf-8")

    assert text.startswith("# Holdings Post-Canary Rollout Evidence Template")
    assert "Status: `TEMPLATE_ONLY`" in text
    assert "Status: `PASSED`" not in text
    for heading in (
        "## Allowed Current Claims",
        "## Operator Gate Record",
        "## Rollback Checklist Record",
        "## Observability Summary",
        "## Audit And Incident Record",
        "## Evidence Hygiene",
        "## Not Claimed",
    ):
        assert heading in text

    hygiene = _markdown_section(text, "## Evidence Hygiene")
    for forbidden_artifact in (
        "runtime artifact files",
        "parquet files",
        "raw manifests",
        "stdout/stderr/exitcode files",
        "tokens",
        "DSNs",
        "raw payload bodies",
        "local proof paths",
    ):
        assert _contains_words(hygiene, forbidden_artifact), forbidden_artifact


def test_readme_and_progress_point_to_post_canary_operationalization_docs() -> None:
    required_refs = (
        "docs/runbook/holdings-post-canary-production-rollout.md",
        "reports/stabilization/holdings-post-canary-rollout-evidence-template-20260508.md",
        "bounded gated canary/live production evidence",
        "production rollout operationalization/runbook hardening",
        "controlled opt-in/default propagation canary",
    )

    for path in (PROJECT_ROOT / "README.md", DOCS_ROOT / "PROGRESS.md"):
        text = path.read_text(encoding="utf-8").lower()
        for required_ref in required_refs:
            assert required_ref.lower() in text, f"{path.name}: missing {required_ref}"


def test_readme_and_progress_keep_protected_boundaries_negated() -> None:
    for path in (PROJECT_ROOT / "README.md", DOCS_ROOT / "PROGRESS.md"):
        _assert_boundary_mentions_are_negated(
            path.read_text(encoding="utf-8"),
            path,
        )


def test_post_canary_docs_keep_not_claimed_boundaries() -> None:
    for path in POST_CANARY_DOCS:
        text = path.read_text(encoding="utf-8")
        not_claimed = _markdown_section(text, "## Not Claimed")
        outside_not_claimed = text.replace(not_claimed, "")
        for claim in POST_CANARY_FORBIDDEN_CLAIMS:
            assert claim in not_claimed, f"{path.name}: missing {claim}"
            assert claim not in outside_not_claimed, f"{path.name}: positive {claim}"


def test_post_canary_docs_do_not_record_runtime_artifacts_or_secrets() -> None:
    forbidden_fragments = (
        "/Users/",
        "/Volumes/",
        ".parquet",
        "stdout_tail",
        "stderr_tail",
        '"stdout"',
        '"stderr"',
        "DP_PG_DSN=",
        "DATABASE_URL=",
        "NEO4J_PASSWORD=",
    )

    for path in POST_CANARY_DOCS:
        text = path.read_text(encoding="utf-8")
        matches = [fragment for fragment in forbidden_fragments if fragment in text]
        assert matches == [], f"{path.name}: {matches}"
