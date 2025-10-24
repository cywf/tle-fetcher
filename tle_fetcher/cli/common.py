"""Common helpers for the TLE fetcher CLI."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Iterable, List, Sequence

DEFAULT_DB_PATH = Path.home() / ".cache" / "tle-fetcher"

LOG_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}


def add_shared_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the CLI options that are common to every mode."""

    parser.add_argument(
        "--mode",
        choices=("fetch", "report"),
        default="fetch",
        help="Select CLI mode. 'fetch' performs network retrievals, 'report' summarises cached data.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=sorted(LOG_LEVELS),
        help="Logging verbosity (default: INFO).",
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Directory containing cached TLE files and generated reports.",
    )


def configure_logging(level_name: str) -> None:
    """Configure :mod:`logging` according to the CLI flag."""

    level = LOG_LEVELS.get(level_name.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def resolve_db_path(raw: str) -> Path:
    """Expand, create, and return the configured database directory."""

    path = Path(raw).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_ids_from_file(path: str | None) -> List[str]:
    """Load NORAD identifiers from a file, ignoring comments and blank lines."""

    if not path:
        return []
    file_path = Path(path).expanduser()
    if not file_path.exists():
        raise FileNotFoundError(f"IDs file not found: {file_path}")
    values: List[str] = []
    for raw in file_path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            values.append(line)
    return values


def merge_ids(explicit: Sequence[str], loaded: Iterable[str]) -> List[str]:
    """Merge user-provided and file-provided IDs preserving order and uniqueness."""

    result: List[str] = []
    seen = set()
    for value in list(explicit) + list(loaded):
        candidate = value.strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        result.append(candidate)
    return result
