"""Click-based command line interface for assembly bootstrap workflows."""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from pathlib import Path

import click

from assembly.bootstrap import BootstrapStageError, bootstrap as execute_bootstrap
from assembly.bootstrap.plan import BootstrapPlan, BootstrapPlanError, build_plan
from assembly.bootstrap.runner import BootstrapResult, ComposeCommandError, Runner
from assembly.cli.release import make_release_freeze_command
from assembly.cli.setup import make_setup_command
from assembly.compat import (
    CompatibilityError,
    CompatibilityReport,
    run_contract_suite as execute_contract_suite,
)
from assembly.contracts.models import HealthResult, HealthStatus, IntegrationRunRecord
from assembly.health import healthcheck as execute_healthcheck
from assembly.profiles.errors import ProfileError, ProfileNotFoundError
from assembly.profiles.loader import list_profiles
from assembly.profiles.resolver import render_profile
from assembly.profiles.schema import EnvironmentProfile
from assembly.registry import (
    RegistryError,
    VersionLock,
    export_module_registry,
    freeze_profile,
    load_all,
)
from assembly.tests.e2e import run_min_cycle_e2e as execute_e2e
from assembly.tests.smoke import run_smoke as execute_smoke


PROFILE_OPTION = click.option(
    "--profile",
    "profile_id",
    default="lite-local",
    show_default=True,
    help="Profile id to operate on.",
)
PROFILES_DIR_OPTION = click.option(
    "--profiles-dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("profiles"),
    show_default=True,
    help="Directory containing profile manifests.",
)
BUNDLES_DIR_OPTION = click.option(
    "--bundles-dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("bundles"),
    show_default=True,
    help="Directory containing service bundle manifests.",
)
ENV_FILE_OPTION = click.option(
    "--env-file",
    type=click.Path(path_type=Path, dir_okay=False),
    default=Path(".env"),
    show_default=True,
    help="Env file to read before applying real environment overrides.",
)
OUT_OPTION = click.option(
    "--out",
    type=click.Path(path_type=Path),
    default=None,
    help="Output file or directory, depending on the command.",
)
TIMEOUT_SEC_OPTION = click.option(
    "--timeout-sec",
    type=float,
    default=30.0,
    show_default=True,
    help="Per-probe timeout in seconds.",
)
REPORTS_DIR_OPTION = click.option(
    "--reports-dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("reports/smoke"),
    show_default=True,
    help="Directory where smoke reports are written.",
)
CONTRACT_REPORTS_DIR_OPTION = click.option(
    "--reports-dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("reports/contract"),
    show_default=True,
    help="Directory where contract reports are written.",
)
E2E_REPORTS_DIR_OPTION = click.option(
    "--reports-dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("reports/e2e"),
    show_default=True,
    help="Directory where e2e reports are written.",
)
DRY_RUN_OPTION = click.option(
    "--dry-run",
    is_flag=True,
    help="Print the planned docker compose command without executing it.",
)
EXTRA_BUNDLES_OPTION = click.option(
    "--extra-bundles",
    default="",
    help="Comma-separated optional service bundles to append to the profile.",
)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def entrypoint() -> None:
    """Assembly bootstrap and artifact commands."""


@entrypoint.command("list-profiles")
@PROFILES_DIR_OPTION
def list_profiles_command(profiles_dir: Path) -> None:
    """List registered profiles."""

    try:
        profiles = list_profiles(profiles_dir)
    except ProfileError as exc:
        raise click.ClickException(str(exc)) from exc

    for profile in profiles:
        click.echo(f"{profile.profile_id}\t{profile.mode.value}")


@entrypoint.command("render-profile")
@PROFILE_OPTION
@PROFILES_DIR_OPTION
@BUNDLES_DIR_OPTION
@ENV_FILE_OPTION
@EXTRA_BUNDLES_OPTION
@OUT_OPTION
def render_profile_command(
    profile_id: str,
    profiles_dir: Path,
    bundles_dir: Path,
    env_file: Path,
    extra_bundles: str,
    out: Path | None,
) -> None:
    """Render a resolved, redacted profile snapshot."""

    try:
        parsed_extra_bundles = _parse_extra_bundles(extra_bundles)
        snapshot = render_profile(
            profile_id,
            profiles_root=profiles_dir,
            bundles_root=bundles_dir,
            env=_combined_env(env_file),
            extra_bundles=parsed_extra_bundles,
        )
        output_path = out or Path("reports/bootstrap") / (
            f"{profile_id}-resolved-config.json"
        )
        _dump_snapshot(snapshot, output_path)
    except (ProfileError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    except OSError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(str(output_path))


@entrypoint.command("bootstrap")
@PROFILE_OPTION
@PROFILES_DIR_OPTION
@BUNDLES_DIR_OPTION
@ENV_FILE_OPTION
@EXTRA_BUNDLES_OPTION
@OUT_OPTION
@DRY_RUN_OPTION
def bootstrap_command(
    profile_id: str,
    profiles_dir: Path,
    bundles_dir: Path,
    env_file: Path,
    extra_bundles: str,
    out: Path | None,
    dry_run: bool,
) -> None:
    """Resolve a profile and start its compose-managed services."""

    try:
        parsed_extra_bundles = _parse_extra_bundles(extra_bundles)
        compose_env_file = _compose_env_file(env_file)
        result = execute_bootstrap(
            profile_id,
            profiles_root=profiles_dir,
            bundle_root=bundles_dir,
            env=_combined_env(env_file),
            env_file=compose_env_file,
            extra_bundles=parsed_extra_bundles,
            runner=Runner(env_file=compose_env_file),
            dry_run=dry_run,
            report_path=out,
        )
        if dry_run:
            _print_start_result(result)
            return
    except (BootstrapPlanError, ProfileError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    except BootstrapStageError as exc:
        raise click.ClickException(_format_stage_error(exc)) from exc
    except ComposeCommandError as exc:
        raise click.ClickException(_format_compose_error(exc)) from exc
    except OSError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"started {profile_id}: {' '.join(result.service_order)}")


@entrypoint.command("shutdown")
@PROFILE_OPTION
@PROFILES_DIR_OPTION
@BUNDLES_DIR_OPTION
@ENV_FILE_OPTION
@EXTRA_BUNDLES_OPTION
@DRY_RUN_OPTION
def shutdown_command(
    profile_id: str,
    profiles_dir: Path,
    bundles_dir: Path,
    env_file: Path,
    extra_bundles: str,
    dry_run: bool,
) -> None:
    """Stop compose-managed services in the bootstrap shutdown order."""

    try:
        parsed_extra_bundles = _parse_extra_bundles(extra_bundles)
        plan = build_plan(
            _load_profile_by_id(profile_id, profiles_dir),
            bundle_root=bundles_dir,
            compose_file=None,
            extra_bundles=parsed_extra_bundles,
        )
        compose_env_file = _compose_env_file(env_file)
        if dry_run:
            _print_stop_plan(plan, compose_env_file)
            return

        result = Runner(env_file=compose_env_file).stop(plan)
    except (BootstrapPlanError, ProfileError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    except ComposeCommandError as exc:
        raise click.ClickException(_format_compose_error(exc)) from exc

    click.echo(f"stopped {profile_id}: {' '.join(result.service_order)}")


@entrypoint.command("healthcheck")
@PROFILE_OPTION
@PROFILES_DIR_OPTION
@BUNDLES_DIR_OPTION
@ENV_FILE_OPTION
@EXTRA_BUNDLES_OPTION
@OUT_OPTION
@TIMEOUT_SEC_OPTION
def healthcheck_command(
    profile_id: str,
    profiles_dir: Path,
    bundles_dir: Path,
    env_file: Path,
    extra_bundles: str,
    out: Path | None,
    timeout_sec: float,
) -> None:
    """Run healthcheck convergence for a resolved profile."""

    try:
        parsed_extra_bundles = _parse_extra_bundles(extra_bundles)
        results = execute_healthcheck(
            profile_id,
            profiles_root=profiles_dir,
            bundles_root=bundles_dir,
            registry_root=Path("."),
            env=_combined_env(env_file),
            extra_bundles=parsed_extra_bundles,
            timeout_sec=timeout_sec,
        )
        if out is not None:
            _dump_health_results(results, out)
    except (ProfileError, RegistryError, OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc

    for result in results:
        click.echo(
            f"{result.module_id}\t{result.probe_name}\t{result.status.value}\t"
            f"{result.message}"
        )

    raise click.exceptions.Exit(_health_exit_code(results))


@entrypoint.command("smoke")
@PROFILE_OPTION
@PROFILES_DIR_OPTION
@BUNDLES_DIR_OPTION
@ENV_FILE_OPTION
@EXTRA_BUNDLES_OPTION
@REPORTS_DIR_OPTION
@TIMEOUT_SEC_OPTION
def smoke_command(
    profile_id: str,
    profiles_dir: Path,
    bundles_dir: Path,
    env_file: Path,
    extra_bundles: str,
    reports_dir: Path,
    timeout_sec: float,
) -> None:
    """Run the system-level smoke suite for a resolved profile."""

    try:
        parsed_extra_bundles = _parse_extra_bundles(extra_bundles)
        record = execute_smoke(
            profile_id,
            profiles_root=profiles_dir,
            bundles_root=bundles_dir,
            registry_root=Path("."),
            reports_dir=reports_dir,
            env=_combined_env(env_file),
            extra_bundles=parsed_extra_bundles,
            timeout_sec=timeout_sec,
        )
    except (ProfileError, RegistryError, OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(
        f"{record.status}\t{record.run_id}\tfailing={','.join(record.failing_modules)}"
    )
    raise click.exceptions.Exit(_smoke_exit_code(record))


@entrypoint.command("contract-suite")
@PROFILE_OPTION
@PROFILES_DIR_OPTION
@BUNDLES_DIR_OPTION
@ENV_FILE_OPTION
@CONTRACT_REPORTS_DIR_OPTION
@TIMEOUT_SEC_OPTION
@EXTRA_BUNDLES_OPTION
@click.option(
    "--promote",
    is_flag=True,
    help=(
        "Promote a matching draft compatibility matrix entry when all required "
        "runs passed."
    ),
)
def contract_suite_command(
    profile_id: str,
    profiles_dir: Path,
    bundles_dir: Path,
    env_file: Path,
    reports_dir: Path,
    timeout_sec: float,
    extra_bundles: str,
    promote: bool,
) -> None:
    """Run the contract compatibility suite for a resolved profile.

    ``--extra-bundles`` routes the contract suite to a per-optional-bundle
    matrix row (codex P2 follow-up on MinIO pilot). Without it, the
    default-profile row is targeted.
    """

    try:
        parsed_extra_bundles = _parse_extra_bundles(extra_bundles)
        report = execute_contract_suite(
            profile_id,
            profiles_root=profiles_dir,
            bundles_root=bundles_dir,
            registry_root=Path("."),
            reports_dir=reports_dir,
            env=_combined_env(env_file),
            timeout_sec=timeout_sec,
            promote=promote,
            extra_bundles=parsed_extra_bundles,
        )
    except (
        ProfileError,
        RegistryError,
        CompatibilityError,
        OSError,
        ValueError,
    ) as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(
        f"{report.run_record.status}\t{report.run_record.run_id}\t"
        f"failing={','.join(report.run_record.failing_modules)}\t"
        f"report={report.report_path}"
    )
    raise click.exceptions.Exit(_contract_exit_code(report))


@entrypoint.command("e2e")
@PROFILE_OPTION
@PROFILES_DIR_OPTION
@BUNDLES_DIR_OPTION
@ENV_FILE_OPTION
@click.option(
    "--fixture",
    "fixture_dir",
    type=click.Path(path_type=Path),
    default=Path("src/assembly/tests/e2e/fixtures/minimal_cycle"),
    show_default=True,
    help="Minimal-cycle fixture directory or manifest path.",
)
@E2E_REPORTS_DIR_OPTION
@TIMEOUT_SEC_OPTION
@EXTRA_BUNDLES_OPTION
@click.option(
    "--skip-bootstrap",
    is_flag=True,
    help="Fail on blocked health preflight instead of attempting bootstrap.",
)
def e2e_command(
    profile_id: str,
    profiles_dir: Path,
    bundles_dir: Path,
    env_file: Path,
    fixture_dir: Path,
    reports_dir: Path,
    timeout_sec: float,
    extra_bundles: str,
    skip_bootstrap: bool,
) -> None:
    """Run the minimal-cycle e2e through orchestrator's public CLI.

    ``--extra-bundles`` opts into full-dev optional service bundles so the
    e2e's run record binds to the corresponding ``(full-dev,
    sorted(extra_bundles))`` matrix row (codex P2 follow-up on MinIO pilot).
    Without it, the default-profile row is targeted.
    """

    try:
        parsed_extra_bundles = _parse_extra_bundles(extra_bundles)
        record = execute_e2e(
            profile_id,
            profiles_root=profiles_dir,
            bundles_root=bundles_dir,
            registry_root=Path("."),
            fixture_dir=fixture_dir,
            reports_dir=reports_dir,
            env=_combined_env(env_file),
            timeout_sec=timeout_sec,
            bootstrap_if_needed=not skip_bootstrap,
            extra_bundles=parsed_extra_bundles,
        )
    except (ProfileError, RegistryError, OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc

    report_path = next(
        (
            artifact["path"]
            for artifact in record.artifacts
            if artifact.get("kind") == "e2e_report"
        ),
        "",
    )
    click.echo(
        f"{record.status}\t{record.run_id}\tfailing="
        f"{','.join(record.failing_modules)}\treport={report_path}"
    )
    raise click.exceptions.Exit(_record_exit_code(record))


@entrypoint.command("export-registry")
@OUT_OPTION
def export_registry_command(out: Path | None) -> None:
    """Validate and export registry artifacts into reports."""

    output_dir = out or Path("reports/registry")

    try:
        registry = load_all(Path("."))
        export = export_module_registry(registry, out_dir=output_dir, root=Path("."))
    except (RegistryError, OSError) as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(
        f"{export.out_dir}\tmodules={export.module_count}\tmatrix={export.matrix_count}"
    )


def execute_release_freeze(
    profile_id: str,
    *,
    registry_root: Path,
    profiles_root: Path,
    reports_root: Path,
    out_dir: Path,
    extra_bundles: Sequence[str] = (),
) -> VersionLock:
    """Freeze the verified compatibility matrix entry for a profile.

    ``extra_bundles`` disambiguates matrix rows that share a ``profile_id``
    (codex P2 follow-up on MinIO pilot). Default ``()`` targets the
    default-profile row.
    """

    return freeze_profile(
        profile_id,
        registry_root=registry_root,
        profiles_root=profiles_root,
        reports_root=reports_root,
        out_dir=out_dir,
        extra_bundles=extra_bundles,
    )


entrypoint.add_command(
    make_setup_command()
)

entrypoint.add_command(
    make_release_freeze_command(
        lambda profile_id, registry_root, profiles_root, reports_root, out_dir, extra_bundles: (
            execute_release_freeze(
                profile_id,
                registry_root=registry_root,
                profiles_root=profiles_root,
                reports_root=reports_root,
                out_dir=out_dir,
                extra_bundles=extra_bundles,
            )
        )
    )
)


def _load_profile_by_id(profile_id: str, profiles_dir: Path) -> EnvironmentProfile:
    for profile in list_profiles(profiles_dir):
        if profile.profile_id == profile_id:
            return profile

    raise ProfileNotFoundError(f"Profile id not found in {profiles_dir}: {profile_id}")


def _combined_env(env_file: Path) -> dict[str, str]:
    env = _read_env_file(env_file)
    env.update(os.environ)
    return env


def _compose_env_file(env_file: Path) -> Path | None:
    path = Path(env_file)
    if path.exists():
        return path

    return None


def _parse_extra_bundles(value: str | None) -> list[str]:
    if value is None or not value.strip():
        return []

    names = [item.strip() for item in value.split(",")]
    if any(not name for name in names):
        raise ValueError("--extra-bundles cannot contain empty bundle names")

    seen: set[str] = set()
    duplicates: list[str] = []
    for name in names:
        if name in seen and name not in duplicates:
            duplicates.append(name)
        seen.add(name)

    if duplicates:
        raise ValueError(
            "--extra-bundles contains duplicate bundle names: "
            + ", ".join(duplicates)
        )

    return names


def _read_env_file(env_file: Path) -> dict[str, str]:
    path = Path(env_file)
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("export "):
            stripped = stripped.removeprefix("export ").strip()

        key, separator, value = stripped.partition("=")
        if not separator:
            continue

        values[key.strip()] = _unquote_env_value(value.strip())

    return values


def _unquote_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]

    return value


def _dump_snapshot(snapshot: object, output_path: Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    snapshot.dump(path)


def _dump_health_results(results: list[HealthResult], output_path: Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            [result.model_dump(mode="json") for result in results],
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _health_exit_code(results: list[HealthResult]) -> int:
    if any(result.status == HealthStatus.blocked for result in results):
        return 2
    if any(result.status == HealthStatus.degraded for result in results):
        return 1
    return 0


def _smoke_exit_code(record: IntegrationRunRecord) -> int:
    if record.status == "failed":
        return 2
    if record.status == "partial":
        return 1
    return 0


def _contract_exit_code(report: CompatibilityReport) -> int:
    if report.run_record.status == "failed":
        return 2
    if report.run_record.status == "partial":
        return 1
    return 0


def _record_exit_code(record: IntegrationRunRecord) -> int:
    if record.status == "failed":
        return 2
    if record.status == "partial":
        return 1
    return 0


def _print_start_plan(plan: BootstrapPlan, env_file: Path | None) -> None:
    click.echo(f"Bootstrap plan for {plan.profile_id}")
    click.echo(f"startup_order: {' -> '.join(plan.startup_order)}")
    click.echo("compose_command: " + " ".join(_start_command(plan, env_file)))


def _print_start_result(result: BootstrapResult) -> None:
    click.echo(f"Bootstrap plan for {result.profile_id}")
    click.echo(f"startup_order: {' -> '.join(result.service_order)}")
    click.echo("compose_command: " + " ".join(result.command))
    if result.report_path is not None:
        click.echo(f"report: {result.report_path}")


def _print_stop_plan(plan: BootstrapPlan, env_file: Path | None) -> None:
    click.echo(f"Shutdown plan for {plan.profile_id}")
    click.echo(f"shutdown_order: {' -> '.join(plan.shutdown_order)}")
    click.echo("compose_command: " + " ".join(_stop_command(plan, env_file)))


def _start_command(plan: BootstrapPlan, env_file: Path | None) -> list[str]:
    return _compose_prefix(plan, env_file) + [
        "up",
        "-d",
        "--wait",
        *plan.startup_order,
    ]


def _stop_command(plan: BootstrapPlan, env_file: Path | None) -> list[str]:
    return _compose_prefix(plan, env_file) + [
        "stop",
        *plan.shutdown_order,
    ]


def _compose_prefix(plan: BootstrapPlan, env_file: Path | None) -> list[str]:
    command = ["docker", "compose"]
    if env_file is not None:
        command.extend(["--env-file", str(env_file)])
    command.extend(["-f", str(plan.compose_file)])
    return command


def _format_compose_error(exc: ComposeCommandError) -> str:
    details = str(exc)
    if exc.stderr.strip():
        details = f"{details}; stderr: {exc.stderr.strip()}"

    return details


def _format_stage_error(exc: BootstrapStageError) -> str:
    details = f"{exc.stage} failed: {exc}"
    if exc.result.report_path is not None:
        details = f"{details}; report: {exc.result.report_path}"

    return details


if __name__ == "__main__":
    entrypoint()
