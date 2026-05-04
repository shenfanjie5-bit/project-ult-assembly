"""M4.6 proof: frontend-api reads same-cycle Ex-3 signals read-only."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSEMBLY_ROOT = PROJECT_ROOT / "assembly"
DEFAULT_FRONTEND_API_ROOT = PROJECT_ROOT / "frontend-api"
DEFAULT_OUT = (
    ASSEMBLY_ROOT
    / "reports"
    / "stabilization"
    / "m4-ex3-frontend-readonly-proof-20260505.json"
)
DEFAULT_GENERATED_AT = datetime(2026, 5, 5, tzinfo=UTC)
DEFAULT_CYCLE_ID = "CYCLE_20260505_M46_EX3"
DEFAULT_CANDIDATE_ID = 46
DEFAULT_DELTA_ID = "m4-6-ex3-frontend-readonly-delta-1"
DEFAULT_SELECTION_REF = f"cycle_candidate_selection:{DEFAULT_CYCLE_ID}"
EX3_ENDPOINT = "/api/project-ult/graph/ex3-signals/{cycle_id}"
EXPECTED_ORCHESTRATOR_MERGE_COMMIT = (
    "947a3a06cfb8c448bf8423bb23ada4147057c57f"
)
EXPECTED_FRONTEND_API_MERGE_COMMIT = (
    "3eee856c4f0ae72acd91a526e46582def0c94151"
)
M4_5_ASSEMBLY_MERGE_COMMIT = "00c4644d6469178e4046c5b5511d93c5ad8f435f"
SAFE_EX3_SIGNAL_KEYS = frozenset(
    {
        "cycle_id",
        "candidate_id",
        "delta_id",
        "delta_type",
        "selection_ref",
        "source_node",
        "target_node",
        "relation_type",
        "properties",
        "evidence_refs",
    }
)
FORBIDDEN_RESPONSE_KEY_TOKENS = frozenset(
    {
        "ingest_seq",
        "submitted_at",
        "raw",
        "provider",
        "source",
        "private",
        "log",
        "logs",
        "metadata",
        "secret",
        "secrets",
        "queue",
        "queue_id",
        "private_id",
        "internal_queue_id",
        "token",
        "password",
        "api_key",
        "authorization",
        "traceback",
    }
)
LOCAL_PATH_PREFIXES = (
    "/Users/",
    "/tmp/",
    "/private/",
    "/var/",
    "file:",
)
SECRET_ENV_KEYS = (
    "DATABASE_URL",
    "DP_PG_DSN",
    "POSTGRES_PASSWORD",
    "OPENAI_API_KEY",
    "DP_TUSHARE_TOKEN",
    "NEO4J_PASSWORD",
    "ANTHROPIC_API_KEY",
    "PROJECT_ULT_API_TOKEN",
    "PROJECT_ULT_BEARER_TOKEN",
)
UPSTREAM_EVIDENCE = [
    {
        "milestone": "M4.4",
        "artifact": "reports/stabilization/m4-bridge-live-proof-20260503.md",
        "proof_artifact": (
            "reports/stabilization/m4-ex3-queue-promotion-proof-20260503.json"
        ),
        "claim": "live PostgreSQL Ex-3 queue/freeze to graph promotion proof",
    },
    {
        "milestone": "M4.5",
        "artifact": (
            "reports/stabilization/m4-ex3-reasoner-consumption-proof-20260505.md"
        ),
        "proof_artifact": (
            "reports/stabilization/m4-ex3-reasoner-consumption-proof-20260505.json"
        ),
        "assembly_pr": "#50",
        "merge_commit": M4_5_ASSEMBLY_MERGE_COMMIT,
        "claim": "deterministic Ex-3 graph context survives reasoner input",
    },
    {
        "milestone": "M4.6",
        "component": "orchestrator",
        "artifact_pr": "#115",
        "merge_commit": EXPECTED_ORCHESTRATOR_MERGE_COMMIT,
        "claim": "merged frontend-api Ex-3 signal artifact writer",
    },
    {
        "milestone": "M4.6",
        "component": "frontend-api",
        "artifact_pr": "#2",
        "merge_commit": EXPECTED_FRONTEND_API_MERGE_COMMIT,
        "claim": "merged read-only Ex-3 signal endpoint",
    },
]
REPORT_MODE = {
    "mode": "deterministic_testclient_synthetic_fixture",
    "scope": (
        "Assembly component proof only: frontend-api origin/main TestClient reads "
        "a synthetic same-cycle orchestrator Ex-3 signal artifact."
    ),
    "live_api_ui_smoke_executed": False,
    "live_pg_end_to_end_claim": False,
    "g4_p5_completion_claim": False,
}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prove merged frontend-api origin/main exposes same-cycle Ex-3 "
            "graph signals through a read-only sanitized endpoint."
        ),
    )
    parser.add_argument(
        "--frontend-api-root",
        type=Path,
        default=Path(os.environ.get("M4_EX3_FRONTEND_API_ROOT", DEFAULT_FRONTEND_API_ROOT)),
        help=(
            "frontend-api checkout at origin/main merge commit 3eee856...; "
            "the local frontend-api main branch is intentionally not modified."
        ),
    )
    parser.add_argument(
        "--fixture-project-root",
        type=Path,
        default=None,
        help=(
            "Optional temporary Project ULT root for the synthetic orchestrator "
            "artifact fixture. Defaults to a TemporaryDirectory."
        ),
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--markdown-out",
        type=Path,
        default=None,
        help="Markdown sibling path. Defaults to --out with .md suffix.",
    )
    args = parser.parse_args(argv)

    markdown_out = args.markdown_out or args.out.with_suffix(".md")
    report: dict[str, Any] = {
        "proof_id": "m4.6-ex3-frontend-readonly-proof",
        "status": "failed",
        "generated_at": DEFAULT_GENERATED_AT.isoformat(),
        "report_mode": dict(REPORT_MODE),
        "upstream_evidence": _json_safe(UPSTREAM_EVIDENCE),
    }

    try:
        if args.fixture_project_root is None:
            with tempfile.TemporaryDirectory(prefix="m4-ex3-frontend-readonly-") as tmp:
                report.update(
                    run_deterministic_proof(
                        frontend_api_root=args.frontend_api_root,
                        fixture_project_root=Path(tmp),
                    )
                )
        else:
            report.update(
                run_deterministic_proof(
                    frontend_api_root=args.frontend_api_root,
                    fixture_project_root=args.fixture_project_root,
                )
            )
        deterministic_status = report["deterministic_proof"]["status"]
        report["status"] = "passed" if deterministic_status == "passed" else "failed"
        return 0 if report["status"] == "passed" else 1
    except Exception as exc:  # noqa: BLE001 - evidence must preserve blockers.
        report["error"] = {
            "type": type(exc).__name__,
            "message": _redact_text(str(exc)),
        }
        return 1
    finally:
        write_reports(report, args.out, markdown_out)


def run_deterministic_proof(
    *,
    frontend_api_root: Path,
    fixture_project_root: Path,
) -> dict[str, Any]:
    frontend_reference = verify_frontend_api_root(frontend_api_root)
    artifact = write_synthetic_orchestrator_artifact(fixture_project_root)
    proof = exercise_frontend_api_testclient(
        frontend_api_root=frontend_api_root,
        fixture_project_root=fixture_project_root,
    )
    live_api_ui = live_api_ui_smoke_status()

    deterministic_passed = (
        proof["api_response"]["status"] == "passed"
        and proof["sanitization"]["status"] == "passed"
        and proof["route_table"]["status"] == "passed"
    )
    report = {
        "deterministic_proof": {
            "status": "passed" if deterministic_passed else "failed",
            "mode": REPORT_MODE["mode"],
            "frontend_api_testclient_executed": True,
            "synthetic_fixture_used": True,
            "live_api_ui_smoke_executed": False,
            "live_pg_end_to_end_claim": False,
            "g4_p5_completion_claim": False,
        },
        "overall": {
            "passed": bool(deterministic_passed),
            "passed_scope": "deterministic_component_proof_only",
            "live_api_ui_smoke_executed": False,
            "live_api_ui_claim": False,
            "live_pg_end_to_end_claim": False,
            "g4_p5_completion_claim": False,
        },
        "frontend_api_reference": frontend_reference,
        "orchestrator_artifact_fixture": artifact,
        "api_response": proof["api_response"],
        "sanitization": proof["sanitization"],
        "route_table": proof["route_table"],
        "live_api_ui_smoke": live_api_ui,
        "safety_assertions": {
            "contracts_changed": False,
            "frontend_api_local_main_rewritten": False,
            "writes_to_frontend_api_repo": False,
            "frontend_api_write_methods_for_ex3_endpoint": False,
            "raw_debug_route_default_mounted": False,
            "runtime_logs_included": False,
            "secret_values_included": False,
        },
    }
    _assert_response_is_sanitized(report["api_response"]["body"])
    _assert_evidence_hygiene(report)
    return report


def verify_frontend_api_root(frontend_api_root: Path) -> dict[str, Any]:
    root = frontend_api_root.resolve(strict=True)
    src = root / "src" / "frontend_api"
    if not src.is_dir():
        raise RuntimeError("frontend-api root does not contain src/frontend_api")

    actual_commit = _git_rev_parse(root)
    if actual_commit != EXPECTED_FRONTEND_API_MERGE_COMMIT:
        raise RuntimeError(
            "frontend-api checkout must be origin/main merge commit "
            f"{EXPECTED_FRONTEND_API_MERGE_COMMIT}; got {actual_commit or '<unverified>'}"
        )

    return {
        "repo": "project-ult/frontend-api",
        "source": "origin/main",
        "merge_commit": actual_commit,
        "artifact_pr": "#2",
        "local_main_rewritten": False,
        "checkout_path_recorded": False,
    }


def write_synthetic_orchestrator_artifact(project_root: Path) -> dict[str, Any]:
    artifact_rel = Path(
        "orchestrator",
        "artifacts",
        "frontend-api",
        "ex3-graph-signals",
        f"{DEFAULT_CYCLE_ID}.json",
    )
    artifact_path = project_root / artifact_rel
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        json.dumps(synthetic_orchestrator_artifact(), sort_keys=True),
        encoding="utf-8",
    )
    return {
        "artifact": artifact_rel.as_posix(),
        "cycle_id": DEFAULT_CYCLE_ID,
        "producer_component": "orchestrator",
        "producer_merge_commit": EXPECTED_ORCHESTRATOR_MERGE_COMMIT,
        "unsafe_fixture_fields_present": True,
        "path_recorded": False,
    }


def synthetic_orchestrator_artifact() -> dict[str, Any]:
    return {
        "cycle_id": DEFAULT_CYCLE_ID,
        "signals": [
            {
                "cycle_id": DEFAULT_CYCLE_ID,
                "candidate_id": DEFAULT_CANDIDATE_ID,
                "delta_id": DEFAULT_DELTA_ID,
                "delta_type": "edge_add",
                "selection_ref": DEFAULT_SELECTION_REF,
                "source_node": "ENT_M4_6_SOURCE",
                "target_node": "ENT_M4_6_TARGET",
                "relation_type": "SEMANTIC_SIGNAL",
                "properties": {
                    "impact_score": 0.74,
                    "confidence": 0.88,
                    "same_cycle": True,
                    "direction": "positive",
                    "time_horizon": "same_cycle",
                    "safe_details": {
                        "signal_family": "semantic",
                        "weighting": 0.51,
                    },
                    "safe_list": [{"flag": True}],
                    "quality_tags": ["m4.6", "readonly"],
                    "raw_text": "producer-only text must be stripped",
                    "provider": "unsafe-provider",
                    "source": "unsafe-source",
                    "metadata": {"ingest_seq": 123},
                    "private_id": "private-candidate-123",
                    "private_note": "internal note",
                    "queue_id": "queue-row-123",
                    "secret": "unsafe-secret",
                    "log": "internal log",
                    "error_log": "internal stack dump",
                    "absolute_path": "/Users/example/project-ult/private.json",
                    "tmp_location": "/tmp/project-ult/private.json",
                },
                "evidence_refs": [
                    "m4.6:evidence:ex3-frontend-signal-1",
                    "https://example.test/evidence/m4.6/ex3",
                    "/tmp/private-evidence.json",
                ],
                "ingest_seq": 999,
                "submitted_at": "2026-05-05T00:00:00Z",
                "raw": "drop",
                "provider": "drop",
                "source": "drop",
                "private_id": "drop",
                "queue_id": "drop",
            }
        ],
    }


def expected_sanitized_response() -> list[dict[str, Any]]:
    return [
        {
            "cycle_id": DEFAULT_CYCLE_ID,
            "candidate_id": DEFAULT_CANDIDATE_ID,
            "delta_id": DEFAULT_DELTA_ID,
            "delta_type": "edge_add",
            "selection_ref": DEFAULT_SELECTION_REF,
            "source_node": "ENT_M4_6_SOURCE",
            "target_node": "ENT_M4_6_TARGET",
            "relation_type": "SEMANTIC_SIGNAL",
            "properties": {
                "impact_score": 0.74,
                "confidence": 0.88,
                "same_cycle": True,
                "direction": "positive",
                "time_horizon": "same_cycle",
                "safe_details": {
                    "signal_family": "semantic",
                    "weighting": 0.51,
                },
                "safe_list": [{"flag": True}],
                "quality_tags": ["m4.6", "readonly"],
            },
            "evidence_refs": [
                "m4.6:evidence:ex3-frontend-signal-1",
                "https://example.test/evidence/m4.6/ex3",
            ],
        }
    ]


def exercise_frontend_api_testclient(
    *,
    frontend_api_root: Path,
    fixture_project_root: Path,
) -> dict[str, Any]:
    _import_frontend_api_from_root(frontend_api_root)
    from fastapi.testclient import TestClient
    from frontend_api.app import create_app
    from frontend_api.settings import FrontendApiSettings

    app = create_app(
        FrontendApiSettings(
            project_root=fixture_project_root,
            profile="lite-local",
            mode="lite-local",
        )
    )
    client = TestClient(app)
    endpoint_path = EX3_ENDPOINT.replace("{cycle_id}", DEFAULT_CYCLE_ID)
    response = client.get(endpoint_path)
    if response.status_code != 200:
        raise RuntimeError(f"frontend-api TestClient returned HTTP {response.status_code}")

    body = response.json()
    if body != expected_sanitized_response():
        raise RuntimeError("frontend-api response did not match sanitized fixture view")

    _assert_response_is_sanitized(body)
    route_table = analyze_route_table(app)
    if route_table["status"] != "passed":
        raise RuntimeError("frontend-api route table failed read-only assertions")

    return {
        "api_response": {
            "status": "passed",
            "client": "fastapi.testclient.TestClient",
            "method": "GET",
            "endpoint": EX3_ENDPOINT,
            "http_status": response.status_code,
            "cycle_id": DEFAULT_CYCLE_ID,
            "body": body,
            "same_cycle_signal_count": len(body),
            "same_cycle_delta_ids": [item["delta_id"] for item in body],
        },
        "sanitization": {
            "status": "passed",
            "public_field_set": sorted(SAFE_EX3_SIGNAL_KEYS),
            "response_matches_expected_sanitized_view": True,
            "unsafe_fixture_fields_present": True,
            "unsafe_field_hits": [],
            "local_absolute_path_hits": [],
            "source_node_is_public_graph_field": True,
        },
        "route_table": route_table,
    }


def analyze_route_table(app: Any) -> dict[str, Any]:
    ex3_methods = sorted(
        {
            method
            for route in app.routes
            if getattr(route, "path", None) == EX3_ENDPOINT
            for method in getattr(route, "methods", set())
        }
    )
    raw_debug_paths = sorted(
        path
        for route in app.routes
        for path in [str(getattr(route, "path", ""))]
        if path
        and path.startswith("/api/project-ult")
        and ("/debug/" in path or "/raw/" in path)
    )
    project_ult_ex3_write_routes = sorted(
        f"{method} {getattr(route, 'path', '')}"
        for route in app.routes
        for method in getattr(route, "methods", set())
        if method in {"POST", "PUT", "PATCH", "DELETE"}
        and str(getattr(route, "path", "")).startswith(
            "/api/project-ult/graph/ex3-signals"
        )
    )
    status = (
        "passed"
        if "GET" in ex3_methods
        and not set(ex3_methods).intersection({"POST", "PUT", "PATCH", "DELETE"})
        and not project_ult_ex3_write_routes
        and not raw_debug_paths
        else "failed"
    )
    return {
        "status": status,
        "ex3_endpoint": EX3_ENDPOINT,
        "ex3_endpoint_methods": ex3_methods,
        "project_ult_graph_ex3_write_routes": project_ult_ex3_write_routes,
        "raw_debug_paths_default_mounted": raw_debug_paths,
        "raw_debug_routes_default_mounted": bool(raw_debug_paths),
    }


def live_api_ui_smoke_status() -> dict[str, Any]:
    required_env = ("PROJECT_ULT_FRONTEND_URL", "PROJECT_ULT_API_BASE")
    missing = [key for key in required_env if not os.environ.get(key)]
    if missing:
        return {
            "status": "blocked",
            "executed": False,
            "blocker": (
                "missing "
                + " / ".join(missing)
                + "; live API/UI smoke not executed"
            ),
            "required_env": list(required_env),
            "env_values_recorded": False,
            "server_reachability_checked": False,
        }
    return {
        "status": "blocked",
        "executed": False,
        "blocker": (
            "deterministic M4.6 proof does not start or probe live frontend/API "
            "servers; service smoke remains unexecuted"
        ),
        "required_env": list(required_env),
        "env_values_recorded": False,
        "server_reachability_checked": False,
    }


def write_reports(report: Mapping[str, Any], json_out: Path, markdown_out: Path) -> None:
    safe_report = _redact_value(_json_safe(report))
    _assert_evidence_hygiene(safe_report)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(
        json.dumps(safe_report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown = markdown_report(safe_report)
    _assert_evidence_hygiene(markdown)
    markdown_out.write_text(markdown, encoding="utf-8")


def markdown_report(report: Mapping[str, Any]) -> str:
    frontend_ref = report.get("frontend_api_reference", {})
    artifact = report.get("orchestrator_artifact_fixture", {})
    api_response = report.get("api_response", {})
    route_table = report.get("route_table", {})
    live_smoke = report.get("live_api_ui_smoke", {})
    deterministic = report.get("deterministic_proof", {})
    return "\n".join(
        [
            "# M4.6 Ex-3 Frontend Read-Only Proof",
            "",
            f"- Status: {report.get('status')}",
            f"- Generated at: {report.get('generated_at')}",
            f"- Report mode: {deterministic.get('mode')}",
            "- Scope: deterministic component proof only; no live PG, API, or UI "
            "end-to-end claim",
            "- Frontend-api reference: PR "
            f"{frontend_ref.get('artifact_pr')}, merge commit "
            f"{frontend_ref.get('merge_commit')}",
            "- Orchestrator reference: PR #115, merge commit "
            f"{EXPECTED_ORCHESTRATOR_MERGE_COMMIT}",
            "- Upstream proof references: "
            "m4-bridge-live-proof-20260503.md; "
            "m4-ex3-queue-promotion-proof-20260503.json; "
            "m4-ex3-reasoner-consumption-proof-20260505.json",
            f"- Fixture artifact: {artifact.get('artifact')}",
            f"- TestClient endpoint: GET {api_response.get('endpoint')}",
            f"- HTTP status: {api_response.get('http_status')}",
            f"- Same-cycle signal count: {api_response.get('same_cycle_signal_count')}",
            f"- Same-cycle delta ids: {', '.join(api_response.get('same_cycle_delta_ids', []))}",
            "- Sanitized public fields: "
            f"{', '.join(report.get('sanitization', {}).get('public_field_set', []))}",
            "- Unsafe producer/provenance/private fields: absent from response",
            "- Local filesystem paths: absent from response and report",
            "- Ex-3 endpoint methods: "
            f"{', '.join(route_table.get('ex3_endpoint_methods', []))}",
            "- Project ULT graph Ex-3 write routes: none",
            "- Default raw debug routes mounted: "
            f"{route_table.get('raw_debug_routes_default_mounted')}",
            f"- Live API/UI smoke status: {live_smoke.get('status')}",
            f"- Live API/UI smoke blocker: {live_smoke.get('blocker')}",
            "- Overall passed scope: deterministic_component_proof_only",
            "- G4/P5 completion claim: False",
            "",
        ]
    )


def _import_frontend_api_from_root(frontend_api_root: Path) -> None:
    src = str(frontend_api_root.resolve(strict=True) / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    for module_name in list(sys.modules):
        if module_name == "frontend_api" or module_name.startswith("frontend_api."):
            del sys.modules[module_name]


def _git_rev_parse(root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip()


def _assert_response_is_sanitized(value: Any) -> None:
    _assert_no_forbidden_response_fields(value)
    _assert_no_local_absolute_paths(value)
    if value != expected_sanitized_response():
        raise RuntimeError("response body is not the expected sanitized Ex-3 view")


def _assert_no_forbidden_response_fields(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            normalized = key_text.lower()
            if not _is_allowed_public_ex3_key(path, normalized) and _is_unsafe_key(
                normalized
            ):
                raise RuntimeError(f"unsafe field survived at {path}.{key_text}")
            _assert_no_forbidden_response_fields(item, f"{path}.{key_text}")
    elif isinstance(value, list | tuple | set | frozenset):
        for index, item in enumerate(value):
            _assert_no_forbidden_response_fields(item, f"{path}[{index}]")


def _is_allowed_public_ex3_key(path: str, normalized_key: str) -> bool:
    return (
        normalized_key in SAFE_EX3_SIGNAL_KEYS
        and re.fullmatch(r"\$\[\d+\]", path) is not None
    )


def _is_unsafe_key(normalized_key: str) -> bool:
    if normalized_key in FORBIDDEN_RESPONSE_KEY_TOKENS:
        return True
    tokens = [token for token in re.split(r"[^a-z0-9]+", normalized_key) if token]
    return any(token in FORBIDDEN_RESPONSE_KEY_TOKENS for token in tokens)


def _assert_no_local_absolute_paths(value: Any) -> None:
    text = json.dumps(_json_safe(value), sort_keys=True, default=str)
    for prefix in LOCAL_PATH_PREFIXES:
        if prefix in text:
            raise RuntimeError("local absolute path survived evidence")
    if re.search(r"(^|[\"'\\s])[A-Za-z]:[\\/]", text):
        raise RuntimeError("local absolute path survived evidence")


def _assert_evidence_hygiene(value: Any) -> None:
    text = json.dumps(_json_safe(value), sort_keys=True, default=str)
    if _redact_text(text) != text:
        raise RuntimeError("secret-like value survived evidence serialization")
    forbidden_text = (
        "/Users/",
        "/tmp/",
        "postgresql://",
        "postgres://",
        "Bearer ",
        "Traceback",
        "traceback",
        "raw_stdout",
        "raw_stderr",
        "stdout",
        "stderr",
    )
    for token in forbidden_text:
        if token in text:
            raise RuntimeError(f"evidence hygiene violation: {token}")


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "model_dump"):
        return _json_safe(value.model_dump(mode="python"))
    return value


def _redact_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _redact_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, str):
        return _redact_text(value)
    return value


def _redact_text(value: str) -> str:
    redacted = value
    for key in SECRET_ENV_KEYS:
        secret = os.environ.get(key)
        if secret and len(secret) >= 8:
            redacted = redacted.replace(secret, "<redacted>")
    redacted = _redact_postgres_uri(redacted)
    redacted = _redact_bearer(redacted)
    return redacted


def _redact_postgres_uri(value: str) -> str:
    prefixes = ("postgresql://", "postgres://", "postgresql+psycopg://")
    redacted = value
    for prefix in prefixes:
        start = redacted.find(prefix)
        while start != -1:
            end = len(redacted)
            for separator in (" ", "\n", "\r", "\t", '"', "'"):
                candidate = redacted.find(separator, start)
                if candidate != -1:
                    end = min(end, candidate)
            redacted = redacted[:start] + prefix + "<redacted>" + redacted[end:]
            start = redacted.find(prefix, start + len(prefix) + len("<redacted>"))
    return redacted


def _redact_bearer(value: str) -> str:
    marker = "Bearer "
    redacted = value
    start = redacted.find(marker)
    while start != -1:
        token_start = start + len(marker)
        end = token_start
        while end < len(redacted) and not redacted[end].isspace():
            end += 1
        redacted = redacted[:token_start] + "<redacted>" + redacted[end:]
        start = redacted.find(marker, token_start + len("<redacted>"))
    return redacted


if __name__ == "__main__":
    raise SystemExit(main())
