from __future__ import annotations

"""Discovery pipeline orchestrating catalogue ingestion."""

import datetime as dt
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Optional

from .catalog_sources import CatalogEntry, CatalogResponseCache, SOURCES
from tle_fetcher.core import http_get


@dataclass
class RunResult:
    """Outcome of a discovery pipeline execution."""

    run_id: int
    source: str
    entries: List[CatalogEntry]
    used_cache: bool
    cursor: Optional[dt.datetime]
    effective_since: Optional[dt.datetime]


class DiscoveryPipeline:
    """Coordinate discovery runs and persist catalogue state."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is None:
            db_path = Path("data") / "ingest.sqlite3"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._ensure_schema()
        self._cache = CatalogResponseCache(self._conn)

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------ schema
    def _ensure_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS catalog_entries (
                source TEXT NOT NULL,
                norad_id TEXT NOT NULL,
                name TEXT,
                line1 TEXT NOT NULL,
                line2 TEXT NOT NULL,
                epoch TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                PRIMARY KEY (source, norad_id, line1, line2)
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                since TEXT,
                cursor TEXT,
                offline INTEGER NOT NULL,
                used_cache INTEGER NOT NULL,
                new_entries INTEGER NOT NULL,
                error TEXT
            )
            """
        )

    # ----------------------------------------------------------------- helpers
    def latest_cursor(self, source: str) -> Optional[dt.datetime]:
        cur = self._conn.execute(
            "SELECT cursor FROM runs WHERE source = ? AND cursor IS NOT NULL ORDER BY id DESC LIMIT 1",
            (source,),
        )
        row = cur.fetchone()
        if not row or not row[0]:
            return None
        return dt.datetime.fromisoformat(row[0])

    def _max_epoch(self, source: str) -> Optional[dt.datetime]:
        cur = self._conn.execute(
            "SELECT MAX(epoch) FROM catalog_entries WHERE source = ?",
            (source,),
        )
        row = cur.fetchone()
        if row and row[0]:
            return dt.datetime.fromisoformat(row[0])
        return None

    @staticmethod
    def _normalise(dt_value: dt.datetime) -> dt.datetime:
        if dt_value.tzinfo is None:
            return dt_value
        return dt_value.astimezone(dt.timezone.utc).replace(tzinfo=None)

    def _log_run_start(
        self,
        source: str,
        since: Optional[dt.datetime],
        offline: bool,
    ) -> int:
        now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        cur = self._conn.execute(
            """
            INSERT INTO runs(source, started_at, since, offline, used_cache, new_entries)
            VALUES (?, ?, ?, ?, 0, 0)
            """,
            (source, now, since.isoformat() if since else None, int(offline)),
        )
        return int(cur.lastrowid)

    def _log_run_finish(
        self,
        run_id: int,
        *,
        cursor: Optional[dt.datetime],
        used_cache: bool,
        new_entries: int,
    ) -> None:
        self._conn.execute(
            """
            UPDATE runs
            SET finished_at = ?,
                cursor = ?,
                used_cache = ?,
                new_entries = ?
            WHERE id = ?
            """,
            (
                dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                cursor.isoformat() if cursor else None,
                int(used_cache),
                new_entries,
                run_id,
            ),
        )

    def _log_run_error(self, run_id: int, message: str) -> None:
        self._conn.execute(
            """
            UPDATE runs
            SET finished_at = ?,
                error = ?
            WHERE id = ?
            """,
            (dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), message, run_id),
        )

    def _store_entries(self, entries: Iterable[CatalogEntry]) -> List[CatalogEntry]:
        new_entries: List[CatalogEntry] = []
        now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        for entry in entries:
            cur = self._conn.execute(
                """
                INSERT OR IGNORE INTO catalog_entries(
                    source, norad_id, name, line1, line2, epoch, first_seen
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.source,
                    entry.norad_id,
                    entry.name,
                    entry.line1,
                    entry.line2,
                    entry.epoch.replace(tzinfo=None).isoformat(),
                    now,
                ),
            )
            if cur.rowcount:
                new_entries.append(entry)
        return new_entries

    # --------------------------------------------------------------- public API
    def run(
        self,
        source: str,
        *,
        since: Optional[dt.datetime] = None,
        offline: bool = False,
        loader: Callable[[str], bytes] = None,
    ) -> RunResult:
        if source not in SOURCES:
            raise KeyError(f"Unknown source '{source}'")
        source_impl = SOURCES[source]
        effective_since = since or self.latest_cursor(source)
        if effective_since is not None:
            effective_since = self._normalise(effective_since)
        loader = loader or http_get

        with self._conn:
            run_id = self._log_run_start(source, effective_since, offline)

        try:
            entries, used_cache = source_impl.fetch(
                effective_since,
                offline=offline,
                cache=self._cache,
                loader=loader,
            )
            boundary = (
                self._normalise(effective_since)
                if effective_since is not None
                else None
            )
            filtered = []
            for entry in entries:
                entry_epoch = self._normalise(entry.epoch)
                if boundary is None or entry_epoch > boundary:
                    filtered.append(
                        CatalogEntry(
                            source=entry.source,
                            norad_id=entry.norad_id,
                            name=entry.name,
                            line1=entry.line1,
                            line2=entry.line2,
                            epoch=entry_epoch,
                        )
                    )
            with self._conn:
                new_entries = self._store_entries(filtered)
                cursor = self._max_epoch(source)
                self._log_run_finish(
                    run_id,
                    cursor=cursor,
                    used_cache=used_cache,
                    new_entries=len(new_entries),
                )
            return RunResult(
                run_id=run_id,
                source=source,
                entries=new_entries,
                used_cache=used_cache,
                cursor=cursor,
                effective_since=effective_since,
            )
        except Exception as exc:
            with self._conn:
                self._log_run_error(run_id, str(exc))
            raise


__all__ = ["DiscoveryPipeline", "RunResult"]
