"""Legacy entrypoint for the tle_fetcher CLI."""

from __future__ import annotations

import os

# Expose package-style imports when this legacy module is imported.
__path__ = [os.path.join(os.path.dirname(__file__), "tle_fetcher")]


def main() -> None:
    from tle_fetcher.cli import main as _main

    _main()


if __name__ == "__main__":
    main()
