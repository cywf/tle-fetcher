"""CRUD helpers for the SQLite database."""

from __future__ import annotations

import datetime as dt
from typing import List, Optional

from . import models


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _iso(value: Optional[dt.datetime]) -> Optional[str]:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    return value.isoformat(timespec="microseconds")


def get_or_create_satellite(conn, norad_id: str, name: Optional[str] = None) -> models.Satellite:
    cur = conn.execute("SELECT * FROM satellites WHERE norad_id = ?", (norad_id,))
    row = cur.fetchone()
    if row:
        if name and not row["name"]:
            conn.execute("UPDATE satellites SET name = ? WHERE id = ?", (name, row["id"]))
            conn.commit()
            row = conn.execute("SELECT * FROM satellites WHERE id = ?", (row["id"],)).fetchone()
        return models.Satellite.from_row(row)

    cur = conn.execute(
        "INSERT INTO satellites(norad_id, name) VALUES (?, ?)",
        (norad_id, name),
    )
    conn.commit()
    new_row = conn.execute("SELECT * FROM satellites WHERE id = ?", (cur.lastrowid,)).fetchone()
    return models.Satellite.from_row(new_row)


def upsert_satellite_name(conn, norad_id: str, name: str) -> models.Satellite:
    sat = get_or_create_satellite(conn, norad_id, name=name)
    if sat.name != name:
        conn.execute("UPDATE satellites SET name = ? WHERE id = ?", (name, sat.id))
        conn.commit()
        row = conn.execute("SELECT * FROM satellites WHERE id = ?", (sat.id,)).fetchone()
        return models.Satellite.from_row(row)
    return sat


def record_tle(
    conn,
    *,
    satellite_id: int,
    line1: str,
    line2: str,
    source: str,
    epoch: dt.datetime,
    fetched_at: Optional[dt.datetime] = None,
) -> models.TLE:
    fetched = fetched_at or _now()
    cur = conn.execute(
        """
        INSERT INTO tles (satellite_id, line1, line2, source, epoch, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(satellite_id, epoch, source) DO UPDATE SET
            line1=excluded.line1,
            line2=excluded.line2,
            fetched_at=excluded.fetched_at
        """,
        (
            satellite_id,
            line1,
            line2,
            source,
            _iso(epoch),
            _iso(fetched),
        ),
    )
    conn.commit()
    if cur.lastrowid is None:
        # Row was updated; fetch the existing record
        row = conn.execute(
            "SELECT * FROM tles WHERE satellite_id = ? AND epoch = ? AND source = ?",
            (satellite_id, _iso(epoch), source),
        ).fetchone()
    else:
        row = conn.execute("SELECT * FROM tles WHERE id = ?", (cur.lastrowid,)).fetchone()
    return models.TLE.from_row(row)


def latest_tle_for_satellite(conn, satellite_id: int) -> Optional[models.TLE]:
    row = conn.execute(
        """
        SELECT * FROM tles
        WHERE satellite_id = ?
        ORDER BY epoch DESC, fetched_at DESC, id DESC
        LIMIT 1
        """,
        (satellite_id,),
    ).fetchone()
    if row is None:
        return None
    return models.TLE.from_row(row)


def create_run(conn, *, command: str, arguments: str, started_at: Optional[dt.datetime] = None, notes: Optional[str] = None) -> models.Run:
    started = started_at or _now()
    cur = conn.execute(
        """
        INSERT INTO runs(command, arguments, status, started_at, notes)
        VALUES (?, ?, 'running', ?, ?)
        """,
        (command, arguments, _iso(started), notes),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM runs WHERE id = ?", (cur.lastrowid,)).fetchone()
    return models.Run.from_row(row)


def finish_run(
    conn,
    run_id: int,
    *,
    status: str = "ok",
    completed_at: Optional[dt.datetime] = None,
    notes: Optional[str] = None,
) -> models.Run:
    completed = completed_at or _now()
    conn.execute(
        """
        UPDATE runs
        SET status = ?, completed_at = ?, notes = COALESCE(?, notes)
        WHERE id = ?
        """,
        (status, _iso(completed), notes, run_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    return models.Run.from_row(row)


def get_run(conn, run_id: int) -> Optional[models.Run]:
    row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        return None
    return models.Run.from_row(row)


def record_position(
    conn,
    *,
    run_id: int,
    satellite_id: int,
    timestamp: dt.datetime,
    latitude: float,
    longitude: float,
    altitude_km: Optional[float] = None,
) -> models.Position:
    cur = conn.execute(
        """
        INSERT INTO positions(run_id, satellite_id, timestamp, latitude, longitude, altitude_km)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_id, satellite_id, timestamp) DO UPDATE SET
            latitude=excluded.latitude,
            longitude=excluded.longitude,
            altitude_km=excluded.altitude_km
        """,
        (
            run_id,
            satellite_id,
            _iso(timestamp),
            latitude,
            longitude,
            altitude_km,
        ),
    )
    conn.commit()
    if cur.lastrowid is None:
        row = conn.execute(
            "SELECT * FROM positions WHERE run_id = ? AND satellite_id = ? AND timestamp = ?",
            (run_id, satellite_id, _iso(timestamp)),
        ).fetchone()
    else:
        row = conn.execute("SELECT * FROM positions WHERE id = ?", (cur.lastrowid,)).fetchone()
    return models.Position.from_row(row)


def positions_for_run(conn, run_id: int) -> List[models.Position]:
    rows = conn.execute(
        "SELECT * FROM positions WHERE run_id = ? ORDER BY timestamp ASC",
        (run_id,),
    ).fetchall()
    return [models.Position.from_row(row) for row in rows]
