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
from pathlib import Path
from time import perf_counter
from typing import Any
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
EVIDENCE_DATE = "2026-04-28"
SUBMITTED_BY = "production-daily-cycle-proof-runner"
SECRET_ENV_KEYS = (
    "DP_TUSHARE_TOKEN",
    "DP_PG_DSN",
    "DATABASE_URL",
    "POSTGRES_PASSWORD",
    "NEO4J_PASSWORD",
    "OPENAI_API_KEY",
)


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
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
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
        "evidence_date": EVIDENCE_DATE,
        "generated_at_utc": datetime.now(UTC).isoformat(),
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
        "preflight": {},
        "steps": {},
        "blockers": [],
        "non_claims": [
            "not_p5_shadow_run_readiness",
            "not_sidecar_or_frontend_write_api",
            "not_api6_news_or_polymarket_flow",
            "not_production_daily_cycle_pass_certificate_unless_dagster_passed",
        ],
    }

    exit_code = 0
    temp_database: str | None = None
    try:
        _configure_runtime_paths(runtime_root)
        report["preflight"] = _run_preflights(
            runtime_root=runtime_root,
            artifact_dir=artifact_dir,
            run_current_selection_tests=args.run_current_selection_tests,
            current_selection_test_timeout_s=args.current_selection_test_timeout_s,
            reasoner_health=not args.skip_reasoner_health,
        )
        preflight_blockers = _failed_probe_names(report["preflight"])
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
        dagster_step = report["steps"].get("production_dagster", {})
        if isinstance(dagster_step, Mapping) and dagster_step.get("status") == "passed":
            report["verdict"] = "PRODUCTION_DAILY_CYCLE_PASS"
            exit_code = 0
        else:
            report["verdict"] = "PARTIAL_PASS_BLOCKED"
            report["blockers"] = _open_blockers(report)
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
        report["blockers"] = _open_blockers(report) or [_redact_text(str(exc))]
        exit_code = 1
        return exit_code
    finally:
        if temp_database and args.drop_isolated_pg:
            report.setdefault("cleanup", {})["postgres"] = _drop_temp_database(
                _resolve_admin_dsn(),
                temp_database,
            )
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
    stdout_path = artifact_dir / "data-platform-current-selection-tests.stdout.txt"
    stderr_path = artifact_dir / "data-platform-current-selection-tests.stderr.txt"
    env = os.environ.copy()
    env["PYTHONPATH"] = (
        f"{DATA_PLATFORM_ROOT / 'src'}{os.pathsep}"
        f"{env.get('PYTHONPATH', '')}"
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/cycle/test_current_selection.py",
            "-q",
            "-rs",
        ],
        cwd=DATA_PLATFORM_ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout_s,
    )
    stdout_path.write_text(_redact_text(completed.stdout), encoding="utf-8")
    stderr_path.write_text(_redact_text(completed.stderr), encoding="utf-8")
    return {
        "status": "passed" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
        "stdout_tail": _tail(completed.stdout),
        "stderr_tail": _tail(completed.stderr),
        "duration_ms": _elapsed_ms(started),
    }


def _apply_data_platform_migrations(pg_dsn: str) -> dict[str, Any]:
    from data_platform.ddl.runner import MigrationRunner

    applied = MigrationRunner().apply_pending(pg_dsn)
    return {
        "status": "passed",
        "applied_versions": list(applied),
        "dsn": "<redacted:set>",
    }


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
    validation = validate_pending_candidates(limit=len(submitted))
    if validation.accepted != len(submitted):
        raise RuntimeError("not all current-cycle candidates were accepted")
    return {
        "status": "passed",
        "cycle_created": cycle_created,
        "cycle_status": getattr(cycle, "status", None) if cycle is not None else "existing",
        "submitted_candidate_ids": [item.id for item in submitted],
        "validation": asdict(validation),
    }


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
    policy_path = Path(
        os.environ.get(
            "ORCHESTRATOR_POLICY_PATH",
            str(ORCHESTRATOR_ROOT / "config" / "policy" / "gate_policy.lite.yaml"),
        )
    )
    os.environ["ORCHESTRATOR_POLICY_PATH"] = str(policy_path)
    _prepare_orchestrator_dbt_project(runtime_root, artifact_dir)
    previous_cwd = Path.cwd()
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
        with dagster.DagsterInstance.ephemeral() as instance:
            result = defs.get_job_def("daily_cycle_job").execute_in_process(
                instance=instance,
                tags={"cycle_id": cycle_id},
            )
    finally:
        os.chdir(previous_cwd)
    if not result.success:
        raise RuntimeError("production daily_cycle_job failed")
    return {
        "status": "passed",
        "cycle_id": cycle_id,
        "dagster_success": bool(result.success),
    }


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


def _prepare_orchestrator_dbt_project(runtime_root: Path, artifact_dir: Path) -> dict[str, Any]:
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
    stdout_path = artifact_dir / "orchestrator-dbt-compile.stdout.txt"
    dbt_executable = os.environ.get("DP_DBT_EXECUTABLE") or str(
        ASSEMBLY_ROOT / ".venv-py312" / "bin" / "dbt"
    )
    os.environ["DP_DBT_EXECUTABLE"] = dbt_executable
    completed = subprocess.run(
        [
            dbt_executable,
            "compile",
            "--profiles-dir",
            ".",
            "--project-dir",
            ".",
        ],
        cwd=dbt_project,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=90,
    )
    stdout_path.write_text(_redact_text(completed.stdout), encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError("orchestrator dbt compile failed")
    return {
        "project_dir": str(dbt_project),
        "manifest": str(dbt_project / "target" / "manifest.json"),
        "compile_stdout": str(stdout_path),
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
        "AUDIT_EVAL_DUCKDB_PATH": str(runtime_root / "audit" / "audit_eval.duckdb"),
    }
    if pg_dsn is not None:
        env["DP_PG_DSN"] = pg_dsn
        env["DATABASE_URL"] = pg_dsn
    os.environ.update(env)
    for key in ("DP_RAW_ZONE_PATH", "DP_ICEBERG_WAREHOUSE_PATH", "DP_DUCKDB_PATH"):
        Path(os.environ[key]).expanduser().parent.mkdir(parents=True, exist_ok=True)
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


def _open_blockers(report: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    for name in _failed_probe_names(report.get("preflight", {})):
        blockers.append(f"runtime preflight failed: {name}")
    dagster_step = _mapping_get(report, "steps", "production_dagster")
    if dagster_step and dagster_step.get("status") != "passed":
        blockers.append("full production daily_cycle_job Dagster proof has not passed")
    provider_status = _mapping_get(report, "steps", "production_provider_status")
    if provider_status:
        for blocker in provider_status.get("runtime_blockers", []):
            blockers.append(f"production provider runtime pending: {blocker}")
    if report.get("verdict") == "BLOCKED" and report.get("error"):
        error = report["error"]
        if isinstance(error, Mapping):
            blockers.append(str(error.get("message", "runner blocked")))
    return _dedupe(blockers)


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
        entry: dict[str, Any] = {
            "path": str(path),
            "committed_with_report": _is_relative_to(path, artifact_dir),
            "exists_at_write_time": path.exists(),
        }
        if path.is_file():
            entry["size_bytes"] = path.stat().st_size
            entry["sha256"] = _sha256_file(path)
        manifest.append(entry)
    return manifest


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
        "NEO4J_URI",
        "NEO4J_USER",
        "NEO4J_PASSWORD",
        "P2_REASONER_PROVIDER",
        "P2_REASONER_MODEL",
        "OPENAI_API_KEY",
        "AUDIT_EVAL_DUCKDB_PATH",
        "ORCHESTRATOR_POLICY_PATH",
        "ORCHESTRATOR_MODULE_FACTORIES",
        "REASONER_RUNTIME_ENABLE_CODEX_OAUTH",
    )
    return {key: "set" if os.environ.get(key) else "missing" for key in keys}


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
