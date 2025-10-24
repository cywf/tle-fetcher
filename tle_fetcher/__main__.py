from __future__ import annotations

"""CLI entry point exposed via ``python -m tle_fetcher``."""

import argparse
import sys
from typing import List, Optional

from .cli import discover, fetch


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tle-fetcher", description="TLE utility toolkit")
    subparsers = parser.add_subparsers(dest="command")
    fetch.configure_parser(subparsers)
    discover.configure_parser(subparsers)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    ns = parser.parse_args(argv)
    if not hasattr(ns, "handler"):
        parser.print_help()
        return 1
    return ns.handler(ns)


if __name__ == "__main__":
    sys.exit(main())
