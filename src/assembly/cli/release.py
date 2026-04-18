"""Click command helpers for release-freeze workflows."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import click

from assembly.registry.freezer import ReleaseFreezeError, VersionLock


def make_release_freeze_command(
    executor: Callable[
        [str, Path, Path, Path, Path],
        VersionLock,
    ],
) -> click.Command:
    """Build the release-freeze Click command with an injectable executor."""

    @click.command("release-freeze")
    @click.option(
        "--profile",
        "profile_id",
        required=True,
        help="Profile id to freeze.",
    )
    @click.option(
        "--out",
        "out_dir",
        type=click.Path(path_type=Path, file_okay=False),
        default=Path("version-lock"),
        show_default=True,
        help="Directory where the version lock YAML is written.",
    )
    @click.option(
        "--registry-root",
        type=click.Path(path_type=Path, file_okay=False),
        default=Path("."),
        show_default=True,
        help="Project root containing registry artifacts.",
    )
    @click.option(
        "--profiles-dir",
        "profiles_root",
        type=click.Path(path_type=Path, file_okay=False),
        default=Path("profiles"),
        show_default=True,
        help="Directory containing profile manifests.",
    )
    @click.option(
        "--reports-root",
        type=click.Path(path_type=Path, file_okay=False),
        default=Path("reports"),
        show_default=True,
        help="Root directory containing contract, smoke, and e2e reports.",
    )
    def release_freeze_command(
        profile_id: str,
        out_dir: Path,
        registry_root: Path,
        profiles_root: Path,
        reports_root: Path,
    ) -> None:
        """Freeze a verified compatibility matrix entry into a lockfile."""

        try:
            lock = executor(
                profile_id,
                registry_root,
                profiles_root,
                reports_root,
                out_dir,
            )
        except ReleaseFreezeError as exc:
            raise click.ClickException(str(exc)) from exc
        except OSError as exc:
            raise click.ClickException(str(exc)) from exc

        click.echo(
            f"lock={lock.lock_file}\tprofile={lock.profile_id}\t"
            f"modules={len(lock.modules)}"
        )

    return release_freeze_command
