"""Command line interface for the TLE fetcher package."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Sequence

from .. import (
    CACHE_TTL_SECS,
    DEFAULT_BACKOFF,
    DEFAULT_RETRIES,
    DEFAULT_TIMEOUT,
    TLE,
    configure_cache_dir,
    fetch_with_fallback,
    format_output_path,
    save_tle,
    tle_epoch,
)
from . import common, report

LOGGER = logging.getLogger("tle_fetcher.cli")
DEFAULT_SOURCES = ["spacetrack", "celestrak", "ivan", "n2yo"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reliable TLE fetcher with multi-source fallback.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    common.add_shared_arguments(parser)
    parser.add_argument("ids", nargs="*", help="NORAD catalog IDs (one or more).")
    parser.add_argument(
        "--ids-file",
        "-f",
        help="Path to file with NORAD IDs (one per line, '#' comments allowed).",
    )
    parser.add_argument(
        "--source-order",
        default=",".join(DEFAULT_SOURCES),
        help="Comma-separated source priority.",
    )
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="HTTP timeout (seconds).")
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES, help="HTTP retries per source.")
    parser.add_argument("--backoff", type=float, default=DEFAULT_BACKOFF, help="Base backoff (seconds).")
    parser.add_argument("--cache-ttl", type=int, default=CACHE_TTL_SECS, help="Cache TTL in seconds.")
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
        help="Output path or pattern. Use '-' for stdout. Pattern supports {id}, {name}, {epoch:%%Y%%m%%d%%H%%M%%S}.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON to stdout.")
    parser.add_argument("--no-name", action="store_true", help="Save as 2-line TLE (omit name line).")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress extra logs.")
    report.register_arguments(parser)
    return parser


def _resolve_ids(ns: argparse.Namespace) -> List[str] | None:
    try:
        loaded = common.load_ids_from_file(ns.ids_file)
    except FileNotFoundError as exc:
        LOGGER.error(str(exc))
        return None
    ids = common.merge_ids(ns.ids, loaded)
    if ids:
        return ids
    return _interactive_prompt()


def _interactive_prompt() -> List[str]:
    print("TLE Fetcher Utility (robust)")
    print("Enter a NORAD catalog ID (or 'q' to quit):")
    while True:
        try:
            user_input = input("> ").strip()
        except EOFError:
            return []
        if user_input.lower() in {"q", "quit", "exit"}:
            return []
        if not user_input.isdigit():
            print("Please enter a numeric NORAD catalog ID.")
            continue
        return [user_input]


def _select_sources(raw: str) -> List[str]:
    values = [item.strip().lower() for item in (raw or "").split(",") if item.strip()]
    return values or list(DEFAULT_SOURCES)


def _emit_tle(ns: argparse.Namespace, tle: TLE) -> None:
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
            LOGGER.info("[%s] %s (NORAD %s) epoch %s", tle.source, tle.name or "", tle.norad_id, epoch)
        print(tle.as_text(three_line=not ns.no_name), end="")
    destination = format_output_path(ns.output, tle)
    if destination != "-":
        save_tle(tle, destination, three_line=not ns.no_name)
        if not ns.quiet:
            LOGGER.info("Saved -> %s", destination)


def _run_fetch_mode(ns: argparse.Namespace) -> int:
    if ns.mode != "fetch":
        raise ValueError("_run_fetch_mode called with non-fetch mode")
    ids = _resolve_ids(ns)
    if ids is None:
        return 2
    if not ids:
        return 0
    sources = _select_sources(ns.source_order)
    exit_code = 0
    for sat_id in ids:
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
            _emit_tle(ns, tle)
        except Exception as exc:  # pragma: no cover - network errors already unit tested elsewhere
            exit_code = 2
            LOGGER.error("ERROR[%s]: %s", sat_id, exc)
    return exit_code


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    ns = parser.parse_args(argv)
    common.configure_logging(ns.log_level)
    db_path = common.resolve_db_path(ns.db_path)
    configure_cache_dir(str(db_path))
    if ns.mode == "report":
        return report.run_report(ns, db_path)
    return _run_fetch_mode(ns)


def entrypoint() -> None:
    sys.exit(main())
