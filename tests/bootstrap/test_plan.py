from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

from assembly.bootstrap.plan import BootstrapPlanError, build_plan
from assembly.profiles.loader import load_profile

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROFILES_ROOT = PROJECT_ROOT / "profiles"
BUNDLES_ROOT = PROJECT_ROOT / "bundles"
COMPOSE_FILE = PROJECT_ROOT / "compose" / "lite-local.yaml"

FORBIDDEN_COMPOSE_SERVICES = {
    "minio",
    "grafana",
    "superset",
    "temporal",
    "feast",
    "milvus",
    "kafka",
    "flink",
    "duckdb",
    "dbt",
    "iceberg",
}


def test_lite_local_plan_uses_hard_ordered_startup_sequence() -> None:
    profile = load_profile(PROFILES_ROOT / "lite-local.yaml")

    plan = build_plan(
        profile,
        bundle_root=BUNDLES_ROOT,
        compose_file=COMPOSE_FILE,
    )

    assert plan.startup_order == [
        "postgres",
        "neo4j",
        "dagster-daemon",
        "dagster-webserver",
    ]
    assert [service.bundle_name for service in plan.services] == [
        "postgres",
        "neo4j",
        "dagster",
        "dagster",
    ]
    assert [stage.name for stage in plan.stages] == [
        "env_filesystem_readiness",
        "service_startup",
        "orchestrator_entrypoint_readiness",
        "public_smoke_probes",
    ]


def test_lite_local_shutdown_order_stops_dagster_before_databases() -> None:
    profile = load_profile(PROFILES_ROOT / "lite-local.yaml")

    plan = build_plan(
        profile,
        bundle_root=BUNDLES_ROOT,
        compose_file=COMPOSE_FILE,
    )

    assert plan.shutdown_order == [
        "dagster-webserver",
        "dagster-daemon",
        "neo4j",
        "postgres",
    ]
    assert plan.shutdown_order[0] == "dagster-webserver"
    assert plan.shutdown_order[-1] == "postgres"


def test_missing_enabled_bundle_raises_plan_error() -> None:
    profile = load_profile(PROFILES_ROOT / "lite-local.yaml").model_copy(
        update={"enabled_service_bundles": ["missing-bundle"]}
    )

    with pytest.raises(BootstrapPlanError, match="missing-bundle"):
        build_plan(profile, bundle_root=BUNDLES_ROOT, compose_file=COMPOSE_FILE)


def test_bundle_required_profiles_must_include_profile(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundles"
    bundle_root.mkdir()
    _write_bundle(
        bundle_root / "postgres.yaml",
        {
            "bundle_name": "postgres",
            "services": [
                {
                    "name": "postgres",
                    "image_or_cmd": "postgres:16",
                    "health_probe": "postgres-ready",
                    "env": {},
                }
            ],
            "startup_order": ["postgres"],
            "shutdown_order": ["postgres"],
            "health_checks": ["postgres-ready"],
            "required_profiles": ["full-dev"],
            "optional": False,
        },
    )
    profile = load_profile(PROFILES_ROOT / "lite-local.yaml").model_copy(
        update={"enabled_service_bundles": ["postgres"]}
    )

    with pytest.raises(BootstrapPlanError, match="not required by profile"):
        build_plan(profile, bundle_root=bundle_root, compose_file=COMPOSE_FILE)


def test_lite_plan_service_count_must_equal_profile_daemon_limit() -> None:
    profile = load_profile(PROFILES_ROOT / "lite-local.yaml").model_copy(
        update={"enabled_service_bundles": ["postgres"]}
    )

    with pytest.raises(BootstrapPlanError, match="expected 4"):
        build_plan(profile, bundle_root=BUNDLES_ROOT, compose_file=COMPOSE_FILE)


def test_optional_bundle_is_rejected_from_lite_bootstrap_plan(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundles"
    bundle_root.mkdir()
    _write_bundle(
        bundle_root / "postgres.yaml",
        {
            "bundle_name": "postgres",
            "services": [
                {
                    "name": "postgres",
                    "image_or_cmd": "postgres:16",
                    "health_probe": "postgres-ready",
                    "env": {},
                }
            ],
            "startup_order": ["postgres"],
            "shutdown_order": ["postgres"],
            "health_checks": ["postgres-ready"],
            "required_profiles": ["lite-local"],
            "optional": True,
        },
    )
    profile = load_profile(PROFILES_ROOT / "lite-local.yaml").model_copy(
        update={"enabled_service_bundles": ["postgres"]}
    )

    with pytest.raises(BootstrapPlanError, match="optional"):
        build_plan(profile, bundle_root=bundle_root, compose_file=COMPOSE_FILE)


def test_missing_compose_file_raises_plan_error(tmp_path: Path) -> None:
    profile = load_profile(PROFILES_ROOT / "lite-local.yaml")

    with pytest.raises(BootstrapPlanError, match="Compose artifact not found"):
        build_plan(
            profile,
            bundle_root=BUNDLES_ROOT,
            compose_file=tmp_path / "missing-compose.yaml",
        )


def test_plan_rejects_compose_image_drift_from_bundle_manifest(tmp_path: Path) -> None:
    profile = load_profile(PROFILES_ROOT / "lite-local.yaml")
    compose_file = _write_compose(
        tmp_path,
        lambda raw: raw["services"]["postgres"].update({"image": "postgres:15"}),
    )

    with pytest.raises(BootstrapPlanError, match="postgres.*image"):
        build_plan(profile, bundle_root=BUNDLES_ROOT, compose_file=compose_file)


def test_plan_rejects_command_service_image_drift_from_bundle_manifest(
    tmp_path: Path,
) -> None:
    profile = load_profile(PROFILES_ROOT / "lite-local.yaml")
    compose_file = _write_compose(
        tmp_path,
        lambda raw: raw["services"]["dagster-daemon"].update(
            {"image": "dagster/dagster:1.8.0"}
        ),
    )

    with pytest.raises(BootstrapPlanError, match="dagster-daemon.*image"):
        build_plan(profile, bundle_root=BUNDLES_ROOT, compose_file=compose_file)


def test_plan_rejects_compose_command_drift_from_bundle_manifest(
    tmp_path: Path,
) -> None:
    profile = load_profile(PROFILES_ROOT / "lite-local.yaml")
    compose_file = _write_compose(
        tmp_path,
        lambda raw: raw["services"]["dagster-daemon"].update(
            {"command": ["dagster-daemon", "run", "--verbose"]}
        ),
    )

    with pytest.raises(BootstrapPlanError, match="dagster-daemon.*command"):
        build_plan(profile, bundle_root=BUNDLES_ROOT, compose_file=compose_file)


def test_plan_rejects_compose_environment_drift_from_bundle_manifest(
    tmp_path: Path,
) -> None:
    profile = load_profile(PROFILES_ROOT / "lite-local.yaml")

    def mutate(raw: dict[str, object]) -> None:
        raw["services"]["postgres"]["environment"]["POSTGRES_DB"] = "${OTHER_DB}"

    compose_file = _write_compose(tmp_path, mutate)

    with pytest.raises(BootstrapPlanError, match="postgres.*environment"):
        build_plan(profile, bundle_root=BUNDLES_ROOT, compose_file=compose_file)


def test_plan_rejects_compose_health_probe_drift_from_bundle_manifest(
    tmp_path: Path,
) -> None:
    profile = load_profile(PROFILES_ROOT / "lite-local.yaml")

    def mutate(raw: dict[str, object]) -> None:
        raw["services"]["postgres"]["healthcheck"]["test"] = [
            "CMD-SHELL",
            "pg_isready",
        ]

    compose_file = _write_compose(tmp_path, mutate)

    with pytest.raises(BootstrapPlanError, match="postgres.*healthcheck"):
        build_plan(profile, bundle_root=BUNDLES_ROOT, compose_file=compose_file)


def test_plan_rejects_compose_dependencies_outside_startup_order(
    tmp_path: Path,
) -> None:
    profile = load_profile(PROFILES_ROOT / "lite-local.yaml")

    def mutate(raw: dict[str, object]) -> None:
        raw["services"]["neo4j"]["depends_on"] = {
            "dagster-daemon": {"condition": "service_healthy"}
        }

    compose_file = _write_compose(tmp_path, mutate)

    with pytest.raises(BootstrapPlanError, match="not earlier in startup_order"):
        build_plan(profile, bundle_root=BUNDLES_ROOT, compose_file=compose_file)


def test_plan_rejects_list_form_depends_on_without_service_healthy(
    tmp_path: Path,
) -> None:
    profile = load_profile(PROFILES_ROOT / "lite-local.yaml")

    def mutate(raw: dict[str, object]) -> None:
        raw["services"]["dagster-daemon"]["depends_on"] = ["postgres"]

    compose_file = _write_compose(tmp_path, mutate)

    with pytest.raises(BootstrapPlanError, match="depends_on.*service_healthy"):
        build_plan(profile, bundle_root=BUNDLES_ROOT, compose_file=compose_file)


def test_plan_rejects_shutdown_order_that_stops_dependency_first(
    tmp_path: Path,
) -> None:
    profile = load_profile(PROFILES_ROOT / "lite-local.yaml")
    bundle_root = _copy_bundle_root(tmp_path)
    dagster_bundle = yaml.safe_load(
        (bundle_root / "dagster.yaml").read_text(encoding="utf-8")
    )
    dagster_bundle["shutdown_order"] = ["dagster-daemon", "dagster-webserver"]
    _write_bundle(bundle_root / "dagster.yaml", dagster_bundle)

    with pytest.raises(
        BootstrapPlanError,
        match="shutdown_order.*dagster-webserver.*dagster-daemon",
    ):
        build_plan(profile, bundle_root=bundle_root, compose_file=COMPOSE_FILE)


def test_lite_compose_file_contains_only_phase_one_services() -> None:
    raw = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))

    assert set(raw["services"]) == {
        "postgres",
        "neo4j",
        "dagster-daemon",
        "dagster-webserver",
    }
    assert FORBIDDEN_COMPOSE_SERVICES.isdisjoint(raw["services"])


def test_lite_compose_stateful_databases_use_named_volumes() -> None:
    raw = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))

    assert set(raw["volumes"]) >= {"postgres_data", "neo4j_data"}
    assert "postgres_data:/var/lib/postgresql/data" in raw["services"]["postgres"][
        "volumes"
    ]
    assert "neo4j_data:/data" in raw["services"]["neo4j"]["volumes"]


def test_lite_compose_published_ports_bind_loopback_only() -> None:
    raw = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))

    published_ports = [
        port
        for service in raw["services"].values()
        for port in service.get("ports", [])
    ]

    assert published_ports
    assert all(port.startswith("127.0.0.1:") for port in published_ports)
    assert "${DAGSTER_HOST:-127.0.0.1}" in raw["services"]["dagster-webserver"][
        "command"
    ]


def test_dagster_daemon_healthcheck_does_not_depend_on_pgrep() -> None:
    raw = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
    healthcheck = raw["services"]["dagster-daemon"]["healthcheck"]["test"]

    assert "dagster-daemon liveness-check" in healthcheck
    assert all("pgrep" not in part for part in healthcheck)


def _write_bundle(path: Path, data: dict[str, object]) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _write_compose(
    tmp_path: Path,
    mutate: Callable[[dict[str, object]], None],
) -> Path:
    raw = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
    mutate(raw)
    compose_file = tmp_path / "compose.yaml"
    compose_file.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return compose_file


def _copy_bundle_root(tmp_path: Path) -> Path:
    bundle_root = tmp_path / "bundles"
    bundle_root.mkdir()
    for bundle_path in BUNDLES_ROOT.glob("*.yaml"):
        data = yaml.safe_load(bundle_path.read_text(encoding="utf-8"))
        _write_bundle(bundle_root / bundle_path.name, data)
    return bundle_root
