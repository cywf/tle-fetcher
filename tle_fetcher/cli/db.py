"""Database management CLI for tle-fetcher."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from db import session


def build_parser(prog: Optional[str] = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog or "tle-fetcher db",
        description="Manage the tle-fetcher SQLite database.",
    )
    parser.add_argument(
        "--db-path",
        default=str(session.get_default_db_path()),
        help="Path to the SQLite database file.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Create the database and apply all migrations.")
    subparsers.add_parser("migrate", help="Apply any pending migrations.")
    subparsers.add_parser("verify", help="Check the schema version and exit non-zero if migrations are missing.")

    backup_parser = subparsers.add_parser("backup", help="Create a SQLite backup at the given destination path.")
    backup_parser.add_argument("destination", help="Path to the backup database file.")
    return parser


def _handle_init(db_path: Path) -> int:
    applied = session.initialize_database(db_path)
    if applied:
        print(f"Initialized database at {db_path} (applied migrations: {', '.join(applied)})")
    else:
        print(f"Database at {db_path} is already up to date.")
    return 0


def _handle_migrate(db_path: Path) -> int:
    with session.get_connection(db_path) as conn:
        applied = session.apply_migrations(conn)
    if applied:
        print(f"Applied migrations: {', '.join(applied)}")
    else:
        print("No migrations to apply.")
    return 0


def _handle_verify(db_path: Path) -> int:
    ok, applied, missing = session.verify_database(db_path)
    if ok:
        latest = session.latest_migration_version()
        label = latest or "no migrations"
        print(f"Database verified. Latest migration: {label}.")
        return 0
    if not applied and missing:
        print("Database is not initialized.")
    else:
        print(f"Missing migrations: {', '.join(missing)}")
    return 1


def _handle_backup(db_path: Path, destination: Path) -> int:
    session.backup_database(db_path, destination)
    print(f"Backup written to {destination}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    db_path = Path(args.db_path)
    if args.command == "init":
        return _handle_init(db_path)
    if args.command == "migrate":
        return _handle_migrate(db_path)
    if args.command == "verify":
        return _handle_verify(db_path)
    if args.command == "backup":
        destination = Path(args.destination)
        return _handle_backup(db_path, destination)
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
