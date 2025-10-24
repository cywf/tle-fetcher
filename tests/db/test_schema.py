import sqlite3
from pathlib import Path

from db import session


def test_initialize_creates_schema(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    applied = session.initialize_database(db_path)
    assert "0001" in applied

    with session.get_connection(db_path) as conn:
        tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert {"satellites", "tles", "runs", "positions", "schema_migrations"}.issubset(tables)

        indexes = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
            )
        }
        assert {
            "idx_satellites_norad_id",
            "idx_tles_satellite_epoch",
            "idx_runs_status_started",
            "idx_positions_sat_time",
        }.issubset(indexes)

        fk_enabled = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk_enabled == 1

        user_version = conn.execute("PRAGMA user_version").fetchone()[0]
        latest = session.latest_migration_version()
        assert user_version == (int(latest) if latest is not None else 0)

        migrations = [row["version"] for row in conn.execute("SELECT version FROM schema_migrations")]
        assert migrations == sorted(migrations)


def test_verify_detects_missing(tmp_path):
    db_path = tmp_path / "empty.sqlite3"
    ok, applied, missing = session.verify_database(db_path)
    assert not ok
    assert applied == []
    assert "0001" in missing
