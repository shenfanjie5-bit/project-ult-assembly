"""Click-based command line interface for assembly bootstrap workflows."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import click

from assembly.bootstrap import BootstrapStageError, bootstrap as execute_bootstrap
from assembly.bootstrap.plan import BootstrapPlan, BootstrapPlanError, build_plan
from assembly.bootstrap.runner import BootstrapResult, ComposeCommandError, Runner
from assembly.profiles.errors import ProfileError, ProfileNotFoundError
from assembly.profiles.loader import list_profiles
from assembly.profiles.resolver import render_profile
from assembly.profiles.schema import EnvironmentProfile
from assembly.registry import RegistryError, assert_md_yaml_consistent


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
DRY_RUN_OPTION = click.option(
    "--dry-run",
    is_flag=True,
    help="Print the planned docker compose command without executing it.",
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
@OUT_OPTION
def render_profile_command(
    profile_id: str,
    profiles_dir: Path,
    bundles_dir: Path,
    env_file: Path,
    out: Path | None,
) -> None:
    """Render a resolved, redacted profile snapshot."""

    try:
        snapshot = render_profile(
            profile_id,
            profiles_root=profiles_dir,
            bundles_root=bundles_dir,
            env=_combined_env(env_file),
        )
        output_path = out or Path("reports/bootstrap") / (
            f"{profile_id}-resolved-config.json"
        )
        _dump_snapshot(snapshot, output_path)
    except ProfileError as exc:
        raise click.ClickException(str(exc)) from exc
    except OSError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(str(output_path))


@entrypoint.command("bootstrap")
@PROFILE_OPTION
@PROFILES_DIR_OPTION
@BUNDLES_DIR_OPTION
@ENV_FILE_OPTION
@OUT_OPTION
@DRY_RUN_OPTION
def bootstrap_command(
    profile_id: str,
    profiles_dir: Path,
    bundles_dir: Path,
    env_file: Path,
    out: Path | None,
    dry_run: bool,
) -> None:
    """Resolve a profile and start its compose-managed services."""

    try:
        compose_env_file = _compose_env_file(env_file)
        result = execute_bootstrap(
            profile_id,
            profiles_root=profiles_dir,
            bundle_root=bundles_dir,
            env=_combined_env(env_file),
            env_file=compose_env_file,
            runner=Runner(env_file=compose_env_file),
            dry_run=dry_run,
            report_path=out,
        )
        if dry_run:
            _print_start_result(result)
            return
    except (BootstrapPlanError, ProfileError) as exc:
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
@DRY_RUN_OPTION
def shutdown_command(
    profile_id: str,
    profiles_dir: Path,
    bundles_dir: Path,
    env_file: Path,
    dry_run: bool,
) -> None:
    """Stop compose-managed services in the bootstrap shutdown order."""

    try:
        profile = _load_profile_by_id(profile_id, profiles_dir)
        plan = build_plan(profile, bundle_root=bundles_dir)
        compose_env_file = _compose_env_file(env_file)
        if dry_run:
            _print_stop_plan(plan, compose_env_file)
            return

        result = Runner(env_file=compose_env_file).stop(plan)
    except (BootstrapPlanError, ProfileError) as exc:
        raise click.ClickException(str(exc)) from exc
    except ComposeCommandError as exc:
        raise click.ClickException(_format_compose_error(exc)) from exc

    click.echo(f"stopped {profile_id}: {' '.join(result.service_order)}")


@entrypoint.command("export-registry")
@OUT_OPTION
def export_registry_command(out: Path | None) -> None:
    """Validate and copy registry artifacts into reports."""

    output_dir = out or Path("reports/registry")
    registry_md = Path("MODULE_REGISTRY.md")
    registry_yaml = Path("module-registry.yaml")
    matrix_yaml = Path("compatibility-matrix.yaml")

    try:
        assert_md_yaml_consistent(registry_md, registry_yaml)
        output_dir.mkdir(parents=True, exist_ok=True)
        for artifact in (registry_md, registry_yaml, matrix_yaml):
            shutil.copy2(artifact, output_dir / artifact.name)
    except (RegistryError, OSError) as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(str(output_dir))


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
