from __future__ import annotations

"""CLI sub-command that drives the discovery ingest pipeline."""

import argparse
import datetime as dt
import sys
from pathlib import Path
from typing import List, Optional

from ingest.catalog_sources import SOURCES
from ingest.pipeline import DiscoveryPipeline


def _parse_since(value: str) -> dt.datetime:
    value = value.strip()
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(
        "--since expects ISO 8601 or YYYY-MM-DD"
    )


def run(ns: argparse.Namespace) -> int:
    since_dt = _parse_since(ns.since) if ns.since else None
    db_path = Path(ns.database)
    pipeline = DiscoveryPipeline(db_path=db_path)
    try:
        result = pipeline.run(
            ns.source,
            since=since_dt,
            offline=ns.offline,
        )
    finally:
        pipeline.close()

    cursor_text = result.cursor.isoformat() if result.cursor else "unknown"
    since_text = (
        result.effective_since.isoformat() if result.effective_since else "none"
    )
    cache_text = "yes" if result.used_cache else "no"
    print(
        f"Run {result.run_id} source={result.source} new={len(result.entries)} "
        f"cache={cache_text} cursor={cursor_text} since={since_text}"
    )
    for entry in result.entries:
        label = entry.name or ""
        print(
            f"  {entry.norad_id:>6} {label:<24} {entry.epoch.isoformat()}"
        )
    return 0


def configure_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        "discover",
        help="Fetch catalogue snapshots and store them locally for offline reuse.",
    )
    parser.add_argument(
        "--source",
        choices=sorted(SOURCES.keys()),
        default="celestrak",
        help="Catalogue source to query.",
    )
    parser.add_argument(
        "--since",
        help="Only consider entries newer than this timestamp (ISO 8601 or YYYY-MM-DD).",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Do not perform network IO; reuse cached catalogue payloads.",
    )
    parser.add_argument(
        "--database",
        default=str(Path("data") / "ingest.sqlite3"),
        help="Path to the ingest SQLite database.",
    )
    parser.set_defaults(handler=run)
    return parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tle-fetcher discover")
    configure_parser(parser.add_subparsers(dest="command"))
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="tle-fetcher discover")
    parser.add_argument(
        "--source",
        choices=sorted(SOURCES.keys()),
        default="celestrak",
    )
    parser.add_argument("--since")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument(
        "--database", default=str(Path("data") / "ingest.sqlite3")
    )
    ns = parser.parse_args(argv)
    return run(ns)


if __name__ == "__main__":
    sys.exit(main())
