"""Run the P2 durable real-data Codex dry-run closure probe."""

from __future__ import annotations

import argparse
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
from typing import Any
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSEMBLY_ROOT = PROJECT_ROOT / "assembly"
DATA_PLATFORM_ROOT = PROJECT_ROOT / "data-platform"
ORCHESTRATOR_ROOT = PROJECT_ROOT / "orchestrator"
DEFAULT_ENV_FILE = ASSEMBLY_ROOT / ".env"
DEFAULT_DATE = "20260415"
DEFAULT_SYMBOLS = ("600519.SH", "000001.SZ")
SUBMITTED_BY = "p2-real-data-codex-dry-run"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a real Tushare + Codex P2 dry-run closure probe."
    )
    parser.add_argument("--date", default=DEFAULT_DATE, help="cycle date YYYYMMDD")
    parser.add_argument(
        "--symbols",
        default=",".join(DEFAULT_SYMBOLS),
        help="comma-separated Tushare ts_code values",
    )
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--json-report", type=Path)
    args = parser.parse_args(argv)

    _load_env_file(args.env_file)
    _prepend_pythonpath(
        [
            ORCHESTRATOR_ROOT / "src",
            PROJECT_ROOT / "main-core" / "src",
            PROJECT_ROOT / "reasoner-runtime",
            PROJECT_ROOT / "contracts" / "src",
            DATA_PLATFORM_ROOT / "src",
            PROJECT_ROOT / "audit-eval" / "src",
        ]
    )

    cycle_date = _parse_yyyymmdd(args.date)
    cycle_id = f"CYCLE_{cycle_date:%Y%m%d}"
    symbols = _split_symbols(args.symbols)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    runtime_root = (
        args.runtime_root
        or DATA_PLATFORM_ROOT / "tmp" / "p2-durable-real-data-codex" / stamp
    ).expanduser()
    artifact_dir = (
        args.artifact_dir
        or ASSEMBLY_ROOT
        / "reports"
        / "stabilization"
        / "p2-durable-real-data-codex-dry-run-artifacts"
        / stamp
    ).expanduser()
    json_report = (
        args.json_report
        or artifact_dir / "p2-durable-real-data-codex-dry-run.json"
    ).expanduser()
    runtime_root.mkdir(parents=True, exist_ok=True)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "status": "failed",
        "cycle_id": cycle_id,
        "trade_date": cycle_date.isoformat(),
        "symbols": list(symbols),
        "runtime_root": str(runtime_root),
        "artifact_dir": str(artifact_dir),
        "secrets": _secret_status(),
        "started_at": datetime.now(UTC).isoformat(),
    }

    try:
        _require_env("DP_TUSHARE_TOKEN")
        admin_dsn = _resolve_admin_dsn()
        temp_database = f"dp_p2_codex_{stamp.lower().replace('-', '_')}_{uuid4().hex[:8]}"
        pg_dsn = _create_temp_database(admin_dsn, temp_database)
        _configure_runtime_env(
            runtime_root=runtime_root,
            pg_dsn=pg_dsn,
            catalog_name=f"data_platform_p2_codex_{stamp.lower()}",
        )
        report["secrets"] = _secret_status()
        report["postgres"] = {
            "database": temp_database,
            "dsn": "<redacted:set>",
        }

        report["daily_refresh"] = _run_daily_refresh(
            cycle_date,
            artifact_dir / "daily-refresh.json",
        )
        report["candidate_freeze"] = _seed_and_freeze_candidates(cycle_date, symbols)
        _transition_cycle_to_phase3(cycle_id)
        report["orchestrator_dbt"] = _prepare_orchestrator_dbt_project(
            runtime_root,
            artifact_dir,
        )
        report["dry_run"] = _run_dagster_p2_dry_run(cycle_id)
        report["serving_readback"] = _read_back_manifest_bound_serving(
            cycle_id,
            report["dry_run"]["recommendation_snapshot_id"],
        )
        report["audit_replay_readback"] = _read_back_audit_replay(
            cycle_id,
            report["dry_run"],
        )
        report["status"] = "passed"
        return 0
    except Exception as exc:  # noqa: BLE001 - evidence must preserve the blocker
        report["error"] = str(exc)
        report["error_type"] = type(exc).__name__
        report["traceback"] = traceback.format_exc()
        return 1
    finally:
        report["finished_at"] = datetime.now(UTC).isoformat()
        json_report.parent.mkdir(parents=True, exist_ok=True)
        json_report.write_text(
            json.dumps(_json_safe(report), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )


def _configure_runtime_env(
    *,
    runtime_root: Path,
    pg_dsn: str,
    catalog_name: str,
) -> None:
    os.environ.update(
        {
            "DP_PG_DSN": pg_dsn,
            "DP_RAW_ZONE_PATH": str(runtime_root / "raw"),
            "DP_ICEBERG_WAREHOUSE_PATH": str(runtime_root / "warehouse"),
            "DP_DUCKDB_PATH": str(runtime_root / "duckdb" / "data_platform.duckdb"),
            "DP_ICEBERG_CATALOG_NAME": catalog_name,
            "AUDIT_EVAL_DUCKDB_PATH": str(runtime_root / "audit" / "audit_eval.duckdb"),
            "P2_REASONER_PROVIDER": os.environ.get(
                "P2_REASONER_PROVIDER",
                "openai-codex",
            ),
            "P2_REASONER_MODEL": os.environ.get("P2_REASONER_MODEL", "gpt-5.5"),
            "P2_REASONER_HEALTH_TIMEOUT_S": os.environ.get(
                "P2_REASONER_HEALTH_TIMEOUT_S",
                "60",
            ),
            "REASONER_RUNTIME_ENABLE_CODEX_OAUTH": os.environ.get(
                "REASONER_RUNTIME_ENABLE_CODEX_OAUTH",
                "1",
            ),
        }
    )
    dbt_executable = os.environ.get("DP_DBT_EXECUTABLE") or str(
        ASSEMBLY_ROOT / ".venv-py312" / "bin" / "dbt"
    )
    os.environ["DP_DBT_EXECUTABLE"] = dbt_executable


def _run_daily_refresh(cycle_date: date, report_path: Path) -> dict[str, Any]:
    from data_platform.daily_refresh import run_daily_refresh

    result = run_daily_refresh(
        cycle_date,
        mock=False,
        select=("stock_basic", "daily"),
        json_report=report_path,
    )
    payload = _json_safe(result)
    if not result.ok:
        raise RuntimeError("daily_refresh failed; see daily-refresh.json")
    return {
        "report": str(report_path),
        "ok": result.ok,
        "steps": [
            {"name": step.name, "status": step.status}
            for step in result.steps
        ],
        "raw_artifacts": _raw_artifact_summary(payload),
    }


def _seed_and_freeze_candidates(
    cycle_date: date,
    symbols: Sequence[str],
) -> dict[str, Any]:
    from data_platform.cycle import create_cycle, freeze_cycle_candidates
    from data_platform.queue import submit_candidate
    from data_platform.queue.worker import validate_pending_candidates

    cycle = create_cycle(cycle_date)
    submitted = [
        submit_candidate(
            {
                "payload_type": "Ex-1",
                "submitted_by": SUBMITTED_BY,
                "source": "tushare-staging",
                "cycle_id": cycle.cycle_id,
                "ts_code": symbol,
            }
        )
        for symbol in symbols
    ]
    validation = validate_pending_candidates(limit=len(submitted))
    if validation.accepted != len(submitted):
        raise RuntimeError("not all P2 current-cycle candidates were accepted")
    frozen = freeze_cycle_candidates(cycle.cycle_id)
    if frozen.candidate_count != len(submitted):
        raise RuntimeError("candidate freeze count does not match submitted symbols")
    return {
        "cycle_id": frozen.cycle_id,
        "candidate_ids": [item.id for item in submitted],
        "candidate_count": frozen.candidate_count,
        "selection_frozen_at": frozen.selection_frozen_at.isoformat()
        if frozen.selection_frozen_at
        else None,
        "validation": asdict(validation),
    }


def _transition_cycle_to_phase3(cycle_id: str) -> None:
    from data_platform.cycle import transition_cycle_status

    transition_cycle_status(cycle_id, "phase1")
    transition_cycle_status(cycle_id, "phase2")
    transition_cycle_status(cycle_id, "phase3")


def _prepare_orchestrator_dbt_project(
    runtime_root: Path,
    artifact_dir: Path,
) -> dict[str, Any]:
    dbt_project = runtime_root / "orchestrator_dbt_stub"
    if dbt_project.exists():
        shutil.rmtree(dbt_project)
    shutil.copytree(
        ORCHESTRATOR_ROOT / "dbt_stub",
        dbt_project,
        ignore=shutil.ignore_patterns("target", "dbt_packages", "logs", "dagster_home"),
    )
    (dbt_project / "dagster_home").mkdir(parents=True, exist_ok=True)
    dbt_executable = os.environ["DP_DBT_EXECUTABLE"]
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
    stdout_path = artifact_dir / "orchestrator-dbt-compile.stdout.txt"
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError("orchestrator dbt compile failed")
    os.environ["ORCHESTRATOR_DBT_PROJECT_DIR"] = str(dbt_project)
    return {
        "project_dir": str(dbt_project),
        "manifest": str(dbt_project / "target" / "manifest.json"),
        "compile_stdout": str(stdout_path),
    }


def _run_dagster_p2_dry_run(cycle_id: str) -> dict[str, Any]:
    policy_path = ORCHESTRATOR_ROOT / "config" / "policy" / "gate_policy.lite.yaml"
    os.environ["ORCHESTRATOR_POLICY_PATH"] = str(policy_path)

    previous_cwd = Path.cwd()
    os.chdir(ORCHESTRATOR_ROOT)
    try:
        import dagster

        from orchestrator.definitions import build_definitions
        from orchestrator.jobs.phase3 import (
            PHASE3_FORMAL_COMMIT_ASSET_KEY,
            PHASE3_MANIFEST_ASSET_KEY,
        )
        from orchestrator_adapters.p2_dry_run import P2DryRunAssetFactoryProvider

        provider = P2DryRunAssetFactoryProvider()
        defs = build_definitions(
            module_factories=[
                _fake_phase0_provider(dagster),
                _fake_phase1_provider(dagster),
                provider,
            ],
            policy_path=policy_path,
        )
        dagster.Definitions.validate_loadable(defs)
        with dagster.DagsterInstance.ephemeral() as instance:
            result = defs.get_job_def("daily_cycle_job").execute_in_process(
                instance=instance,
                tags={"cycle_id": cycle_id},
            )
    finally:
        os.chdir(previous_cwd)

    if not result.success:
        raise RuntimeError("daily_cycle_job failed")
    formal_commit = result.output_for_node(PHASE3_FORMAL_COMMIT_ASSET_KEY)
    manifest = result.output_for_node(PHASE3_MANIFEST_ASSET_KEY)
    recommendation_snapshot_id = int(manifest.table_snapshots["recommendation_snapshot"])
    audit_bundle = formal_commit.audit_write_bundle
    llm_audit_records = [
        record
        for record in audit_bundle.audit_records
        if record.llm_lineage.get("called") is True
    ]
    return {
        "provider": os.environ["P2_REASONER_PROVIDER"],
        "model": os.environ["P2_REASONER_MODEL"],
        "dagster_success": result.success,
        "input_evidence": dict(formal_commit.state.input_evidence),
        "audit_record_ids": list(formal_commit.persisted_audit_record_ids),
        "replay_record_ids": list(formal_commit.persisted_replay_record_ids),
        "llm_call_count": len(llm_audit_records),
        "llm_layers": [record.layer for record in llm_audit_records],
        "recommendation_snapshot_id": recommendation_snapshot_id,
        "manifest_ref": manifest.manifest_ref,
        "table_snapshots": dict(manifest.table_snapshots),
    }


def _read_back_manifest_bound_serving(
    cycle_id: str,
    recommendation_snapshot_id: int,
) -> dict[str, Any]:
    from data_platform.serving.formal import get_formal_by_id, get_formal_by_snapshot

    by_id = get_formal_by_id(cycle_id, "recommendation_snapshot")
    by_snapshot = get_formal_by_snapshot(
        recommendation_snapshot_id,
        "recommendation_snapshot",
    )
    return {
        "by_id": {
            "cycle_id": by_id.cycle_id,
            "snapshot_id": by_id.snapshot_id,
            "row_count": by_id.payload.num_rows,
        },
        "by_snapshot": {
            "cycle_id": by_snapshot.cycle_id,
            "snapshot_id": by_snapshot.snapshot_id,
            "row_count": by_snapshot.payload.num_rows,
        },
    }


def _read_back_audit_replay(cycle_id: str, dry_run: Mapping[str, Any]) -> dict[str, Any]:
    from audit_eval.audit import (
        DataPlatformFormalSnapshotGateway,
        DataPlatformManifestGateway,
        DuckDBReplayRepository,
        ReplayQueryContext,
        replay_cycle_object,
    )

    repository = DuckDBReplayRepository(os.environ["AUDIT_EVAL_DUCKDB_PATH"])
    audit_ids = [str(item) for item in dry_run["audit_record_ids"]]
    replay_ids = [str(item) for item in dry_run["replay_record_ids"]]
    missing_audit_ids = [
        record_id
        for record_id in audit_ids
        if repository.get_audit_record_by_id(record_id) is None
    ]
    missing_replay_ids = [
        replay_id
        for replay_id in replay_ids
        if repository.get_replay_record_by_id(replay_id) is None
    ]
    if missing_audit_ids or missing_replay_ids:
        raise RuntimeError("persisted audit/replay ids could not be queried")

    context = ReplayQueryContext(
        repository=repository,
        manifest_gateway=DataPlatformManifestGateway(),
        formal_gateway=DataPlatformFormalSnapshotGateway(),
        dagster_gateway=_StaticDagsterGateway(cycle_id=cycle_id),
        graph_gateway=None,
    )
    replay_view = replay_cycle_object(cycle_id, "recommendation_snapshot", context)
    return {
        "queried_audit_ids": len(audit_ids),
        "queried_replay_ids": len(replay_ids),
        "replay_object_ref": replay_view.object_ref,
        "replay_audit_record_count": len(replay_view.audit_records),
        "manifest_snapshot_keys": sorted(replay_view.manifest_snapshot_set),
        "historical_formal_object_keys": sorted(replay_view.historical_formal_objects),
    }


class _StaticDagsterGateway:
    def __init__(self, *, cycle_id: str) -> None:
        self.cycle_id = cycle_id

    def load_summary(self, dagster_run_id: str) -> dict[str, Any]:
        return {
            "run_id": dagster_run_id,
            "cycle_id": self.cycle_id,
            "source": "p2-durable-real-data-codex-dry-run",
        }


def _fake_phase0_provider(dagster: Any) -> object:
    from orchestrator.checks import DataReadinessSignal
    from orchestrator.jobs.phase0_constants import (
        PHASE0_CANDIDATE_FREEZE_ASSET_KEY,
        PHASE0_GRAPH_CONSISTENCY_CHECK_NAME,
        PHASE0_GRAPH_STATUS_ASSET_KEY,
        PHASE0_GROUP_NAME,
    )
    from orchestrator.sensors.data_readiness import DATA_READINESS_RESOURCE_KEY

    class FakeDataReadinessProvider:
        def get_data_readiness_signal(self) -> DataReadinessSignal:
            return DataReadinessSignal(ready=True, cycle_id="runtime-cycle")

    class FakeDataReadinessResource(dagster.ConfigurableResource):
        def create_resource(self, context: object) -> FakeDataReadinessProvider:
            return FakeDataReadinessProvider()

    @dagster.asset(
        name=PHASE0_CANDIDATE_FREEZE_ASSET_KEY,
        group_name=PHASE0_GROUP_NAME,
    )
    def candidate_freeze() -> str:
        return "data-platform-cycle-candidates-frozen"

    @dagster.asset(name=PHASE0_GRAPH_STATUS_ASSET_KEY, group_name=PHASE0_GROUP_NAME)
    def graph_status(candidate_freeze: str) -> str:
        return f"{candidate_freeze}:ready"

    @dagster.asset_check(
        asset=graph_status,
        name=PHASE0_GRAPH_CONSISTENCY_CHECK_NAME,
        blocking=True,
    )
    def neo4j_graph_consistency_check() -> object:
        return dagster.AssetCheckResult(passed=True)

    class FakePhase0Provider:
        def get_assets(self) -> tuple[object, ...]:
            return (candidate_freeze, graph_status)

        def get_checks(self) -> tuple[object, ...]:
            return (neo4j_graph_consistency_check,)

        def get_resources(self) -> dict[str, object]:
            return {DATA_READINESS_RESOURCE_KEY: FakeDataReadinessResource()}

    return FakePhase0Provider()


def _fake_phase1_provider(dagster: Any) -> object:
    from orchestrator.jobs.phase0_constants import (
        PHASE0_CANDIDATE_FREEZE_ASSET_KEY,
        PHASE0_GRAPH_STATUS_ASSET_KEY,
        PHASE0_READINESS_ASSET_KEY,
    )
    from orchestrator.jobs.phase1 import (
        PHASE1_GRAPH_PROMOTION_ASSET_KEY,
        PHASE1_GRAPH_SNAPSHOT_ASSET_KEY,
        PHASE1_GROUP_NAME,
    )

    @dagster.asset(
        name=PHASE1_GRAPH_PROMOTION_ASSET_KEY,
        group_name=PHASE1_GROUP_NAME,
        deps=[
            dagster.AssetKey([PHASE0_READINESS_ASSET_KEY]),
            dagster.AssetKey([PHASE0_CANDIDATE_FREEZE_ASSET_KEY]),
            dagster.AssetKey([PHASE0_GRAPH_STATUS_ASSET_KEY]),
        ],
    )
    def graph_promotion() -> str:
        return "promoted"

    @dagster.asset(
        name=PHASE1_GRAPH_SNAPSHOT_ASSET_KEY,
        group_name=PHASE1_GROUP_NAME,
    )
    def graph_snapshot(graph_promotion: str) -> str:
        return f"snapshot:{graph_promotion}"

    class FakePhase1Provider:
        def get_assets(self) -> tuple[object, ...]:
            return (graph_promotion, graph_snapshot)

        def get_checks(self) -> tuple[object, ...]:
            return ()

        def get_resources(self) -> dict[str, object]:
            return {}

    return FakePhase1Provider()


def _create_temp_database(admin_dsn: str, database_name: str) -> str:
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url

    from data_platform.serving.catalog import _sqlalchemy_postgres_uri

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


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = _strip_env_value(value.strip())


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
    symbols = tuple(symbol.strip() for symbol in value.split(",") if symbol.strip())
    if not symbols:
        raise ValueError("--symbols must include at least one ts_code")
    return symbols


def _require_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(f"{key} is required")
    return value


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
            "one of DP_PG_DSN, DATABASE_URL is required, or set POSTGRES_* "
            "variables; missing " + ", ".join(missing)
        )
    return (
        "postgresql://"
        f"{required['POSTGRES_USER']}:{required['POSTGRES_PASSWORD']}"
        f"@{required['POSTGRES_HOST']}:{required['POSTGRES_PORT']}"
        f"/{required['POSTGRES_DB']}"
    )


def _secret_status() -> dict[str, str]:
    return {
        key: "set" if os.environ.get(key) else "missing"
        for key in (
            "DP_TUSHARE_TOKEN",
            "DP_PG_DSN",
            "DATABASE_URL",
            "REASONER_RUNTIME_ENABLE_CODEX_OAUTH",
        )
    }


def _json_safe(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _json_safe(asdict(value))
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


if __name__ == "__main__":
    raise SystemExit(main())
