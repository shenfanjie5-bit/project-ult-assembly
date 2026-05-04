"""M4.5 proof: frozen Ex-3 graph deltas survive L6 reasoner input."""

from __future__ import annotations

import argparse
import ast
import json
import os
import sys
import traceback
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSEMBLY_ROOT = PROJECT_ROOT / "assembly"
CONTRACTS_ROOT = PROJECT_ROOT / "contracts"
MAIN_CORE_ROOT = PROJECT_ROOT / "main-core"
REASONER_RUNTIME_ROOT = PROJECT_ROOT / "reasoner-runtime"

DEFAULT_CYCLE_ID = "cycle-m4-5-ex3-reasoner-consumption"
DEFAULT_ENTITY_ID = "ENT_M4_5_TARGET"
DEFAULT_CANDIDATE_ID = 1
DEFAULT_DELTA_ID = "m4-5-ex3-reasoner-delta-1"
DEFAULT_SELECTION_REF = f"cycle_candidate_selection:{DEFAULT_CYCLE_ID}"
DEFAULT_GENERATED_AT = datetime(2026, 5, 5, tzinfo=UTC)
DEFAULT_OUT = (
    ASSEMBLY_ROOT
    / "reports"
    / "stabilization"
    / "m4-ex3-reasoner-consumption-proof-20260505.json"
)
LIVE_PG_DSN_ENV = "M4_EX3_DISPOSABLE_LIVE_PG_DSN"
LIVE_PG_BLOCKER = (
    f"{LIVE_PG_DSN_ENV} is not set; live_pg proof blocked; "
    "destructive DB operations were not run"
)
PREREQUISITE_ARTIFACT = {
    "milestone": "M3.5",
    "artifact_pr": "#49",
    "merge_commit": "7dec6cd999998bcbb36f20a40406152969c09f93",
}
SECRET_ENV_KEYS = (
    LIVE_PG_DSN_ENV,
    "DATABASE_URL",
    "DP_PG_DSN",
    "POSTGRES_PASSWORD",
    "OPENAI_API_KEY",
    "DP_TUSHARE_TOKEN",
    "NEO4J_PASSWORD",
    "ANTHROPIC_API_KEY",
)
SAFE_DELTA_FIELDS = (
    "delta_id",
    "delta_type",
    "source_node",
    "target_node",
    "relation_type",
)
SAFE_PROPERTY_FIELDS = (
    "confidence",
    "direction",
    "impact_score",
    "same_cycle",
    "time_horizon",
    "weight",
)
FORBIDDEN_FIELD_NAMES = frozenset(
    {
        "api_key",
        "chunk",
        "chunks",
        "ingest_seq",
        "internal_queue_id",
        "large_blob",
        "light_rag_artifact",
        "logs",
        "metadata",
        "password",
        "private_queue_id",
        "queue_id",
        "queue_record_id",
        "queue_row_id",
        "raw_log",
        "raw_logs",
        "raw_text",
        "refresh_token",
        "secret",
        "secrets",
        "submitted_at",
        "token",
    }
)
FORBIDDEN_IMPORT_ROOTS = frozenset({"data_platform", "graph_engine"})


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prove accepted frozen Ex-3 graph signals survive serialized "
            "main-core reasoner input without live database writes."
        ),
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--markdown-out",
        type=Path,
        default=None,
        help="Markdown sibling path. Defaults to --out with .md suffix.",
    )
    parser.add_argument(
        "--disposable-live-pg-dsn",
        default=os.environ.get(LIVE_PG_DSN_ENV),
        help=(
            "Optional isolated PostgreSQL DSN. This deterministic proof records "
            "its presence but does not run destructive database operations."
        ),
    )
    parser.add_argument(
        "--include-traceback",
        action="store_true",
        help="Include redacted traceback text in failed JSON evidence.",
    )
    args = parser.parse_args(argv)

    markdown_out = args.markdown_out or args.out.with_suffix(".md")
    report: dict[str, Any] = {
        "proof_id": "m4.5-ex3-reasoner-consumption-proof",
        "status": "failed",
        "generated_at": DEFAULT_GENERATED_AT.isoformat(),
        "prerequisite_artifact": dict(PREREQUISITE_ARTIFACT),
    }

    try:
        deterministic_proof = run_deterministic_proof()
        report.update(deterministic_proof)
        report["live_pg"] = _live_pg_status(args.disposable_live_pg_dsn)
        report["status"] = "passed"
        return 0
    except Exception as exc:  # noqa: BLE001 - evidence must preserve blockers.
        report["error"] = {
            "message": _redact_text(str(exc)),
            "type": type(exc).__name__,
        }
        if args.include_traceback:
            report["traceback"] = _redact_text(traceback.format_exc())
        return 1
    finally:
        write_reports(report, args.out, markdown_out)


def run_deterministic_proof() -> dict[str, Any]:
    _ensure_project_paths()

    accepted_payload = accepted_frozen_ex3_payload()
    validated = validate_accepted_frozen_ex3_payload(accepted_payload)
    ex3_delta = validated["ex3_delta"]
    candidate_delta = validated["candidate_delta"]
    delta_ids = [str(ex3_delta.delta_id)]

    if ex3_delta.model_dump(mode="python") != candidate_delta.model_dump(mode="python"):
        raise RuntimeError("CandidateGraphDelta and Ex3CandidateGraphDelta diverged")

    summary = sanitize_graph_summary(
        ex3_delta,
        cycle_id=DEFAULT_CYCLE_ID,
        candidate_id=validated["candidate_id"],
        selection_ref=validated["selection_ref"],
    )
    graph_features = build_graph_features(
        summaries=[summary],
    )
    context = build_alpha_context(
        cycle_id=DEFAULT_CYCLE_ID,
        entity_id=DEFAULT_ENTITY_ID,
        graph_features=graph_features,
    )
    reasoner_evidence = prove_reasoner_input_survives(
        entity_id=DEFAULT_ENTITY_ID,
        context=context,
        delta_ids=delta_ids,
    )
    source_scan = scan_reasoner_runtime_imports(
        REASONER_RUNTIME_ROOT / "reasoner_runtime"
    )
    if not source_scan["passed"]:
        raise RuntimeError(
            "reasoner-runtime forbidden import scan failed: "
            f"{source_scan['forbidden_imports_found']}"
        )

    report = {
        "deterministic_proof": {
            "status": "passed",
            "mode": "offline_contract_and_source_scan",
        },
        "accepted_frozen_ex3": {
            "candidate_id": validated["candidate_id"],
            "payload_type": accepted_payload["payload_type"],
            "selection_ref": validated["selection_ref"],
            "validation_status": accepted_payload["validation_status"],
            "freeze_status": accepted_payload["freeze_status"],
        },
        "validated_schemas": [
            "contracts.schemas.Ex3CandidateGraphDelta",
            "contracts.schemas.CandidateGraphDelta",
        ],
        "delta_ids": delta_ids,
        "graph_features": graph_features,
        "reasoner_input": reasoner_evidence,
        "source_scan": source_scan,
        "safety_assertions": {
            "unsafe_payload_fields_absent": True,
            "runtime_logs_included": False,
            "secret_values_included": False,
            "destructive_db_operations_run": False,
        },
    }
    _assert_no_forbidden_fields(report["graph_features"])
    _assert_no_forbidden_fields(report["reasoner_input"])
    _assert_no_secret_values(report)
    return report


def accepted_frozen_ex3_payload(delta_id: str = DEFAULT_DELTA_ID) -> dict[str, Any]:
    return {
        "payload_type": "Ex-3",
        "validation_status": "accepted",
        "freeze_status": "frozen",
        "candidate_id": DEFAULT_CANDIDATE_ID,
        "selection_ref": DEFAULT_SELECTION_REF,
        "payload": {
            "subsystem_id": "m4-5-ex3-reasoner-proof",
            "delta_id": delta_id,
            "delta_type": "add",
            "source_node": "ENT_M4_5_SOURCE",
            "target_node": DEFAULT_ENTITY_ID,
            "relation_type": "SUPPLY_CHAIN",
            "properties": {
                "confidence": 0.91,
                "direction": "bullish",
                "impact_score": 0.63,
                "same_cycle": True,
                "weight": 0.82,
                "raw_text": "producer-only text must not reach reasoner input",
                "light_rag_artifact": {"artifact_id": "unsafe"},
                "large_blob": "x" * 128,
                "metadata": {"queue_row_id": 42},
                "private_queue_id": "candidate_queue_private_42",
            },
            "evidence": ["m4.5:evidence:ex3-reasoner-delta-1"],
        },
    }


def validate_accepted_frozen_ex3_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("payload_type") != "Ex-3":
        raise RuntimeError("M4.5 proof payload_type must be Ex-3")
    if payload.get("validation_status") != "accepted":
        raise RuntimeError("M4.5 proof payload must be accepted")
    if payload.get("freeze_status") != "frozen":
        raise RuntimeError("M4.5 proof payload must be frozen")
    candidate_id = payload.get("candidate_id")
    if type(candidate_id) is not int or candidate_id < 1:
        raise RuntimeError("M4.5 proof payload must contain positive candidate_id")
    selection_ref = payload.get("selection_ref")
    if not isinstance(selection_ref, str) or not selection_ref.strip():
        raise RuntimeError("M4.5 proof payload must contain selection_ref")

    graph_delta_payload = payload.get("payload")
    if not isinstance(graph_delta_payload, Mapping):
        raise RuntimeError("M4.5 proof payload must contain graph delta mapping")

    _ensure_project_paths()
    from contracts.schemas import CandidateGraphDelta, Ex3CandidateGraphDelta

    ex3_delta = Ex3CandidateGraphDelta.model_validate(dict(graph_delta_payload))
    candidate_delta = CandidateGraphDelta.model_validate(dict(graph_delta_payload))
    return {
        "ex3_delta": ex3_delta,
        "candidate_delta": candidate_delta,
        "candidate_id": candidate_id,
        "selection_ref": selection_ref.strip(),
    }


def sanitize_graph_summary(
    delta: Any,
    *,
    cycle_id: str = DEFAULT_CYCLE_ID,
    candidate_id: int = DEFAULT_CANDIDATE_ID,
    selection_ref: str = DEFAULT_SELECTION_REF,
) -> dict[str, Any]:
    payload = _model_dump(delta)
    summary = {
        field_name: _json_safe(payload[field_name])
        for field_name in SAFE_DELTA_FIELDS
        if field_name in payload
    }
    properties = payload.get("properties")
    safe_properties: dict[str, Any] = {}
    if isinstance(properties, Mapping):
        for key in SAFE_PROPERTY_FIELDS:
            if key in properties and _is_safe_summary_value(properties[key]):
                safe_properties[key] = _json_safe(properties[key])
    if safe_properties:
        summary["properties"] = safe_properties
    evidence = payload.get("evidence")
    if isinstance(evidence, list):
        summary["evidence_refs"] = [_json_safe(item) for item in evidence]
    summary["cycle_id"] = cycle_id
    summary["candidate_id"] = int(candidate_id)
    summary["selection_ref"] = selection_ref
    _assert_no_forbidden_fields(summary)
    return summary


def build_graph_features(
    *,
    summaries: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    safe_summaries = [_json_safe(dict(summary)) for summary in summaries]
    graph_features = {
        "ex3_graph_signals": list(safe_summaries),
        "same_cycle_ex3_graph_signals": [dict(summary) for summary in safe_summaries],
    }
    _assert_no_forbidden_fields(graph_features)
    return graph_features


def build_alpha_context(
    *,
    cycle_id: str,
    entity_id: str,
    graph_features: Mapping[str, Any],
) -> Any:
    _ensure_project_paths()
    from main_core.common.contexts import AlphaAnalysisContext
    from main_core.common.schemas import FeatureSignalBundle, WorldStateSnapshot

    return AlphaAnalysisContext(
        cycle_id=cycle_id,
        entity_id=entity_id,
        feature_bundle=FeatureSignalBundle(
            cycle_id=cycle_id,
            entity_id=entity_id,
            feature_values={"m4_5_contract_feature": 1.0},
            signal_values={"contract_signal": {"value": 1.0, "source": "m4.5"}},
            graph_features=dict(graph_features),
            feature_weight_multiplier={"m4_5_contract_feature": 1.0},
            generated_at=DEFAULT_GENERATED_AT,
        ),
        world_state=WorldStateSnapshot(
            cycle_id=cycle_id,
            baseline_regime="neutral",
            llm_delta=0,
            final_regime="neutral",
            llm_rationale="deterministic proof fixture",
            actual_model_used="deterministic-fixture",
            actual_provider="local",
            fallback_path=[],
        ),
        similar_cases=[{"entity_id": "ENT_M4_5_SIMILAR", "score": 0.31}],
    )


def prove_reasoner_input_survives(
    *,
    entity_id: str,
    context: Any,
    delta_ids: Sequence[str],
) -> dict[str, Any]:
    _ensure_project_paths()
    from contracts.schemas import ReasonerRequest
    from main_core.l6_alpha.multi_agent_analyzer import build_multi_agent_input_payload

    feature_bundle_payload = context.feature_bundle.model_dump(mode="json")
    graph_features = feature_bundle_payload["graph_features"]
    reasoner_payload = build_multi_agent_input_payload(entity_id, context)
    serialized_reasoner_payload = json.loads(
        json.dumps(_json_safe(reasoner_payload), sort_keys=True)
    )
    contract_request = ReasonerRequest(
        request_id="m4-5-ex3-reasoner-request-1",
        cycle_id=context.cycle_id,
        reasoner_name="main-core.l6_alpha.multi_agent",
        reasoner_version="0.1.0",
        prompt="Assess alpha using structured graph context.",
        context=serialized_reasoner_payload,
        requested_at=DEFAULT_GENERATED_AT,
        input_refs=[f"ex3-delta:{delta_id}" for delta_id in delta_ids],
    )
    serialized_contract_request = contract_request.model_dump(mode="json")
    retained = serialized_contract_request["context"]["graph_features"]
    expected_keys = ["ex3_graph_signals", "same_cycle_ex3_graph_signals"]

    for key in expected_keys:
        if retained.get(key) != graph_features.get(key):
            raise RuntimeError(f"serialized reasoner input did not retain {key}")
        if not isinstance(retained.get(key), list):
            raise RuntimeError(f"serialized reasoner input retained {key} as non-list")

    retained_delta_ids = sorted(
        {
            str(signal["delta_id"])
            for key in expected_keys
            for signal in retained[key]
        }
    )
    if retained_delta_ids != sorted(str(delta_id) for delta_id in delta_ids):
        raise RuntimeError(
            "serialized reasoner input did not retain expected delta ids: "
            f"{retained_delta_ids}"
        )

    evidence = {
        "serializer": "main_core.l6_alpha.multi_agent_analyzer.build_multi_agent_input_payload",
        "retained_graph_feature_keys": expected_keys,
        "retained_delta_ids": retained_delta_ids,
        "retained_graph_feature_shape": "list",
        "serialized_payload": serialized_reasoner_payload,
        "contract_request": serialized_contract_request,
    }
    _assert_no_forbidden_fields(evidence)
    _assert_no_secret_values(evidence)
    return evidence


def scan_reasoner_runtime_imports(runtime_root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    python_files = sorted(
        path
        for path in runtime_root.rglob("*.py")
        if ".venv" not in path.parts and ".git" not in path.parts
    )
    for path in python_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            for module in _imported_module_roots(node):
                if module in FORBIDDEN_IMPORT_ROOTS:
                    findings.append(
                        {
                            "path": str(path.relative_to(runtime_root.parent)),
                            "line": getattr(node, "lineno", None),
                            "module": module,
                        }
                    )

    return {
        "status": "passed" if not findings else "failed",
        "passed": not findings,
        "runtime_path": str(runtime_root),
        "python_file_count": len(python_files),
        "forbidden_imports_found": findings,
        "claim": (
            "reasoner-runtime package has no imports of graph_engine or data_platform"
        ),
    }


def write_reports(report: Mapping[str, Any], json_out: Path, markdown_out: Path) -> None:
    safe_report = _redact_value(_json_safe(report))
    _assert_no_secret_values(safe_report)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(
        json.dumps(safe_report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(markdown_report(safe_report), encoding="utf-8")


def markdown_report(report: Mapping[str, Any]) -> str:
    delta_ids = ", ".join(str(delta_id) for delta_id in report.get("delta_ids", []))
    accepted_ex3 = report.get("accepted_frozen_ex3", {})
    reasoner_input = report.get("reasoner_input", {})
    retained_keys = ", ".join(
        str(key) for key in reasoner_input.get("retained_graph_feature_keys", [])
    )
    live_pg = report.get("live_pg", {})
    source_scan = report.get("source_scan", {})
    safety = report.get("safety_assertions", {})
    return "\n".join(
        [
            "# M4.5 Ex-3 Reasoner Consumption Proof",
            "",
            f"- Status: {report.get('status')}",
            f"- Generated at: {report.get('generated_at')}",
            "- Prerequisite: M3.5 artifact PR #49, merge commit "
            "7dec6cd999998bcbb36f20a40406152969c09f93",
            f"- Delta ids: {delta_ids}",
            f"- Candidate id: {accepted_ex3.get('candidate_id')}",
            f"- Retained graph feature keys: {retained_keys}",
            f"- Retained graph feature shape: {reasoner_input.get('retained_graph_feature_shape')}",
            f"- Source scan: {source_scan.get('status')} - {source_scan.get('claim')}",
            f"- Live PG status: {live_pg.get('status')}",
            f"- Live PG blocker: {live_pg.get('blocker')}",
            f"- Runtime logs included: {safety.get('runtime_logs_included')}",
            f"- Secret values included: {safety.get('secret_values_included')}",
            "",
        ]
    )


def _live_pg_status(disposable_live_pg_dsn: str | None) -> dict[str, Any]:
    if not disposable_live_pg_dsn:
        return {
            "status": "blocked",
            "blocker": LIVE_PG_BLOCKER,
            "dsn": "<missing>",
            "destructive_db_operations_run": False,
        }
    return {
        "status": "not_run",
        "blocker": (
            "live_pg proof intentionally not executed in deterministic default; "
            "destructive DB operations were not run"
        ),
        "dsn": "<redacted:set>",
        "destructive_db_operations_run": False,
    }


def _imported_module_roots(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name.split(".", maxsplit=1)[0] for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.module:
        return [node.module.split(".", maxsplit=1)[0]]
    return []


def _ensure_project_paths() -> None:
    for path in (
        CONTRACTS_ROOT / "src",
        MAIN_CORE_ROOT / "src",
    ):
        path_text = str(path)
        if path_text not in sys.path:
            sys.path.insert(0, path_text)


def _model_dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="python")
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError(f"expected Pydantic model or mapping, got {type(value).__name__}")


def _is_safe_summary_value(value: Any) -> bool:
    if value is None or isinstance(value, str | int | float | bool):
        return True
    if isinstance(value, list | tuple):
        return all(_is_safe_summary_value(item) for item in value)
    return False


def _assert_no_forbidden_fields(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized_key = str(key).lower()
            if _is_forbidden_field_name(normalized_key):
                raise RuntimeError(f"forbidden field survived at {path}.{key}")
            _assert_no_forbidden_fields(item, f"{path}.{key}")
    elif isinstance(value, list | tuple | set | frozenset):
        for index, item in enumerate(value):
            _assert_no_forbidden_fields(item, f"{path}[{index}]")


def _is_forbidden_field_name(normalized_key: str) -> bool:
    return (
        normalized_key in FORBIDDEN_FIELD_NAMES
        or normalized_key.startswith("private_queue")
        or normalized_key.startswith("internal_queue")
        or normalized_key.startswith("queue_")
    )


def _assert_no_secret_values(value: Any) -> None:
    text = json.dumps(_json_safe(value), sort_keys=True, default=str)
    if _redact_text(text) != text:
        raise RuntimeError("secret-like value survived evidence serialization")


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
