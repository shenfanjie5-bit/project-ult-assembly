"""Shared helpers for public entrypoint references."""

from __future__ import annotations

import importlib
from collections import Counter
from typing import Any

from assembly.contracts.primitives import EntrypointKind

PUBLIC_ENTRYPOINT_KINDS: frozenset[EntrypointKind] = frozenset(
    {
        "health_probe",
        "smoke_hook",
        "init_hook",
        "version_declaration",
        "cli",
    }
)
PUBLIC_COMPAT_IMPORT_KINDS: frozenset[EntrypointKind] = frozenset(
    {
        "version_declaration",
        "smoke_hook",
        "health_probe",
        "cli",
    }
)


def load_reference(reference: str) -> Any:
    """Import a public entrypoint by ``module.path:symbol`` reference."""

    module_name, _, symbol_name = reference.partition(":")
    if not module_name or not symbol_name:
        raise ValueError(f"Invalid public entrypoint reference: {reference}")

    module = importlib.import_module(module_name)
    return getattr(module, symbol_name)


def load_public_entrypoint(
    public_entrypoint: Any,
    *,
    allowed_kinds: frozenset[str] = PUBLIC_COMPAT_IMPORT_KINDS,
) -> Any:
    """Import a registered public entrypoint after checking its kind."""

    if public_entrypoint.kind not in allowed_kinds:
        raise ValueError(
            f"Unsupported compatibility entrypoint kind: {public_entrypoint.kind}"
        )

    return load_reference(public_entrypoint.reference)


def duplicate_entrypoint_kinds(public_entrypoints: list[Any]) -> list[str]:
    """Return duplicate public entrypoint kind values in deterministic order."""

    counts = Counter(str(entrypoint.kind) for entrypoint in public_entrypoints)
    return sorted(kind for kind, count in counts.items() if count > 1)


__all__ = [
    "PUBLIC_COMPAT_IMPORT_KINDS",
    "PUBLIC_ENTRYPOINT_KINDS",
    "duplicate_entrypoint_kinds",
    "load_public_entrypoint",
    "load_reference",
]
