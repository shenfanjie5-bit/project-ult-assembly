"""M4.4 proof: public queue Ex-3 output promotes into graph-engine plans."""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSEMBLY_ROOT = PROJECT_ROOT / "assembly"
DATA_PLATFORM_ROOT = PROJECT_ROOT / "data-platform"
GRAPH_ENGINE_ROOT = PROJECT_ROOT / "graph-engine"
CONTRACTS_ROOT = PROJECT_ROOT / "contracts"
DEFAULT_TRADE_DATE = "20260418"
DEFAULT_SUBMITTED_BY = "m4-ex3-queue-promotion-proof"
DEFAULT_OUT = (
    ASSEMBLY_ROOT
    / "reports"
    / "stabilization"
    / "m4-ex3-queue-promotion-proof-20260503.json"
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prove public data-platform Ex-3 queue outputs feed graph promotion."
        ),
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL") or os.environ.get("DP_PG_DSN"),
        help="PostgreSQL DSN for an isolated migrated data-platform database.",
    )
    parser.add_argument("--trade-date", default=DEFAULT_TRADE_DATE, help="YYYYMMDD")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--skip-migrations",
        action="store_true",
        help="Assume data-platform PostgreSQL migrations are already applied.",
    )
    args = parser.parse_args(argv)

    _ensure_project_paths()
    report: dict[str, Any] = {
        "status": "failed",
        "started_at": datetime.now(UTC).isoformat(),
        "trade_date": _parse_yyyymmdd(args.trade_date).isoformat(),
        "database_url": "<redacted:set>" if args.database_url else "<missing>",
        "applied_migrations": [],
        "skipped_live_prerequisites": [],
    }

    try:
        if not args.database_url:
            report["skipped_live_prerequisites"].append("DATABASE_URL or DP_PG_DSN")
            raise RuntimeError(
                "DATABASE_URL or DP_PG_DSN is required for M4.4 live queue proof"
            )

        report.update(
            _run_live_queue_promotion_proof(
                database_url=args.database_url,
                trade_date=_parse_yyyymmdd(args.trade_date),
                apply_migrations=not args.skip_migrations,
            )
        )
        report["status"] = "passed"
        return 0
    except Exception as exc:  # noqa: BLE001 - evidence must preserve blockers.
        report["error"] = str(exc)
        report["error_type"] = type(exc).__name__
        report["traceback"] = traceback.format_exc()
        return 1
    finally:
        report["finished_at"] = datetime.now(UTC).isoformat()
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(_json_safe(report), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )


def _run_live_queue_promotion_proof(
    *,
    database_url: str,
    trade_date: date,
    apply_migrations: bool,
) -> dict[str, Any]:
    os.environ["DP_PG_DSN"] = database_url

    applied_migrations: list[str] = []
    if apply_migrations:
        from data_platform.ddl.runner import MigrationRunner

        applied_migrations = MigrationRunner().apply_pending(database_url)

    from data_platform.cycle import (
        create_cycle,
        freeze_cycle_candidates,
        load_frozen_candidate_ids,
    )
    from data_platform.cycle.graph_phase1_adapters import PostgresCandidateDeltaReader
    from data_platform.queue import submit_candidate
    from data_platform.queue.worker import validate_pending_candidates

    cycle = create_cycle(trade_date)
    payload = _ex3_queue_payload(
        delta_id=f"m4-ex3-queue-promotion-delta-{uuid4().hex}"
    )
    candidate = submit_candidate(payload)
    validation = validate_pending_candidates(limit=1000)
    if validation.accepted < 1:
        raise RuntimeError(
            "M4.4 proof queue worker did not accept any pending candidates: "
            f"{asdict(validation)}"
        )

    frozen = freeze_cycle_candidates(cycle.cycle_id)
    frozen_candidate_ids = load_frozen_candidate_ids(cycle.cycle_id)
    selection_ref = f"cycle_candidate_selection:{frozen.cycle_id}"
    reader = PostgresCandidateDeltaReader.from_env()
    deltas = reader.read_candidate_graph_deltas(cycle.cycle_id, selection_ref)
    reader_delta_ids = [delta.delta_id for delta in deltas]
    queue_evidence = _queue_evidence_from_public_outputs(
        candidate_id=int(candidate.id),
        payload_delta_id=payload["delta_id"],
        frozen_candidate_ids=frozen_candidate_ids,
        reader_delta_ids=reader_delta_ids,
    )

    plan, writer = _promote_deltas(cycle.cycle_id, selection_ref, deltas)
    _assert_promotion_plan_output(payload["delta_id"], plan, writer)

    return {
        "applied_migrations": applied_migrations,
        "candidate_id": candidate.id,
        "candidate_ingest_seq": candidate.ingest_seq,
        "candidate_queue_evidence_source": queue_evidence["evidence_source"],
        "candidate_queue_payload_delta_id": queue_evidence["payload_delta_id"],
        "candidate_queue_validation_status": queue_evidence["validation_status"],
        "cycle_id": cycle.cycle_id,
        "selection_ref": selection_ref,
        "freeze_candidate_count": frozen.candidate_count,
        "frozen_candidate_ids": list(frozen_candidate_ids),
        "public_queue_evidence": queue_evidence,
        "validation": asdict(validation),
        "reader_delta_ids": reader_delta_ids,
        "plan_delta_ids": list(plan.delta_ids),
        "plan_edge_ids": [edge.edge_id for edge in plan.edge_records],
        "edge_count": len(plan.edge_records),
        "node_count": len(plan.node_records),
        "assertion_count": len(plan.assertion_records),
        "writer_called": writer.called,
        "skipped_live_prerequisites": [],
    }


def _queue_evidence_from_public_outputs(
    *,
    candidate_id: int,
    payload_delta_id: str,
    frozen_candidate_ids: Sequence[int],
    reader_delta_ids: Sequence[str],
) -> dict[str, Any]:
    if int(candidate_id) not in {int(item) for item in frozen_candidate_ids}:
        raise RuntimeError(
            "M4.4 proof candidate was not frozen into cycle selection: "
            f"candidate_id={candidate_id}, frozen_candidate_ids={frozen_candidate_ids}"
        )

    if payload_delta_id not in reader_delta_ids:
        raise RuntimeError(
            "PostgresCandidateDeltaReader did not return proof delta "
            f"{payload_delta_id!r}; got {reader_delta_ids}"
        )

    return {
        "candidate_id": int(candidate_id),
        "evidence_source": "public_data_platform_queue_freeze_and_graph_reader",
        "payload_delta_id": payload_delta_id,
        "private_table_read": False,
        "validation_status": "accepted",
    }


def _promote_deltas(
    cycle_id: str,
    selection_ref: str,
    deltas: Sequence[Any],
) -> tuple[Any, "_CapturingCanonicalWriter"]:
    from graph_engine import promote_graph_deltas

    writer = _CapturingCanonicalWriter()
    plan = promote_graph_deltas(
        cycle_id,
        selection_ref,
        candidate_reader=_StaticCandidateDeltaReader(deltas),
        entity_reader=_StaticEntityAnchorReader(deltas),
        canonical_writer=writer,
        sync_to_live_graph=False,
    )
    return plan, writer


def _assert_promotion_plan_output(
    delta_id: str,
    plan: Any,
    writer: "_CapturingCanonicalWriter",
) -> None:
    if delta_id not in plan.delta_ids:
        raise RuntimeError(
            "graph-engine PromotionPlan did not include proof delta "
            f"{delta_id!r}; got {plan.delta_ids}"
        )
    if not writer.called:
        raise RuntimeError("graph-engine canonical writer was not called")

    edge_ids = [edge.edge_id for edge in plan.edge_records]
    if delta_id not in edge_ids:
        raise RuntimeError(
            "graph-engine PromotionPlan did not include proof edge "
            f"{delta_id!r}; got {edge_ids}"
        )


def _ex3_queue_payload(
    delta_id: str = "m4-ex3-queue-promotion-delta-1",
) -> dict[str, Any]:
    return {
        "payload_type": "Ex-3",
        "submitted_by": DEFAULT_SUBMITTED_BY,
        "subsystem_id": DEFAULT_SUBMITTED_BY,
        "delta_id": delta_id,
        "delta_type": "add",
        "source_node": "ENT_M4_QUEUE_SOURCE",
        "target_node": "ENT_M4_QUEUE_TARGET",
        "relation_type": "SUPPLY_CHAIN",
        "properties": {"weight": 0.82, "proof": "m4-ex3-queue-promotion"},
        "evidence": ["m4-proof:candidate_queue:ex3"],
    }


class _StaticCandidateDeltaReader:
    def __init__(self, deltas: Sequence[Any]) -> None:
        self._deltas = list(deltas)

    def read_candidate_graph_deltas(
        self,
        cycle_id: str,
        selection_ref: str,
    ) -> list[Any]:
        del cycle_id, selection_ref
        return list(self._deltas)


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

    def canonical_entity_ids_for_node_ids(
        self,
        node_ids: set[str],
    ) -> dict[str, str]:
        return {
            node_id: self._node_entity_ids[node_id]
            for node_id in node_ids
            if node_id in self._node_entity_ids
        }

    def existing_entity_ids(self, entity_ids: set[str]) -> set[str]:
        return set(entity_ids)


class _CapturingCanonicalWriter:
    def __init__(self) -> None:
        self.plan: Any | None = None

    @property
    def called(self) -> bool:
        return self.plan is not None

    def write_canonical_records(self, plan: Any) -> None:
        self.plan = plan


def _ensure_project_paths() -> None:
    for path in (
        DATA_PLATFORM_ROOT / "src",
        GRAPH_ENGINE_ROOT,
        CONTRACTS_ROOT / "src",
    ):
        path_text = str(path)
        if path_text not in sys.path:
            sys.path.insert(0, path_text)


def _parse_yyyymmdd(value: str) -> date:
    return datetime.strptime(value, "%Y%m%d").date()


def _json_safe(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _json_safe(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "model_dump"):
        return _json_safe(value.model_dump(mode="python"))
    return value


if __name__ == "__main__":
    raise SystemExit(main())
