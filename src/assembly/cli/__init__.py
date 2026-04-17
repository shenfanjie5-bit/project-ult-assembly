"""Command line entry points for assembly."""

from __future__ import annotations


def __getattr__(name: str) -> object:
    if name == "entrypoint":
        from assembly.cli.main import entrypoint

        return entrypoint

    raise AttributeError(name)

__all__ = ["entrypoint"]
