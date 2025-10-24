"""SQLite session and migration helpers for the TLE fetcher database."""
from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
DEFAULT_DB_FILENAME = "tle_fetcher.sqlite3"
DEFAULT_DB_PATH = DATA_DIR / DEFAULT_DB_FILENAME


class MigrationError(RuntimeError):
    """Raised when migrations cannot be applied."""


def get_default_db_path() -> Path:
    """Resolve the default database path.

    The path can be overridden with the ``TLE_FETCHER_DB`` environment variable.
    """

    override = os.getenv("TLE_FETCHER_DB")
    if override:
        return Path(override)
    return DEFAULT_DB_PATH


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def get_connection(path: Optional[Path] = None, *, readonly: bool = False) -> sqlite3.Connection:
    """Open a SQLite connection with the required pragmas enabled."""

    db_path = Path(path or get_default_db_path())
    if not readonly:
        _ensure_parent(db_path)
        conn = sqlite3.connect(str(db_path))
    else:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _available_migrations() -> List[Path]:
    if not MIGRATIONS_DIR.exists():
        return []
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def parse_version(migration_file: Path) -> str:
    return migration_file.stem.split("_", 1)[0]


def applied_migrations(conn: sqlite3.Connection) -> List[str]:
    try:
        rows = conn.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
        return [row["version"] for row in rows]
    except sqlite3.OperationalError:
        # Table does not exist yet.
        return []


def apply_migrations(conn: sqlite3.Connection, *, target: Optional[str] = None) -> List[str]:
    """Apply pending migrations up to ``target`` (inclusive).

    Returns the list of version strings that were applied.
    """

    available = _available_migrations()
    if not available:
        return []

    applied = set(applied_migrations(conn))
    pending: Sequence[Path]
    if target is None:
        pending = [m for m in available if parse_version(m) not in applied]
    else:
        pending = [
            m for m in available
            if parse_version(m) not in applied and parse_version(m) <= target
        ]

    applied_now: List[str] = []
    for migration in pending:
        sql = migration.read_text(encoding="utf-8")
        try:
            conn.executescript(sql)
        except sqlite3.DatabaseError as exc:
            raise MigrationError(f"Failed to apply migration {migration.name}: {exc}") from exc
        version = parse_version(migration)
        conn.execute(
            "INSERT INTO schema_migrations(version, applied_at) VALUES (?, datetime('now'))",
            (version,),
        )
        try:
            conn.execute(f"PRAGMA user_version = {int(version)}")
        except ValueError:
            # Ignore non-numeric versions for PRAGMA user_version.
            pass
        applied_now.append(version)
    if applied_now:
        conn.commit()
    return applied_now


def latest_migration_version() -> Optional[str]:
    migrations = _available_migrations()
    if not migrations:
        return None
    return parse_version(migrations[-1])


def initialize_database(path: Optional[Path] = None) -> List[str]:
    """Create the database (if needed) and apply all migrations."""

    db_path = Path(path or get_default_db_path())
    _ensure_parent(db_path)
    with get_connection(db_path) as conn:
        applied = apply_migrations(conn)
    return applied


def verify_database(path: Optional[Path] = None) -> Tuple[bool, List[str], List[str]]:
    """Check whether the database at ``path`` has all migrations applied."""

    db_path = Path(path or get_default_db_path())
    if not db_path.exists():
        return False, [], [parse_version(m) for m in _available_migrations()]

    with get_connection(db_path, readonly=True) as conn:
        applied = applied_migrations(conn)
    expected = [parse_version(m) for m in _available_migrations()]
    missing = [v for v in expected if v not in applied]
    return not missing, applied, missing


def backup_database(source: Optional[Path], destination: Path) -> None:
    src_path = Path(source or get_default_db_path())
    if not src_path.exists():
        raise FileNotFoundError(src_path)
    _ensure_parent(destination)
    with get_connection(src_path, readonly=True) as src, sqlite3.connect(str(destination)) as dst:
        src.backup(dst)


def build_arg_parser(prog: Optional[str] = None) -> argparse.ArgumentParser:
    """Utility parser for CLI integration."""

    parser = argparse.ArgumentParser(prog=prog or "tle-fetcher db")
    parser.add_argument("--db-path", default=str(get_default_db_path()), help="Path to the SQLite database.")
    return parser
