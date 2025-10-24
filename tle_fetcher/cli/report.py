"""Reporting helpers for the TLE fetcher CLI."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Dict, List

from .. import parse_tle_text, tle_epoch


def register_arguments(parser: argparse.ArgumentParser) -> None:
    """Add reporting related arguments to the top-level parser."""

    parser.add_argument(
        "--report",
        metavar="DEST",
        nargs="?",
        const="-",
        help="Emit a JSON summary of cached TLEs to DEST (default: stdout).",
    )


def _collect_entries(db_path: Path) -> List[Dict[str, object]]:
    entries: List[Dict[str, object]] = []
    for tle_file in sorted(db_path.glob("*.tle")):
        try:
            text = tle_file.read_text(encoding="utf-8")
            tle = parse_tle_text(tle_file.stem, text, source="cache")
            epoch = tle_epoch(tle.line1)
            entries.append(
                {
                    "id": tle.norad_id,
                    "name": tle.name,
                    "epoch": epoch.isoformat(),
                    "source": tle.source,
                    "path": str(tle_file),
                }
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            entries.append(
                {
                    "id": tle_file.stem,
                    "error": str(exc),
                    "path": str(tle_file),
                }
            )
    return entries


def generate_summary(db_path: Path) -> Dict[str, object]:
    """Generate a machine-readable summary of cached TLE entries."""

    entries = _collect_entries(db_path)
    epochs = [dt.datetime.fromisoformat(e["epoch"]) for e in entries if "epoch" in e]
    summary: Dict[str, object] = {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(),
        "count": len(entries),
        "ids": sorted({e.get("id") for e in entries if e.get("id")}),
        "sources": sorted({e.get("source") for e in entries if e.get("source")}),
        "entries": entries,
    }
    summary["latest_epoch"] = epochs and max(epochs).isoformat()
    return summary


def run_report(ns, db_path: Path) -> int:
    """Handle the `--mode report` execution path."""

    destination = getattr(ns, "report", None) or "-"
    payload = json.dumps(generate_summary(db_path), indent=2, sort_keys=True)
    if destination == "-":
        print(payload)
    else:
        path = Path(destination).expanduser()
        path.write_text(payload + "\n", encoding="utf-8")
    return 0
