from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest


ASSEMBLY_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ASSEMBLY_ROOT / "scripts" / "holdings_live_graph_proof.py"


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "holdings_live_graph_proof",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeServices:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def submit_holdings_payloads(self, config: Any) -> dict[str, Any]:
        self.calls.append("submit")
        return {
            "payload_count": 2,
            "relation_counts": {"CO_HOLDING": 1, "NORTHBOUND_HOLD": 1},
            "receipt_count": 2,
            "accepted_receipt_count": 2,
            "submitted": True,
        }

    def accept_queue_candidates(self, config: Any) -> dict[str, Any]:
        self.calls.append("worker")
        return {"accepted": 2, "rejected": 0}

    def freeze_cycle(self, config: Any) -> dict[str, Any]:
        self.calls.append("freeze")
        return {
            "cycle_id": "CYCLE_20260507",
            "selection_ref": "cycle_candidate_selection:CYCLE_20260507",
            "frozen_candidate_count": 2,
            "frozen_candidate_id_count": 2,
        }

    def read_frozen_candidates(
        self,
        config: Any,
        freeze_summary: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls.append("reader")
        return {
            "candidate_count": 2,
            "cycle_id": freeze_summary["cycle_id"],
            "selection_ref": freeze_summary["selection_ref"],
            "relation_counts": {"CO_HOLDING": 1, "NORTHBOUND_HOLD": 1},
            "relation_type_set": ["CO_HOLDING", "NORTHBOUND_HOLD"],
        }

    def run_graph_live_proof(
        self,
        config: Any,
        frozen_summary: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls.append("graph")
        return {
            "namespace": config.namespace,
            "neo4j_database": config.neo4j_database,
            "cycle_id": frozen_summary["cycle_id"],
            "selection_ref": frozen_summary["selection_ref"],
            "layer_a_artifact": {
                "manifest_path": "proof-artifacts/manifest.json",
                "records_path": "proof-artifacts/records.jsonl",
                "delta_count": 2,
                "node_count": 4,
                "edge_count": 2,
                "assertion_count": 2,
                "relation_counts": {"CO_HOLDING": 1, "NORTHBOUND_HOLD": 1},
            },
            "edge_verification": {
                "expected_edge_count": 2,
                "edge_count": 2,
                "relation_counts": {"CO_HOLDING": 1, "NORTHBOUND_HOLD": 1},
                "missing_edge_ids": [],
                "disallowed_relation_types": [],
            },
            "algorithm_proof": {
                "co_holding_path_count": 1,
                "northbound_path_count": 1,
                "total_path_count": 2,
                "impacted_entity_count": 3,
                "co_holding_diagnostics": {},
                "northbound_diagnostics": {"below_threshold": 0},
            },
        }


class EnvCapturingServices(FakeServices):
    def __init__(self) -> None:
        super().__init__()
        self.env_by_step: dict[str, dict[str, str | None]] = {}

    def _capture_env(self, step: str) -> None:
        import os

        self.env_by_step[step] = {
            "DP_PG_DSN": os.environ.get("DP_PG_DSN"),
            "DATABASE_URL": os.environ.get("DATABASE_URL"),
            "NEO4J_DATABASE": os.environ.get("NEO4J_DATABASE"),
        }

    def submit_holdings_payloads(self, config: Any) -> dict[str, Any]:
        self._capture_env("submit")
        return super().submit_holdings_payloads(config)

    def accept_queue_candidates(self, config: Any) -> dict[str, Any]:
        self._capture_env("worker")
        return super().accept_queue_candidates(config)

    def freeze_cycle(self, config: Any) -> dict[str, Any]:
        self._capture_env("freeze")
        return super().freeze_cycle(config)

    def read_frozen_candidates(
        self,
        config: Any,
        freeze_summary: dict[str, Any],
    ) -> dict[str, Any]:
        self._capture_env("reader")
        return super().read_frozen_candidates(config, freeze_summary)

    def run_graph_live_proof(
        self,
        config: Any,
        frozen_summary: dict[str, Any],
    ) -> dict[str, Any]:
        self._capture_env("graph")
        return super().run_graph_live_proof(config, frozen_summary)


def _config(tmp_path: Path, *, execute: bool = True, **overrides: Any) -> Any:
    module = _load_module()
    duckdb_path = tmp_path / "holdings.duckdb"
    duckdb_path.write_text("fixture", encoding="utf-8")
    values = {
        "execute": execute,
        "dp_env": "test",
        "pg_dsn": _dsn("dp_holdings_proof_20260507"),
        "duckdb_path": duckdb_path,
        "neo4j_database": "projectultproof20260507",
        "namespace": "holdings-proof-20260507",
        "artifact_root": tmp_path / "graph-proof-artifacts",
        "cycle_date": module._parse_yyyymmdd("20260507"),
        "max_payloads": None,
        "worker_limit": 1000,
    }
    values.update(overrides)
    return module.ProofConfig(**values)


def _env() -> dict[str, str]:
    return {
        "SUBSYSTEM_HOLDINGS_LIVE_QUEUE_SUBMIT_CONFIRM": "1",
        "GRAPH_ENGINE_LIVE_PROOF_CONFIRM": "1",
    }


def _dsn(database_name: str) -> str:
    return "postgresql" + "://dp:example@localhost:5432/" + database_name


def test_dry_run_validates_preflight_without_calling_services(tmp_path: Path) -> None:
    module = _load_module()
    services = FakeServices()

    summary = module.run_holdings_live_graph_proof(
        _config(tmp_path, execute=False),
        services,
        env={},
    )

    assert summary["status"] == "dry_run_ready"
    assert services.calls == []
    assert summary["not_claimed"]["default_full_propagation_rollout"] is False


def test_execute_runs_fake_services_in_order(tmp_path: Path) -> None:
    module = _load_module()
    services = FakeServices()

    summary = module.run_holdings_live_graph_proof(
        _config(tmp_path),
        services,
        env=_env(),
    )

    assert summary["status"] == "passed"
    assert services.calls == ["submit", "worker", "freeze", "reader", "graph"]
    assert summary["counts"] == {
        "submitted_payload_count": 2,
        "accepted_candidate_count": 2,
        "frozen_candidate_count": 2,
        "frozen_reader_candidate_count": 2,
        "neo4j_edge_count": 2,
    }
    assert summary["relation_type_set"] == ["CO_HOLDING", "NORTHBOUND_HOLD"]
    assert summary["not_claimed"] == {
        "contracts_subtype": False,
        "default_full_propagation_rollout": False,
        "financial_doc": False,
        "production_entity_registry_m4_8": False,
        "production_queue_propagation": False,
    }


def test_execute_binds_pg_env_before_queue_submit(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    module = _load_module()
    stale_dsn = _dsn("proj")
    proof_dsn = _dsn("dp_graph_live_proof_test")
    monkeypatch.setenv("DP_PG_DSN", stale_dsn)
    monkeypatch.setenv("DATABASE_URL", stale_dsn)
    services = EnvCapturingServices()

    module.run_holdings_live_graph_proof(
        _config(tmp_path, pg_dsn=proof_dsn),
        services,
        env=_env(),
    )

    assert services.env_by_step["submit"]["DP_PG_DSN"] == proof_dsn
    assert services.env_by_step["submit"]["DATABASE_URL"] == proof_dsn
    assert services.env_by_step["submit"]["DP_PG_DSN"] != stale_dsn
    assert services.env_by_step["worker"]["DP_PG_DSN"] == proof_dsn
    assert services.env_by_step["freeze"]["DATABASE_URL"] == proof_dsn
    assert services.env_by_step["reader"]["DP_PG_DSN"] == proof_dsn
    assert services.env_by_step["graph"]["DATABASE_URL"] == proof_dsn
    assert module.os.environ["DP_PG_DSN"] == stale_dsn
    assert module.os.environ["DATABASE_URL"] == stale_dsn


def test_execute_binds_neo4j_env_before_graph_step(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    module = _load_module()
    proof_database = "projectultproof_test"
    monkeypatch.setenv("NEO4J_DATABASE", "neo4j")
    services = EnvCapturingServices()

    module.run_holdings_live_graph_proof(
        _config(tmp_path, neo4j_database=proof_database),
        services,
        env=_env(),
    )

    assert services.env_by_step["submit"]["NEO4J_DATABASE"] == proof_database
    assert services.env_by_step["graph"]["NEO4J_DATABASE"] == proof_database
    assert services.env_by_step["graph"]["NEO4J_DATABASE"] != "neo4j"
    assert module.os.environ["NEO4J_DATABASE"] == "neo4j"


@pytest.mark.parametrize(
    ("override", "match"),
    [
        ({"dp_env": "prod"}, "DP_ENV must be test"),
        (
            {"pg_dsn": _dsn("proj")},
            "PG database name",
        ),
        ({"neo4j_database": "neo4j"}, "default/shared"),
        ({"neo4j_database": "customer_live"}, "default/shared"),
        ({"neo4j_database": "projectult"}, "proof, smoke, or test"),
        ({"duckdb_path": Path("/definitely/missing/holdings.duckdb")}, "duckdb"),
    ],
)
def test_preflight_rejects_unsafe_environment(
    tmp_path: Path,
    override: dict[str, Any],
    match: str,
) -> None:
    module = _load_module()

    with pytest.raises(module.ProofError, match=match):
        module.run_holdings_live_graph_proof(
            _config(tmp_path, **override),
            FakeServices(),
            env=_env(),
        )


def test_execute_requires_both_live_gates(tmp_path: Path) -> None:
    module = _load_module()

    with pytest.raises(module.ProofError, match="SUBSYSTEM_HOLDINGS"):
        module.run_holdings_live_graph_proof(
            _config(tmp_path),
            FakeServices(),
            env={"GRAPH_ENGINE_LIVE_PROOF_CONFIRM": "1"},
        )

    with pytest.raises(module.ProofError, match="GRAPH_ENGINE"):
        module.run_holdings_live_graph_proof(
            _config(tmp_path),
            FakeServices(),
            env={"SUBSYSTEM_HOLDINGS_LIVE_QUEUE_SUBMIT_CONFIRM": "1"},
        )


def test_relation_set_must_be_exactly_holdings_types(tmp_path: Path) -> None:
    module = _load_module()

    with pytest.raises(module.ProofError, match="relation set"):
        module._assert_required_relations({"CO_HOLDING": 2})

    with pytest.raises(module.ProofError, match="relation set"):
        module._assert_required_relations(
            {"CO_HOLDING": 1, "NORTHBOUND_HOLD": 1, "SUPPLY_CHAIN": 1}
        )


def test_positive_counts_are_required(tmp_path: Path) -> None:
    module = _load_module()

    with pytest.raises(module.ProofError, match="greater than zero"):
        module._require_positive_count({"payload_count": 0}, "payload_count")


def test_summary_redacts_runtime_paths_and_secrets(tmp_path: Path) -> None:
    module = _load_module()
    config = _config(tmp_path)
    summary = module.run_holdings_live_graph_proof(config, FakeServices(), env=_env())
    text = json.dumps(module._redact_payload(summary), sort_keys=True)

    assert "proof-artifacts/manifest.json" not in text
    assert str(tmp_path) not in text
    assert "postgresql" + "://" not in text
    assert "<redacted>" in text
    assert summary["graph_live_proof"]["layer_a_artifact"]["manifest_path"] == "<redacted>"


def test_main_writes_failed_redacted_summary(tmp_path: Path, monkeypatch: Any) -> None:
    module = _load_module()
    out = tmp_path / "summary.json"
    monkeypatch.setenv("DP_ENV", "prod")
    monkeypatch.setenv("DP_PG_DSN", _dsn("proj"))

    exit_code = module.main(["--summary-json", str(out)])

    payload = json.loads(out.read_text(encoding="utf-8"))
    payload_text = json.dumps(payload, sort_keys=True)
    assert exit_code == 2
    assert payload["status"] == "failed"
    assert "DP_ENV must be test" in payload["reason"]
    assert "postgresql" + "://" not in payload_text
