"""Cross-repo holdings live graph proof runner.

The CLI defaults to dry-run preflight. The real proof path is gated and must
use injected or live service adapters; tests exercise only fake services.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import traceback
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Protocol

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSEMBLY_ROOT = PROJECT_ROOT / "assembly"
DATA_PLATFORM_ROOT = PROJECT_ROOT / "data-platform"
GRAPH_ENGINE_ROOT = PROJECT_ROOT / "graph-engine"
SUBSYSTEM_HOLDINGS_ROOT = PROJECT_ROOT / "subsystem-holdings"
SUBSYSTEM_SDK_ROOT = PROJECT_ROOT / "subsystem-sdk"
CONTRACTS_ROOT = PROJECT_ROOT / "contracts"

SCHEMA_VERSION = "project-ult.holdings-live-graph-proof.v1"
DEFAULT_OUT = (
    ASSEMBLY_ROOT
    / "reports"
    / "stabilization"
    / "holdings-live-graph-proof-summary-20260507.json"
)
DEFAULT_CYCLE_DATE = "20260507"
QUEUE_CONFIRM_ENV = "SUBSYSTEM_HOLDINGS_LIVE_QUEUE_SUBMIT_CONFIRM"
GRAPH_CONFIRM_ENV = "GRAPH_ENGINE_LIVE_PROOF_CONFIRM"
GRAPH_NAMESPACE_ENV = "GRAPH_ENGINE_LIVE_PROOF_NAMESPACE"
ALLOWED_RELATION_TYPES = frozenset({"CO_HOLDING", "NORTHBOUND_HOLD"})
REQUIRED_DB_MARKERS = ("proof", "smoke", "test")
UNSAFE_NEO4J_DATABASES = frozenset(
    {"default", "live", "main", "neo4j", "prod", "production", "system"}
)
SECRET_ENV_KEYS = (
    "DATABASE_URL",
    "DP_PG_DSN",
    "NEO4J_PASSWORD",
    "POSTGRES_PASSWORD",
    "DP_TUSHARE_TOKEN",
    "OPENAI_API_KEY",
)
SENSITIVE_KEY_PATTERN = re.compile(
    r"(token|secret|password|passwd|pwd|dsn|database_url|private_key|"
    r"raw[_-]?(payload|response|provider)?|provider[_-]?payload|"
    r"local[_-]?path|runtime[_-]?path|duckdb_path|artifact_root)",
    re.IGNORECASE,
)
SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"\b(?:postgres(?:ql)?|mysql|redis|mongodb)://\S+", re.IGNORECASE),
    re.compile(r"\b(?:ghp|gho|github_pat)_[A-Za-z0-9_]+\b"),
    re.compile(r"/" + r"Users/[^,\s\"']+"),
    re.compile(r"/tmp/[^,\s\"']*project-ult[^,\s\"']*", re.IGNORECASE),
)


@dataclass(frozen=True, slots=True)
class ProofError(RuntimeError):
    reason: str
    exit_code: int = 2

    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True, slots=True)
class ProofConfig:
    execute: bool
    dp_env: str | None
    pg_dsn: str | None
    duckdb_path: Path | None
    neo4j_database: str | None
    namespace: str | None
    artifact_root: Path
    cycle_date: date
    max_payloads: int | None = None
    worker_limit: int = 1000


class ProofServices(Protocol):
    def submit_holdings_payloads(self, config: ProofConfig) -> Mapping[str, Any]:
        """Submit or summarize subsystem-holdings payloads."""

    def accept_queue_candidates(self, config: ProofConfig) -> Mapping[str, Any]:
        """Run data-platform queue validation worker."""

    def freeze_cycle(self, config: ProofConfig) -> Mapping[str, Any]:
        """Create/freeze a cycle and return cycle metadata."""

    def read_frozen_candidates(
        self,
        config: ProofConfig,
        freeze_summary: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Read frozen Ex-3 candidates through the public graph Phase 1 adapter."""

    def run_graph_live_proof(
        self,
        config: ProofConfig,
        frozen_summary: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Run graph-engine Layer A/live graph proof harness."""


class LiveProofServices:
    """Live service adapter used only when the CLI is explicitly executed."""

    def submit_holdings_payloads(self, config: ProofConfig) -> Mapping[str, Any]:
        _ensure_project_paths()
        _set_runtime_env(config)
        module = _load_subsystem_holdings_submit_runner()
        return module.run_real_queue_submit_proof(
            _require_path(config.duckdb_path, "duckdb_path"),
            execute=True,
            max_payloads=config.max_payloads,
        )

    def accept_queue_candidates(self, config: ProofConfig) -> Mapping[str, Any]:
        _ensure_project_paths()
        _set_runtime_env(config)
        from data_platform.queue.worker import validate_pending_candidates

        result = validate_pending_candidates(limit=config.worker_limit)
        return _json_safe(result)

    def freeze_cycle(self, config: ProofConfig) -> Mapping[str, Any]:
        _ensure_project_paths()
        _set_runtime_env(config)
        from data_platform.cycle import (
            create_cycle,
            freeze_cycle_candidates,
            load_frozen_candidate_ids,
        )

        cycle = create_cycle(config.cycle_date)
        frozen = freeze_cycle_candidates(cycle.cycle_id)
        frozen_candidate_ids = load_frozen_candidate_ids(cycle.cycle_id)
        return {
            "cycle_id": cycle.cycle_id,
            "selection_ref": f"cycle_candidate_selection:{frozen.cycle_id}",
            "frozen_candidate_count": int(frozen.candidate_count),
            "frozen_candidate_id_count": len(tuple(frozen_candidate_ids)),
        }

    def read_frozen_candidates(
        self,
        config: ProofConfig,
        freeze_summary: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        _ensure_project_paths()
        _set_runtime_env(config)
        from data_platform.cycle.graph_phase1_adapters import PostgresCandidateDeltaReader

        cycle_id = str(freeze_summary["cycle_id"])
        selection_ref = str(freeze_summary["selection_ref"])
        deltas = PostgresCandidateDeltaReader.from_env().read_candidate_graph_deltas(
            cycle_id,
            selection_ref,
        )
        relation_counts = dict(Counter(str(delta.relation_type) for delta in deltas))
        _assert_required_relations(relation_counts)
        return {
            "candidate_count": len(deltas),
            "relation_counts": relation_counts,
            "relation_type_set": sorted(relation_counts),
            "cycle_id": cycle_id,
            "selection_ref": selection_ref,
            "_candidate_deltas": deltas,
        }

    def run_graph_live_proof(
        self,
        config: ProofConfig,
        frozen_summary: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        _ensure_project_paths()
        _set_runtime_env(config)
        from graph_engine import Neo4jClient, load_config_from_env
        from graph_engine.proofs import run_holdings_live_graph_proof
        from graph_engine.status import GraphStatusManager
        from graph_engine.status.store import PostgreSQLStatusStore

        client = Neo4jClient(load_config_from_env())
        status_store = PostgreSQLStatusStore.from_database_url(config.pg_dsn)
        status_manager = GraphStatusManager(status_store)
        entity_reader = _StaticEntityAnchorReader(frozen_summary["_candidate_deltas"])
        with client:
            summary = run_holdings_live_graph_proof(
                cycle_id=str(frozen_summary["cycle_id"]),
                selection_ref=str(frozen_summary["selection_ref"]),
                candidate_deltas=frozen_summary["_candidate_deltas"],
                entity_reader=entity_reader,
                client=client,
                status_manager=status_manager,
                env=os.environ,
                artifact_root=config.artifact_root,
            )
        return _json_safe(summary)


class _StaticEntityAnchorReader:
    def __init__(self, deltas: Sequence[Any]) -> None:
        node_ids = {
            node_id
            for delta in deltas
            for node_id in (delta.source_node, delta.target_node)
        }
        self._node_entity_ids = {
            node_id: f"CANONICAL_{node_id}"
            for node_id in node_ids
        }

    def canonical_entity_ids_for_node_ids(self, node_ids: set[str]) -> dict[str, str]:
        return {
            node_id: self._node_entity_ids[node_id]
            for node_id in node_ids
            if node_id in self._node_entity_ids
        }

    def existing_entity_ids(self, entity_ids: set[str]) -> set[str]:
        return set(entity_ids)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    env = os.environ
    config = ProofConfig(
        execute=args.execute,
        dp_env=env.get("DP_ENV"),
        pg_dsn=args.pg_dsn or env.get("DP_PG_DSN") or env.get("DATABASE_URL"),
        duckdb_path=args.duckdb_path or _optional_path(env.get("DP_DUCKDB_PATH")),
        neo4j_database=args.neo4j_database or env.get("NEO4J_DATABASE"),
        namespace=args.namespace or env.get(GRAPH_NAMESPACE_ENV),
        artifact_root=args.artifact_root,
        cycle_date=_parse_yyyymmdd(args.cycle_date),
        max_payloads=args.max_payloads,
        worker_limit=args.worker_limit,
    )
    try:
        summary = run_holdings_live_graph_proof(config, LiveProofServices(), env=env)
        exit_code = 0
    except ProofError as exc:
        summary = _failure_summary(config, reason=exc.reason, error_type=type(exc).__name__)
        exit_code = exc.exit_code
    except Exception as exc:  # noqa: BLE001 - evidence should preserve blockers.
        summary = _failure_summary(
            config,
            reason=_redact_text(str(exc)),
            error_type=type(exc).__name__,
        )
        if args.include_traceback:
            summary["traceback"] = _redact_text(traceback.format_exc())
        exit_code = 1

    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(
        json.dumps(_redact_payload(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(_redact_payload(summary), indent=2, sort_keys=True))
    return exit_code


def run_holdings_live_graph_proof(
    config: ProofConfig,
    services: ProofServices,
    *,
    env: Mapping[str, str | None],
) -> dict[str, Any]:
    """Run preflight or execute the gated cross-repo holdings proof."""

    preflight = _validate_config(config, env=env)
    summary = _base_summary(config, preflight=preflight)

    if not config.execute:
        summary["status"] = "dry_run_ready"
        summary["mode"] = "dry_run"
        return summary

    with _bound_runtime_env(config):
        submit_summary = services.submit_holdings_payloads(config)
        _require_positive_count(submit_summary, "payload_count")
        _assert_required_relations(_relation_counts_from(submit_summary))

        worker_summary = services.accept_queue_candidates(config)
        _require_positive_count(worker_summary, "accepted")

        freeze_summary = services.freeze_cycle(config)
        _require_positive_count(freeze_summary, "frozen_candidate_count")

        frozen_summary = services.read_frozen_candidates(config, freeze_summary)
        _require_positive_count(frozen_summary, "candidate_count")
        _assert_required_relations(_relation_counts_from(frozen_summary))

        graph_summary = services.run_graph_live_proof(config, frozen_summary)
        edge_summary = _edge_verification_from(graph_summary)
        _require_positive_count(edge_summary, "edge_count")
        _assert_required_relations(_relation_counts_from(edge_summary))

    summary.update(
        {
            "status": "passed",
            "mode": "execute",
            "queue_submit": _public_step_summary(submit_summary),
            "worker_accept": _public_step_summary(worker_summary),
            "cycle_freeze": _public_step_summary(freeze_summary),
            "frozen_candidates": _public_step_summary(frozen_summary),
            "graph_live_proof": _public_graph_summary(graph_summary),
            "counts": {
                "submitted_payload_count": int(submit_summary["payload_count"]),
                "accepted_candidate_count": int(worker_summary["accepted"]),
                "frozen_candidate_count": int(freeze_summary["frozen_candidate_count"]),
                "frozen_reader_candidate_count": int(frozen_summary["candidate_count"]),
                "neo4j_edge_count": int(edge_summary["edge_count"]),
            },
            "relation_type_set": sorted(_relation_counts_from(edge_summary)),
        }
    )
    return summary


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run or preflight the cross-repo holdings live graph proof. "
            "Real execution requires --execute plus all proof gates."
        ),
    )
    parser.add_argument("--execute", action="store_true", help="Run live proof steps.")
    parser.add_argument("--pg-dsn", default=None, help="One-time proof PostgreSQL DSN.")
    parser.add_argument("--duckdb-path", type=Path, default=None)
    parser.add_argument("--neo4j-database", default=None)
    parser.add_argument("--namespace", default=None)
    parser.add_argument("--cycle-date", default=DEFAULT_CYCLE_DATE, help="YYYYMMDD")
    parser.add_argument("--max-payloads", type=_positive_int, default=None)
    parser.add_argument("--worker-limit", type=_positive_int, default=1000)
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=ASSEMBLY_ROOT / "tmp" / "holdings-live-graph-proof",
    )
    parser.add_argument("--summary-json", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--include-traceback",
        action="store_true",
        help="Include redacted traceback in failed summary JSON.",
    )
    return parser.parse_args(argv)


def _validate_config(
    config: ProofConfig,
    *,
    env: Mapping[str, str | None],
) -> dict[str, Any]:
    blockers: list[str] = []
    if config.dp_env != "test":
        blockers.append("DP_ENV must be test")
    if not config.pg_dsn:
        blockers.append("DP_PG_DSN or DATABASE_URL missing")
    elif not _database_name_is_proof_like(_postgres_database_name(config.pg_dsn)):
        blockers.append("PG database name must contain proof, smoke, or test")

    if config.duckdb_path is None:
        blockers.append("DP_DUCKDB_PATH or --duckdb-path missing")
    elif not config.duckdb_path.exists():
        blockers.append("duckdb_path target missing")

    if not config.neo4j_database:
        blockers.append("NEO4J_DATABASE missing")
    else:
        _validate_neo4j_database(config.neo4j_database)

    if not config.namespace:
        blockers.append(f"{GRAPH_NAMESPACE_ENV} missing")
    elif not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{2,95}", config.namespace):
        blockers.append(f"{GRAPH_NAMESPACE_ENV} must be a safe unique identifier")

    if config.execute:
        if env.get(QUEUE_CONFIRM_ENV) != "1":
            blockers.append(f"{QUEUE_CONFIRM_ENV}=1 required")
        if env.get(GRAPH_CONFIRM_ENV) != "1":
            blockers.append(f"{GRAPH_CONFIRM_ENV}=1 required")

    if blockers:
        raise ProofError("; ".join(blockers), 2)

    return {
        "dp_env": "test",
        "pg_database": _postgres_database_name(config.pg_dsn or ""),
        "duckdb_path": "<redacted>",
        "neo4j_database": config.neo4j_database,
        "namespace": config.namespace,
        "queue_submit_gate": _gate_status(env.get(QUEUE_CONFIRM_ENV)),
        "graph_live_gate": _gate_status(env.get(GRAPH_CONFIRM_ENV)),
        "execute_gates_required": config.execute,
    }


def _validate_neo4j_database(database: str) -> None:
    value = str(database).strip()
    if not value:
        raise ProofError("NEO4J_DATABASE missing", 2)
    lowered = value.lower()
    if lowered in UNSAFE_NEO4J_DATABASES or any(
        marker in lowered for marker in ("live", "prod", "production")
    ):
        raise ProofError("NEO4J_DATABASE must not be default/shared", 2)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{2,95}", value):
        raise ProofError("NEO4J_DATABASE must be a safe identifier", 2)
    if not _database_name_is_proof_like(value):
        raise ProofError("NEO4J_DATABASE must contain proof, smoke, or test", 2)


def _base_summary(config: ProofConfig, *, preflight: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "failed",
        "mode": "execute" if config.execute else "dry_run",
        "generated_at": datetime.now(UTC).isoformat(),
        "preflight": dict(preflight),
        "inputs": {
            "duckdb_path": "<redacted>",
            "artifact_root": "<redacted>",
            "cycle_date": config.cycle_date.isoformat(),
            "max_payloads": config.max_payloads,
        },
        "planned_chain": [
            "subsystem-holdings real queue submit",
            "data-platform worker accept",
            "cycle freeze",
            "PostgresCandidateDeltaReader frozen candidates",
            "graph-engine Layer A promotion/live proof harness",
            "Neo4j edge verification",
            "explicit #55 holdings algorithms",
        ],
        "not_claimed": _not_claimed(),
    }


def _failure_summary(
    config: ProofConfig,
    *,
    reason: str,
    error_type: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "failed",
        "mode": "execute" if config.execute else "dry_run",
        "generated_at": datetime.now(UTC).isoformat(),
        "reason": _redact_text(reason),
        "error_type": error_type,
        "inputs": {
            "duckdb_path": "<redacted>",
            "artifact_root": "<redacted>",
            "cycle_date": config.cycle_date.isoformat(),
        },
        "not_claimed": _not_claimed(),
    }


def _not_claimed() -> dict[str, bool]:
    return {
        "default_full_propagation_rollout": False,
        "production_entity_registry_m4_8": False,
        "contracts_subtype": False,
        "financial_doc": False,
        "production_queue_propagation": False,
    }


def _public_step_summary(summary: Mapping[str, Any]) -> dict[str, Any]:
    public: dict[str, Any] = {}
    allowed_keys = {
        "accepted",
        "adapter_diagnostics",
        "audit_count",
        "built_payload_count",
        "candidate_count",
        "cycle_id",
        "disallowed_relation_types",
        "edge_count",
        "frozen_candidate_count",
        "frozen_candidate_id_count",
        "payload_count",
        "private_wire_field_leaks",
        "receipt_backend_kinds",
        "receipt_count",
        "relation_counts",
        "relation_type_set",
        "rejected",
        "selection_ref",
        "submitted",
        "updated",
    }
    for key in allowed_keys:
        if key in summary:
            public[key] = _redact_payload(summary[key])
    return public


def _public_graph_summary(summary: Mapping[str, Any]) -> dict[str, Any]:
    graph = _json_safe(summary)
    return {
        "namespace": graph.get("namespace"),
        "neo4j_database": graph.get("neo4j_database"),
        "cycle_id": graph.get("cycle_id"),
        "selection_ref": graph.get("selection_ref"),
        "layer_a_artifact": _layer_a_summary(graph.get("layer_a_artifact")),
        "edge_verification": _edge_verification_from(graph),
        "algorithm_proof": _algorithm_summary(graph.get("algorithm_proof")),
    }


def _layer_a_summary(value: Any) -> dict[str, Any]:
    payload = value if isinstance(value, Mapping) else {}
    return {
        "manifest_path": "<redacted>",
        "records_path": "<redacted>",
        "delta_count": int(payload.get("delta_count", 0) or 0),
        "node_count": int(payload.get("node_count", 0) or 0),
        "edge_count": int(payload.get("edge_count", 0) or 0),
        "assertion_count": int(payload.get("assertion_count", 0) or 0),
        "relation_counts": dict(payload.get("relation_counts", {}) or {}),
    }


def _edge_verification_from(summary: Mapping[str, Any]) -> dict[str, Any]:
    raw = summary.get("edge_verification", summary)
    value = raw if isinstance(raw, Mapping) else {}
    return {
        "expected_edge_count": int(value.get("expected_edge_count", 0) or 0),
        "edge_count": int(value.get("edge_count", 0) or 0),
        "relation_counts": dict(value.get("relation_counts", {}) or {}),
        "missing_edge_ids": list(value.get("missing_edge_ids", []) or []),
        "disallowed_relation_types": list(value.get("disallowed_relation_types", []) or []),
    }


def _algorithm_summary(value: Any) -> dict[str, Any]:
    payload = value if isinstance(value, Mapping) else {}
    return {
        "co_holding_path_count": int(payload.get("co_holding_path_count", 0) or 0),
        "northbound_path_count": int(payload.get("northbound_path_count", 0) or 0),
        "total_path_count": int(payload.get("total_path_count", 0) or 0),
        "impacted_entity_count": int(payload.get("impacted_entity_count", 0) or 0),
        "co_holding_diagnostics": dict(payload.get("co_holding_diagnostics", {}) or {}),
        "northbound_diagnostics": dict(payload.get("northbound_diagnostics", {}) or {}),
    }


def _require_positive_count(summary: Mapping[str, Any], key: str) -> None:
    try:
        count = int(summary.get(key, 0) or 0)
    except (TypeError, ValueError) as exc:
        raise ProofError(f"{key} must be numeric", 3) from exc
    if count <= 0:
        raise ProofError(f"{key} must be greater than zero", 3)


def _relation_counts_from(summary: Mapping[str, Any]) -> dict[str, int]:
    raw = summary.get("relation_counts")
    if not isinstance(raw, Mapping):
        raw_set = summary.get("relation_type_set", ())
        if isinstance(raw_set, Sequence) and not isinstance(raw_set, str):
            return {str(item): 1 for item in raw_set}
        return {}
    return {str(key): int(value) for key, value in raw.items()}


def _assert_required_relations(relation_counts: Mapping[str, int]) -> None:
    relation_set = set(relation_counts)
    if relation_set != ALLOWED_RELATION_TYPES:
        raise ProofError(
            "relation set must be exactly CO_HOLDING and NORTHBOUND_HOLD",
            4,
        )
    if any(int(count) <= 0 for count in relation_counts.values()):
        raise ProofError("each holdings relation type must have positive count", 4)


def _database_name_is_proof_like(value: str | None) -> bool:
    lowered = str(value or "").lower()
    return any(marker in lowered for marker in REQUIRED_DB_MARKERS)


def _postgres_database_name(dsn: str) -> str:
    if not dsn:
        return ""
    without_query = dsn.split("?", 1)[0].rstrip("/")
    return without_query.rsplit("/", 1)[-1]


@contextmanager
def _bound_runtime_env(config: ProofConfig) -> Iterator[None]:
    previous = {
        "DP_PG_DSN": os.environ.get("DP_PG_DSN"),
        "DATABASE_URL": os.environ.get("DATABASE_URL"),
        "NEO4J_DATABASE": os.environ.get("NEO4J_DATABASE"),
    }
    try:
        _set_runtime_env(config)
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _set_runtime_env(config: ProofConfig) -> None:
    _set_pg_env(config.pg_dsn)
    _set_neo4j_env(config.neo4j_database)


def _set_pg_env(pg_dsn: str | None) -> None:
    if not pg_dsn:
        raise ProofError("DP_PG_DSN or DATABASE_URL missing", 2)
    if not _database_name_is_proof_like(_postgres_database_name(pg_dsn)):
        raise ProofError("PG database name must contain proof, smoke, or test", 2)
    os.environ["DP_PG_DSN"] = pg_dsn
    os.environ["DATABASE_URL"] = pg_dsn


def _set_neo4j_env(database: str | None) -> None:
    if database is None:
        raise ProofError("NEO4J_DATABASE missing", 2)
    _validate_neo4j_database(database)
    os.environ["NEO4J_DATABASE"] = str(database)


def _ensure_project_paths() -> None:
    paths = (
        DATA_PLATFORM_ROOT / "src",
        GRAPH_ENGINE_ROOT,
        CONTRACTS_ROOT / "src",
        SUBSYSTEM_HOLDINGS_ROOT / "src",
        SUBSYSTEM_HOLDINGS_ROOT / "scripts",
        SUBSYSTEM_SDK_ROOT,
    )
    for path in paths:
        path_text = str(path)
        if path_text not in sys.path:
            sys.path.insert(0, path_text)


def _load_subsystem_holdings_submit_runner() -> Any:
    script_path = SUBSYSTEM_HOLDINGS_ROOT / "scripts" / "proof_real_queue_submit_path.py"
    spec = importlib.util.spec_from_file_location(
        "subsystem_holdings_real_queue_submit_proof",
        script_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load subsystem-holdings real queue submit runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _json_safe(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _json_safe(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items() if not str(key).startswith("_")}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return "<redacted>"
    if hasattr(value, "model_dump"):
        return _json_safe(value.model_dump(mode="python"))
    return value


def _redact_payload(value: Any, *, key: str | None = None) -> Any:
    if key is not None and SENSITIVE_KEY_PATTERN.search(key):
        return "<redacted>"
    if isinstance(value, Mapping):
        return {
            str(item_key): _redact_payload(item_value, key=str(item_key))
            for item_key, item_value in value.items()
            if not str(item_key).startswith("_")
        }
    if isinstance(value, list):
        return [_redact_payload(item) for item in value]
    if isinstance(value, tuple):
        return [_redact_payload(item) for item in value]
    if isinstance(value, Path):
        return "<redacted>"
    if isinstance(value, str):
        return _redact_text(value)
    return value


def _redact_text(value: str) -> str:
    redacted = value
    for key in SECRET_ENV_KEYS:
        env_value = os.environ.get(key)
        if env_value and len(env_value) >= 8:
            redacted = redacted.replace(env_value, "<redacted>")
    for pattern in SENSITIVE_VALUE_PATTERNS:
        redacted = pattern.sub("<redacted>", redacted)
    return redacted


def _gate_status(value: str | None) -> str:
    return "SET" if value == "1" else "missing"


def _optional_path(value: str | None) -> Path | None:
    return Path(value) if value else None


def _require_path(path: Path | None, name: str) -> Path:
    if path is None:
        raise ProofError(f"{name} missing", 2)
    return path


def _parse_yyyymmdd(value: str) -> date:
    return datetime.strptime(value, "%Y%m%d").date()


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
