from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


ASSEMBLY_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ASSEMBLY_ROOT / "scripts" / "m4_ex3_queue_promotion_proof.py"


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "m4_ex3_queue_promotion_proof",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ex3_queue_payload_matches_contract_and_promotion_plan() -> None:
    module = _load_module()
    module._ensure_project_paths()

    from contracts.schemas import CandidateGraphDelta

    payload = module._ex3_queue_payload()
    contract_payload = {
        key: value
        for key, value in payload.items()
        if key not in {"payload_type", "submitted_by"}
    }
    delta = CandidateGraphDelta.model_validate(contract_payload)

    plan, writer = module._promote_deltas(
        "CYCLE_20260418",
        "cycle_candidate_selection:CYCLE_20260418",
        [delta],
    )

    assert writer.called is True
    assert writer.plan is plan
    assert plan.delta_ids == ["m4-ex3-queue-promotion-delta-1"]
    assert len(plan.edge_records) == 1
    assert plan.edge_records[0].relationship_type == "SUPPLY_CHAIN"


def test_ex3_queue_payload_accepts_unique_delta_id() -> None:
    module = _load_module()

    payload = module._ex3_queue_payload(delta_id="m4-proof-unique-delta")

    assert payload["delta_id"] == "m4-proof-unique-delta"


def test_promotion_output_assertion_requires_writer_call() -> None:
    module = _load_module()
    writer = module._CapturingCanonicalWriter()
    plan = SimpleNamespace(
        delta_ids=["delta-1"],
        edge_records=[SimpleNamespace(edge_id="delta-1")],
    )

    with pytest.raises(RuntimeError, match="canonical writer"):
        module._assert_promotion_plan_output("delta-1", plan, writer)


def test_promotion_output_assertion_requires_proof_edge() -> None:
    module = _load_module()
    writer = module._CapturingCanonicalWriter()
    plan = SimpleNamespace(
        delta_ids=["delta-1"],
        edge_records=[],
    )
    writer.write_canonical_records(plan)

    with pytest.raises(RuntimeError, match="proof edge"):
        module._assert_promotion_plan_output("delta-1", plan, writer)


def test_main_records_missing_database_url_as_live_prerequisite(
    tmp_path: Path,
) -> None:
    module = _load_module()
    out = tmp_path / "proof.json"

    exit_code = module.main(
        [
            "--database-url",
            "",
            "--out",
            str(out),
        ]
    )

    payload = __import__("json").loads(out.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert payload["status"] == "failed"
    assert payload["skipped_live_prerequisites"] == ["DATABASE_URL or DP_PG_DSN"]
