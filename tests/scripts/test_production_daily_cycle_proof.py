from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
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


def _install_fake_graph_engine_modules(monkeypatch: Any, client_cls: type) -> None:
    graph_engine = ModuleType("graph_engine")
    graph_engine.__path__ = []  # type: ignore[attr-defined]
    client_module = ModuleType("graph_engine.client")
    config_module = ModuleType("graph_engine.config")
    propagation_module = ModuleType("graph_engine.propagation")
    propagation_module.__path__ = []  # type: ignore[attr-defined]
    gds_module = ModuleType("graph_engine.propagation._gds")

    client_module.Neo4jClient = client_cls
    config_module.load_config_from_env = lambda: SimpleNamespace(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="password",
        database="neo4j",
    )

    def probe_gds_availability(client: Any) -> Any:
        version_rows = client.execute_read(
            "CALL gds.version() YIELD gdsVersion RETURN gdsVersion",
            {},
        )
        exists_rows = client.execute_read(
            "CALL gds.graph.exists($graph_name) YIELD exists RETURN exists",
            {"graph_name": "__graph_engine_gds_probe__"},
        )
        return SimpleNamespace(
            gds_version=version_rows[0]["gdsVersion"],
            graph_exists_procedure_available=isinstance(
                exists_rows[0].get("exists"),
                bool,
            ),
        )

    gds_module.probe_gds_availability = probe_gds_availability

    monkeypatch.setitem(sys.modules, "graph_engine", graph_engine)
    monkeypatch.setitem(sys.modules, "graph_engine.client", client_module)
    monkeypatch.setitem(sys.modules, "graph_engine.config", config_module)
    monkeypatch.setitem(sys.modules, "graph_engine.propagation", propagation_module)
    monkeypatch.setitem(sys.modules, "graph_engine.propagation._gds", gds_module)


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


def _asset_check_event(
    index: int,
    check_name: str,
    *,
    passed: bool | None = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        event_type_value="ASSET_CHECK_EVALUATION",
        step_key=f"{check_name}_step",
        is_asset_check_evaluation=True,
        event_specific_data=SimpleNamespace(
            passed=passed,
            check_name=check_name,
            metadata={"check_index": SimpleNamespace(value=index)},
        ),
    )


def _asset_check_record(
    check_name: str,
    *,
    passed: bool | None = True,
) -> dict[str, Any]:
    return {
        "check_name": check_name,
        "passed": passed,
        "metadata": {},
    }


def _passing_asset_check_records(module: Any) -> list[dict[str, Any]]:
    return [
        _asset_check_record(check_name)
        for check_name in module.EXPECTED_DAGSTER_ASSET_CHECK_NAMES
    ]


def _passing_asset_check_events(
    module: Any,
    *,
    start_index: int,
) -> tuple[SimpleNamespace, ...]:
    return tuple(
        _asset_check_event(index, check_name)
        for index, check_name in enumerate(
            module.EXPECTED_DAGSTER_ASSET_CHECK_NAMES,
            start=start_index,
        )
    )


def test_neo4j_gds_preflight_writes_pass_artifact(tmp_path: Path, monkeypatch: Any) -> None:
    module = _load_module()

    class FakeGDSClient:
        def __init__(self, config: object) -> None:
            self.config = config

        def __enter__(self) -> "FakeGDSClient":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def verify_connectivity(self) -> bool:
            return True

        def execute_read(
            self,
            query: str,
            parameters: dict[str, Any],
        ) -> list[dict[str, Any]]:
            if "gds.version" in query:
                return [{"gdsVersion": "2.13.2"}]
            if "gds.graph.exists" in query:
                assert parameters == {"graph_name": "__graph_engine_gds_probe__"}
                return [{"exists": False}]
            raise AssertionError(f"unexpected query: {query}")

    _install_fake_graph_engine_modules(monkeypatch, FakeGDSClient)
    monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7687")
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "password")

    result = module._probe_neo4j_gds(tmp_path)
    payload = json.loads((tmp_path / "neo4j-gds-preflight.json").read_text())

    assert result["status"] == "passed"
    assert result["blocker"] is None
    assert result["gds_version"] == "2.13.2"
    assert payload["blocker"] is None
    assert payload["gds_graph_exists_probe"] == {
        "graph_name": "__graph_engine_gds_probe__",
        "procedure_available": True,
    }
    assert payload["v5_0_1_semantics"]["neo4j_role"] == "hot_mirror"


def test_neo4j_gds_preflight_writes_blocker_artifact(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    module = _load_module()

    class MissingGDSClient:
        def __init__(self, config: object) -> None:
            self.config = config

        def __enter__(self) -> "MissingGDSClient":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def verify_connectivity(self) -> bool:
            return True

        def execute_read(
            self,
            query: str,
            parameters: dict[str, Any],
        ) -> list[dict[str, Any]]:
            del query, parameters
            raise RuntimeError("GDS plugin not available")

    _install_fake_graph_engine_modules(monkeypatch, MissingGDSClient)
    monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7687")
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "password")

    result = module._probe_neo4j_gds(tmp_path)
    payload = json.loads((tmp_path / "neo4j-gds-preflight.json").read_text())

    assert result["status"] == "failed"
    assert result["blocker"] == "configured_neo4j_gds_runtime"
    assert payload["status"] == "failed"
    assert payload["error"] == "GDS plugin not available"


def test_proof_graph_delta_payload_is_valid_ex3_contract() -> None:
    module = _load_module()

    nodes = module._proof_graph_nodes(("600519.SH", "000001.SZ"))
    payload = module._proof_graph_delta_payload(
        cycle_id="CYCLE_20260415",
        nodes=nodes,
    )

    from contracts.schemas import CandidateGraphDelta

    contract_payload = {
        key: value
        for key, value in payload.items()
        if key not in {"payload_type", "submitted_by"}
    }
    delta = CandidateGraphDelta.model_validate(contract_payload)

    assert payload["payload_type"] == "Ex-3"
    assert payload["submitted_by"] == module.SUBMITTED_BY
    assert delta.delta_type == "upsert_edge"
    assert delta.relation_type == "SUPPLY_CHAIN"
    assert delta.properties["propagation_channel"] == "fundamental"
    assert [node["node_id"] for node in nodes] == [
        "proof-node-600519_SH",
        "proof-node-000001_SZ",
    ]


def test_proof_graph_nodes_require_two_symbols() -> None:
    module = _load_module()

    import pytest

    with pytest.raises(RuntimeError, match="at least two current-cycle symbols"):
        module._proof_graph_nodes(("600519.SH",))


def test_proof_report_dates_use_run_date_not_baseline_date() -> None:
    module = _load_module()

    dates = module._proof_report_dates(module.datetime(2026, 5, 1, tzinfo=module.UTC))

    assert dates == {
        "baseline_evidence_date": "2026-04-28",
        "evidence_date": "2026-05-01",
        "proof_run_date": "2026-05-01",
    }


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
        legacy_materialization_claim_count=15,
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
    assert evidence["materialization_count_against_selected_assets"] == {
        "expected_selected_asset_count": 3,
        "actual_count": 2,
        "actual_unique_count": 2,
        "has_exactly_selected_asset_count": False,
        "missing_selected_asset_count": 1,
        "extra_materialized_asset_count": 0,
    }
    assert evidence["legacy_materialization_count_against_claim_15"] == {
        "legacy_claim_count": 15,
        "actual_count": 2,
        "actual_unique_count": 2,
        "has_at_least_15": False,
        "has_exactly_15": False,
        "historical_only": True,
    }
    assert evidence["selected_asset_count_matches_legacy_claim"] is False
    assert evidence["missing_selected_asset_keys"] == ["graph_status"]
    assert evidence["terminal_observed_steps"] == []
    step = module._dagster_step_from_evidence(evidence)
    assert step["failure_error"] == {
        "message": "status row missing",
        "type": "RuntimeError",
    }
    assert step["failure_root_cause"] == "status row missing"


def test_finalized_dagster_artifact_persists_step_summary(tmp_path: Path) -> None:
    module = _load_module()
    evidence_path = tmp_path / "dagster-execution-evidence.json"
    evidence = {
        "schema_version": "test",
        "status": "failed",
        "artifact": str(evidence_path),
        "cycle_id": "CYCLE_20260415",
        "dagster_success": False,
        "run_id": "run-123",
        "selected_asset_count": 3,
        "selected_materializations_complete": False,
        "materialized_asset_keys": ["candidate_freeze"],
        "materialized_asset_count": 1,
        "materialization_count_against_selected_assets": {
            "expected_selected_asset_count": 3,
            "actual_unique_count": 1,
        },
        "legacy_materialization_count_against_claim_15": {
            "legacy_claim_count": 15,
            "actual_unique_count": 1,
            "has_exactly_15": False,
        },
        "failure_step": "graph_snapshot",
        "failure_events": [
            {
                "error": {
                    "message": (
                        "ValueError: GraphImpactSnapshot requires at least one "
                        "target entity for cycle_id='CYCLE_20260415'"
                    ),
                    "type": "ValueError",
                }
            }
        ],
    }

    step = module._finalize_dagster_evidence(
        evidence,
        evidence_path,
        module.perf_counter(),
    )
    payload = json.loads(evidence_path.read_text())

    assert step["failure_step"] == "graph_snapshot"
    assert payload["failure_root_cause"].startswith(
        "ValueError: GraphImpactSnapshot requires at least one target entity"
    )
    assert payload["artifact_backed_pass_claim"] is False
    assert payload["supports_selected_asset_materialization_claim"] is False
    assert payload["supports_legacy_15_materializations_claim"] is False
    assert payload["dagster_step_summary"]["failure_root_cause"] == payload[
        "failure_root_cause"
    ]


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
            "materialization_count_against_selected_assets": {
                "expected_selected_asset_count": 2,
                "actual_unique_count": 1,
            },
        }
    )
    passed_step = module._dagster_step_from_evidence(
        {
            "artifact": "/tmp/dagster-execution-evidence.json",
            "cycle_id": "CYCLE_20260415",
            "dagster_success": True,
            "run_id": "run-456",
            "asset_checks": _passing_asset_check_records(module),
            "materialized_asset_keys": [f"asset_{index}" for index in range(15)],
            "materialized_asset_count": 15,
            "selected_asset_count": 15,
            "selected_materializations_complete": True,
            "materialization_count_against_selected_assets": {
                "expected_selected_asset_count": 15,
                "actual_unique_count": 15,
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
            "materialization_count_against_selected_assets": {
                "expected_selected_asset_count": 15,
                "actual_unique_count": 15,
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
            for index in range(17)
        ],
    )
    selected_asset_keys = module._selected_job_asset_keys(
        SimpleNamespace(selection=None),
        defs,
    )
    result = SimpleNamespace(
        success=True,
        run_id="run-all-assets",
        all_events=(
            *tuple(
                _materialization_event(index, asset_name)
                for index, asset_name in enumerate(selected_asset_keys)
            ),
            *_passing_asset_check_events(
                module,
                start_index=len(selected_asset_keys),
            ),
        ),
    )

    evidence = module._dagster_execution_evidence_from_result(
        result,
        cycle_id="CYCLE_20260415",
        job_name="daily_cycle_job",
        selected_asset_keys=selected_asset_keys,
        legacy_materialization_claim_count=15,
    )
    step = module._dagster_step_from_evidence(evidence)

    assert evidence["selected_asset_count"] == 17
    assert evidence["selected_asset_count_matches_legacy_claim"] is False
    assert evidence["selected_materializations_complete"] is True
    assert evidence["materialization_count_against_selected_assets"] == {
        "expected_selected_asset_count": 17,
        "actual_count": 17,
        "actual_unique_count": 17,
        "has_exactly_selected_asset_count": True,
        "missing_selected_asset_count": 0,
        "extra_materialized_asset_count": 0,
    }
    assert step["status"] == "passed"
    assert step["artifact_backed_pass_claim"] is True
    assert step["supports_legacy_15_materializations_claim"] is False


def test_dagster_step_rejects_failed_asset_check_even_with_all_materializations() -> None:
    module = _load_module()
    selected_asset_keys = [f"asset_{index}" for index in range(17)]
    failed_check = module.EXPECTED_DAGSTER_ASSET_CHECK_NAMES[0]
    check_events = tuple(
        _asset_check_event(
            index,
            check_name,
            passed=False if check_name == failed_check else True,
        )
        for index, check_name in enumerate(
            module.EXPECTED_DAGSTER_ASSET_CHECK_NAMES,
            start=len(selected_asset_keys),
        )
    )
    result = SimpleNamespace(
        success=True,
        run_id="run-failed-check",
        all_events=(
            *tuple(
                _materialization_event(index, asset_name)
                for index, asset_name in enumerate(selected_asset_keys)
            ),
            *check_events,
        ),
    )

    evidence = module._dagster_execution_evidence_from_result(
        result,
        cycle_id="CYCLE_20260415",
        job_name="daily_cycle_job",
        selected_asset_keys=selected_asset_keys,
        legacy_materialization_claim_count=15,
    )
    step = module._dagster_step_from_evidence(evidence)

    assert evidence["dagster_success"] is True
    assert evidence["selected_materializations_complete"] is True
    assert step["status"] == "failed"
    assert step["artifact_backed_pass_claim"] is False
    assert step["asset_checks_complete"] is False
    assert step["failed_asset_check_names"] == [failed_check]


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
        legacy_materialization_claim_count=15,
    )
    step = module._dagster_step_from_evidence(evidence)

    assert (
        evidence["legacy_materialization_count_against_claim_15"]["has_exactly_15"]
        is True
    )
    assert evidence["extra_materialized_asset_keys"] == ["asset_14"]
    assert step["selected_asset_count_matches_materialization_basis"] is True
    assert step["status"] == "failed"
    assert step["artifact_backed_pass_claim"] is False


def test_artifact_backed_dagster_pass_satisfies_provider_runtime_blockers() -> None:
    module = _load_module()
    report = {
        "preflight": {},
        "steps": {
            "production_dagster": {
                "status": "passed",
                "artifact_backed_pass_claim": True,
            },
            "production_provider_status": {
                "status": "passed",
                "blocked": True,
                "missing_surfaces": [],
                "runtime_blockers": [
                    "configured_data_platform_current_cycle_runtime",
                    "configured_graph_phase0_status_runtime",
                    "configured_graph_phase1_runtime",
                    "configured_reasoner_runtime",
                    "configured_audit_eval_retrospective_hook_runtime",
                    "production_current_cycle_dagster_run_evidence",
                ],
            },
        },
    }

    module._apply_effective_provider_status(report)

    provider_status = report["steps"]["production_provider_status"]
    assert provider_status["static_blocked"] is True
    assert provider_status["effective_blocked"] is False
    assert provider_status["resolved_by_artifact_backed_run"] is True
    assert provider_status["effective_runtime_blockers"] == []
    assert module._open_blockers(report) == []


def test_provider_runtime_blockers_remain_when_dagster_pass_is_not_artifact_backed() -> None:
    module = _load_module()
    report = {
        "preflight": {},
        "steps": {
            "production_dagster": {
                "status": "failed",
                "artifact_backed_pass_claim": False,
                "failure_step": "graph_snapshot",
            },
            "production_provider_status": {
                "status": "passed",
                "blocked": True,
                "missing_surfaces": [],
                "runtime_blockers": [
                    "configured_data_platform_current_cycle_runtime",
                    "configured_graph_phase1_runtime",
                    "configured_reasoner_runtime",
                ],
            },
        },
    }

    assert module._open_blockers(report) == [
        "full production daily_cycle_job Dagster proof has not passed",
        "Dagster failure step: graph_snapshot",
        "production provider status is blocked",
        "production provider runtime pending: configured_graph_phase1_runtime",
    ]


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
        legacy_materialization_claim_count=15,
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
        legacy_materialization_claim_count=15,
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
