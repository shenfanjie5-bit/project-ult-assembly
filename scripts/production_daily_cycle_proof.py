"""Bounded production daily-cycle proof runner.

The runner stays evidence-focused: it prepares isolated runtime paths,
optionally creates an isolated PostgreSQL database from the configured admin
DSN, runs the bounded Tushare/current-cycle/freeze chain, and writes a redacted
``production-daily-cycle-proof.json`` artifact even when a later runtime surface
fails closed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import traceback
from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Any
from urllib.parse import unquote, urlparse
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSEMBLY_ROOT = PROJECT_ROOT / "assembly"
DATA_PLATFORM_ROOT = PROJECT_ROOT / "data-platform"
ORCHESTRATOR_ROOT = PROJECT_ROOT / "orchestrator"
AUDIT_EVAL_ROOT = PROJECT_ROOT / "audit-eval"
REASONER_RUNTIME_ROOT = PROJECT_ROOT / "reasoner-runtime"
MAIN_CORE_ROOT = PROJECT_ROOT / "main-core"
CONTRACTS_ROOT = PROJECT_ROOT / "contracts"
GRAPH_ENGINE_ROOT = PROJECT_ROOT / "graph-engine"

DEFAULT_ENV_FILE = ASSEMBLY_ROOT / ".env"
DEFAULT_DATE = "20260415"
DEFAULT_SYMBOLS = ("600519.SH", "000001.SZ")
DEFAULT_SELECT = ("trade_cal", "stock_basic", "daily")
SCHEMA_VERSION = "project-ult.production-daily-cycle-proof.v2"
BASELINE_EVIDENCE_DATE = "2026-04-28"
SUBMITTED_BY = "production-daily-cycle-proof-runner"
EXPECTED_DAGSTER_MATERIALIZATION_CLAIM_COUNT = 15
EXPECTED_DAGSTER_ASSET_CHECK_NAMES = (
    "not_null_heartbeat_heartbeat",
    "llm_health_check",
    "phase0_ping_check",
    "neo4j_graph_consistency_check",
    "phase2_pool_failure_rate_gate",
)
SECRET_ENV_KEYS = (
    "DP_TUSHARE_TOKEN",
    "DP_PG_DSN",
    "DATABASE_URL",
    "POSTGRES_PASSWORD",
    "NEO4J_PASSWORD",
    "OPENAI_API_KEY",
)
PROCESS_STREAM_FIELD_NAMES = frozenset(
    ("stdout", "stderr", "stdout_tail", "stderr_tail", "compile_stdout")
)


def _proof_report_dates(generated_at: datetime) -> dict[str, str]:
    proof_run_date = generated_at.astimezone(UTC).date().isoformat()
    return {
        "evidence_date": proof_run_date,
        "proof_run_date": proof_run_date,
        "baseline_evidence_date": BASELINE_EVIDENCE_DATE,
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    _load_env_file(args.env_file)
    _prepend_pythonpath(
        [
            ORCHESTRATOR_ROOT / "src",
            MAIN_CORE_ROOT / "src",
            REASONER_RUNTIME_ROOT,
            CONTRACTS_ROOT / "src",
            DATA_PLATFORM_ROOT / "src",
            AUDIT_EVAL_ROOT / "src",
            GRAPH_ENGINE_ROOT,
        ]
    )

    cycle_date = _parse_yyyymmdd(args.date)
    symbols = _split_symbols(args.symbols)
    generated_at = datetime.now(UTC)
    stamp = generated_at.strftime("%Y%m%dT%H%M%SZ")
    runtime_root = (
        args.runtime_root
        or ASSEMBLY_ROOT / "tmp" / "production-daily-cycle-proof" / stamp
    ).expanduser()
    artifact_dir = (
        args.artifact_dir
        or ASSEMBLY_ROOT
        / "reports"
        / "stabilization"
        / "p1-p2-production-daily-cycle-proof-artifacts"
        / stamp
    ).expanduser()
    json_report = (
        args.json_report or artifact_dir / "production-daily-cycle-proof.json"
    ).expanduser()
    runtime_root.mkdir(parents=True, exist_ok=True)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        **_proof_report_dates(generated_at),
        "generated_at_utc": generated_at.isoformat(),
        "verdict": "RUNNING",
        "mode": "preflight_only" if args.preflight_only else "bounded_runner",
        "runtime_root": str(runtime_root),
        "artifact_dir": str(artifact_dir),
        "env": _env_presence(),
        "redaction": {
            "secret_values": "omitted",
            "dsn_values": "omitted",
        },
        "inputs": {
            "requested_partition_date": cycle_date.isoformat(),
            "symbols": list(symbols),
            "tushare_mode": "mock" if args.mock_tushare else "live",
            "selected_assets": list(DEFAULT_SELECT),
            "run_dagster": bool(args.run_dagster),
        },
        "command": {
            "argv": list(argv if argv is not None else sys.argv[1:]),
            "cwd": str(Path.cwd()),
            "env_file": str(args.env_file.expanduser()),
            "python_executable": sys.executable,
            "script": str(Path(__file__).resolve()),
        },
        "repo_revisions": _repo_revisions(),
        "preflight": {},
        "steps": {},
        "blockers": [],
        "evidence_policy": {
            "artifact_backed_pass_claims_only": True,
            "non_artifact_tmp_paths_pass_critical": False,
            "terminal_observed_steps_policy": (
                "terminal output is captured only as operator context and is "
                "not promoted to PASS evidence unless the same fact is present "
                "in a structured artifact listed by file_evidence_manifest"
            ),
            "runtime_tmp_evidence_policy": (
                "runtime files under assembly/tmp are source context; "
                "pass-critical runtime facts must be summarized or copied under "
                "the report artifact directory"
            ),
        },
        "non_claims": [
            "not_p5_shadow_run_readiness",
            "not_m3_3_production_same_cycle_graph_consumption",
            "not_p4_m4_bridge_readiness",
            "not_full_stack_components",
            "neo4j_not_canonical_truth",
            "not_sidecar_or_frontend_write_api",
            "not_api6_news_or_polymarket_flow",
            "not_production_daily_cycle_pass_certificate_unless_dagster_passed",
        ],
    }

    exit_code = 0
    temp_database: str | None = None
    try:
        _configure_runtime_paths(runtime_root)
        report["env"] = _env_presence()
        report["preflight"] = _run_preflights(
            runtime_root=runtime_root,
            artifact_dir=artifact_dir,
            run_current_selection_tests=args.run_current_selection_tests,
            current_selection_test_timeout_s=args.current_selection_test_timeout_s,
            reasoner_health=not args.skip_reasoner_health,
        )
        preflight_blockers = _failed_probe_names(report["preflight"])
        if args.run_dagster and "neo4j_gds" in preflight_blockers:
            raise RuntimeError(
                "configured_neo4j_gds_runtime is required before running "
                "daily_cycle_job; see neo4j-gds-preflight.json"
            )
        if args.preflight_only:
            report["verdict"] = (
                "RUNTIME_PREFLIGHT_PASS"
                if not preflight_blockers
                else "RUNTIME_PREFLIGHT_BLOCKED"
            )
            report["blockers"] = preflight_blockers
            exit_code = 0 if not preflight_blockers else 1
            return exit_code

        admin_dsn = _resolve_admin_dsn()
        if args.use_isolated_pg:
            temp_database = _temp_database_name(stamp)
            pg_dsn = _create_temp_database(admin_dsn, temp_database)
            report["steps"]["postgres_bootstrap"] = {
                "status": "passed",
                "mode": "isolated_database",
                "database": temp_database,
                "dsn": "<redacted:set>",
            }
        else:
            pg_dsn = admin_dsn
            report["steps"]["postgres_bootstrap"] = {
                "status": "passed",
                "mode": "configured_database",
                "dsn": "<redacted:set>",
            }
        _configure_runtime_paths(runtime_root, pg_dsn=pg_dsn)
        report["env"] = _env_presence()
        report["steps"]["data_platform_migrations"] = _apply_data_platform_migrations(pg_dsn)

        if not args.mock_tushare:
            _require_env("DP_TUSHARE_TOKEN")
        report["steps"]["tushare_refresh"] = _run_daily_refresh(
            cycle_date=cycle_date,
            mock=args.mock_tushare,
            artifact_dir=artifact_dir,
        )
        report["steps"]["current_cycle_selection"] = _select_current_cycle(
            symbols=symbols,
        )
        if args.run_dagster:
            report["steps"]["candidate_seed"] = _seed_current_cycle_candidates(
                selection=report["steps"]["current_cycle_selection"],
                symbols=symbols,
            )
            report["steps"]["graph_status_initialization"] = (
                _initialize_proof_graph_status(
                    pg_dsn=pg_dsn,
                    cycle_id=str(report["steps"]["current_cycle_selection"]["cycle_id"]),
                    artifact_dir=artifact_dir,
                    isolated_proof_db=args.use_isolated_pg,
                )
            )
            if report["steps"]["graph_status_initialization"].get("status") != "passed":
                raise RuntimeError(
                    "graph status initialization failed before graph_status "
                    "could be consumed; see graph-status-initialization.json"
                )
            report["steps"]["production_dagster"] = _run_production_dagster(
                cycle_id=str(report["steps"]["current_cycle_selection"]["cycle_id"]),
                runtime_root=runtime_root,
                artifact_dir=artifact_dir,
            )
        else:
            report["steps"]["candidate_seed"] = _seed_current_cycle_candidates(
                selection=report["steps"]["current_cycle_selection"],
                symbols=symbols,
            )
            report["steps"]["candidate_freeze"] = _freeze_current_cycle_candidates(
                symbols=symbols,
            )
            report["steps"]["production_dagster"] = _production_dagster_not_run()

        report["steps"]["production_provider_status"] = _production_provider_status()
        _apply_effective_provider_status(report)
        dagster_step = report["steps"].get("production_dagster", {})
        report["blockers"] = _open_blockers(report)
        if (
            isinstance(dagster_step, Mapping)
            and dagster_step.get("status") == "passed"
            and not report["blockers"]
        ):
            report["verdict"] = "PRODUCTION_DAILY_CYCLE_PASS"
            exit_code = 0
        else:
            report["verdict"] = "PARTIAL_PASS_BLOCKED"
            exit_code = 2
        return exit_code
    except Exception as exc:  # noqa: BLE001 - artifact must preserve blockers
        report["verdict"] = "BLOCKED"
        report["error"] = {
            "type": type(exc).__name__,
            "message": _redact_text(str(exc)),
        }
        if args.include_traceback:
            report["error"]["traceback"] = _redact_text(traceback.format_exc())
        report["blockers"] = _dedupe(
            [*_open_blockers(report), _redact_text(str(exc))]
        )
        exit_code = 1
        return exit_code
    finally:
        if temp_database and args.drop_isolated_pg:
            report.setdefault("cleanup", {})["postgres"] = _drop_temp_database(
                _resolve_admin_dsn(),
                temp_database,
            )
        try:
            report["artifact_backed_runtime_evidence"] = (
                _write_runtime_evidence_summary(
                    report,
                    runtime_root=runtime_root,
                    artifact_dir=artifact_dir,
                )
            )
        except Exception as exc:  # noqa: BLE001 - final report must still be written
            report["artifact_backed_runtime_evidence"] = {
                "status": "failed",
                "error_type": type(exc).__name__,
                "error": _redact_text(str(exc)),
            }
        report["file_evidence_manifest"] = _file_evidence_manifest(
            report,
            runtime_root=runtime_root,
            artifact_dir=artifact_dir,
        )
        report["clock_note"] = (
            "Timestamps may come from Python, PostgreSQL, and file-system clocks; "
            "reviewers should use step status and IDs as ordering evidence."
        )
        report["runner_exit_code"] = exit_code
        report["finished_at_utc"] = datetime.now(UTC).isoformat()
        report = _json_safe(_redact_obj(report))
        json_report.parent.mkdir(parents=True, exist_ok=True)
        json_report.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"{report.get('verdict')} {json_report}")


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run bounded redacted production daily-cycle proof evidence."
    )
    parser.add_argument("--date", default=DEFAULT_DATE, help="Tushare partition date YYYYMMDD")
    parser.add_argument(
        "--symbols",
        default=",".join(DEFAULT_SYMBOLS),
        help="comma-separated Tushare ts_code values",
    )
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--json-report", type=Path)
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="run redacted runtime preflights and write the JSON artifact",
    )
    parser.add_argument(
        "--mock-tushare",
        action="store_true",
        help="use data-platform's fixture adapter; marks evidence non-production",
    )
    parser.add_argument(
        "--run-dagster",
        action="store_true",
        help="attempt daily_cycle_job.execute_in_process with production providers",
    )
    parser.add_argument(
        "--no-isolated-pg",
        dest="use_isolated_pg",
        action="store_false",
        help="use configured DP_PG_DSN/DATABASE_URL directly",
    )
    parser.set_defaults(use_isolated_pg=True)
    parser.add_argument(
        "--drop-isolated-pg",
        action="store_true",
        help="drop the temporary PostgreSQL database after writing evidence",
    )
    parser.add_argument(
        "--skip-reasoner-health",
        action="store_true",
        help="skip live reasoner-runtime provider health check",
    )
    parser.add_argument(
        "--run-current-selection-tests",
        action="store_true",
        help="run data-platform tests/cycle/test_current_selection.py in preflight",
    )
    parser.add_argument(
        "--current-selection-test-timeout-s",
        type=int,
        default=180,
        help="timeout for optional data-platform current-selection tests",
    )
    parser.add_argument(
        "--include-traceback",
        action="store_true",
        help="include redacted traceback text in failed JSON evidence",
    )
    return parser.parse_args(argv)


def _run_preflights(
    *,
    runtime_root: Path,
    artifact_dir: Path,
    run_current_selection_tests: bool,
    current_selection_test_timeout_s: int,
    reasoner_health: bool,
) -> dict[str, Any]:
    probes: dict[str, Any] = {
        "imports": _probe_imports(),
        "pg_connect": _probe_pg_connect(),
        "neo4j_gds": _probe_neo4j_gds(artifact_dir),
        "audit_duckdb_write_read": _probe_audit_duckdb(runtime_root),
    }
    if reasoner_health:
        probes["codex_reasoner_health"] = _probe_reasoner_health()
    else:
        probes["codex_reasoner_health"] = {
            "status": "skipped",
            "reason": "--skip-reasoner-health",
        }
    if run_current_selection_tests:
        probes["data_platform_current_selection_tests"] = (
            _run_current_selection_tests(
                artifact_dir=artifact_dir,
                timeout_s=current_selection_test_timeout_s,
            )
        )
    else:
        probes["data_platform_current_selection_tests"] = {
            "status": "not_run",
            "reason": "--run-current-selection-tests was not set",
        }
    return probes


def _probe_imports() -> dict[str, Any]:
    modules = (
        "data_platform.cycle.current_selection",
        "data_platform.daily_refresh",
        "orchestrator_adapters.production_daily_cycle",
        "audit_eval.audit",
        "reasoner_runtime",
    )
    imported: list[str] = []
    try:
        for module in modules:
            __import__(module)
            imported.append(module)
    except Exception as exc:  # noqa: BLE001 - preflight evidence
        return {
            "status": "failed",
            "imported": imported,
            "error_type": type(exc).__name__,
            "error": _redact_text(str(exc)),
        }
    return {"status": "passed", "imported": list(modules)}


def _probe_pg_connect() -> dict[str, Any]:
    started = perf_counter()
    try:
        dsn = _resolve_admin_dsn()
        from sqlalchemy import create_engine, text

        from data_platform.ddl.runner import _sqlalchemy_postgres_uri

        engine = create_engine(_sqlalchemy_postgres_uri(dsn), pool_pre_ping=True)
        try:
            with engine.connect() as connection:
                one = connection.execute(text("SELECT 1")).scalar_one()
        finally:
            engine.dispose()
        return {
            "status": "passed",
            "result": int(one),
            "dsn": "<redacted:set>",
            "duration_ms": _elapsed_ms(started),
        }
    except Exception as exc:  # noqa: BLE001 - preflight evidence
        return {
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": _redact_text(str(exc)),
            "duration_ms": _elapsed_ms(started),
        }


def _probe_neo4j_gds(artifact_dir: Path) -> dict[str, Any]:
    artifact_path = artifact_dir / "neo4j-gds-preflight.json"
    started = perf_counter()
    evidence: dict[str, Any] = {
        "schema_version": f"{SCHEMA_VERSION}.neo4j-gds-preflight.v1",
        "status": "running",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "artifact": str(artifact_path),
        "neo4j_uri": _redact_text(os.environ.get("NEO4J_URI", "missing")),
        "neo4j_user": "set" if os.environ.get("NEO4J_USER") else "missing",
        "neo4j_database": os.environ.get("NEO4J_DATABASE", "neo4j"),
        "required_runtime": "Neo4j Graph Data Science plugin",
        "required_probes": [
            "CALL gds.version() YIELD gdsVersion RETURN gdsVersion",
            "CALL gds.graph.exists($graph_name) YIELD exists RETURN exists",
        ],
        "v5_0_1_semantics": {
            "neo4j_role": "hot_mirror",
            "canonical_truth": "Layer A canonical stores, not Neo4j",
            "no_graph_delta_writes": True,
            "gds_required_for_layer_c_graph_snapshot": True,
        },
    }
    try:
        from graph_engine.client import Neo4jClient
        from graph_engine.config import load_config_from_env
        from graph_engine.propagation._gds import probe_gds_availability

        config = load_config_from_env()
        with Neo4jClient(config) as client:
            connected = client.verify_connectivity()
            if not connected:
                raise ConnectionError("Neo4j connectivity check failed")
            availability = probe_gds_availability(client)
        evidence.update(
            {
                "status": "passed",
                "blocker": None,
                "gds_version": availability.gds_version,
                "gds_graph_exists_probe": {
                    "graph_name": "__graph_engine_gds_probe__",
                    "procedure_available": (
                        availability.graph_exists_procedure_available
                    ),
                },
            }
        )
    except Exception as exc:  # noqa: BLE001 - structured preflight evidence
        evidence.update(
            {
                "status": "failed",
                "blocker": "configured_neo4j_gds_runtime",
                "error_type": type(exc).__name__,
                "error": _redact_text(str(exc)),
            }
        )
    evidence["duration_ms"] = _elapsed_ms(started)
    _write_json_artifact(artifact_path, evidence)
    return {
        "status": evidence["status"],
        "artifact": str(artifact_path),
        "blocker": "configured_neo4j_gds_runtime"
        if evidence["status"] == "failed"
        else None,
        "gds_version": evidence.get("gds_version"),
        "duration_ms": evidence["duration_ms"],
    }


def _probe_reasoner_health() -> dict[str, Any]:
    started = perf_counter()
    try:
        import reasoner_runtime

        provider = os.environ.get("P2_REASONER_PROVIDER", "openai-codex")
        model = os.environ.get("P2_REASONER_MODEL", "gpt-5.5")
        timeout_s = _float_env("P2_REASONER_HEALTH_TIMEOUT_S", 60.0)
        profile = reasoner_runtime.ProviderProfile(
            provider=provider,
            model=model,
            timeout_ms=max(int(timeout_s * 1000), 1),
        )
        result = reasoner_runtime.health_check([profile], timeout_s=timeout_s)
        payload = result.model_dump(mode="json")
        statuses = payload.get("provider_statuses", [])
        return {
            "status": "passed"
            if payload.get("all_critical_targets_available") is True
            else "failed",
            "provider": provider,
            "model": model,
            "all_critical_targets_available": bool(
                payload.get("all_critical_targets_available")
            ),
            "summary": _redact_text(str(payload.get("summary", ""))),
            "provider_statuses": [
                {
                    "provider": item.get("provider"),
                    "model": item.get("model"),
                    "reachable": item.get("reachable"),
                    "latency_ms": item.get("latency_ms"),
                    "quota_status": item.get("quota_status"),
                    "error": _redact_text(str(item.get("error")))
                    if item.get("error")
                    else None,
                }
                for item in statuses
                if isinstance(item, Mapping)
            ],
            "duration_ms": _elapsed_ms(started),
        }
    except Exception as exc:  # noqa: BLE001 - preflight evidence
        return {
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": _redact_text(str(exc)),
            "duration_ms": _elapsed_ms(started),
        }


def _probe_audit_duckdb(runtime_root: Path) -> dict[str, Any]:
    started = perf_counter()
    db_path = runtime_root / "audit" / "preflight_audit_eval.duckdb"
    try:
        from audit_eval.audit import (
            DuckDBReplayRepository,
            ManagedDuckDBFormalAuditStorageAdapter,
            persist_audit_write_bundle,
        )

        storage = ManagedDuckDBFormalAuditStorageAdapter(db_path)
        bundle = _preflight_audit_bundle()
        audit_ids, replay_ids = persist_audit_write_bundle(bundle, storage)
        repository = DuckDBReplayRepository(db_path)
        audit_record = repository.get_audit_record_by_id(audit_ids[0])
        replay_record = repository.get_replay_record_by_id(replay_ids[0])
        if audit_record is None or replay_record is None:
            raise RuntimeError("audit/replay readback returned no rows")
        return {
            "status": "passed",
            "duckdb_path": str(db_path),
            "audit_ids": audit_ids,
            "replay_ids": replay_ids,
            "duration_ms": _elapsed_ms(started),
        }
    except Exception as exc:  # noqa: BLE001 - preflight evidence
        return {
            "status": "failed",
            "duckdb_path": str(db_path),
            "error_type": type(exc).__name__,
            "error": _redact_text(str(exc)),
            "duration_ms": _elapsed_ms(started),
        }


def _run_current_selection_tests(*, artifact_dir: Path, timeout_s: int) -> dict[str, Any]:
    started = perf_counter()
    summary_path = artifact_dir / "data-platform-current-selection-tests-summary.json"
    env = os.environ.copy()
    env["PYTHONPATH"] = (
        f"{DATA_PLATFORM_ROOT / 'src'}{os.pathsep}"
        f"{env.get('PYTHONPATH', '')}"
    )
    command = [
        sys.executable,
        "-m",
        "pytest",
        "tests/cycle/test_current_selection.py",
        "-q",
        "-rs",
    ]
    completed = subprocess.run(
        command,
        cwd=DATA_PLATFORM_ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout_s,
    )
    duration_ms = _elapsed_ms(started)
    status = "passed" if completed.returncode == 0 else "failed"
    summary_payload = {
        "schema_version": f"{SCHEMA_VERSION}.current-selection-tests-summary.v1",
        "status": status,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "artifact": str(summary_path),
        "command": command,
        "cwd": str(DATA_PLATFORM_ROOT),
        "test_path": "tests/cycle/test_current_selection.py",
        "returncode": completed.returncode,
        "duration_ms": duration_ms,
        "timeout_s": timeout_s,
        "process_stream_policy": _process_stream_policy(),
    }
    _write_json_artifact(summary_path, summary_payload)
    return {
        "status": "passed" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
        "summary_artifact": str(summary_path),
        "duration_ms": duration_ms,
        "process_stream_policy": _process_stream_policy(),
    }


def _process_stream_policy() -> dict[str, Any]:
    return {
        "captured_for_status_only": True,
        "persisted_text_artifact": False,
        "log_text_omitted_from_artifact": True,
        "pass_critical_facts_in_structured_fields": True,
    }


def _apply_data_platform_migrations(pg_dsn: str) -> dict[str, Any]:
    from data_platform.ddl.runner import MigrationRunner

    applied = MigrationRunner().apply_pending(pg_dsn)
    return {
        "status": "passed",
        "applied_versions": list(applied),
        "dsn": "<redacted:set>",
    }


def _initialize_proof_graph_status(
    *,
    pg_dsn: str,
    cycle_id: str,
    artifact_dir: Path,
    isolated_proof_db: bool,
) -> dict[str, Any]:
    artifact_path = artifact_dir / "graph-status-initialization.json"
    started = perf_counter()
    evidence: dict[str, Any] = {
        "schema_version": f"{SCHEMA_VERSION}.graph-status-initialization.v1",
        "status": "running",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "cycle_id": cycle_id,
        "artifact": str(artifact_path),
        "mode": "proof_only_live_metric_ready_seed"
        if isolated_proof_db
        else "configured_database_readiness_check",
        "dsn": "<redacted:set>",
        "v5_0_1_semantics": {
            "phase0_validates_only": True,
            "phase0_graph_delta_writes": 0,
            "neo4j_role": "hot_mirror",
            "canonical_truth": "Layer A canonical stores, not Neo4j",
            "proof_setup_step": True,
        },
    }
    try:
        from graph_engine.client import Neo4jClient
        from graph_engine.config import load_config_from_env
        from graph_engine.live_metrics import read_live_graph_metrics
        from graph_engine.models import Neo4jGraphStatus

        if isolated_proof_db:
            with Neo4jClient(load_config_from_env()) as client:
                node_count, edge_count, key_label_counts, checksum = (
                    read_live_graph_metrics(client)
                )
            seed_status = Neo4jGraphStatus(
                graph_status="ready",
                graph_generation_id=0,
                node_count=node_count,
                edge_count=edge_count,
                key_label_counts=key_label_counts,
                checksum=checksum,
                last_verified_at=datetime.now(UTC),
                last_reload_at=None,
                writer_lock_token=None,
            )
            before_status = _read_graph_status_row(pg_dsn)
            _upsert_graph_status_row(pg_dsn, seed_status)
            after_status = _read_graph_status_row(pg_dsn)
            evidence.update(
                {
                    "status": "passed",
                    "row_action": "upserted_live_metric_ready_status",
                    "previous_status_present": before_status is not None,
                    "previous_status": before_status,
                    "live_metric_seed": {
                        "node_count": node_count,
                        "edge_count": edge_count,
                        "key_label_counts": key_label_counts,
                        "checksum": checksum,
                    },
                    "seed_status": _json_safe(seed_status),
                    "readback_status": after_status,
                    "ready_for_graph_status_asset": _graph_status_row_ready(after_status),
                }
            )
        else:
            existing_status = _read_graph_status_row(pg_dsn)
            evidence.update(
                {
                    "status": "passed"
                    if _graph_status_row_ready(existing_status)
                    else "failed",
                    "row_action": "validated_existing_status_only",
                    "reason": (
                        "--no-isolated-pg was set; proof runner does not seed "
                        "neo4j_graph_status in a configured database"
                    ),
                    "readback_status": existing_status,
                    "ready_for_graph_status_asset": _graph_status_row_ready(
                        existing_status
                    ),
                }
            )
    except Exception as exc:  # noqa: BLE001 - proof evidence
        evidence.update(
            {
                "status": "failed",
                "error_type": type(exc).__name__,
                "error": _redact_text(str(exc)),
            }
        )
    evidence["duration_ms"] = _elapsed_ms(started)
    _write_json_artifact(artifact_path, evidence)
    return {
        "status": evidence["status"],
        "mode": evidence["mode"],
        "artifact": str(artifact_path),
        "ready_for_graph_status_asset": evidence.get("ready_for_graph_status_asset"),
        "phase0_graph_delta_writes": 0,
        "duration_ms": evidence["duration_ms"],
    }


def _upsert_graph_status_row(pg_dsn: str, status: Any) -> None:
    from sqlalchemy import create_engine, text

    from data_platform.ddl.runner import _sqlalchemy_postgres_uri

    engine = create_engine(_sqlalchemy_postgres_uri(pg_dsn), pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
CREATE TABLE IF NOT EXISTS neo4j_graph_status (
    status_key text PRIMARY KEY,
    graph_status text NOT NULL CHECK (
        graph_status IN ('ready', 'rebuilding', 'failed')
    ),
    graph_generation_id bigint NOT NULL CHECK (graph_generation_id >= 0),
    node_count bigint NOT NULL CHECK (node_count >= 0),
    edge_count bigint NOT NULL CHECK (edge_count >= 0),
    key_label_counts jsonb NOT NULL CHECK (jsonb_typeof(key_label_counts) = 'object'),
    checksum text NOT NULL CHECK (checksum <> ''),
    last_verified_at timestamptz NULL,
    last_reload_at timestamptz NULL,
    writer_lock_token text NULL CHECK (
        writer_lock_token IS NULL OR writer_lock_token <> ''
    ),
    updated_at timestamptz NOT NULL DEFAULT now()
)
"""
                )
            )
            connection.execute(
                text(
                    """
INSERT INTO neo4j_graph_status (
    status_key,
    graph_status,
    graph_generation_id,
    node_count,
    edge_count,
    key_label_counts,
    checksum,
    last_verified_at,
    last_reload_at,
    writer_lock_token
)
VALUES (
    'current',
    :graph_status,
    :graph_generation_id,
    :node_count,
    :edge_count,
    CAST(:key_label_counts AS jsonb),
    :checksum,
    :last_verified_at,
    :last_reload_at,
    :writer_lock_token
)
ON CONFLICT (status_key) DO UPDATE SET
    graph_status = EXCLUDED.graph_status,
    graph_generation_id = EXCLUDED.graph_generation_id,
    node_count = EXCLUDED.node_count,
    edge_count = EXCLUDED.edge_count,
    key_label_counts = EXCLUDED.key_label_counts,
    checksum = EXCLUDED.checksum,
    last_verified_at = EXCLUDED.last_verified_at,
    last_reload_at = EXCLUDED.last_reload_at,
    writer_lock_token = EXCLUDED.writer_lock_token,
    updated_at = now()
"""
                ),
                {
                    "graph_status": status.graph_status,
                    "graph_generation_id": status.graph_generation_id,
                    "node_count": status.node_count,
                    "edge_count": status.edge_count,
                    "key_label_counts": json.dumps(
                        status.key_label_counts,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    "checksum": status.checksum,
                    "last_verified_at": status.last_verified_at,
                    "last_reload_at": status.last_reload_at,
                    "writer_lock_token": status.writer_lock_token,
                },
            )
    finally:
        engine.dispose()


def _read_graph_status_row(pg_dsn: str) -> dict[str, Any] | None:
    from sqlalchemy import create_engine, text

    from data_platform.ddl.runner import _sqlalchemy_postgres_uri

    engine = create_engine(_sqlalchemy_postgres_uri(pg_dsn), pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            table_exists = connection.execute(
                text("SELECT to_regclass('public.neo4j_graph_status')")
            ).scalar_one()
            if table_exists is None:
                return None
            row = (
                connection.execute(
                    text(
                        """
SELECT graph_status,
       graph_generation_id,
       node_count,
       edge_count,
       key_label_counts,
       checksum,
       last_verified_at,
       last_reload_at,
       writer_lock_token
FROM neo4j_graph_status
WHERE status_key = 'current'
"""
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                return None
            payload = dict(row)
            key_label_counts = payload.get("key_label_counts")
            if isinstance(key_label_counts, str):
                payload["key_label_counts"] = json.loads(key_label_counts)
            elif isinstance(key_label_counts, Mapping):
                payload["key_label_counts"] = dict(key_label_counts)
            return _json_safe(payload)
    finally:
        engine.dispose()


def _graph_status_row_ready(row: Mapping[str, Any] | None) -> bool:
    if row is None:
        return False
    return (
        row.get("graph_status") == "ready"
        and row.get("writer_lock_token") is None
        and isinstance(row.get("graph_generation_id"), int)
        and isinstance(row.get("node_count"), int)
        and isinstance(row.get("edge_count"), int)
        and isinstance(row.get("key_label_counts"), Mapping)
        and bool(row.get("checksum"))
    )


def _run_daily_refresh(
    *,
    cycle_date: date,
    mock: bool,
    artifact_dir: Path,
) -> dict[str, Any]:
    from data_platform.config import reset_settings_cache
    from data_platform.daily_refresh import run_daily_refresh

    reset_settings_cache()
    report_path = artifact_dir / "daily-refresh.json"
    result = run_daily_refresh(
        cycle_date,
        mock=mock,
        select=DEFAULT_SELECT,
        json_report=report_path,
    )
    _sanitize_json_artifact_process_streams(report_path)
    if not result.ok:
        raise RuntimeError("daily_refresh failed; see daily-refresh.json")
    return {
        "status": "passed",
        "mock": bool(mock),
        "report": str(report_path),
        "steps": [
            {"name": step.name, "status": step.status}
            for step in result.steps
        ],
        "raw_artifacts": _raw_artifact_summary(_json_safe(result)),
    }


def _select_current_cycle(*, symbols: Sequence[str]) -> dict[str, Any]:
    from data_platform.cycle import select_current_cycle

    selection = select_current_cycle(symbols=symbols)
    evidence = _json_safe(selection.evidence)
    return {
        "status": "passed",
        "cycle_id": selection.cycle_id,
        "trade_date": selection.trade_date.isoformat(),
        "symbols": list(selection.symbols),
        "input_tables": list(selection.input_tables),
        "evidence": evidence,
    }


def _seed_current_cycle_candidates(
    *,
    selection: Mapping[str, Any],
    symbols: Sequence[str],
) -> dict[str, Any]:
    from data_platform.cycle import CycleAlreadyExists, create_cycle
    from data_platform.queue import submit_candidate
    from data_platform.queue.worker import validate_pending_candidates

    trade_date = date.fromisoformat(str(selection["trade_date"]))
    cycle_id = str(selection["cycle_id"])
    current_cycle_canonical_bootstrap = _seed_proof_current_cycle_canonical_inputs(
        cycle_id=cycle_id,
        trade_date=trade_date,
        symbols=symbols,
    )
    graph_bootstrap = _seed_proof_graph_inputs(cycle_id=cycle_id, symbols=symbols)
    try:
        cycle = create_cycle(trade_date)
        cycle_created = True
    except CycleAlreadyExists:
        cycle = None
        cycle_created = False
    submitted = [
        submit_candidate(
            {
                "payload_type": "Ex-1",
                "submitted_by": SUBMITTED_BY,
                "source": "tushare-current-cycle",
                "cycle_id": cycle_id,
                "ts_code": symbol,
            }
        )
        for symbol in symbols
    ]
    submitted.append(submit_candidate(graph_bootstrap["candidate_payload"]))
    validation = validate_pending_candidates(limit=len(submitted))
    if validation.accepted != len(submitted):
        raise RuntimeError("not all current-cycle candidates were accepted")
    return {
        "status": "passed",
        "cycle_created": cycle_created,
        "cycle_status": getattr(cycle, "status", None) if cycle is not None else "existing",
        "submitted_candidate_ids": [item.id for item in submitted],
        "proof_current_cycle_canonical_bootstrap": current_cycle_canonical_bootstrap,
        "proof_graph_bootstrap": graph_bootstrap["evidence"],
        "validation": asdict(validation),
    }


def _seed_proof_current_cycle_canonical_inputs(
    *,
    cycle_id: str,
    trade_date: date,
    symbols: Sequence[str],
) -> dict[str, Any]:
    """Seed proof-only canonical_v2 input rows from live staging views.

    The bounded proof fetches only the Tushare surfaces needed by P2 L1. The
    normal reader still requires provider-neutral canonical_v2 mart snapshots,
    so this setup step projects the freshly refreshed staging views into the
    minimal canonical marts for the selected symbols and publishes a local
    mart snapshot-set sidecar in the isolated proof warehouse.
    """

    import pyarrow as pa

    from data_platform.config import get_settings
    from data_platform.ddl.iceberg_tables import (
        CANONICAL_ENTITY_SPEC,
        CANONICAL_LINEAGE_DIM_SECURITY_SPEC,
        CANONICAL_LINEAGE_FACT_PRICE_BAR_SPEC,
        CANONICAL_V2_DIM_SECURITY_SPEC,
        CANONICAL_V2_FACT_PRICE_BAR_SPEC,
        ENTITY_ALIAS_SPEC,
        ensure_tables,
    )
    from data_platform.serving.catalog import load_catalog

    normalized_symbols = tuple(str(symbol).strip() for symbol in symbols if str(symbol).strip())
    if not normalized_symbols:
        raise RuntimeError("M2.6 proof canonical input bootstrap requires symbols")

    settings = get_settings()
    stock_rows, price_rows = _load_proof_staging_rows(
        settings.duckdb_path,
        trade_date=trade_date,
        symbols=normalized_symbols,
    )
    created_at = datetime.now(UTC).replace(tzinfo=None)
    catalog = load_catalog()
    ensure_tables(
        catalog,
        [
            CANONICAL_ENTITY_SPEC,
            ENTITY_ALIAS_SPEC,
            CANONICAL_V2_DIM_SECURITY_SPEC,
            CANONICAL_V2_FACT_PRICE_BAR_SPEC,
            CANONICAL_LINEAGE_DIM_SECURITY_SPEC,
            CANONICAL_LINEAGE_FACT_PRICE_BAR_SPEC,
        ],
    )

    entity_ids = [f"ENT_STOCK_{symbol}" for symbol in normalized_symbols]
    canonical_entity_table = catalog.load_table("canonical.canonical_entity")
    canonical_entity_table.append(
        pa.table(
            {
                "canonical_entity_id": entity_ids,
                "created_at": [created_at for _ in entity_ids],
            },
            schema=CANONICAL_ENTITY_SPEC.schema,
        )
    )

    alias_table = catalog.load_table("canonical.entity_alias")
    alias_table.append(
        pa.table(
            {
                "alias": list(normalized_symbols),
                "canonical_entity_id": entity_ids,
                "source": [SUBMITTED_BY for _ in entity_ids],
                "created_at": [created_at for _ in entity_ids],
            },
            schema=ENTITY_ALIAS_SPEC.schema,
        )
    )

    dim_security_table = catalog.load_table("canonical_v2.dim_security")
    dim_security_table.append(
        pa.table(
            _proof_dim_security_columns(stock_rows, canonical_loaded_at=created_at),
            schema=CANONICAL_V2_DIM_SECURITY_SPEC.schema,
        )
    )

    fact_price_bar_table = catalog.load_table("canonical_v2.fact_price_bar")
    fact_price_bar_table.append(
        pa.table(
            _proof_fact_price_bar_columns(price_rows, canonical_loaded_at=created_at),
            schema=CANONICAL_V2_FACT_PRICE_BAR_SPEC.schema,
        )
    )

    lineage_dim_security_table = catalog.load_table("canonical_lineage.lineage_dim_security")
    lineage_dim_security_table.append(
        pa.table(
            _proof_dim_security_lineage_columns(
                stock_rows,
                canonical_loaded_at=created_at,
            ),
            schema=CANONICAL_LINEAGE_DIM_SECURITY_SPEC.schema,
        )
    )

    lineage_fact_price_bar_table = catalog.load_table(
        "canonical_lineage.lineage_fact_price_bar"
    )
    lineage_fact_price_bar_table.append(
        pa.table(
            _proof_fact_price_bar_lineage_columns(
                price_rows,
                canonical_loaded_at=created_at,
            ),
            schema=CANONICAL_LINEAGE_FACT_PRICE_BAR_SPEC.schema,
        )
    )

    manifest_path = _write_proof_canonical_v2_snapshot_set(
        dim_security_table=dim_security_table,
        fact_price_bar_table=fact_price_bar_table,
        lineage_dim_security_table=lineage_dim_security_table,
        lineage_fact_price_bar_table=lineage_fact_price_bar_table,
    )
    return {
        "mode": "isolated_proof_current_cycle_canonical_input_seed",
        "proof_setup_step": True,
        "cycle_id": cycle_id,
        "trade_date": trade_date.isoformat(),
        "symbols": list(normalized_symbols),
        "canonical_entity_ids": entity_ids,
        "canonical_v2_tables": [
            "canonical_v2.dim_security",
            "canonical_v2.fact_price_bar",
        ],
        "canonical_lineage_tables": [
            "canonical_lineage.lineage_dim_security",
            "canonical_lineage.lineage_fact_price_bar",
        ],
        "mart_snapshot_set_manifest": str(manifest_path),
        "v5_0_1_semantics": {
            "source": "fresh daily_refresh staging views",
            "canonical_truth": "Layer A Iceberg proof warehouse",
            "neo4j_role": "not_used_for_p2_inputs",
            "phase0_graph_delta_write": False,
        },
    }


def _load_proof_staging_rows(
    duckdb_path: Path,
    *,
    trade_date: date,
    symbols: Sequence[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    import duckdb

    placeholders = ", ".join("?" for _ in symbols)
    connection = duckdb.connect(str(duckdb_path))
    try:
        stock_rows = _duckdb_rows(
            connection,
            f"""
            SELECT
                ts_code, symbol, name, market, industry, list_date, is_active,
                area, fullname, exchange, curr_type, list_status, delist_date,
                source_run_id, raw_loaded_at
            FROM stg_stock_basic
            WHERE ts_code IN ({placeholders})
            ORDER BY ts_code
            """,
            list(symbols),
        )
        price_rows = _duckdb_rows(
            connection,
            f"""
            SELECT
                ts_code, trade_date, open, high, low, close, pre_close, change,
                pct_chg, vol, amount, source_run_id, raw_loaded_at
            FROM stg_daily
            WHERE trade_date = ? AND ts_code IN ({placeholders})
            ORDER BY ts_code
            """,
            [trade_date, *list(symbols)],
        )
    finally:
        connection.close()

    stock_symbols = {str(row["ts_code"]) for row in stock_rows}
    price_symbols = {str(row["ts_code"]) for row in price_rows}
    missing_stock = sorted(set(symbols) - stock_symbols)
    missing_price = sorted(set(symbols) - price_symbols)
    if missing_stock or missing_price:
        raise RuntimeError(
            "proof canonical input bootstrap missing staging rows: "
            f"stock_basic={missing_stock}, daily={missing_price}"
        )
    return stock_rows, price_rows


def _duckdb_rows(connection: Any, sql: str, params: Sequence[Any]) -> list[dict[str, Any]]:
    cursor = connection.execute(sql, list(params))
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _proof_dim_security_columns(
    rows: Sequence[Mapping[str, Any]],
    *,
    canonical_loaded_at: datetime,
) -> dict[str, list[Any]]:
    return {
        "security_id": [_string(row.get("ts_code")) for row in rows],
        "symbol": [_string(row.get("symbol")) for row in rows],
        "display_name": [_string(row.get("name")) for row in rows],
        "market": [_string(row.get("market")) for row in rows],
        "industry": [_string(row.get("industry")) for row in rows],
        "list_date": [_date_or_none(row.get("list_date")) for row in rows],
        "is_active": [_bool_or_none(row.get("is_active")) for row in rows],
        "area": [_string_or_none(row.get("area")) for row in rows],
        "fullname": [_string_or_none(row.get("fullname")) for row in rows],
        "exchange": [_string_or_none(row.get("exchange")) for row in rows],
        "curr_type": [_string_or_none(row.get("curr_type")) for row in rows],
        "list_status": [_string_or_none(row.get("list_status")) for row in rows],
        "delist_date": [_date_or_none(row.get("delist_date")) for row in rows],
        "setup_date": [None for _ in rows],
        "province": [None for _ in rows],
        "city": [None for _ in rows],
        "reg_capital": [None for _ in rows],
        "employees": [None for _ in rows],
        "main_business": [None for _ in rows],
        "latest_namechange_name": [None for _ in rows],
        "latest_namechange_start_date": [None for _ in rows],
        "latest_namechange_end_date": [None for _ in rows],
        "latest_namechange_ann_date": [None for _ in rows],
        "latest_namechange_reason": [None for _ in rows],
        "canonical_loaded_at": [canonical_loaded_at for _ in rows],
    }


def _proof_fact_price_bar_columns(
    rows: Sequence[Mapping[str, Any]],
    *,
    canonical_loaded_at: datetime,
) -> dict[str, list[Any]]:
    return {
        "security_id": [_string(row.get("ts_code")) for row in rows],
        "trade_date": [_date_or_none(row.get("trade_date")) for row in rows],
        "freq": ["daily" for _ in rows],
        "open": [_decimal_or_none(row.get("open")) for row in rows],
        "high": [_decimal_or_none(row.get("high")) for row in rows],
        "low": [_decimal_or_none(row.get("low")) for row in rows],
        "close": [_decimal_or_none(row.get("close")) for row in rows],
        "pre_close": [_decimal_or_none(row.get("pre_close")) for row in rows],
        "change": [_decimal_or_none(row.get("change")) for row in rows],
        "pct_chg": [_decimal_or_none(row.get("pct_chg")) for row in rows],
        "vol": [_decimal_or_none(row.get("vol")) for row in rows],
        "amount": [_decimal_or_none(row.get("amount")) for row in rows],
        "adj_factor": [None for _ in rows],
        "canonical_loaded_at": [canonical_loaded_at for _ in rows],
    }


def _proof_dim_security_lineage_columns(
    rows: Sequence[Mapping[str, Any]],
    *,
    canonical_loaded_at: datetime,
) -> dict[str, list[Any]]:
    return {
        "security_id": [_string(row.get("ts_code")) for row in rows],
        "source_provider": ["tushare" for _ in rows],
        "source_interface_id": ["stock_basic" for _ in rows],
        "source_run_id": [_string(row.get("source_run_id")) for row in rows],
        "raw_loaded_at": [_datetime_or_none(row.get("raw_loaded_at")) for row in rows],
        "canonical_loaded_at": [canonical_loaded_at for _ in rows],
    }


def _proof_fact_price_bar_lineage_columns(
    rows: Sequence[Mapping[str, Any]],
    *,
    canonical_loaded_at: datetime,
) -> dict[str, list[Any]]:
    return {
        "security_id": [_string(row.get("ts_code")) for row in rows],
        "trade_date": [_date_or_none(row.get("trade_date")) for row in rows],
        "freq": ["daily" for _ in rows],
        "source_provider": ["tushare" for _ in rows],
        "source_interface_id": ["daily" for _ in rows],
        "source_run_id": [_string(row.get("source_run_id")) for row in rows],
        "raw_loaded_at": [_datetime_or_none(row.get("raw_loaded_at")) for row in rows],
        "canonical_loaded_at": [canonical_loaded_at for _ in rows],
    }


def _write_proof_canonical_v2_snapshot_set(
    *,
    dim_security_table: Any,
    fact_price_bar_table: Any,
    lineage_dim_security_table: Any,
    lineage_fact_price_bar_table: Any,
) -> Path:
    load_id = uuid4().hex
    canonical_v2_tables = {
        "dim_security": _snapshot_entry(dim_security_table, "canonical_v2.dim_security"),
        "fact_price_bar": _snapshot_entry(
            fact_price_bar_table,
            "canonical_v2.fact_price_bar",
        ),
    }
    canonical_lineage_tables = {
        "lineage_dim_security": _snapshot_entry(
            lineage_dim_security_table,
            "canonical_lineage.lineage_dim_security",
        ),
        "lineage_fact_price_bar": _snapshot_entry(
            lineage_fact_price_bar_table,
            "canonical_lineage.lineage_fact_price_bar",
        ),
    }
    manifest_path = _local_path_from_location(dim_security_table.location()).parent / (
        "_mart_snapshot_set.json"
    )
    payload = {
        "version": 2,
        "load_id": load_id,
        "published_at": datetime.now(UTC).isoformat(),
        "canonical_v2_tables": canonical_v2_tables,
        "canonical_lineage_tables": canonical_lineage_tables,
    }
    temp_path = manifest_path.with_name(f".{manifest_path.name}.{load_id}.tmp")
    temp_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    temp_path.replace(manifest_path)
    return manifest_path


def _snapshot_entry(table: Any, identifier: str) -> dict[str, int | str]:
    refreshed = table.refresh()
    snapshot = refreshed.current_snapshot()
    if snapshot is None:
        raise RuntimeError(f"{identifier} proof bootstrap did not create a snapshot")
    return {
        "identifier": identifier,
        "snapshot_id": int(snapshot.snapshot_id),
        "metadata_location": str(_local_path_from_location(refreshed.metadata_location)),
    }


def _local_path_from_location(location: str) -> Path:
    parsed = urlparse(location)
    if parsed.scheme == "file":
        return Path(unquote(parsed.path))
    if parsed.scheme:
        raise ValueError("proof canonical bootstrap requires local Iceberg metadata")
    return Path(location)


def _string(value: object) -> str:
    if value is None or not str(value).strip():
        raise RuntimeError("proof canonical bootstrap encountered an empty required value")
    return str(value).strip()


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _bool_or_none(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "t", "yes", "y"}:
        return True
    if text in {"0", "false", "f", "no", "n"}:
        return False
    return None


def _date_or_none(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    if len(text) == 8 and text.isdigit():
        return datetime.strptime(text, "%Y%m%d").date()
    return date.fromisoformat(text)


def _datetime_or_none(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value
        return value.astimezone(UTC).replace(tzinfo=None)
    text = str(value).strip()
    if not text:
        return None
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed
    return parsed.astimezone(UTC).replace(tzinfo=None)


def _decimal_or_none(value: object) -> Decimal | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return Decimal(text)


def _seed_proof_graph_inputs(
    *,
    cycle_id: str,
    symbols: Sequence[str],
) -> dict[str, Any]:
    """Seed the minimal proof inputs required for real Phase 1 propagation.

    The production daily-cycle proof is intentionally isolated. It already
    bootstraps current-cycle queue inputs; this companion seed provides one
    canonical entity pair plus one Ex-3 candidate graph delta so the proof can
    exercise the real data-platform reader, canonical write-back, Neo4j mirror,
    and GDS propagation path. This is proof runtime input, not a production
    shortcut or a graph snapshot fabrication.
    """

    import pyarrow as pa

    from data_platform.ddl.iceberg_tables import (
        CANONICAL_ENTITY_SPEC,
        ENTITY_ALIAS_SPEC,
        ensure_tables,
    )
    from data_platform.serving.catalog import load_catalog

    graph_nodes = _proof_graph_nodes(symbols)
    created_at = datetime.now(UTC).replace(tzinfo=None)
    catalog = load_catalog()
    ensure_tables(catalog, [CANONICAL_ENTITY_SPEC, ENTITY_ALIAS_SPEC])

    entity_table = catalog.load_table("canonical.canonical_entity")
    entity_table.append(
        pa.table(
            {
                "canonical_entity_id": [
                    node["canonical_entity_id"] for node in graph_nodes
                ],
                "created_at": [created_at for _ in graph_nodes],
            },
            schema=CANONICAL_ENTITY_SPEC.schema,
        )
    )

    alias_table = catalog.load_table("canonical.entity_alias")
    alias_table.append(
        pa.table(
            {
                "alias": [node["node_id"] for node in graph_nodes],
                "canonical_entity_id": [
                    node["canonical_entity_id"] for node in graph_nodes
                ],
                "source": [SUBMITTED_BY for _ in graph_nodes],
                "created_at": [created_at for _ in graph_nodes],
            },
            schema=ENTITY_ALIAS_SPEC.schema,
        )
    )

    live_node_seed = _seed_proof_live_graph_nodes(graph_nodes)
    candidate_payload = _proof_graph_delta_payload(cycle_id=cycle_id, nodes=graph_nodes)
    return {
        "candidate_payload": candidate_payload,
        "evidence": {
            "mode": "isolated_proof_graph_input_seed",
            "proof_setup_step": True,
            "v5_0_1_semantics": {
                "phase0_graph_delta_write": False,
                "neo4j_role": "hot_mirror",
                "canonical_truth": "Layer A Iceberg",
                "graph_delta_source": "candidate_queue Ex-3 proof input",
            },
            "canonical_entity_ids": [
                node["canonical_entity_id"] for node in graph_nodes
            ],
            "entity_aliases": [node["node_id"] for node in graph_nodes],
            "live_node_seed": live_node_seed,
            "candidate_delta_id": candidate_payload["delta_id"],
            "candidate_relation_type": candidate_payload["relation_type"],
            "candidate_payload_type": candidate_payload["payload_type"],
        },
    }


def _seed_proof_live_graph_nodes(nodes: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    """Seed proof-only endpoint nodes in the Neo4j hot mirror.

    Phase 1 sync is intentionally edge-only for Ex-3 candidate graph deltas:
    endpoint nodes must already exist in the hot mirror. The proof runner
    creates only nodes it marks as ``proof_bootstrap`` and first removes prior
    proof-bootstrap nodes, avoiding destructive operations against non-proof
    live graph data.
    """

    from graph_engine.client import Neo4jClient
    from graph_engine.config import load_config_from_env

    now = datetime.now(UTC).isoformat()
    rows = []
    for node in nodes:
        properties = {
            "proof_bootstrap": True,
            "symbol": node["symbol"],
        }
        rows.append(
            {
                **dict(node),
                "label": "Entity",
                "properties_json": json.dumps(properties, sort_keys=True),
                "canonical_id_rule_version": "proof-v1",
                "created_at": now,
                "updated_at": now,
            }
        )
    with Neo4jClient(load_config_from_env()) as client:
        cleanup_rows = client.execute_write(
            """
MATCH (node)
WHERE node.proof_bootstrap = true
WITH collect(node) AS proof_nodes
FOREACH (node IN proof_nodes | DETACH DELETE node)
RETURN size(proof_nodes) AS deleted_node_count
""",
            {},
        )
        seed_rows = client.execute_write(
            """
UNWIND $nodes AS row
MERGE (node:Entity {node_id: row.node_id})
SET node.canonical_entity_id = row.canonical_entity_id,
    node.canonical_id_rule_version = row.canonical_id_rule_version,
    node.label = row.label,
    node.properties_json = row.properties_json,
    node.symbol = row.symbol,
    node.proof_bootstrap = true,
    node.created_at = row.created_at,
    node.updated_at = row.updated_at
RETURN count(node) AS seeded_node_count
""",
            {"nodes": rows},
        )
    return {
        "deleted_prior_proof_nodes": int(
            (cleanup_rows[0] if cleanup_rows else {}).get("deleted_node_count") or 0
        ),
        "seeded_node_count": int(
            (seed_rows[0] if seed_rows else {}).get("seeded_node_count") or 0
        ),
        "node_ids": [node["node_id"] for node in nodes],
    }


def _proof_graph_nodes(symbols: Sequence[str]) -> tuple[dict[str, str], dict[str, str]]:
    if len(symbols) < 2:
        raise RuntimeError(
            "M2.6 graph proof bootstrap requires at least two current-cycle symbols "
            "to seed one propagation edge"
        )
    source_symbol = _proof_symbol_token(symbols[0])
    target_symbol = _proof_symbol_token(symbols[1])
    return (
        {
            "symbol": source_symbol,
            "node_id": f"proof-node-{source_symbol}",
            "canonical_entity_id": f"proof-entity-{source_symbol}",
        },
        {
            "symbol": target_symbol,
            "node_id": f"proof-node-{target_symbol}",
            "canonical_entity_id": f"proof-entity-{target_symbol}",
        },
    )


def _proof_graph_delta_payload(
    *,
    cycle_id: str,
    nodes: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    if len(nodes) < 2:
        raise RuntimeError("proof graph delta requires source and target nodes")
    source_node = nodes[0]
    target_node = nodes[1]
    delta_id = f"proof-delta-{cycle_id}-{source_node['symbol']}-{target_node['symbol']}"
    return {
        "payload_type": "Ex-3",
        "submitted_by": SUBMITTED_BY,
        "subsystem_id": "assembly.production_daily_cycle_proof",
        "delta_id": delta_id,
        "delta_type": "upsert_edge",
        "source_node": source_node["node_id"],
        "target_node": target_node["node_id"],
        "relation_type": "SUPPLY_CHAIN",
        "properties": {
            "weight": 1.0,
            "propagation_channel": "fundamental",
            "evidence_confidence": 1.0,
            "recency_decay": 1.0,
            "proof_bootstrap": True,
        },
        "evidence": [f"proof://m2.6/{cycle_id}/graph-delta"],
        "producer_context": {
            "source": "assembly.production_daily_cycle_proof",
            "proof_only": True,
        },
    }


def _proof_symbol_token(symbol: object) -> str:
    token = str(symbol).strip().upper()
    if not token:
        raise RuntimeError("proof graph bootstrap symbols must not be empty")
    return token.replace(".", "_")


def _freeze_current_cycle_candidates(*, symbols: Sequence[str]) -> dict[str, Any]:
    from data_platform.cycle import freeze_current_cycle_candidates

    frozen = freeze_current_cycle_candidates(symbols=symbols)
    return {
        "status": "passed",
        "cycle_id": frozen.selection.cycle_id,
        "trade_date": frozen.selection.trade_date.isoformat(),
        "frozen_candidate_ids": list(frozen.frozen_candidate_ids),
        "cutoff_metadata": _json_safe(frozen.evidence.get("cutoff_metadata")),
        "evidence": _json_safe(frozen.evidence),
    }


def _run_production_dagster(
    *,
    cycle_id: str,
    runtime_root: Path,
    artifact_dir: Path,
) -> dict[str, Any]:
    started = perf_counter()
    evidence_path = artifact_dir / "dagster-execution-evidence.json"
    policy_path = Path(
        os.environ.get(
            "ORCHESTRATOR_POLICY_PATH",
            str(ORCHESTRATOR_ROOT / "config" / "policy" / "gate_policy.lite.yaml"),
        )
    )
    os.environ["ORCHESTRATOR_POLICY_PATH"] = str(policy_path)
    evidence: dict[str, Any] = {
        "schema_version": f"{SCHEMA_VERSION}.dagster-execution-evidence.v1",
        "status": "running",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "job_name": "daily_cycle_job",
        "cycle_id": cycle_id,
        "artifact": str(evidence_path),
        "pass_basis": "resolved_selected_asset_keys",
        "legacy_materialization_claim_count": EXPECTED_DAGSTER_MATERIALIZATION_CLAIM_COUNT,
        "terminal_observed_steps": [],
        "terminal_observed_policy": (
            "terminal-observed progress is operator context only; PASS claims "
            "must come from this structured Dagster event artifact"
        ),
    }
    previous_cwd = Path.cwd()
    try:
        evidence["dbt_prepare"] = _prepare_orchestrator_dbt_project(
            runtime_root,
            artifact_dir,
        )
        if evidence["dbt_prepare"].get("status") != "passed":
            raise RuntimeError("orchestrator dbt compile failed")
    except Exception as exc:  # noqa: BLE001 - evidence before Dagster run
        evidence.update(
            {
                "status": "failed",
                "dagster_success": False,
                "failure_step": "orchestrator_dbt_compile",
                "error_type": type(exc).__name__,
                "error": _redact_text(str(exc)),
            }
        )
        return _finalize_dagster_evidence(evidence, evidence_path, started)

    os.chdir(ORCHESTRATOR_ROOT)
    try:
        import dagster

        from orchestrator.definitions import build_definitions
        from orchestrator_adapters.production_daily_cycle import (
            production_daily_cycle_provider,
        )

        provider = production_daily_cycle_provider()
        defs = build_definitions(module_factories=[provider], policy_path=policy_path)
        dagster.Definitions.validate_loadable(defs)
        job_def = defs.get_job_def("daily_cycle_job")
        selected_asset_keys = _selected_job_asset_keys(job_def, defs)
        if not selected_asset_keys:
            evidence.update(
                {
                    "status": "failed",
                    "dagster_success": False,
                    "failure_step": "dagster_setup",
                    "error_type": "RuntimeError",
                    "error": (
                        "daily_cycle_job resolved an empty selected asset set; "
                        "proof pass/fail cannot be evaluated without an asset basis"
                    ),
                    "selected_asset_count": 0,
                    "selected_asset_keys": [],
                }
            )
            return _finalize_dagster_evidence(evidence, evidence_path, started)
        with dagster.DagsterInstance.ephemeral() as instance:
            result = job_def.execute_in_process(
                instance=instance,
                tags={"cycle_id": cycle_id},
                raise_on_error=False,
            )
        evidence.update(
            _dagster_execution_evidence_from_result(
                result,
                cycle_id=cycle_id,
                job_name="daily_cycle_job",
                selected_asset_keys=selected_asset_keys,
                legacy_materialization_claim_count=(
                    EXPECTED_DAGSTER_MATERIALIZATION_CLAIM_COUNT
                ),
            )
        )
    except Exception as exc:  # noqa: BLE001 - Dagster evidence surface
        evidence.update(
            {
                "status": "failed",
                "dagster_success": False,
                "failure_step": evidence.get("failure_step") or "dagster_setup",
                "error_type": type(exc).__name__,
                "error": _redact_text(str(exc)),
            }
        )
    finally:
        os.chdir(previous_cwd)
    return _finalize_dagster_evidence(evidence, evidence_path, started)


def _finalize_dagster_evidence(
    evidence: dict[str, Any],
    evidence_path: Path,
    started: float,
) -> dict[str, Any]:
    evidence["duration_ms"] = _elapsed_ms(started)
    step = _dagster_step_from_evidence(evidence)
    evidence["status"] = step["status"]
    evidence["dagster_step_summary"] = step
    for key in (
        "asset_check_pass_basis",
        "asset_checks_complete",
        "artifact_backed_pass_claim",
        "expected_materialized_asset_count",
        "failed_asset_check_names",
        "failure_error",
        "failure_message",
        "failure_root_cause",
        "missing_expected_asset_check_names",
        "recorded_asset_check_count",
        "selected_asset_count_matches_materialization_basis",
        "supports_legacy_15_materializations_claim",
        "supports_selected_asset_materialization_claim",
    ):
        evidence[key] = step.get(key)
    _write_json_artifact(evidence_path, evidence)
    return step


def _dagster_step_from_evidence(evidence: Mapping[str, Any]) -> dict[str, Any]:
    selected_claim = evidence.get("materialization_count_against_selected_assets")
    if not isinstance(selected_claim, Mapping):
        selected_claim = {}
    legacy_claim = evidence.get("legacy_materialization_count_against_claim_15")
    if not isinstance(legacy_claim, Mapping):
        legacy_claim = {}
    selected_asset_count = int(evidence.get("selected_asset_count") or 0)
    selected_materializations_complete = bool(
        evidence.get("selected_materializations_complete")
    )
    selected_unique_count_matches = bool(
        selected_claim.get("actual_unique_count")
        == selected_claim.get("expected_selected_asset_count")
    )
    no_extra_materializations = not evidence.get("extra_materialized_asset_keys")
    failure_event = _first_mapping(evidence.get("failure_events"))
    failure_error = failure_event.get("error") if failure_event else None
    failure_message = failure_event.get("message") if failure_event else None
    failure_root_cause = _failure_root_cause(failure_error, failure_message)
    asset_check_basis = evidence.get("asset_check_pass_basis")
    if not isinstance(asset_check_basis, Mapping):
        asset_check_basis = _asset_check_pass_basis(evidence.get("asset_checks", []))
    asset_checks_complete = bool(asset_check_basis.get("asset_checks_complete"))
    artifact_backed_pass = bool(
        evidence.get("dagster_success") is True
        and selected_asset_count > 0
        and selected_materializations_complete
        and selected_unique_count_matches
        and no_extra_materializations
        and asset_checks_complete
    )
    return {
        "status": "passed" if artifact_backed_pass else "failed",
        "cycle_id": evidence.get("cycle_id"),
        "run_id": evidence.get("run_id"),
        "dagster_success": bool(evidence.get("dagster_success")),
        "artifact": evidence.get("artifact"),
        "dbt_prepare": evidence.get("dbt_prepare"),
        "artifact_backed_pass_claim": artifact_backed_pass,
        "asset_check_pass_basis": asset_check_basis,
        "asset_checks_complete": asset_checks_complete,
        "recorded_asset_check_count": asset_check_basis.get(
            "recorded_asset_check_count",
            0,
        ),
        "failed_asset_check_names": asset_check_basis.get(
            "failed_asset_check_names",
            [],
        ),
        "missing_expected_asset_check_names": asset_check_basis.get(
            "missing_expected_asset_check_names",
            [],
        ),
        "materialized_asset_count": evidence.get("materialized_asset_count", 0),
        "materialized_asset_keys": evidence.get("materialized_asset_keys", []),
        "selected_asset_count": selected_asset_count,
        "expected_materialized_asset_count": selected_claim.get(
            "expected_selected_asset_count", 0
        ),
        "selected_asset_count_matches_materialization_basis": selected_asset_count
        == selected_claim.get("expected_selected_asset_count"),
        "selected_materializations_complete": selected_materializations_complete,
        "failure_step": evidence.get("failure_step"),
        "failure_error": failure_error if isinstance(failure_error, Mapping) else None,
        "failure_message": failure_message,
        "failure_root_cause": failure_root_cause,
        "supports_selected_asset_materialization_claim": artifact_backed_pass,
        "legacy_claim_count": legacy_claim.get("legacy_claim_count"),
        "supports_legacy_15_materializations_claim": bool(
            legacy_claim.get("has_exactly_15") is True
            and legacy_claim.get("actual_unique_count")
            == legacy_claim.get("legacy_claim_count")
        ),
    }


def _first_mapping(value: Any) -> Mapping[str, Any] | None:
    if isinstance(value, Sequence) and not isinstance(value, str):
        for item in value:
            if isinstance(item, Mapping):
                return item
    return None


def _failure_root_cause(
    failure_error: object,
    failure_message: object,
) -> str | None:
    candidates: list[str] = []
    if isinstance(failure_error, Mapping) and failure_error.get("message"):
        candidates.append(str(failure_error["message"]))
    if failure_message:
        candidates.append(str(failure_message))
    for candidate in candidates:
        for raw_line in candidate.splitlines():
            line = raw_line.strip()
            if line.startswith(("ValueError:", "RuntimeError:", "ConnectionError:")):
                return _redact_text(line)
            if "GraphImpactSnapshot requires at least one target entity" in line:
                return _redact_text(line)
    if candidates:
        return _tail(candidates[0], limit=500)
    return None


def _selected_job_asset_keys(job_def: Any, defs: Any) -> list[str]:
    asset_keys: Any = ()
    try:
        selection = getattr(job_def, "selection", None)
        if selection is not None:
            asset_keys = selection.resolve(getattr(defs, "assets", None) or ())
    except Exception:  # noqa: BLE001 - best-effort evidence only
        asset_keys = ()
    selected_asset_keys = _asset_keys_to_sorted_strings(asset_keys)
    if selected_asset_keys:
        return selected_asset_keys
    return _definition_asset_keys(defs)


def _definition_asset_keys(defs: Any) -> list[str]:
    asset_keys: list[Any] = []
    for asset_def in getattr(defs, "assets", None) or ():
        keys = getattr(asset_def, "keys", None)
        if keys is not None:
            asset_keys.extend(keys)
            continue
        keys_by_output_name = getattr(asset_def, "keys_by_output_name", None)
        if isinstance(keys_by_output_name, Mapping):
            asset_keys.extend(keys_by_output_name.values())
            continue
        specs = getattr(asset_def, "specs", None)
        if specs is not None:
            asset_keys.extend(
                key
                for key in (getattr(spec, "key", None) for spec in specs)
                if key is not None
            )
            continue
        key = getattr(asset_def, "key", None)
        if key is not None:
            asset_keys.append(key)
            continue
        asset_key = getattr(asset_def, "asset_key", None)
        if asset_key is not None:
            asset_keys.append(asset_key)
    return _asset_keys_to_sorted_strings(asset_keys)


def _asset_keys_to_sorted_strings(asset_keys: Any) -> list[str]:
    return sorted(
        key
        for key in (_dagster_asset_key_to_string(asset_key) for asset_key in asset_keys)
        if key is not None
    )


def _dagster_execution_evidence_from_result(
    result: Any,
    *,
    cycle_id: str,
    job_name: str,
    selected_asset_keys: Sequence[str],
    legacy_materialization_claim_count: int,
) -> dict[str, Any]:
    events = tuple(getattr(result, "all_events", ()) or ())
    materializations: list[dict[str, Any]] = []
    asset_checks: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for index, event in enumerate(events):
        event_type = _dagster_event_type(event)
        step_key = _optional_event_attr(event, "step_key")
        asset_key = _dagster_asset_key_from_event(event)
        asset_key_text = _dagster_asset_key_to_string(asset_key)
        message = _optional_event_attr(event, "message")

        if _is_dagster_materialization_event(event, event_type):
            materializations.append(
                {
                    "index": index,
                    "step_key": step_key,
                    "asset_key": asset_key_text,
                    "metadata": _dagster_materialization_metadata(event),
                }
            )
        if _is_dagster_asset_check_event(event, event_type):
            asset_checks.append(
                {
                    "index": index,
                    "step_key": step_key,
                    "asset_key": asset_key_text,
                    "check_name": _dagster_asset_check_name(event),
                    "passed": _dagster_asset_check_passed(event),
                    "metadata": _dagster_asset_check_metadata(event),
                }
            )
        if _is_dagster_failure_event(event, event_type):
            failures.append(
                {
                    "index": index,
                    "step_key": step_key,
                    "event_type": event_type,
                    "message": _tail(str(message or ""), limit=2000),
                    "error": _dagster_failure_error(event),
                }
            )

    materialized_asset_keys = [
        str(record["asset_key"])
        for record in materializations
        if record.get("asset_key") is not None
    ]
    unique_materialized_asset_keys = sorted(set(materialized_asset_keys))
    missing_selected_asset_keys = sorted(
        set(selected_asset_keys).difference(unique_materialized_asset_keys)
    )
    extra_materialized_asset_keys = sorted(
        set(unique_materialized_asset_keys).difference(selected_asset_keys)
    )
    selected_materialization_claim = {
        "expected_selected_asset_count": len(selected_asset_keys),
        "actual_count": len(materialized_asset_keys),
        "actual_unique_count": len(unique_materialized_asset_keys),
        "has_exactly_selected_asset_count": len(unique_materialized_asset_keys)
        == len(selected_asset_keys),
        "missing_selected_asset_count": len(missing_selected_asset_keys),
        "extra_materialized_asset_count": len(extra_materialized_asset_keys),
    }
    legacy_materialization_claim = {
        "legacy_claim_count": legacy_materialization_claim_count,
        "actual_count": len(materialized_asset_keys),
        "actual_unique_count": len(unique_materialized_asset_keys),
        "has_at_least_15": len(materialized_asset_keys)
        >= legacy_materialization_claim_count,
        "has_exactly_15": len(unique_materialized_asset_keys)
        == legacy_materialization_claim_count,
        "historical_only": True,
    }
    selected_asset_count_matches_legacy_claim = (
        len(selected_asset_keys) == legacy_materialization_claim_count
    )
    failure_step = failures[0].get("step_key") if failures else None
    dagster_success = bool(getattr(result, "success", False))
    asset_check_basis = _asset_check_pass_basis(asset_checks)
    return {
        "status": "passed" if dagster_success else "failed",
        "dagster_execution_status": "passed" if dagster_success else "failed",
        "dagster_success": dagster_success,
        "run_id": getattr(result, "run_id", None),
        "job_name": job_name,
        "cycle_id": cycle_id,
        "selected_asset_count": len(selected_asset_keys),
        "selected_asset_keys": list(selected_asset_keys),
        "selected_asset_count_matches_legacy_claim": (
            selected_asset_count_matches_legacy_claim
        ),
        "materializations": materializations,
        "materialized_asset_count": len(materialized_asset_keys),
        "unique_materialized_asset_count": len(unique_materialized_asset_keys),
        "materialized_asset_keys": materialized_asset_keys,
        "unique_materialized_asset_keys": unique_materialized_asset_keys,
        "materialization_order": materialized_asset_keys,
        "materialization_count_against_selected_assets": selected_materialization_claim,
        "legacy_materialization_count_against_claim_15": legacy_materialization_claim,
        "selected_materializations_complete": (
            bool(selected_asset_keys) and not missing_selected_asset_keys
        ),
        "missing_selected_asset_keys": missing_selected_asset_keys,
        "extra_materialized_asset_keys": extra_materialized_asset_keys,
        "asset_checks": asset_checks,
        "asset_check_pass_basis": asset_check_basis,
        "asset_checks_complete": asset_check_basis["asset_checks_complete"],
        "recorded_asset_check_count": asset_check_basis["recorded_asset_check_count"],
        "failed_asset_check_names": asset_check_basis["failed_asset_check_names"],
        "missing_expected_asset_check_names": asset_check_basis[
            "missing_expected_asset_check_names"
        ],
        "failure_step": failure_step,
        "failure_events": failures,
        "terminal_observed_steps": [],
        "event_count": len(events),
    }


def _asset_check_pass_basis(asset_checks_value: Any) -> dict[str, Any]:
    asset_checks = [
        item for item in asset_checks_value or [] if isinstance(item, Mapping)
    ]
    expected_names = tuple(EXPECTED_DAGSTER_ASSET_CHECK_NAMES)
    recorded_names = [
        str(item.get("check_name"))
        for item in asset_checks
        if item.get("check_name") is not None
    ]
    recorded_name_set = set(recorded_names)
    missing_expected_names = sorted(set(expected_names).difference(recorded_name_set))
    failed_names: list[str] = []
    unknown_names: list[str] = []
    nonpassing_names: list[str] = []
    for index, item in enumerate(asset_checks):
        name = str(
            item.get("check_name")
            or item.get("step_key")
            or f"asset_check_{item.get('index', index)}"
        )
        passed = item.get("passed")
        if passed is not True:
            nonpassing_names.append(name)
        if passed is False:
            failed_names.append(name)
        elif passed is None:
            unknown_names.append(name)
    all_recorded_passed = not nonpassing_names
    return {
        "asset_checks_complete": bool(
            asset_checks and all_recorded_passed and not missing_expected_names
        ),
        "recorded_asset_check_count": len(asset_checks),
        "recorded_asset_check_names": sorted(recorded_names),
        "expected_asset_check_names": list(expected_names),
        "all_recorded_asset_checks_passed": all_recorded_passed,
        "failed_asset_check_names": failed_names,
        "unknown_asset_check_names": unknown_names,
        "nonpassing_asset_check_names": nonpassing_names,
        "missing_expected_asset_check_names": missing_expected_names,
    }


def _dagster_event_type(event: Any) -> str:
    event_type_value = getattr(event, "event_type_value", None)
    if event_type_value:
        return str(event_type_value)
    event_type = getattr(event, "event_type", None)
    value = getattr(event_type, "value", None)
    if value:
        return str(value)
    return str(event_type or "")


def _optional_event_attr(event: Any, attr: str) -> str | None:
    value = getattr(event, attr, None)
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _is_dagster_materialization_event(event: Any, event_type: str) -> bool:
    return bool(
        getattr(event, "is_step_materialization", False)
        or event_type == "ASSET_MATERIALIZATION"
    )


def _is_dagster_asset_check_event(event: Any, event_type: str) -> bool:
    return bool(
        getattr(event, "is_asset_check_evaluation", False)
        or event_type == "ASSET_CHECK_EVALUATION"
    )


def _is_dagster_failure_event(event: Any, event_type: str) -> bool:
    return bool(
        getattr(event, "is_step_failure", False)
        or event_type in {"STEP_FAILURE", "RUN_FAILURE"}
    )


def _dagster_asset_key_from_event(event: Any) -> Any:
    asset_key = getattr(event, "asset_key", None)
    if asset_key is not None:
        return asset_key
    event_specific_data = getattr(event, "event_specific_data", None)
    materialization = getattr(event_specific_data, "materialization", None)
    asset_key = getattr(materialization, "asset_key", None)
    if asset_key is not None:
        return asset_key
    evaluation = _dagster_asset_check_evaluation(event)
    check_key = getattr(evaluation, "check_key", None)
    return getattr(check_key, "asset_key", None)


def _dagster_asset_key_to_string(asset_key: Any) -> str | None:
    if asset_key is None:
        return None
    to_user_string = getattr(asset_key, "to_user_string", None)
    if callable(to_user_string):
        return str(to_user_string())
    path = getattr(asset_key, "path", None)
    if isinstance(path, Sequence) and not isinstance(path, str):
        return "/".join(str(part) for part in path)
    return str(asset_key)


def _dagster_materialization_metadata(event: Any) -> dict[str, Any]:
    event_specific_data = getattr(event, "event_specific_data", None)
    materialization = getattr(event_specific_data, "materialization", None)
    metadata = getattr(materialization, "metadata", None)
    if isinstance(metadata, Mapping):
        return _dagster_metadata_mapping(metadata)
    return {}


def _dagster_asset_check_evaluation(event: Any) -> Any:
    event_specific_data = getattr(event, "event_specific_data", None)
    for attr in ("asset_check_evaluation", "evaluation"):
        evaluation = getattr(event_specific_data, attr, None)
        if evaluation is not None:
            return evaluation
    if _looks_like_asset_check_evaluation(event_specific_data):
        return event_specific_data
    return getattr(event, "asset_check_evaluation", None)


def _looks_like_asset_check_evaluation(value: Any) -> bool:
    return value is not None and any(
        hasattr(value, attr)
        for attr in ("passed", "check_name", "check_key", "metadata")
    )


def _dagster_asset_check_name(event: Any) -> str | None:
    evaluation = _dagster_asset_check_evaluation(event)
    check_name = getattr(evaluation, "check_name", None)
    if check_name is not None:
        return str(check_name)
    check_key = getattr(evaluation, "check_key", None)
    name = getattr(check_key, "name", None)
    return str(name) if name is not None else None


def _dagster_asset_check_passed(event: Any) -> bool | None:
    evaluation = _dagster_asset_check_evaluation(event)
    passed = getattr(evaluation, "passed", None)
    return bool(passed) if passed is not None else None


def _dagster_asset_check_metadata(event: Any) -> dict[str, Any]:
    evaluation = _dagster_asset_check_evaluation(event)
    metadata = getattr(evaluation, "metadata", None)
    if isinstance(metadata, Mapping):
        return _dagster_metadata_mapping(metadata)
    return {}


def _dagster_failure_error(event: Any) -> dict[str, Any] | None:
    event_specific_data = getattr(event, "event_specific_data", None)
    error = getattr(event_specific_data, "error", None)
    if error is None:
        return None
    return {
        "type": type(error).__name__,
        "message": _redact_text(str(error)),
    }


def _dagster_metadata_mapping(metadata: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key): _dagster_metadata_value(value)
        for key, value in metadata.items()
    }


def _dagster_metadata_value(value: Any) -> Any:
    for attr in ("value", "text", "path", "url"):
        attr_value = getattr(value, attr, None)
        if attr_value is not None:
            return _json_safe(attr_value)
    safe_value = _json_safe(value)
    try:
        json.dumps(safe_value)
    except TypeError:
        return str(safe_value)
    return safe_value


def _write_json_artifact(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            _redact_obj(_json_safe(payload)),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _production_dagster_not_run() -> dict[str, Any]:
    return {
        "status": "not_run",
        "reason": "pass --run-dagster only when production graph/audit/provider runtime wiring is configured",
    }


def _production_provider_status() -> dict[str, Any]:
    try:
        from orchestrator_adapters.production_daily_cycle import (
            production_daily_cycle_status,
        )

        status = production_daily_cycle_status()
        return {"status": "passed", **_json_safe(asdict(status))}
    except Exception as exc:  # noqa: BLE001 - provider status evidence
        return {
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": _redact_text(str(exc)),
        }


def _apply_effective_provider_status(report: dict[str, Any]) -> None:
    provider_status = _mapping_get(report, "steps", "production_provider_status")
    if provider_status is None:
        return
    dagster_step = _mapping_get(report, "steps", "production_dagster")
    artifact_backed_dagster_pass = bool(
        dagster_step
        and dagster_step.get("status") == "passed"
        and dagster_step.get("artifact_backed_pass_claim") is True
    )
    raw_runtime_blockers = [
        str(blocker)
        for blocker in provider_status.get("runtime_blockers", [])
        if str(blocker)
    ]
    effective_runtime_blockers = _active_provider_runtime_blockers(
        report,
        provider_status=provider_status,
    )
    missing_surfaces = [
        str(surface)
        for surface in provider_status.get("missing_surfaces", [])
        if str(surface)
    ]
    provider_status["static_blocked"] = provider_status.get("blocked")
    provider_status["static_runtime_blockers"] = raw_runtime_blockers
    provider_status["effective_runtime_blockers"] = effective_runtime_blockers
    provider_status["effective_blocked"] = bool(
        provider_status.get("status") != "passed"
        or missing_surfaces
        or effective_runtime_blockers
    )
    provider_status["resolved_by_artifact_backed_run"] = bool(
        artifact_backed_dagster_pass
        and provider_status.get("status") == "passed"
        and not missing_surfaces
    )
    provider_status["resolution_basis"] = (
        "static provider runtime blockers are superseded by the structured "
        "artifact-backed daily_cycle_job pass for this proof run"
        if provider_status["resolved_by_artifact_backed_run"]
        else "static provider status remains effective until a structured "
        "artifact-backed daily_cycle_job pass resolves it"
    )


def _prepare_orchestrator_dbt_project(runtime_root: Path, artifact_dir: Path) -> dict[str, Any]:
    started = perf_counter()
    dbt_project = runtime_root / "orchestrator_dbt_stub"
    if dbt_project.exists():
        shutil.rmtree(dbt_project)
    shutil.copytree(
        ORCHESTRATOR_ROOT / "dbt_stub",
        dbt_project,
        ignore=shutil.ignore_patterns("target", "dbt_packages", "logs", "dagster_home"),
    )
    (dbt_project / "dagster_home").mkdir(parents=True, exist_ok=True)
    os.environ["ORCHESTRATOR_DBT_PROJECT_DIR"] = str(dbt_project)
    summary_path = artifact_dir / "orchestrator-dbt-compile-summary.json"
    dbt_executable = os.environ.get("DP_DBT_EXECUTABLE") or str(
        ASSEMBLY_ROOT / ".venv-py312" / "bin" / "dbt"
    )
    os.environ["DP_DBT_EXECUTABLE"] = dbt_executable
    command = [
        dbt_executable,
        "compile",
        "--profiles-dir",
        ".",
        "--project-dir",
        ".",
    ]
    completed = subprocess.run(
        command,
        cwd=dbt_project,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=90,
    )
    duration_ms = _elapsed_ms(started)
    status = "passed" if completed.returncode == 0 else "failed"
    manifest_path = dbt_project / "target" / "manifest.json"
    _write_json_artifact(
        summary_path,
        {
            "schema_version": f"{SCHEMA_VERSION}.orchestrator-dbt-compile-summary.v1",
            "status": status,
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "artifact": str(summary_path),
            "command": command,
            "cwd": str(dbt_project),
            "dbt_executable": dbt_executable,
            "project_dir": str(dbt_project),
            "manifest": str(manifest_path),
            "returncode": completed.returncode,
            "duration_ms": duration_ms,
            "timeout_s": 90,
            "process_stream_policy": _process_stream_policy(),
        },
    )
    return {
        "status": status,
        "project_dir": str(dbt_project),
        "manifest": str(manifest_path),
        "summary_artifact": str(summary_path),
        "returncode": completed.returncode,
        "duration_ms": duration_ms,
        "process_stream_policy": _process_stream_policy(),
    }


def _create_temp_database(admin_dsn: str, database_name: str) -> str:
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url

    from data_platform.ddl.runner import _sqlalchemy_postgres_uri

    admin_url = make_url(_sqlalchemy_postgres_uri(admin_dsn))
    server_url = admin_url.set(database="postgres")
    target_url = admin_url.set(database=database_name)
    engine = create_engine(
        server_url.render_as_string(hide_password=False),
        isolation_level="AUTOCOMMIT",
    )
    try:
        with engine.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{database_name}"'))
    finally:
        engine.dispose()
    return target_url.render_as_string(hide_password=False)


def _drop_temp_database(admin_dsn: str, database_name: str) -> dict[str, Any]:
    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.engine import make_url

        from data_platform.ddl.runner import _sqlalchemy_postgres_uri

        admin_url = make_url(_sqlalchemy_postgres_uri(admin_dsn))
        server_url = admin_url.set(database="postgres")
        engine = create_engine(
            server_url.render_as_string(hide_password=False),
            isolation_level="AUTOCOMMIT",
        )
        try:
            with engine.connect() as connection:
                connection.execute(
                    text(
                        """
                        SELECT pg_terminate_backend(pid)
                        FROM pg_stat_activity
                        WHERE datname = :database_name
                          AND pid <> pg_backend_pid()
                        """
                    ),
                    {"database_name": database_name},
                )
                connection.execute(text(f'DROP DATABASE IF EXISTS "{database_name}"'))
        finally:
            engine.dispose()
        return {"status": "passed", "database": database_name}
    except Exception as exc:  # noqa: BLE001 - cleanup evidence
        return {
            "status": "failed",
            "database": database_name,
            "error_type": type(exc).__name__,
            "error": _redact_text(str(exc)),
        }


def _configure_runtime_paths(runtime_root: Path, *, pg_dsn: str | None = None) -> None:
    env = {
        "DP_RAW_ZONE_PATH": str(runtime_root / "raw"),
        "DP_ICEBERG_WAREHOUSE_PATH": str(runtime_root / "warehouse"),
        "DP_DUCKDB_PATH": str(runtime_root / "duckdb" / "data_platform.duckdb"),
        "DP_ICEBERG_CATALOG_NAME": f"data_platform_daily_proof_{uuid4().hex[:8]}",
        "DP_CANONICAL_USE_V2": "1",
        "AUDIT_EVAL_DUCKDB_PATH": str(runtime_root / "audit" / "audit_eval.duckdb"),
        "GRAPH_PHASE1_SNAPSHOT_ARTIFACT_ROOT": str(
            runtime_root / "graph-phase1-snapshots"
        ),
    }
    if pg_dsn is not None:
        env["DP_PG_DSN"] = pg_dsn
        env["DATABASE_URL"] = pg_dsn
    os.environ.update(env)
    for key in (
        "DP_RAW_ZONE_PATH",
        "DP_ICEBERG_WAREHOUSE_PATH",
        "DP_DUCKDB_PATH",
        "GRAPH_PHASE1_SNAPSHOT_ARTIFACT_ROOT",
    ):
        Path(os.environ[key]).expanduser().parent.mkdir(parents=True, exist_ok=True)
    Path(os.environ["GRAPH_PHASE1_SNAPSHOT_ARTIFACT_ROOT"]).expanduser().mkdir(
        parents=True,
        exist_ok=True,
    )
    dbt_executable = os.environ.get("DP_DBT_EXECUTABLE") or str(
        ASSEMBLY_ROOT / ".venv-py312" / "bin" / "dbt"
    )
    os.environ["DP_DBT_EXECUTABLE"] = dbt_executable


def _resolve_admin_dsn() -> str:
    existing = os.environ.get("DP_PG_DSN") or os.environ.get("DATABASE_URL")
    if existing:
        return existing
    required = {
        key: os.environ.get(key)
        for key in (
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_HOST",
            "POSTGRES_PORT",
            "POSTGRES_DB",
        )
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise RuntimeError(
            "one of DP_PG_DSN, DATABASE_URL is required, or set POSTGRES_* variables; "
            "missing " + ", ".join(missing)
        )
    return (
        "postgresql://"
        f"{required['POSTGRES_USER']}:{required['POSTGRES_PASSWORD']}"
        f"@{required['POSTGRES_HOST']}:{required['POSTGRES_PORT']}"
        f"/{required['POSTGRES_DB']}"
    )


def _preflight_audit_bundle() -> Any:
    from audit_eval.contracts import AuditRecord, AuditWriteBundle, ReplayRecord

    now = datetime.now(UTC)
    sanitized_input = "runtime preflight input"
    raw_output = '{"ok":true}'
    input_hash = hashlib.sha256(sanitized_input.encode("utf-8")).hexdigest()
    output_hash = hashlib.sha256(raw_output.encode("utf-8")).hexdigest()
    audit_record = AuditRecord(
        record_id="audit-runtime-preflight-L4",
        cycle_id="cycle_runtime_preflight_20260428",
        layer="L4",
        object_ref="runtime_preflight",
        params_snapshot={"scope": "runtime_preflight"},
        llm_lineage={
            "called": True,
            "provider": "preflight",
            "model": "preflight",
            "input_hash": input_hash,
            "output_hash": output_hash,
        },
        llm_cost={"input_tokens": 1, "output_tokens": 1, "cost_usd": 0.0},
        sanitized_input=sanitized_input,
        input_hash=input_hash,
        raw_output=raw_output,
        parsed_result={"ok": True},
        output_hash=output_hash,
        degradation_flags={"degraded": False},
        created_at=now,
    )
    replay_record = ReplayRecord(
        replay_id="replay-runtime-preflight-runtime_preflight",
        cycle_id="cycle_runtime_preflight_20260428",
        object_ref="runtime_preflight",
        audit_record_ids=[audit_record.record_id],
        manifest_cycle_id="cycle_runtime_preflight_20260428",
        formal_snapshot_refs={"runtime_preflight": "snapshot://runtime-preflight"},
        graph_snapshot_ref=None,
        dagster_run_id="runtime-preflight",
        created_at=now,
    )
    return AuditWriteBundle(
        bundle_id="bundle-runtime-preflight-20260428",
        manifest_cycle_id="cycle_runtime_preflight_20260428",
        audit_records=[audit_record],
        replay_records=[replay_record],
        submitted_at=now,
        metadata={"source": "assembly.production_daily_cycle_proof.preflight"},
    )


def _raw_artifact_summary(result_payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for step in result_payload.get("steps", []):
        if not isinstance(step, Mapping) or step.get("name") != "adapter":
            continue
        metadata = step.get("metadata", {})
        if not isinstance(metadata, Mapping):
            continue
        for artifact in metadata.get("artifacts", []):
            if isinstance(artifact, Mapping):
                artifacts.append(
                    {
                        "dataset": artifact.get("dataset"),
                        "partition_date": artifact.get("partition_date"),
                        "row_count": artifact.get("row_count"),
                        "path": artifact.get("path"),
                    }
                )
    return artifacts


def _sanitize_json_artifact_process_streams(path: Path) -> None:
    if not path.exists():
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    sanitized = _sanitize_process_stream_fields(payload)
    _write_json_artifact(path, sanitized)


def _sanitize_process_stream_fields(value: Any) -> Any:
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        removed_stream_field = False
        for key, item in value.items():
            key_text = str(key)
            if key_text in PROCESS_STREAM_FIELD_NAMES:
                removed_stream_field = True
                continue
            sanitized[key_text] = _sanitize_process_stream_fields(item)
        if removed_stream_field:
            sanitized.setdefault("process_stream_policy", _process_stream_policy())
        return sanitized
    if isinstance(value, list | tuple):
        return [_sanitize_process_stream_fields(item) for item in value]
    return value


def _write_json_artifact(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            _json_safe(_redact_obj(payload)),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _open_blockers(report: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    for name in _failed_probe_names(report.get("preflight", {})):
        blockers.append(f"runtime preflight failed: {name}")
    dagster_step = _mapping_get(report, "steps", "production_dagster")
    if dagster_step and dagster_step.get("status") != "passed":
        blockers.append("full production daily_cycle_job Dagster proof has not passed")
        failure_step = dagster_step.get("failure_step")
        if failure_step:
            blockers.append(f"Dagster failure step: {failure_step}")
        failure_root_cause = dagster_step.get("failure_root_cause")
        if failure_root_cause:
            blockers.append(f"Dagster failure root cause: {failure_root_cause}")
    provider_status = _mapping_get(report, "steps", "production_provider_status")
    if provider_status:
        if provider_status.get("status") != "passed":
            blockers.append("production provider status collection failed")
        runtime_blockers = _active_provider_runtime_blockers(
            report,
            provider_status=provider_status,
        )
        effective_blocked = provider_status.get("effective_blocked")
        if effective_blocked is None:
            effective_blocked = provider_status.get("blocked") is True
        if effective_blocked is True and runtime_blockers:
            blockers.append("production provider status is blocked")
        for surface in provider_status.get("missing_surfaces", []):
            blockers.append(f"production provider surface missing: {surface}")
        for blocker in runtime_blockers:
            blockers.append(f"production provider runtime pending: {blocker}")
    else:
        blockers.append("production provider status is missing")
    if report.get("verdict") == "BLOCKED" and report.get("error"):
        error = report["error"]
        if isinstance(error, Mapping):
            blockers.append(str(error.get("message", "runner blocked")))
    return _dedupe(blockers)


def _active_provider_runtime_blockers(
    report: Mapping[str, Any],
    *,
    provider_status: Mapping[str, Any],
) -> list[str]:
    raw_blockers = [
        str(blocker)
        for blocker in provider_status.get("runtime_blockers", [])
        if str(blocker)
    ]
    dagster_step = _mapping_get(report, "steps", "production_dagster")
    if (
        dagster_step
        and dagster_step.get("status") == "passed"
        and dagster_step.get("artifact_backed_pass_claim") is True
    ):
        return []
    if not dagster_step:
        return raw_blockers

    failure_step = str(dagster_step.get("failure_step") or "")
    if failure_step == "graph_status":
        return _filter_blockers(raw_blockers, {"configured_graph_phase0_status_runtime"})
    if failure_step == "graph_promotion":
        return _filter_blockers(raw_blockers, {"configured_graph_phase1_runtime"})
    if failure_step == "graph_snapshot":
        return _filter_blockers(raw_blockers, {"configured_graph_phase1_runtime"})
    if failure_step in {"l1", "l2", "l3", "l4", "l5", "l6", "l7", "l8"}:
        return _filter_blockers(raw_blockers, {"configured_reasoner_runtime"})
    if failure_step in {
        "formal_objects_commit",
        "cycle_publish_manifest",
        "retrospective_hook",
    }:
        return _filter_blockers(
            raw_blockers,
            {"configured_audit_eval_retrospective_hook_runtime"},
        )
    return raw_blockers


def _filter_blockers(blockers: Sequence[str], allowed: set[str]) -> list[str]:
    return [blocker for blocker in blockers if blocker in allowed]


def _write_runtime_evidence_summary(
    report: Mapping[str, Any],
    *,
    runtime_root: Path,
    artifact_dir: Path,
) -> dict[str, Any]:
    summary_path = artifact_dir / "runtime-evidence-summary.json"
    runtime_files = _runtime_file_summaries(report, runtime_root=runtime_root)
    payload = {
        "schema_version": f"{SCHEMA_VERSION}.runtime-evidence-summary.v1",
        "status": "passed",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "artifact": str(summary_path),
        "runtime_root": str(runtime_root),
        "policy": {
            "non_artifact_tmp_paths_pass_critical": False,
            "pass_critical_runtime_evidence": (
                "Runtime files under assembly/tmp are source context only; "
                "pass-critical runtime facts are summarized and hashed in this "
                "artifact-root JSON."
            ),
        },
        "runtime_files": runtime_files,
        "raw_artifacts": _runtime_raw_artifact_summaries(report),
        "process_evidence_summaries": _runtime_process_evidence_summaries(report),
        "canonical_snapshot_set": _runtime_canonical_snapshot_summary(report),
        "preflight_audit_duckdb": _runtime_preflight_audit_summary(report),
    }
    _write_json_artifact(summary_path, payload)
    return {
        "status": "passed",
        "artifact": str(summary_path),
        "runtime_file_count": len(runtime_files),
        "sha256": _sha256_file(summary_path),
        "size_bytes": summary_path.stat().st_size,
        "non_artifact_tmp_paths_pass_critical": False,
    }


def _runtime_file_summaries(
    report: Mapping[str, Any],
    *,
    runtime_root: Path,
) -> list[dict[str, Any]]:
    paths: list[Path] = []
    _collect_evidence_paths(report, roots=(runtime_root,), paths=paths)
    summaries: list[dict[str, Any]] = []
    for path in sorted(set(paths), key=lambda item: str(item)):
        if not path.is_file():
            continue
        summaries.append(_path_hash_summary(path, root=runtime_root))
    return summaries


def _runtime_raw_artifact_summaries(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    records: list[Mapping[str, Any]] = []
    tushare_raw_artifacts = _nested_get(
        report,
        "steps",
        "tushare_refresh",
        "raw_artifacts",
    )
    if isinstance(tushare_raw_artifacts, Sequence) and not isinstance(
        tushare_raw_artifacts,
        str,
    ):
        records.extend(
            item for item in tushare_raw_artifacts if isinstance(item, Mapping)
        )
    input_refs = _nested_get(
        report,
        "steps",
        "current_cycle_selection",
        "evidence",
        "input_artifact_refs",
    )
    if isinstance(input_refs, Mapping):
        for value in input_refs.values():
            if isinstance(value, Sequence) and not isinstance(value, str):
                records.extend(item for item in value if isinstance(item, Mapping))

    merged_by_path: dict[str, dict[str, Any]] = {}
    for record in records:
        path_text = str(record.get("path") or "")
        if not path_text:
            continue
        summary = merged_by_path.setdefault(path_text, {"source_path": path_text})
        for field in (
            "dataset",
            "partition_date",
            "row_count",
            "run_id",
            "source_id",
            "written_at",
        ):
            value = record.get(field)
            if value is not None and summary.get(field) is None:
                summary[field] = value

    summaries: list[dict[str, Any]] = []
    for path_text, summary in merged_by_path.items():
        path = Path(path_text)
        summary.update(_path_hash_fields(path))
        summaries.append(summary)
    return summaries


def _runtime_process_evidence_summaries(
    report: Mapping[str, Any],
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    candidates = (
        (
            "data_platform_current_selection_tests",
            _nested_get(report, "preflight", "data_platform_current_selection_tests"),
        ),
        (
            "orchestrator_dbt_compile",
            _nested_get(report, "steps", "production_dagster", "dbt_prepare"),
        ),
    )
    for name, record in candidates:
        if not isinstance(record, Mapping):
            continue
        artifact_text = record.get("summary_artifact")
        if not isinstance(artifact_text, str) or not artifact_text:
            continue
        summary = {
            "name": name,
            "status": record.get("status"),
            "returncode": record.get("returncode"),
            "artifact": artifact_text,
            "process_stream_policy": record.get("process_stream_policy"),
        }
        summary.update(_path_hash_fields(Path(artifact_text)))
        summaries.append(summary)
    return summaries


def _runtime_canonical_snapshot_summary(
    report: Mapping[str, Any],
) -> dict[str, Any] | None:
    path_text = _nested_get(
        report,
        "steps",
        "candidate_seed",
        "proof_current_cycle_canonical_bootstrap",
        "mart_snapshot_set_manifest",
    )
    if not isinstance(path_text, str) or not path_text:
        return None
    path = Path(path_text)
    summary: dict[str, Any] = {"source_path": path_text}
    summary.update(_path_hash_fields(path))
    if path.is_file():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            summary.update(
                {
                    "load_id": payload.get("load_id"),
                    "published_at": payload.get("published_at"),
                    "canonical_v2_tables": payload.get("canonical_v2_tables"),
                    "canonical_lineage_tables": payload.get("canonical_lineage_tables"),
                }
            )
        except Exception as exc:  # noqa: BLE001 - summary should be best effort
            summary["parse_error"] = _redact_text(str(exc))
    return summary


def _runtime_preflight_audit_summary(
    report: Mapping[str, Any],
) -> dict[str, Any] | None:
    audit_probe = _mapping_get(report, "preflight", "audit_duckdb_write_read")
    if not audit_probe:
        return None
    path_text = audit_probe.get("duckdb_path")
    summary = {
        "audit_ids": audit_probe.get("audit_ids", []),
        "replay_ids": audit_probe.get("replay_ids", []),
        "source_path": path_text,
    }
    if isinstance(path_text, str) and path_text:
        summary.update(_path_hash_fields(Path(path_text)))
    return summary


def _path_hash_summary(path: Path, *, root: Path) -> dict[str, Any]:
    summary = {
        "path": str(path),
        "relative_to_runtime_root": str(path.relative_to(root)),
    }
    summary.update(_path_hash_fields(path))
    return summary


def _path_hash_fields(path: Path) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "exists_at_write_time": path.exists(),
    }
    if path.is_file():
        fields["size_bytes"] = path.stat().st_size
        fields["sha256"] = _sha256_file(path)
    return fields


def _file_evidence_manifest(
    report: Mapping[str, Any],
    *,
    runtime_root: Path,
    artifact_dir: Path,
) -> list[dict[str, Any]]:
    roots = (
        runtime_root.expanduser().resolve(strict=False),
        artifact_dir.expanduser().resolve(strict=False),
    )
    paths: list[Path] = []
    _collect_evidence_paths(report, roots=roots, paths=paths)
    manifest: list[dict[str, Any]] = []
    for path in sorted(set(paths), key=lambda item: str(item)):
        under_artifact_dir = _is_relative_to(path, artifact_dir)
        under_runtime_root = _is_relative_to(path, runtime_root)
        process_stream_artifact = _is_process_stream_artifact(path)
        entry: dict[str, Any] = {
            "path": str(path),
            "under_report_artifact_dir": under_artifact_dir,
            "under_runtime_root": under_runtime_root,
            "git_tracked_at_write_time": _git_tracked(path),
            "exists_at_write_time": path.exists(),
            "pass_critical": bool(
                under_artifact_dir
                and path.is_file()
                and not process_stream_artifact
            ),
        }
        if process_stream_artifact:
            entry["pass_critical"] = False
            entry["evidence_role"] = "process_stream_text_not_pass_critical"
        if under_runtime_root and not under_artifact_dir:
            entry["pass_critical"] = False
            entry["evidence_role"] = (
                "runtime_tmp_source_context_summarized_by_artifact_root"
            )
            entry["pass_critical_replacement"] = str(
                artifact_dir / "runtime-evidence-summary.json"
            )
        if path.is_file():
            entry["size_bytes"] = path.stat().st_size
            entry["sha256"] = _sha256_file(path)
        manifest.append(entry)
    return manifest


def _is_process_stream_artifact(path: Path) -> bool:
    return path.name.endswith((".stdout.txt", ".stderr.txt"))


def _collect_evidence_paths(
    value: Any,
    *,
    roots: tuple[Path, ...],
    paths: list[Path],
) -> None:
    if isinstance(value, Mapping):
        for item in value.values():
            _collect_evidence_paths(item, roots=roots, paths=paths)
        return
    if isinstance(value, list | tuple):
        for item in value:
            _collect_evidence_paths(item, roots=roots, paths=paths)
        return
    if not isinstance(value, str) or "/" not in value:
        return
    path = Path(value).expanduser()
    if not path.is_absolute():
        return
    resolved = path.resolve(strict=False)
    if any(_is_relative_to(resolved, root) for root in roots):
        paths.append(resolved)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root.expanduser().resolve(strict=False))
        return True
    except ValueError:
        return False


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_tracked(path: Path) -> bool:
    try:
        relative_path = path.resolve(strict=False).relative_to(ASSEMBLY_ROOT)
    except ValueError:
        return False
    if path.is_dir():
        return False
    completed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative_path)],
        cwd=ASSEMBLY_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def _failed_probe_names(preflight: object) -> list[str]:
    if not isinstance(preflight, Mapping):
        return []
    failed: list[str] = []
    for name, payload in preflight.items():
        if not isinstance(payload, Mapping):
            continue
        if payload.get("status") == "failed":
            failed.append(str(name))
    return failed


def _mapping_get(mapping: Mapping[str, Any], *keys: str) -> Mapping[str, Any] | None:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, Mapping) else None


def _nested_get(mapping: Mapping[str, Any], *keys: str) -> Any:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _dedupe(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    loaded_keys: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = _strip_env_value(value.strip())
        loaded_keys.append(key)
    for key in loaded_keys:
        os.environ[key] = os.path.expandvars(os.environ[key])


def _strip_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _prepend_pythonpath(paths: Sequence[Path]) -> None:
    existing = os.environ.get("PYTHONPATH")
    path_text = os.pathsep.join(str(path) for path in paths)
    os.environ["PYTHONPATH"] = path_text if not existing else path_text + os.pathsep + existing
    for path in reversed(paths):
        sys.path.insert(0, str(path))


def _parse_yyyymmdd(value: str) -> date:
    return datetime.strptime(value, "%Y%m%d").date()


def _split_symbols(value: str) -> tuple[str, ...]:
    symbols = tuple(symbol.strip().upper() for symbol in value.split(",") if symbol.strip())
    if not symbols:
        raise ValueError("--symbols must include at least one ts_code")
    return symbols


def _require_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(f"{key} is required")
    return value


def _env_presence() -> dict[str, str]:
    keys = (
        "DP_TUSHARE_TOKEN",
        "DP_PG_DSN",
        "DATABASE_URL",
        "DP_CANONICAL_USE_V2",
        "NEO4J_URI",
        "NEO4J_USER",
        "NEO4J_PASSWORD",
        "P2_REASONER_PROVIDER",
        "P2_REASONER_MODEL",
        "OPENAI_API_KEY",
        "AUDIT_EVAL_DUCKDB_PATH",
        "ORCHESTRATOR_POLICY_PATH",
        "ORCHESTRATOR_MODULE_FACTORIES",
        "GRAPH_PHASE1_SNAPSHOT_ARTIFACT_ROOT",
        "REASONER_RUNTIME_ENABLE_CODEX_OAUTH",
    )
    return {key: "set" if os.environ.get(key) else "missing" for key in keys}


def _repo_revisions() -> dict[str, dict[str, str]]:
    repos = {
        "data-platform": DATA_PLATFORM_ROOT,
        "main-core": MAIN_CORE_ROOT,
        "graph-engine": GRAPH_ENGINE_ROOT,
        "orchestrator": ORCHESTRATOR_ROOT,
        "audit-eval": AUDIT_EVAL_ROOT,
        "reasoner-runtime": REASONER_RUNTIME_ROOT,
        "assembly": ASSEMBLY_ROOT,
    }
    return {name: _repo_revision(path) for name, path in repos.items()}


def _repo_revision(path: Path) -> dict[str, str]:
    def _git(*args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=path,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            return "unknown"
        return completed.stdout.strip() or "unknown"

    status = _git("status", "--short")
    return {
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "head": _git("rev-parse", "--short", "HEAD"),
        "dirty": "yes" if status != "unknown" and status else "no",
    }


def _temp_database_name(stamp: str) -> str:
    normalized = stamp.lower().replace("-", "_")
    return f"dp_prod_cycle_proof_{normalized}_{uuid4().hex[:8]}"


def _elapsed_ms(started: float) -> int:
    return int((perf_counter() - started) * 1000)


def _float_env(key: str, default: float) -> float:
    raw = os.environ.get(key)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _tail(text: str, *, limit: int = 4000) -> str:
    redacted = _redact_text(text)
    if len(redacted) <= limit:
        return redacted
    return redacted[-limit:]


def _json_safe(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _json_safe(asdict(value))
    if hasattr(value, "model_dump") and callable(value.model_dump):
        return _json_safe(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def _redact_obj(value: Any, *, key_name: str = "") -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _redact_obj(item, key_name=str(key))
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [_redact_obj(item, key_name=key_name) for item in value]
    if isinstance(value, str):
        lowered = key_name.lower()
        if any(marker in lowered for marker in ("dsn", "token", "password", "secret", "api_key")):
            if value in {"missing", "set", "<redacted:set>", ""}:
                return value
            return "<redacted:set>"
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
