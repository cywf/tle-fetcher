#!/usr/bin/env python3
"""Backward compatible entrypoint for :mod:`tle_fetcher.cli`."""

from __future__ import annotations

from tle_fetcher.cli import entrypoint as _entrypoint, main as cli_main

__all__ = ["cli_main", "main"]


def main() -> None:
    """Execute the CLI using the new architecture."""

    _entrypoint()


if __name__ == "__main__":
    main()
