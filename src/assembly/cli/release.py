"""Click command helpers for release-freeze workflows."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import click

from assembly.registry.freezer import ReleaseFreezeError, VersionLock


def make_release_freeze_command(
    executor: Callable[
        [str, Path, Path, Path, Path, Sequence[str]],
        VersionLock,
    ],
) -> click.Command:
    """Build the release-freeze Click command with an injectable executor.

    The ``executor`` signature takes ``(profile_id, registry_root,
    profiles_root, reports_root, out_dir, extra_bundles)`` — the last
    argument was added in the codex P2 follow-up on the matrix-identity
    fix so ``--extra-bundles`` can target the verified
    ``(full-dev, [minio])`` row. For default profiles, pass ``()``.
    """

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
    @click.option(
        "--extra-bundles",
        default="",
        help=(
            "Comma-separated opt-in bundle names; disambiguates matrix rows "
            "that share a profile_id (e.g. ``full-dev`` default vs "
            "``full-dev + minio``). Default: no extras."
        ),
    )
    def release_freeze_command(
        profile_id: str,
        out_dir: Path,
        registry_root: Path,
        profiles_root: Path,
        reports_root: Path,
        extra_bundles: str,
    ) -> None:
        """Freeze a verified compatibility matrix entry into a lockfile."""

        try:
            parsed_extra_bundles = _parse_extra_bundles(extra_bundles)
            lock = executor(
                profile_id,
                registry_root,
                profiles_root,
                reports_root,
                out_dir,
                parsed_extra_bundles,
            )
        except ReleaseFreezeError as exc:
            raise click.ClickException(str(exc)) from exc
        except (OSError, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc

        click.echo(
            f"lock={lock.lock_file}\tprofile={lock.profile_id}\t"
            f"modules={len(lock.modules)}"
        )

    return release_freeze_command


def _parse_extra_bundles(value: str | None) -> tuple[str, ...]:
    """Parse the comma-separated ``--extra-bundles`` CLI value.

    Mirrors ``assembly.cli.main._parse_extra_bundles`` (same format +
    validation); kept local to avoid a main→release→main import cycle.
    Returns a tuple so downstream Python APIs can use it as an immutable
    Sequence kwarg default.
    """
    if value is None or not value.strip():
        return ()

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

    return tuple(names)
