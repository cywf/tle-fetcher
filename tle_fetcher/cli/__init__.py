"""Command-line entrypoints for the :mod:`tle_fetcher` toolkit."""

from __future__ import annotations

from typing import Optional, Sequence

from . import legacy

__all__ = ["bootstrap_cli", "legacy", "main"]


def bootstrap_cli(argv: Optional[Sequence[str]] = None) -> int:
    """Execute the legacy CLI implementation with optional ``argv`` injection."""
    parsed = legacy.parse_args(list(argv) if argv is not None else None)
    return legacy.run_cli(parsed)


def main(argv: Optional[Sequence[str]] = None) -> None:
    """``python -m tle_fetcher.cli`` compat shim."""
    raise SystemExit(bootstrap_cli(argv))
