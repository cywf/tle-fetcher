from __future__ import annotations

"""Command line interface for fetching individual TLE records.

This is a light refactor of the historical ``tle_fetcher.py`` script. The
core parsing and HTTP logic now lives in :mod:`tle_fetcher.core`; this
module is only responsible for user interaction and IO plumbing.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from ..core import (
    CACHE_TTL_SECS,
    DEFAULT_BACKOFF,
    DEFAULT_RETRIES,
    DEFAULT_TIMEOUT,
    SOURCE_FUNCS,
    TLE,
    fetch_with_fallback,
    tle_epoch,
)


def _merge_ids_from_file(ns: argparse.Namespace) -> None:
    if not ns.ids_file:
        return
    path = Path(ns.ids_file)
    if not path.exists():
        print(f"IDs file not found: {path}", file=sys.stderr)
        sys.exit(2)
    loaded: List[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            loaded.append(line)
    ns.ids = list(dict.fromkeys([*ns.ids, *loaded]))


def _format_output_path(pattern: str, tle: TLE) -> str:
    if pattern == "-":
        return "-"
    try:
        epoch = tle_epoch(tle.line1)
        name = (tle.name or "").replace("/", "-").replace(" ", "_")
        return pattern.format(id=tle.norad_id, name=name, epoch=epoch)
    except Exception:
        return pattern


def _save_tle(tle: TLE, path: str, three_line: bool) -> None:
    txt = tle.as_text(three_line=three_line)
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(txt, encoding="utf-8")


def run(ns: argparse.Namespace) -> int:
    _merge_ids_from_file(ns)

    if not ns.ids:
        print("TLE Fetcher Utility (robust)")
        print("Enter a NORAD catalog ID (or 'q' to quit):")
        while True:
            user_input = input("> ").strip()
            if user_input.lower() in {"q", "quit", "exit"}:
                return 0
            if not user_input.isdigit():
                print("Please enter a numeric NORAD catalog ID.")
                continue
            ns.ids = [user_input]
            break

    sources = [s.strip().lower() for s in ns.source_order.split(",") if s.strip()]
    if not sources:
        sources = list(SOURCE_FUNCS.keys())

    exit_code = 0
    for sat_id in ns.ids:
        try:
            tle = fetch_with_fallback(
                sat_id,
                sources=sources,
                timeout=ns.timeout,
                retries=ns.retries,
                backoff=ns.backoff,
                cache_ttl=ns.cache_ttl,
                verify_with=ns.verify,
            )
            if ns.json:
                payload = {
                    "id": tle.norad_id,
                    "name": tle.name,
                    "line1": tle.line1,
                    "line2": tle.line2,
                    "source": tle.source,
                    "epoch": tle_epoch(tle.line1).isoformat(),
                }
                print(json.dumps(payload, ensure_ascii=False))
            else:
                if not ns.quiet:
                    epoch = tle_epoch(tle.line1).strftime("%Y-%m-%d %H:%M:%S UTC")
                    label = tle.name or ""
                    print(f"\n[{tle.source}] {label} (NORAD {tle.norad_id}) epoch {epoch}")
                print(tle.as_text(three_line=not ns.no_name), end="")
            out_path = _format_output_path(ns.output, tle)
            if out_path != "-":
                _save_tle(tle, out_path, three_line=not ns.no_name)
                if not ns.quiet:
                    print(f"Saved -> {out_path}")
        except Exception as exc:
            exit_code = 2
            print(f"ERROR[{sat_id}]: {exc}", file=sys.stderr)
    return exit_code


def configure_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        "fetch",
        help="Fetch one or more NORAD IDs using the legacy retrieval flow.",
    )
    parser.add_argument("ids", nargs="*", help="NORAD catalog IDs (one or more).")
    parser.add_argument(
        "--source-order",
        default="spacetrack,celestrak,ivan,n2yo",
        help="Comma-separated source priority.",
    )
    parser.add_argument("--ids-file", "-f", help="Path to a file with NORAD IDs.")
    parser.add_argument(
        "--timeout", type=float, default=DEFAULT_TIMEOUT, help="HTTP timeout (seconds)."
    )
    parser.add_argument(
        "--retries", type=int, default=DEFAULT_RETRIES, help="HTTP retries per source."
    )
    parser.add_argument(
        "--backoff", type=float, default=DEFAULT_BACKOFF, help="Base backoff (seconds)."
    )
    parser.add_argument(
        "--cache-ttl",
        type=int,
        default=CACHE_TTL_SECS,
        help="Cache TTL in seconds for individual TLE lookups.",
    )
    parser.add_argument(
        "--verify",
        type=int,
        default=0,
        help="Fetch from up to N additional sources to cross-verify (0=off).",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="-",
        help="Output path or pattern. Use '-' for stdout. Pattern supports {id}, {name}, {epoch:%Y%m%d%H%M%S}.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON to stdout.")
    parser.add_argument("--no-name", action="store_true", help="Save as 2-line TLE (omit name line).")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress extra logs.")
    parser.set_defaults(handler=run)
    return parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reliable TLE fetcher with multi-source fallback.")
    subparsers = parser.add_subparsers(dest="command")
    configure_parser(subparsers)
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
