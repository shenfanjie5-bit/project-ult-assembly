from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


ASSEMBLY_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ASSEMBLY_ROOT / "scripts" / "m4_ex3_frontend_readonly_proof.py"
PROJECT_ROOT = ASSEMBLY_ROOT.parent


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "m4_ex3_frontend_readonly_proof",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _frontend_api_origin_main_root(tmp_path: Path, module: Any) -> Path:
    source_repo = PROJECT_ROOT / "frontend-api"
    if not (source_repo / ".git").exists():
        pytest.skip("frontend-api sibling checkout unavailable")

    actual_origin_main = subprocess.run(
        ["git", "-C", str(source_repo), "rev-parse", "origin/main"],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout.strip()
    if actual_origin_main != module.EXPECTED_FRONTEND_API_MERGE_COMMIT:
        pytest.skip("frontend-api origin/main is not the M4.6 merge commit")

    clone_root = tmp_path / "frontend-api-origin-main"
    subprocess.run(
        [
            "git",
            "clone",
            "--quiet",
            "--no-hardlinks",
            "--no-checkout",
            str(source_repo),
            str(clone_root),
        ],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(clone_root),
            "checkout",
            "--quiet",
            "--detach",
            module.EXPECTED_FRONTEND_API_MERGE_COMMIT,
        ],
        check=True,
    )
    return clone_root


def test_deterministic_proof_uses_frontend_api_origin_main_testclient(
    tmp_path: Path,
) -> None:
    module = _load_module()
    frontend_root = _frontend_api_origin_main_root(tmp_path, module)

    report = module.run_deterministic_proof(
        frontend_api_root=frontend_root,
        fixture_project_root=tmp_path / "fixture-project-root",
    )

    assert report["deterministic_proof"]["status"] == "passed"
    assert report["deterministic_proof"]["frontend_api_testclient_executed"] is True
    assert report["frontend_api_reference"] == {
        "repo": "project-ult/frontend-api",
        "source": "origin/main",
        "merge_commit": module.EXPECTED_FRONTEND_API_MERGE_COMMIT,
        "artifact_pr": "#2",
        "local_main_rewritten": False,
        "checkout_path_recorded": False,
    }
    assert report["orchestrator_artifact_fixture"] == {
        "artifact": (
            "orchestrator/artifacts/frontend-api/ex3-graph-signals/"
            f"{module.DEFAULT_CYCLE_ID}.json"
        ),
        "cycle_id": module.DEFAULT_CYCLE_ID,
        "producer_component": "orchestrator",
        "producer_merge_commit": module.EXPECTED_ORCHESTRATOR_MERGE_COMMIT,
        "unsafe_fixture_fields_present": True,
        "path_recorded": False,
    }
    assert report["api_response"]["body"] == module.expected_sanitized_response()
    assert report["api_response"]["same_cycle_delta_ids"] == [module.DEFAULT_DELTA_ID]
    assert report["route_table"]["ex3_endpoint_methods"] == ["GET"]
    assert report["route_table"]["project_ult_graph_ex3_write_routes"] == []
    assert report["route_table"]["raw_debug_routes_default_mounted"] is False
    assert report["overall"] == {
        "passed": True,
        "passed_scope": "deterministic_component_proof_only",
        "live_api_ui_smoke_executed": False,
        "live_api_ui_claim": False,
        "live_pg_end_to_end_claim": False,
        "g4_p5_completion_claim": False,
    }


def test_main_writes_json_markdown_and_keeps_evidence_hygiene(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    frontend_root = _frontend_api_origin_main_root(tmp_path, module)
    json_out = tmp_path / "proof.json"
    markdown_out = tmp_path / "proof.md"
    dsn = "postgresql://proof_user:supersecret@localhost:5432/proofdb"
    token = "sk-test-secret-token"
    monkeypatch.setenv("DATABASE_URL", dsn)
    monkeypatch.setenv("POSTGRES_PASSWORD", "supersecret")
    monkeypatch.setenv("OPENAI_API_KEY", token)
    monkeypatch.delenv("PROJECT_ULT_FRONTEND_URL", raising=False)
    monkeypatch.delenv("PROJECT_ULT_API_BASE", raising=False)

    exit_code = module.main(
        [
            "--frontend-api-root",
            str(frontend_root),
            "--fixture-project-root",
            str(tmp_path / "fixture-project-root"),
            "--out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
        ]
    )

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    combined = json_out.read_text(encoding="utf-8") + markdown_out.read_text(
        encoding="utf-8"
    )
    assert exit_code == 0
    assert payload["status"] == "passed"
    assert payload["deterministic_proof"]["status"] == "passed"
    assert payload["live_api_ui_smoke"] == {
        "status": "blocked",
        "executed": False,
        "blocker": (
            "missing PROJECT_ULT_FRONTEND_URL / PROJECT_ULT_API_BASE; "
            "live API/UI smoke not executed"
        ),
        "required_env": ["PROJECT_ULT_FRONTEND_URL", "PROJECT_ULT_API_BASE"],
        "env_values_recorded": False,
        "server_reachability_checked": False,
    }
    assert dsn not in combined
    assert "supersecret" not in combined
    assert token not in combined
    assert "Bearer " not in combined
    assert "/Users/" not in combined
    assert "/tmp/" not in combined
    assert str(tmp_path) not in combined
    assert "traceback" not in combined.lower()
    assert "stdout" not in combined.lower()
    assert "stderr" not in combined.lower()
    assert "deterministic_component_proof_only" in combined


def test_response_sanitizer_allows_public_source_node_only() -> None:
    module = _load_module()
    response = module.expected_sanitized_response()

    module._assert_response_is_sanitized(response)
    assert response[0]["source_node"] == "ENT_M4_6_SOURCE"

    with_unsafe_source = copy.deepcopy(response)
    with_unsafe_source[0]["properties"]["source"] = "unsafe"
    with pytest.raises(RuntimeError, match="unsafe field"):
        module._assert_response_is_sanitized(with_unsafe_source)


def test_response_sanitizer_rejects_private_queue_and_local_paths() -> None:
    module = _load_module()
    response = module.expected_sanitized_response()

    with_private_id = copy.deepcopy(response)
    with_private_id[0]["properties"]["private_id"] = "private-1"
    with pytest.raises(RuntimeError, match="unsafe field"):
        module._assert_response_is_sanitized(with_private_id)

    with_local_path = copy.deepcopy(response)
    with_local_path[0]["evidence_refs"].append("/Users/example/private.json")
    with pytest.raises(RuntimeError, match="local absolute path"):
        module._assert_response_is_sanitized(with_local_path)


def test_route_table_detects_write_methods_and_raw_debug_routes() -> None:
    module = _load_module()
    app = SimpleNamespace(
        routes=[
            SimpleNamespace(path=module.EX3_ENDPOINT, methods={"GET", "POST"}),
            SimpleNamespace(
                path="/api/project-ult/debug/graph/ex3-signals/{cycle_id}",
                methods={"GET"},
            ),
        ]
    )

    route_table = module.analyze_route_table(app)

    assert route_table["status"] == "failed"
    assert route_table["project_ult_graph_ex3_write_routes"] == [
        f"POST {module.EX3_ENDPOINT}"
    ]
    assert route_table["raw_debug_routes_default_mounted"] is True


def test_live_api_ui_smoke_is_blocked_without_required_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    monkeypatch.delenv("PROJECT_ULT_FRONTEND_URL", raising=False)
    monkeypatch.delenv("PROJECT_ULT_API_BASE", raising=False)

    assert module.live_api_ui_smoke_status() == {
        "status": "blocked",
        "executed": False,
        "blocker": (
            "missing PROJECT_ULT_FRONTEND_URL / PROJECT_ULT_API_BASE; "
            "live API/UI smoke not executed"
        ),
        "required_env": ["PROJECT_ULT_FRONTEND_URL", "PROJECT_ULT_API_BASE"],
        "env_values_recorded": False,
        "server_reachability_checked": False,
    }


def test_verify_frontend_api_root_requires_exact_merge_commit(tmp_path: Path) -> None:
    module = _load_module()
    fake_root = tmp_path / "frontend-api"
    (fake_root / "src" / "frontend_api").mkdir(parents=True)

    with pytest.raises(RuntimeError, match="origin/main merge commit"):
        module.verify_frontend_api_root(fake_root)


def test_report_hygiene_rejects_local_paths_and_secret_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-secret-token")

    with pytest.raises(RuntimeError, match="hygiene violation"):
        module._assert_evidence_hygiene({"path": "/tmp/private.json"})

    with pytest.raises(RuntimeError, match="secret-like value"):
        module._assert_evidence_hygiene({"token": "sk-test-secret-token"})
