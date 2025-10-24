"""Command line interface for fetching TLEs."""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path
from typing import Iterable, List

from fetch.cache import FileRepository, InMemoryCache
from fetch.service import FetchService
from fetch.sources import build_clients, parse_source_order


DEFAULT_SOURCE_ORDER = ["celestrak", "ivan", "spacetrack", "n2yo"]
DEFAULT_CACHE_TTL = 2 * 60 * 60


def _load_ids(path: Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(path)
    ids: List[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            ids.extend(part.strip() for part in line.split() if part.strip())
    return ids


def _normalize_ids(values: Iterable[str]) -> List[str]:
    normalized: List[str] = []
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if part:
                normalized.append(part)
    return normalized


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch TLEs with cache/DB/network fallback")
    parser.add_argument("--ids", nargs="*", default=[], help="NORAD IDs to fetch (comma or space separated)")
    parser.add_argument("--all", action="store_true", help="Fetch all IDs listed in ids.txt")
    parser.add_argument("--ids-file", type=Path, default=Path("ids.txt"), help="Override ids.txt path")
    parser.add_argument("--cache-ttl", type=int, default=DEFAULT_CACHE_TTL, help="Cache TTL in seconds")
    parser.add_argument("--source-order", default=",".join(DEFAULT_SOURCE_ORDER), help="Comma separated source priority")
    parser.add_argument("--verify", type=float, default=0.0, help="Percentage of lookups to verify via network (0-100 or 0-1)")
    parser.add_argument("--offline", action="store_true", help="Do not perform network calls; use cached data only")
    parser.add_argument("--state-dir", type=Path, default=None, help="Override state directory (cache + repository)")
    parser.add_argument("--quiet", action="store_true", help="Suppress informational output")
    return parser


def _resolve_state_dir(ns: argparse.Namespace) -> Path:
    env_dir = os.getenv("TLE_FETCHER_STATE_DIR")
    if ns.state_dir:
        return ns.state_dir
    if env_dir:
        return Path(env_dir)
    return Path.home() / ".cache" / "tle-fetcher"


def _determine_offline(ns: argparse.Namespace) -> bool:
    if ns.offline:
        return True
    return os.getenv("TLE_FETCHER_OFFLINE", "").lower() in {"1", "true", "yes"}


def _format_warning(msg: str) -> str:
    return f"warning: {msg}"


def run(args: argparse.Namespace) -> int:
    ids: List[str] = []
    if args.all:
        try:
            ids.extend(_load_ids(args.ids_file))
        except FileNotFoundError:
            print(f"ids file not found: {args.ids_file}", file=sys.stderr)
            return 2
    ids.extend(_normalize_ids(args.ids))

    if not ids:
        print("no NORAD IDs supplied; use --ids or --all", file=sys.stderr)
        return 2

    state_dir = _resolve_state_dir(args)
    repo_dir = state_dir / "db"
    cache = InMemoryCache()
    repository = FileRepository(repo_dir)

    source_order = parse_source_order(args.source_order, default=DEFAULT_SOURCE_ORDER)
    clients = build_clients(source_order)
    service = FetchService(cache=cache, repository=repository, sources=clients)

    ttl = dt.timedelta(seconds=max(args.cache_ttl, 0))
    offline = _determine_offline(args)
    verify_percent = args.verify

    exit_code = 0
    for norad_id in ids:
        try:
            result = service.fetch_one(norad_id, cache_ttl=ttl, verify_percent=verify_percent, offline=offline)
        except Exception as exc:
            print(f"error: {norad_id}: {exc}", file=sys.stderr)
            exit_code = 1
            continue

        if result.warnings and not args.quiet:
            for msg in result.warnings:
                print(_format_warning(f"{norad_id}: {msg}"), file=sys.stderr)
        if result.stale and not args.quiet:
            print(_format_warning(f"{norad_id}: result is older than TTL"), file=sys.stderr)

        sys.stdout.write(result.tle.as_text(include_name=True))
        sys.stdout.flush()
    return exit_code


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
