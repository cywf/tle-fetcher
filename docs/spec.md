# Database Specification

## Overview

The application persists data in a SQLite database located at `data/tle_fetcher.sqlite3` by default.  The location can be overridden with the `TLE_FETCHER_DB` environment variable or via the `--db-path` flag on the CLI.  Migrations are stored as plain SQL files under `db/migrations/` and are applied sequentially in lexicographic order.

## Schema (Migration 0001)

### `satellites`
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `norad_id` TEXT UNIQUE NOT NULL
- `name` TEXT NULLABLE
- `created_at` TEXT UTC timestamp (`datetime('now')` default)

Index: `idx_satellites_norad_id` on `norad_id`.

### `tles`
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `satellite_id` INTEGER NOT NULL REFERENCES `satellites(id)` ON DELETE CASCADE
- `line1`, `line2` TEXT NOT NULL
- `source` TEXT NOT NULL
- `epoch` TEXT (ISO-8601 timestamp) NOT NULL
- `fetched_at` TEXT UTC timestamp (`datetime('now')` default)
- `created_at` TEXT UTC timestamp (`datetime('now')` default)

Constraints / indexes:
- UNIQUE (`satellite_id`, `epoch`, `source`)
- `idx_tles_satellite_epoch` on (`satellite_id`, `epoch` DESC)

### `runs`
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `command` TEXT NOT NULL
- `arguments` TEXT NOT NULL
- `status` TEXT NOT NULL (`running` default)
- `started_at` TEXT UTC timestamp (`datetime('now')` default)
- `completed_at` TEXT UTC timestamp NULLABLE
- `notes` TEXT NULLABLE
- `created_at` TEXT UTC timestamp (`datetime('now')` default)

Index: `idx_runs_status_started` on (`status`, `started_at` DESC).

### `positions`
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `run_id` INTEGER NOT NULL REFERENCES `runs(id)` ON DELETE CASCADE
- `satellite_id` INTEGER NOT NULL REFERENCES `satellites(id)` ON DELETE CASCADE
- `timestamp` TEXT UTC timestamp NOT NULL
- `latitude` REAL NOT NULL
- `longitude` REAL NOT NULL
- `altitude_km` REAL NULLABLE
- `created_at` TEXT UTC timestamp (`datetime('now')` default)

Constraints / indexes:
- UNIQUE (`run_id`, `satellite_id`, `timestamp`)
- `idx_positions_sat_time` on (`satellite_id`, `timestamp`)

## Migration Policy

- Each migration file is named `<version>_<slug>.sql`.  Versions are zero-padded integers (e.g. `0001`).
- Migrations are applied in ascending version order.  The schema version is tracked via the `schema_migrations` table, with an auxiliary `PRAGMA user_version` update for interoperability.
- Migrations must be idempotent: use `IF NOT EXISTS` / `ON CONFLICT` to allow reapplication without errors.
- New migrations should be appended to `db/migrations/` and accompanied by schema tests.
- Use the CLI commands `python -m tle_fetcher.cli.db <command>` or `python tle_fetcher.py db <command>` to initialise (`init`), upgrade (`migrate`), verify (`verify`), or back up (`backup`) databases.

## Pragmas

Migration `0001` enables `journal_mode=WAL` and `foreign_keys=ON`.  Runtime connections re-enable foreign keys in `db.session.get_connection`.
