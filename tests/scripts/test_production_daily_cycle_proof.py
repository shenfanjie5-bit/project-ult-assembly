from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from typing import Any


ASSEMBLY_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ASSEMBLY_ROOT / "scripts" / "production_daily_cycle_proof.py"


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "production_daily_cycle_proof",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeAssetKey:
    def __init__(self, name: str) -> None:
        self.path = [name]

    def to_user_string(self) -> str:
        return "/".join(self.path)


class FailingSelection:
    def resolve(self, assets: object) -> object:
        del assets
        raise RuntimeError("selection resolution failed")


def _materialization_event(index: int, asset_name: str) -> SimpleNamespace:
    del index
    asset_key = FakeAssetKey(asset_name)
    materialization = SimpleNamespace(
        asset_key=asset_key,
        metadata={"rows": SimpleNamespace(value=1)},
    )
    return SimpleNamespace(
        event_type_value="ASSET_MATERIALIZATION",
        step_key=asset_name,
        message=f"materialized {asset_name}",
        asset_key=asset_key,
        is_step_materialization=True,
        event_specific_data=SimpleNamespace(materialization=materialization),
    )


def test_dagster_execution_evidence_rejects_incomplete_15_materialization_claim() -> None:
    module = _load_module()
    result = SimpleNamespace(
        success=False,
        run_id="run-123",
        all_events=(
            _materialization_event(0, "phase0_readiness_ping"),
            _materialization_event(1, "candidate_freeze"),
            SimpleNamespace(
                event_type_value="STEP_FAILURE",
                step_key="graph_status",
                message="graph status failed",
                is_step_failure=True,
                event_specific_data=SimpleNamespace(
                    error=RuntimeError("status row missing"),
                ),
            ),
        ),
    )

    evidence = module._dagster_execution_evidence_from_result(
        result,
        cycle_id="CYCLE_20260415",
        job_name="daily_cycle_job",
        selected_asset_keys=[
            "phase0_readiness_ping",
            "candidate_freeze",
            "graph_status",
        ],
        expected_materialization_count=15,
    )

    assert evidence["run_id"] == "run-123"
    assert evidence["cycle_id"] == "CYCLE_20260415"
    assert evidence["dagster_success"] is False
    assert evidence["failure_step"] == "graph_status"
    assert evidence["materialized_asset_keys"] == [
        "phase0_readiness_ping",
        "candidate_freeze",
    ]
    assert evidence["materializations"] == [
        {
            "index": 0,
            "step_key": "phase0_readiness_ping",
            "asset_key": "phase0_readiness_ping",
            "metadata": {"rows": 1},
        },
        {
            "index": 1,
            "step_key": "candidate_freeze",
            "asset_key": "candidate_freeze",
            "metadata": {"rows": 1},
        },
    ]
    assert evidence["materialization_count_against_claim_15"] == {
        "claim_count": 15,
        "actual_count": 2,
        "actual_unique_count": 2,
        "has_at_least_15": False,
        "has_exactly_15": False,
    }
    assert evidence["selected_asset_count_matches_claim"] is False
    assert evidence["missing_selected_asset_keys"] == ["graph_status"]
    assert evidence["terminal_observed_steps"] == []


def test_dagster_step_pass_claim_requires_artifact_backed_materializations() -> None:
    module = _load_module()

    failed_step = module._dagster_step_from_evidence(
        {
            "artifact": "/tmp/dagster-execution-evidence.json",
            "cycle_id": "CYCLE_20260415",
            "dagster_success": True,
            "run_id": "run-123",
            "materialized_asset_keys": ["a"],
            "materialized_asset_count": 1,
            "selected_asset_count": 1,
            "selected_materializations_complete": True,
            "materialization_count_against_claim_15": {
                "has_at_least_15": False,
                "has_exactly_15": False,
                "actual_unique_count": 1,
                "claim_count": 15,
            },
        }
    )
    passed_step = module._dagster_step_from_evidence(
        {
            "artifact": "/tmp/dagster-execution-evidence.json",
            "cycle_id": "CYCLE_20260415",
            "dagster_success": True,
            "run_id": "run-456",
            "materialized_asset_keys": [f"asset_{index}" for index in range(15)],
            "materialized_asset_count": 15,
            "selected_asset_count": 15,
            "selected_materializations_complete": True,
            "materialization_count_against_claim_15": {
                "has_at_least_15": True,
                "has_exactly_15": True,
                "actual_unique_count": 15,
                "claim_count": 15,
            },
        }
    )
    weak_step = module._dagster_step_from_evidence(
        {
            "artifact": "/tmp/dagster-execution-evidence.json",
            "cycle_id": "CYCLE_20260415",
            "dagster_success": True,
            "run_id": "run-789",
            "materialized_asset_keys": [f"asset_{index}" for index in range(15)],
            "materialized_asset_count": 15,
            "selected_asset_count": 0,
            "selected_materializations_complete": False,
            "materialization_count_against_claim_15": {
                "has_at_least_15": True,
                "has_exactly_15": True,
                "actual_unique_count": 15,
                "claim_count": 15,
            },
        }
    )

    assert failed_step["status"] == "failed"
    assert failed_step["artifact_backed_pass_claim"] is False
    assert passed_step["status"] == "passed"
    assert passed_step["artifact_backed_pass_claim"] is True
    assert weak_step["status"] == "failed"
    assert weak_step["artifact_backed_pass_claim"] is False


def test_selected_job_asset_keys_falls_back_to_definition_assets_for_all_assets_job() -> None:
    module = _load_module()
    job_def = SimpleNamespace(selection=None)
    defs = SimpleNamespace(
        assets=[
            SimpleNamespace(keys={FakeAssetKey("asset_b"), FakeAssetKey("asset_a")}),
            SimpleNamespace(specs=[SimpleNamespace(key=FakeAssetKey("asset_c"))]),
            SimpleNamespace(key=FakeAssetKey("asset_d")),
        ],
    )

    assert module._selected_job_asset_keys(job_def, defs) == [
        "asset_a",
        "asset_b",
        "asset_c",
        "asset_d",
    ]


def test_selected_job_asset_keys_falls_back_when_selection_cannot_resolve() -> None:
    module = _load_module()
    job_def = SimpleNamespace(selection=FailingSelection())
    defs = SimpleNamespace(
        assets=[
            SimpleNamespace(keys_by_output_name={"result": FakeAssetKey("asset_a")}),
        ],
    )

    assert module._selected_job_asset_keys(job_def, defs) == ["asset_a"]


def test_all_assets_selection_fallback_can_support_artifact_backed_pass_claim() -> None:
    module = _load_module()
    defs = SimpleNamespace(
        assets=[
            SimpleNamespace(key=FakeAssetKey(f"asset_{index}"))
            for index in range(15)
        ],
    )
    selected_asset_keys = module._selected_job_asset_keys(
        SimpleNamespace(selection=None),
        defs,
    )
    result = SimpleNamespace(
        success=True,
        run_id="run-all-assets",
        all_events=tuple(
            _materialization_event(index, asset_name)
            for index, asset_name in enumerate(selected_asset_keys)
        ),
    )

    evidence = module._dagster_execution_evidence_from_result(
        result,
        cycle_id="CYCLE_20260415",
        job_name="daily_cycle_job",
        selected_asset_keys=selected_asset_keys,
        expected_materialization_count=15,
    )
    step = module._dagster_step_from_evidence(evidence)

    assert evidence["selected_asset_count"] == 15
    assert evidence["selected_asset_count_matches_claim"] is True
    assert evidence["selected_materializations_complete"] is True
    assert step["status"] == "passed"
    assert step["artifact_backed_pass_claim"] is True


def test_dagster_step_rejects_partial_selection_even_with_15_materializations() -> None:
    module = _load_module()
    materialized_asset_keys = [f"asset_{index}" for index in range(15)]
    result = SimpleNamespace(
        success=True,
        run_id="run-partial-selection",
        all_events=tuple(
            _materialization_event(index, asset_name)
            for index, asset_name in enumerate(materialized_asset_keys)
        ),
    )

    evidence = module._dagster_execution_evidence_from_result(
        result,
        cycle_id="CYCLE_20260415",
        job_name="daily_cycle_job",
        selected_asset_keys=materialized_asset_keys[:14],
        expected_materialization_count=15,
    )
    step = module._dagster_step_from_evidence(evidence)

    assert evidence["materialization_count_against_claim_15"]["has_exactly_15"] is True
    assert evidence["extra_materialized_asset_keys"] == ["asset_14"]
    assert step["selected_asset_count_matches_claim"] is False
    assert step["status"] == "failed"
    assert step["artifact_backed_pass_claim"] is False


def test_graph_promotion_materialization_record_is_artifact_backed() -> None:
    module = _load_module()
    result = SimpleNamespace(
        success=True,
        run_id="run-graph-promotion",
        all_events=(
            _materialization_event(0, "candidate_freeze"),
            _materialization_event(1, "graph_status"),
            _materialization_event(2, "graph_promotion"),
        ),
    )

    evidence = module._dagster_execution_evidence_from_result(
        result,
        cycle_id="CYCLE_20260415",
        job_name="daily_cycle_job",
        selected_asset_keys=[
            "candidate_freeze",
            "graph_status",
            "graph_promotion",
        ],
        expected_materialization_count=15,
    )

    graph_promotion_records = [
        record
        for record in evidence["materializations"]
        if record["asset_key"] == "graph_promotion"
    ]
    assert graph_promotion_records == [
        {
            "index": 2,
            "step_key": "graph_promotion",
            "asset_key": "graph_promotion",
            "metadata": {"rows": 1},
        }
    ]


def test_asset_check_evidence_accepts_event_specific_data_evaluation_shape() -> None:
    module = _load_module()
    evaluation = SimpleNamespace(
        passed=True,
        check_name="neo4j_graph_consistency",
        metadata={"graph_status": SimpleNamespace(value="ready")},
    )
    event = SimpleNamespace(
        event_type_value="ASSET_CHECK_EVALUATION",
        step_key="graph_status_neo4j_graph_consistency_check",
        is_asset_check_evaluation=True,
        event_specific_data=evaluation,
    )
    result = SimpleNamespace(
        success=False,
        run_id="run-check",
        all_events=(event,),
    )

    evidence = module._dagster_execution_evidence_from_result(
        result,
        cycle_id="CYCLE_20260415",
        job_name="daily_cycle_job",
        selected_asset_keys=["graph_status"],
        expected_materialization_count=15,
    )

    assert evidence["asset_checks"] == [
        {
            "index": 0,
            "step_key": "graph_status_neo4j_graph_consistency_check",
            "asset_key": None,
            "check_name": "neo4j_graph_consistency",
            "passed": True,
            "metadata": {"graph_status": "ready"},
        }
    ]
