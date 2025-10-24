"""Top-level package for the ``tle_fetcher`` offline-first tooling."""

from __future__ import annotations

from .cli import bootstrap_cli
from . import cli

__all__ = ["bootstrap_cli", "cli", "main"]


def main(argv=None) -> int:
    """Entry point for ``python -m tle_fetcher`` invocations."""
    return bootstrap_cli(argv)
