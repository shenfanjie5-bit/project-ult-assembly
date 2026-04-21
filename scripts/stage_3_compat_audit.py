"""Stage 3 cross-project compat audit.

Per the master plan
(``~/.claude/plans/codex-ai-dev-workflow-findings-1-p0-dir-mellow-dongarra.md``,
section "阶段 3：跨项目 shared fixtures 消费验证 + 跨项目 compat check 验证")
this script invokes the **real** ``assembly.compat.checks.public_api_boundary
.PublicApiBoundaryCheck`` against the 11 target subsystem modules and reports
the result.

It is intentionally read-only:

- Loads ``module-registry.yaml`` + ``compatibility-matrix.yaml`` from the
  assembly repo root via the canonical ``assembly.registry.load_all`` (NOT a
  custom YAML parser; matches what production assembly bootstrap reads).
- Builds an in-memory promoted view of the 11 target modules' integration
  status (``not_started`` → ``partial``) so ``PublicApiBoundaryCheck`` exits
  the early-skip path at lines 41-54 of ``public_api_boundary.py`` and
  actually runs ``_check_entry`` (the isinstance / signature / duplicate-kind
  / unsupported-kind / load_public_entrypoint allowed-kinds sub-checks).
- Constructs a real ``CompatibilityCheckContext`` with all 5 required fields
  via the canonical pattern from
  ``assembly/tests/compat/test_checks.py::_context()`` (line 372-396).
- Picks the matrix entry by explicit ``profile_id`` lookup (NOT ``[0]``;
  matrix order is not stable — ``compatibility-matrix.yaml`` has
  ``lite-local`` + ``full-dev`` today, taking ``[0]`` would silently audit
  the wrong profile if YAML order changes).
- Persists ZERO state. ``module-registry.yaml`` is NOT mutated.
  ``promote()`` returns a ``model_copy`` per entry. The original Registry
  object is left untouched.

Constraint compliance (assembly/CLAUDE.md):

- §1 (only via public entrypoints): the script imports the 11 target
  modules' public entrypoints via ``importlib.import_module`` — same path as
  ``load_public_entrypoint``. No private-module imports.
- §6 (no claim of verified before MODULE_REGISTRY first version): this
  script does NOT promote any module to ``verified``. It runs the audit
  read-only and reports findings. Stage 4 (separate work) is what would
  upgrade ``module-registry.yaml`` integration_status to ``verified``.

Exit codes:

- ``0``: All 11 target modules report ``CompatibilityCheckStatus.success``.
  Ready to proceed to Stage 4.
- ``1``: At least one module FAILED. Details printed for each failed module.
- ``2``: Setup error (registry artifacts missing, matrix entry not found,
  Python imports broken, etc.). Audit could not complete.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from assembly.compat.checks.public_api_boundary import PublicApiBoundaryCheck
from assembly.compat.schema import (
    CompatibilityCheckContext,
    CompatibilityCheckStatus,
)
from assembly.profiles.resolver import ResolvedConfigSnapshot
from assembly.registry import (
    IntegrationStatus,
    Registry,
    load_all,
)

#: The 11 subsystem modules whose milestone-test-baseline is complete (per
#: master plan Current State ledger as of 2026-04-21). assembly itself
#: (#12) is excluded — it is the audit runner, and Stage 4 handles its own
#: ``partial`` → ``verified`` upgrade. ``feature-store`` and
#: ``stream-layer`` are excluded — they are intentionally frozen
#: (``not_started``, no ``public.py`` yet), per master plan §1.1 frozen
#: slots.
TARGET_MODULES: frozenset[str] = frozenset(
    {
        "contracts",
        "audit-eval",
        "reasoner-runtime",
        "main-core",
        "data-platform",
        "orchestrator",
        "entity-registry",
        "subsystem-sdk",
        "subsystem-announcement",
        "subsystem-news",
        "graph-engine",
    }
)


def _promote_target_modules_to_partial(registry: Registry) -> Registry:
    """Return a NEW Registry with target modules promoted to ``partial``.

    The original ``registry`` is not mutated. Each promoted entry is created
    via ``ModuleRegistryEntry.model_copy(update=...)`` — Pydantic's
    canonical immutable-update pattern. Non-target modules (assembly,
    feature-store, stream-layer, plus any other unknown future modules) are
    passed through unchanged.

    Why promote: ``PublicApiBoundaryCheck.run()`` (lines 41-54) early-exits
    on ``integration_status == not_started`` for non-focus modules, and
    reports ``not_started`` (not ``success``) for the focus subset
    (``main-core``, ``graph-engine``, ``audit-eval``). To exercise the
    isinstance / signature / duplicate-kind / unsupported-kind /
    load_public_entrypoint sub-checks against the actual implementations,
    every target module must be at ``partial`` or higher.
    """

    def promote(entry):  # type: ignore[no-untyped-def]
        if entry.module_id in TARGET_MODULES:
            return entry.model_copy(
                update={"integration_status": IntegrationStatus.partial}
            )
        return entry

    promoted_entries = [promote(entry) for entry in registry.modules]
    return Registry(
        root=registry.root,
        modules=promoted_entries,
        compatibility_matrix=registry.compatibility_matrix,
    )


def _pick_matrix_entry(registry: Registry, *, profile_id: str):  # type: ignore[no-untyped-def]
    """Return the compatibility matrix entry for ``profile_id``.

    Uses explicit ``profile_id`` lookup — NOT ``[0]``. The matrix has at
    least ``lite-local`` and ``full-dev`` today; YAML list order is not a
    stable contract. Taking ``[0]`` would silently audit the wrong profile
    if ``compatibility-matrix.yaml`` is reordered.
    """

    for entry in registry.compatibility_matrix:
        if entry.profile_id == profile_id:
            return entry
    available = [entry.profile_id for entry in registry.compatibility_matrix]
    raise SystemExit(
        f"compatibility_matrix has no entry with profile_id={profile_id!r}; "
        f"available: {available}"
    )


def _build_context(
    registry: Registry, *, profile_id: str
) -> CompatibilityCheckContext:
    """Build a CompatibilityCheckContext mirroring tests/compat/test_checks.py::_context().

    All 5 required fields are populated. ``ResolvedConfigSnapshot`` uses
    ``extra="forbid"`` so all 11 fields must match exactly.
    """

    matrix_entry = _pick_matrix_entry(registry, profile_id=profile_id)
    return CompatibilityCheckContext(
        profile_id=profile_id,
        snapshot=ResolvedConfigSnapshot(
            profile_id=profile_id,
            mode="lite",
            enabled_modules=[entry.module_id for entry in registry.modules],
            enabled_service_bundles=[],
            required_env={},
            optional_env={},
            storage_backends={},
            resource_expectation={},
            max_long_running_daemons=4,
            service_bundles=[],
            resolved_at=datetime.now(timezone.utc),
        ),
        registry=registry,
        resolved_entries=registry.modules,
        matrix_entry=matrix_entry,
        timeout_sec=30.0,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="stage_3_compat_audit",
        description=(
            "Stage 3 cross-project compat audit. Runs the real "
            "PublicApiBoundaryCheck against the 11 target subsystem modules "
            "and reports the result. Read-only — does NOT mutate "
            "module-registry.yaml."
        ),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help=(
            "Path to the assembly repo root containing module-registry.yaml + "
            "compatibility-matrix.yaml + MODULE_REGISTRY.md. Defaults to '.'."
        ),
    )
    parser.add_argument(
        "--profile-id",
        type=str,
        default="lite-local",
        help=(
            "Profile id to pick from compatibility-matrix.yaml. "
            "Defaults to 'lite-local'."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-module success messages (not just failures).",
    )
    args = parser.parse_args(argv)

    # Load registry artifacts via the canonical loader. Any registry-level
    # validation error (e.g. md/yaml drift) raises RegistryError, which we
    # surface as exit 2 (setup error).
    try:
        registry = load_all(args.repo_root)
    except Exception as exc:  # pragma: no cover - exec environment-dependent
        print(
            f"[stage_3_compat_audit] SETUP ERROR loading registry: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 2

    promoted_registry = _promote_target_modules_to_partial(registry)

    try:
        context = _build_context(promoted_registry, profile_id=args.profile_id)
    except SystemExit as exc:
        # _pick_matrix_entry raises SystemExit on missing profile.
        print(f"[stage_3_compat_audit] SETUP ERROR: {exc}", file=sys.stderr)
        return 2

    # Run the check. Each target module's public_entrypoints reference is
    # imported at this point — failures are caught by _check_entry and
    # surfaced as CompatibilityCheckStatus.failed (NOT script-level
    # ImportError).
    results = PublicApiBoundaryCheck().run(context)

    target_results = [r for r in results if r.module_id in TARGET_MODULES]
    failed_results = [
        r for r in target_results if r.status != CompatibilityCheckStatus.success
    ]

    if args.verbose or failed_results:
        for result in target_results:
            marker = (
                "OK   "
                if result.status == CompatibilityCheckStatus.success
                else "FAIL "
            )
            print(
                f"  {marker}{result.module_id:<30} "
                f"status={result.status.value} - {result.message}"
            )
            if (
                result.status != CompatibilityCheckStatus.success
                and result.details
            ):
                for key, value in sorted(result.details.items()):
                    print(f"        {key}: {value}")

    audited_target_ids = {r.module_id for r in target_results}
    missing_targets = TARGET_MODULES - audited_target_ids
    if missing_targets:
        # Targets that early-exited the check (no result row at all): these
        # are non-focus modules still at integration_status==not_started in
        # the underlying registry that survived our promote() somehow, OR
        # modules listed in TARGET_MODULES but absent from the registry.
        # Either way it's a setup mismatch.
        print(
            "[stage_3_compat_audit] SETUP MISMATCH: target modules with no "
            f"PublicApiBoundaryCheck result row: {sorted(missing_targets)}",
            file=sys.stderr,
        )
        return 2

    if failed_results:
        print(
            f"\n[stage_3_compat_audit] FAIL: "
            f"{len(failed_results)}/{len(TARGET_MODULES)} target modules "
            "did not pass PublicApiBoundaryCheck. See per-module details "
            "above. Stage 4 BLOCKED until these are resolved.",
            file=sys.stderr,
        )
        return 1

    print(
        f"\n[stage_3_compat_audit] OK: "
        f"{len(TARGET_MODULES)}/{len(TARGET_MODULES)} target modules pass "
        f"PublicApiBoundaryCheck (profile={args.profile_id!r}). "
        "Ready for Stage 4."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
