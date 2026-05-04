from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest


ASSEMBLY_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ASSEMBLY_ROOT / "scripts" / "m4_ex3_reasoner_consumption_proof.py"
MISSING_CONTRACTS_REASON = (
    "contracts.schemas unavailable; M4.5 Ex-3 contract validation blocked"
)


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "m4_ex3_reasoner_consumption_proof",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _skip_if_contracts_missing(module: Any) -> None:
    try:
        module._ensure_project_paths()
        from contracts.schemas import CandidateGraphDelta, Ex3CandidateGraphDelta
    except ModuleNotFoundError as exc:
        if exc.name in {"contracts", "contracts.schemas"}:
            pytest.skip(MISSING_CONTRACTS_REASON)
        raise

    assert CandidateGraphDelta is Ex3CandidateGraphDelta


def test_payload_validation_uses_candidate_graph_delta_schemas() -> None:
    module = _load_module()
    _skip_if_contracts_missing(module)

    payload = module.accepted_frozen_ex3_payload(delta_id="m4-5-proof-delta-test")
    validated = module.validate_accepted_frozen_ex3_payload(payload)

    assert validated["ex3_delta"].delta_id == "m4-5-proof-delta-test"
    assert validated["candidate_delta"].delta_id == "m4-5-proof-delta-test"
    assert validated["candidate_id"] == module.DEFAULT_CANDIDATE_ID
    assert validated["selection_ref"] == module.DEFAULT_SELECTION_REF
    assert (
        validated["ex3_delta"].model_dump(mode="python")
        == validated["candidate_delta"].model_dump(mode="python")
    )


def test_payload_validation_requires_accepted_and_frozen() -> None:
    module = _load_module()
    payload = module.accepted_frozen_ex3_payload()
    payload["validation_status"] = "pending"

    with pytest.raises(RuntimeError, match="accepted"):
        module.validate_accepted_frozen_ex3_payload(payload)

    payload = module.accepted_frozen_ex3_payload()
    payload["freeze_status"] = "open"

    with pytest.raises(RuntimeError, match="frozen"):
        module.validate_accepted_frozen_ex3_payload(payload)


def test_sanitizer_keeps_only_safe_graph_summary_fields() -> None:
    module = _load_module()
    _skip_if_contracts_missing(module)

    validated = module.validate_accepted_frozen_ex3_payload(
        module.accepted_frozen_ex3_payload()
    )
    summary = module.sanitize_graph_summary(validated["ex3_delta"])

    assert summary == {
        "delta_id": module.DEFAULT_DELTA_ID,
        "delta_type": "add",
        "source_node": "ENT_M4_5_SOURCE",
        "target_node": module.DEFAULT_ENTITY_ID,
        "relation_type": "SUPPLY_CHAIN",
        "properties": {
            "confidence": 0.91,
            "direction": "bullish",
            "impact_score": 0.63,
            "same_cycle": True,
            "weight": 0.82,
        },
        "evidence_refs": ["m4.5:evidence:ex3-reasoner-delta-1"],
        "cycle_id": module.DEFAULT_CYCLE_ID,
        "candidate_id": module.DEFAULT_CANDIDATE_ID,
        "selection_ref": module.DEFAULT_SELECTION_REF,
    }
    summary_text = json.dumps(summary, sort_keys=True)
    assert "raw_text" not in summary_text
    assert "chunk" not in summary_text
    assert "light_rag_artifact" not in summary_text
    assert "large_blob" not in summary_text
    assert "metadata" not in summary_text
    assert "private_queue" not in summary_text


def test_reasoner_input_keeps_graph_fields_and_no_forbidden_fields() -> None:
    module = _load_module()
    _skip_if_contracts_missing(module)

    report = module.run_deterministic_proof()

    reasoner_input = report["reasoner_input"]
    serialized_payload = reasoner_input["serialized_payload"]
    contract_request = reasoner_input["contract_request"]
    graph_features = serialized_payload["graph_features"]

    assert set(graph_features) == {
        "ex3_graph_signals",
        "same_cycle_ex3_graph_signals",
    }
    expected_signal = {
        "delta_id": module.DEFAULT_DELTA_ID,
        "delta_type": "add",
        "source_node": "ENT_M4_5_SOURCE",
        "target_node": module.DEFAULT_ENTITY_ID,
        "relation_type": "SUPPLY_CHAIN",
        "properties": {
            "confidence": 0.91,
            "direction": "bullish",
            "impact_score": 0.63,
            "same_cycle": True,
            "weight": 0.82,
        },
        "evidence_refs": ["m4.5:evidence:ex3-reasoner-delta-1"],
        "cycle_id": module.DEFAULT_CYCLE_ID,
        "candidate_id": module.DEFAULT_CANDIDATE_ID,
        "selection_ref": module.DEFAULT_SELECTION_REF,
    }
    assert graph_features["ex3_graph_signals"] == [expected_signal]
    assert graph_features["same_cycle_ex3_graph_signals"] == [expected_signal]
    assert reasoner_input["retained_delta_ids"] == [module.DEFAULT_DELTA_ID]
    assert reasoner_input["retained_graph_feature_shape"] == "list"
    assert contract_request["context"]["graph_features"] == graph_features
    module._assert_no_forbidden_fields(reasoner_input)

    for key in ("ex3_graph_signals", "same_cycle_ex3_graph_signals"):
        assert isinstance(graph_features[key], list)
        assert all("signals" not in signal for signal in graph_features[key])

    payload_text = json.dumps(reasoner_input, sort_keys=True)
    assert "raw_text" not in payload_text
    assert "chunk" not in payload_text
    assert "light_rag_artifact" not in payload_text
    assert "large_blob" not in payload_text
    assert "metadata" not in payload_text
    assert "private_queue" not in payload_text


def test_main_writes_json_markdown_and_redacts_without_live_pg(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    _skip_if_contracts_missing(module)
    json_out = tmp_path / "proof.json"
    markdown_out = tmp_path / "proof.md"
    secret_dsn = "postgresql://proof_user:supersecret@localhost:5432/proofdb"
    monkeypatch.setenv(module.LIVE_PG_DSN_ENV, "")
    monkeypatch.setenv("DATABASE_URL", secret_dsn)
    monkeypatch.setenv("POSTGRES_PASSWORD", "supersecret")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-secret-token")

    exit_code = module.main(
        [
            "--out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
        ]
    )

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    json_text = json_out.read_text(encoding="utf-8")
    markdown_text = markdown_out.read_text(encoding="utf-8")
    combined_text = json_text + markdown_text
    assert exit_code == 0
    assert payload["status"] == "passed"
    assert payload["deterministic_proof"]["status"] == "passed"
    assert payload["accepted_frozen_ex3"]["candidate_id"] == module.DEFAULT_CANDIDATE_ID
    assert payload["accepted_frozen_ex3"]["selection_ref"] == module.DEFAULT_SELECTION_REF
    assert payload["live_pg"] == {
        "status": "blocked",
        "blocker": module.LIVE_PG_BLOCKER,
        "dsn": "<missing>",
        "destructive_db_operations_run": False,
    }
    assert payload["prerequisite_artifact"] == {
        "milestone": "M3.5",
        "artifact_pr": "#49",
        "merge_commit": "7dec6cd999998bcbb36f20a40406152969c09f93",
    }
    assert secret_dsn not in combined_text
    assert "supersecret" not in combined_text
    assert "sk-test-secret-token" not in combined_text
    assert "Traceback (most recent call last)" not in combined_text


def test_source_scan_reports_no_reasoner_runtime_forbidden_imports() -> None:
    module = _load_module()

    scan = module.scan_reasoner_runtime_imports(
        module.REASONER_RUNTIME_ROOT / "reasoner_runtime"
    )

    assert scan["status"] == "passed"
    assert scan["passed"] is True
    assert scan["forbidden_imports_found"] == []
    assert scan["python_file_count"] > 0
    assert "graph_engine" in scan["claim"]
    assert "data_platform" in scan["claim"]


def test_source_scan_detects_forbidden_imports(tmp_path: Path) -> None:
    module = _load_module()
    package = tmp_path / "reasoner_runtime"
    package.mkdir()
    (package / "__init__.py").write_text(
        "import graph_engine\nfrom data_platform.cycle import create_cycle\n",
        encoding="utf-8",
    )

    scan = module.scan_reasoner_runtime_imports(package)

    assert scan["status"] == "failed"
    assert scan["passed"] is False
    assert {
        finding["module"] for finding in scan["forbidden_imports_found"]
    } == {"graph_engine", "data_platform"}
