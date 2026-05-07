from __future__ import annotations

import fnmatch
import json
import subprocess
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXEMPTIONS_PATH = (
    PROJECT_ROOT / "reports/stabilization/evidence-hygiene-exemptions.yaml"
)


def _tracked_files(*patterns: str) -> list[str]:
    completed = subprocess.run(
        ["git", "ls-files", *patterns],
        cwd=PROJECT_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return [line for line in completed.stdout.splitlines() if line]


def _json_string_value_matches(
    value: Any,
    *,
    forbidden_fragments: list[str],
) -> list[str]:
    if isinstance(value, str):
        return [fragment for fragment in forbidden_fragments if fragment in value]
    if isinstance(value, list):
        matches: list[str] = []
        for item in value:
            matches.extend(
                _json_string_value_matches(
                    item,
                    forbidden_fragments=forbidden_fragments,
                ),
            )
        return matches
    if isinstance(value, dict):
        matches = []
        for item in value.values():
            matches.extend(
                _json_string_value_matches(
                    item,
                    forbidden_fragments=forbidden_fragments,
                ),
            )
        return matches
    return []


def test_stabilization_raw_runtime_artifacts_are_not_tracked() -> None:
    tracked = _tracked_files("reports/stabilization/**")
    forbidden = [
        "reports/stabilization/**/raw/tushare/**",
        "reports/stabilization/**/runtime/**",
        "reports/stabilization/**/*.parquet",
        "reports/stabilization/**/*stdout*",
        "reports/stabilization/**/*stderr*",
        "reports/stabilization/**/*.exitcode",
        "reports/stabilization/**/runtime-env*",
        "reports/stabilization/**/runtime-preflight*",
        "reports/stabilization/**/daily_refresh_dbt_profiles/**",
        "reports/stabilization/**/*_manifest.json",
    ]

    offenders = [
        path
        for path in tracked
        if any(fnmatch.fnmatch(path, pattern) for pattern in forbidden)
    ]

    assert offenders == []


def test_stabilization_json_artifacts_are_sanitized() -> None:
    forbidden_tokens = [
        "/Users/",
        "/Volumes/",
        "stdout_tail",
        "stderr_tail",
        '"stdout"',
        '"stderr"',
        "600519.SH",
        "000001.SZ",
        "000063.SZ",
    ]
    offenders: dict[str, list[str]] = {}

    for path_text in _tracked_files("reports/stabilization/**/*.json"):
        text = (PROJECT_ROOT / path_text).read_text(encoding="utf-8")
        matches = [token for token in forbidden_tokens if token in text]
        if matches:
            offenders[path_text] = matches

    assert offenders == {}


def test_stabilization_json_values_do_not_reference_deleted_artifacts() -> None:
    forbidden_value_fragments = [
        ".stdout",
        ".stderr",
        "stdout.txt",
        "stderr.txt",
        ".exitcode",
        "raw_stdout",
        "raw_stderr",
        "/raw/tushare/",
        "\\raw\\tushare\\",
        ".parquet",
        "_manifest.json",
    ]
    offenders: dict[str, list[str]] = {}

    for path_text in _tracked_files("reports/stabilization/**/*.json"):
        payload = json.loads((PROJECT_ROOT / path_text).read_text(encoding="utf-8"))
        matches = sorted(
            set(
                _json_string_value_matches(
                    payload,
                    forbidden_fragments=forbidden_value_fragments,
                ),
            ),
        )
        if matches:
            offenders[path_text] = matches

    assert offenders == {}


def test_hygiene_exemptions_do_not_allow_raw_runtime_bodies() -> None:
    payload = yaml.safe_load(EXEMPTIONS_PATH.read_text(encoding="utf-8"))

    assert payload["policy"]["raw_runtime_artifact_exemptions"] == []
