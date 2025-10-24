"""Caching utilities used by the TLE fetch service."""
from __future__ import annotations

import dataclasses
import datetime as dt
from pathlib import Path
from typing import Callable, Dict, Optional

from tle_fetcher.tle import TLE, parse_tle_text


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


@dataclasses.dataclass
class CacheEntry:
    tle: TLE
    fetched_at: dt.datetime
    source: str

    def age(self, now: Optional[dt.datetime] = None) -> dt.timedelta:
        now = now or _utcnow()
        return now - self.fetched_at

    def is_stale(self, ttl: Optional[dt.timedelta], now: Optional[dt.datetime] = None) -> bool:
        if ttl is None:
            return False
        now = now or _utcnow()
        return self.age(now) > ttl


class InMemoryCache:
    """Simple in-memory cache supporting TTL lookups."""

    def __init__(self, clock: Optional[Callable[[], dt.datetime]] = None) -> None:
        self._clock = clock or _utcnow
        self._entries: Dict[str, CacheEntry] = {}

    def get(self, norad_id: str, ttl: Optional[dt.timedelta] = None, allow_stale: bool = False) -> Optional[CacheEntry]:
        entry = self._entries.get(norad_id)
        if not entry:
            return None
        if ttl is None:
            return entry
        stale = entry.is_stale(ttl, now=self._clock())
        if stale and not allow_stale:
            return None
        return entry

    def set(self, entry: CacheEntry) -> None:
        self._entries[entry.tle.norad_id] = entry

    def delete(self, norad_id: str) -> None:
        self._entries.pop(norad_id, None)

    def clear(self) -> None:
        self._entries.clear()


class FileRepository:
    """Persist TLEs to disk using ``*.tle`` files.

    File modification times are treated as the fetch timestamp.  The directory
    is created on demand and each NORAD identifier is stored as ``<id>.tle``.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, norad_id: str) -> Path:
        return self.root / f"{norad_id}.tle"

    def save(self, entry: CacheEntry) -> None:
        path = self._path(entry.tle.norad_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(entry.tle.as_text(include_name=True), encoding="utf-8")

    def get(self, norad_id: str) -> Optional[CacheEntry]:
        path = self._path(norad_id)
        if not path.exists():
            return None
        text = path.read_text(encoding="utf-8")
        tle = parse_tle_text(norad_id, text, source="local")
        fetched_at = dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).replace(tzinfo=None)
        return CacheEntry(tle=tle, fetched_at=fetched_at, source="local")

    def delete(self, norad_id: str) -> None:
        path = self._path(norad_id)
        if path.exists():
            path.unlink()


__all__ = ["CacheEntry", "InMemoryCache", "FileRepository"]
