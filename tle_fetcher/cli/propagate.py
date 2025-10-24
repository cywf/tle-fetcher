"""Command line entry point for propagating cached TLEs."""
from __future__ import annotations

import argparse
import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional

from propagate.frames import Frame
from propagate.service import PropagationBackend, propagate
from tle_fetcher import (
    CACHE_TTL_SECS,
    TLE,
    fetch_with_fallback,
    parse_tle_text,
    read_cache,
)
from tle_fetcher import fetcher

DEFAULT_SOURCE_ORDER = "spacetrack,celestrak,ivan,n2yo"


def parse_datetime(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:  # pragma: no cover
        raise argparse.ArgumentTypeError(f"Invalid datetime '{value}'") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_step(value: str) -> timedelta:
    v = value.strip().lower()
    if v.startswith("pt"):
        amount = v[2:]
        if amount.endswith("h"):
            return timedelta(hours=float(amount[:-1]))
        if amount.endswith("m"):
            return timedelta(minutes=float(amount[:-1]))
        if amount.endswith("s"):
            return timedelta(seconds=float(amount[:-1]))
        return timedelta(seconds=float(amount))
    if v.endswith("h"):
        return timedelta(hours=float(v[:-1]))
    if v.endswith("m"):
        return timedelta(minutes=float(v[:-1]))
    if v.endswith("s"):
        return timedelta(seconds=float(v[:-1]))
    return timedelta(seconds=float(v))


def load_tle(
    norad_id: str,
    *,
    tle_path: Optional[Path],
    offline: bool,
    cache_ttl: int,
    source_order: Iterable[str],
    timeout: float,
    retries: int,
    backoff: float,
) -> TLE:
    if tle_path:
        text = tle_path.read_text(encoding="utf-8")
        return parse_tle_text(norad_id, text, source=f"file:{tle_path}")

    local_candidates = [
        Path("tles") / f"{norad_id}.tle",
        Path("data") / f"{norad_id}.tle",
    ]
    for candidate in local_candidates:
        if candidate.exists():
            text = candidate.read_text(encoding="utf-8")
            return parse_tle_text(norad_id, text, source=f"file:{candidate}")

    cache_max = cache_ttl if not offline else int(10 * 365 * 24 * 3600)
    cached = read_cache(norad_id, cache_max)
    if cached:
        return cached

    if offline:
        raise RuntimeError("Offline mode requested but TLE not found in cache or local paths")

    sources = [src.strip() for src in source_order if src.strip()]
    if not sources:
        sources = DEFAULT_SOURCE_ORDER.split(",")

    return fetch_with_fallback(
        norad_id,
        sources,
        timeout=timeout,
        retries=retries,
        backoff=backoff,
        cache_ttl=cache_ttl,
    )


def ensure_positions_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            norad_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            frame TEXT NOT NULL,
            x REAL NOT NULL,
            y REAL NOT NULL,
            z REAL NOT NULL,
            vx REAL NOT NULL,
            vy REAL NOT NULL,
            vz REAL NOT NULL,
            backend TEXT NOT NULL,
            run_id TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_positions_norad ON positions(norad_id, timestamp)")


def write_db(conn: sqlite3.Connection, run_id: str, result) -> int:
    ensure_positions_table(conn)
    rows = [
        (
            result.tle.norad_id,
            sample.timestamp.isoformat(),
            result.frame.value,
            *sample.state.position_km,
            *sample.state.velocity_km_s,
            result.backend.value,
            run_id,
        )
        for sample in result.samples
    ]
    conn.executemany(
        """
        INSERT INTO positions (
            norad_id, timestamp, frame, x, y, z, vx, vy, vz, backend, run_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def record_metadata(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True))
        fh.write("\n")


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Propagate NORAD TLEs using SGP4")
    parser.add_argument("norad_id", help="NORAD catalog ID")
    parser.add_argument("--start", required=True, help="Start time (ISO-8601, default UTC)")
    parser.add_argument("--end", required=True, help="End time (ISO-8601, default UTC)")
    parser.add_argument("--step", required=True, help="Step duration (seconds, e.g. 60 or PT5M)")
    parser.add_argument("--frame", default="eci", choices=[f.value for f in Frame], help="Output frame")
    parser.add_argument("--backend", default="python", choices=[b.value for b in PropagationBackend], help="Propagation backend")
    parser.add_argument("--tle-path", type=Path, help="Explicit TLE file path")
    parser.add_argument("--offline", action="store_true", help="Do not perform network requests; rely on cached TLEs only")
    parser.add_argument("--cache-ttl", type=int, default=CACHE_TTL_SECS, help="Cache TTL in seconds for online fetches")
    parser.add_argument("--source-order", default=DEFAULT_SOURCE_ORDER, help="Comma separated source priority for online mode")
    parser.add_argument("--timeout", type=float, default=fetcher.DEFAULT_TIMEOUT, help="Network timeout")
    parser.add_argument("--retries", type=int, default=fetcher.DEFAULT_RETRIES, help="Network retries")
    parser.add_argument("--backoff", type=float, default=fetcher.DEFAULT_BACKOFF, help="Backoff base seconds")
    parser.add_argument("--db", type=Path, help="SQLite database path for persisting positions")
    parser.add_argument("--write-db", action="store_true", help="Insert propagated positions into the database")
    parser.add_argument("--metadata", type=Path, default=Path("logs/propagate_runs.jsonl"), help="Path to append metadata JSON records")
    parser.add_argument("--no-metadata", action="store_true", help="Skip writing metadata records")
    parser.add_argument("--json", action="store_true", help="Emit result as JSON")
    parser.add_argument("--quiet", action="store_true", help="Reduce stdout chatter")
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)

    start = parse_datetime(args.start)
    end = parse_datetime(args.end)
    step = parse_step(args.step)
    frame = Frame.from_string(args.frame)
    backend = PropagationBackend.from_string(args.backend)

    tle = load_tle(
        args.norad_id,
        tle_path=args.tle_path,
        offline=args.offline,
        cache_ttl=args.cache_ttl,
        source_order=args.source_order.split(","),
        timeout=args.timeout,
        retries=args.retries,
        backoff=args.backoff,
    )

    result = propagate(
        tle,
        start=start,
        end=end,
        step=step,
        frame=frame,
        backend=backend,
    )

    run_id = str(uuid.uuid4())
    inserted = 0
    if args.db and args.write_db:
        conn = sqlite3.connect(args.db)
        with conn:
            inserted = write_db(conn, run_id, result)
        if not args.quiet:
            print(f"Inserted {inserted} positions into {args.db}")
    elif args.db and not args.quiet:
        print("Database path provided but --write-db not set; skipping inserts")

    if args.json:
        print(json.dumps(result.as_dict(), indent=2))
    elif not args.quiet:
        print(f"Propagated {len(result.samples)} samples for NORAD {result.tle.norad_id}")
        first = result.samples[0]
        last = result.samples[-1]
        print(f"Start {first.timestamp.isoformat()} -> {first.state.position_km}")
        print(f"End   {last.timestamp.isoformat()} -> {last.state.position_km}")

    if not args.no_metadata:
        payload = {
            "run_id": run_id,
            "norad_id": result.tle.norad_id,
            "backend": backend.value,
            "frame": frame.value,
            "start": result.start.isoformat(),
            "end": result.end.isoformat(),
            "step_seconds": step.total_seconds(),
            "samples": len(result.samples),
            "offline": args.offline,
            "tle_source": result.tle.source,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "db_path": str(args.db) if args.db else None,
            "db_records": inserted,
        }
        record_metadata(args.metadata, payload)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
