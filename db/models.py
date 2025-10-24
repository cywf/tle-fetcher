"""Dataclasses describing persisted database entities."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Optional


def _parse_dt(value: Any) -> Optional[dt.datetime]:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value
    text = str(value)
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    try:
        return dt.datetime.fromisoformat(text)
    except ValueError:
        if "+" not in text:
            try:
                return dt.datetime.fromisoformat(text + "+00:00")
            except ValueError:
                return None
        return None


@dataclass(frozen=True)
class Satellite:
    id: int
    norad_id: str
    name: Optional[str]
    created_at: dt.datetime

    @classmethod
    def from_row(cls, row: Any) -> "Satellite":
        return cls(
            id=int(row["id"]),
            norad_id=str(row["norad_id"]),
            name=row["name"],
            created_at=_parse_dt(row["created_at"]) or dt.datetime.fromtimestamp(0),
        )


@dataclass(frozen=True)
class TLE:
    id: int
    satellite_id: int
    line1: str
    line2: str
    source: str
    epoch: dt.datetime
    fetched_at: dt.datetime

    @classmethod
    def from_row(cls, row: Any) -> "TLE":
        return cls(
            id=int(row["id"]),
            satellite_id=int(row["satellite_id"]),
            line1=str(row["line1"]),
            line2=str(row["line2"]),
            source=str(row["source"]),
            epoch=_parse_dt(row["epoch"]) or dt.datetime.fromtimestamp(0, dt.timezone.utc),
            fetched_at=_parse_dt(row["fetched_at"]) or dt.datetime.fromtimestamp(0, dt.timezone.utc),
        )


@dataclass(frozen=True)
class Run:
    id: int
    command: str
    arguments: str
    status: str
    started_at: dt.datetime
    completed_at: Optional[dt.datetime]
    notes: Optional[str]

    @classmethod
    def from_row(cls, row: Any) -> "Run":
        return cls(
            id=int(row["id"]),
            command=str(row["command"]),
            arguments=str(row["arguments"]),
            status=str(row["status"]),
            started_at=_parse_dt(row["started_at"]) or dt.datetime.fromtimestamp(0, dt.timezone.utc),
            completed_at=_parse_dt(row["completed_at"]),
            notes=row["notes"],
        )


@dataclass(frozen=True)
class Position:
    id: int
    run_id: int
    satellite_id: int
    timestamp: dt.datetime
    latitude: float
    longitude: float
    altitude_km: Optional[float]
    created_at: dt.datetime

    @classmethod
    def from_row(cls, row: Any) -> "Position":
        return cls(
            id=int(row["id"]),
            run_id=int(row["run_id"]),
            satellite_id=int(row["satellite_id"]),
            timestamp=_parse_dt(row["timestamp"]) or dt.datetime.fromtimestamp(0, dt.timezone.utc),
            latitude=float(row["latitude"]),
            longitude=float(row["longitude"]),
            altitude_km=float(row["altitude_km"]) if row["altitude_km"] is not None else None,
            created_at=_parse_dt(row["created_at"]) or dt.datetime.fromtimestamp(0, dt.timezone.utc),
        )
