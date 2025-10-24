from __future__ import annotations

"""Parsers and helpers for ingesting public TLE catalog feeds.

The module focuses on CelesTrak and Ivan Stanojević's API – the two
sources that are always available without credentials. Responses are
cached so that the discovery pipeline can be executed in offline mode.
"""

import dataclasses
import datetime as dt
import json
import sqlite3
import urllib.parse
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from tle_fetcher.core import http_get, parse_tle_text, tle_epoch


@dataclasses.dataclass(frozen=True)
class CatalogEntry:
    """A TLE discovered from a catalogue feed."""

    source: str
    norad_id: str
    name: Optional[str]
    line1: str
    line2: str
    epoch: dt.datetime

    def identity(self) -> Tuple[str, str, str, str]:
        return (self.source, self.norad_id, self.line1, self.line2)


class CatalogResponseCache:
    """SQLite-backed cache for raw catalogue responses."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS catalog_cache (
                cache_key TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                requested_since TEXT,
                fetched_at TEXT NOT NULL,
                payload TEXT NOT NULL
            )
            """
        )

    @staticmethod
    def _cache_key(source: str, since: Optional[dt.datetime]) -> str:
        return f"{source}|{since.isoformat() if since else 'none'}"

    def store(self, source: str, since: Optional[dt.datetime], payload: str) -> None:
        key = self._cache_key(source, since)
        self._conn.execute(
            """
            INSERT INTO catalog_cache(cache_key, source, requested_since, fetched_at, payload)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                fetched_at=excluded.fetched_at,
                payload=excluded.payload,
                requested_since=excluded.requested_since
            """,
            (
                key,
                source,
                since.isoformat() if since else None,
                dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                payload,
            ),
        )

    def load(self, source: str, since: Optional[dt.datetime]) -> Optional[str]:
        key = self._cache_key(source, since)
        cur = self._conn.execute(
            "SELECT payload FROM catalog_cache WHERE cache_key = ?", (key,)
        )
        row = cur.fetchone()
        return row[0] if row else None


class CatalogSource:
    """Abstract representation of a catalogue feed."""

    name: str
    attribution: str
    supports_since: bool

    def build_url(self, since: Optional[dt.datetime]) -> str:
        raise NotImplementedError

    def parse(self, payload: str) -> List[CatalogEntry]:
        raise NotImplementedError

    def fetch(
        self,
        since: Optional[dt.datetime] = None,
        *,
        offline: bool = False,
        cache: CatalogResponseCache,
        loader: Callable[[str], bytes] = http_get,
    ) -> Tuple[List[CatalogEntry], bool]:
        if offline:
            cached = cache.load(self.name, since)
            if cached is None:
                raise RuntimeError(
                    f"{self.name}: no cached response available for offline mode"
                )
            return self.parse(cached), True

        url = self.build_url(since)
        payload_bytes = loader(url)
        payload = payload_bytes.decode("utf-8", errors="replace")
        entries = self.parse(payload)
        cache.store(self.name, since, payload)
        return entries, False


def _iter_tle_blocks(lines: List[str]) -> Iterable[Tuple[Optional[str], str, str]]:
    seen = set()
    for idx, line in enumerate(lines):
        if not line.startswith("1 "):
            continue
        if idx + 1 >= len(lines):
            continue
        if not lines[idx + 1].startswith("2 "):
            continue
        name = None
        if idx - 1 >= 0 and not lines[idx - 1].startswith(("1 ", "2 ")):
            name = lines[idx - 1]
        line1, line2 = lines[idx], lines[idx + 1]
        fingerprint = (line1, line2)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        yield name, line1, line2


def _entries_from_lines(lines: List[str], source: str) -> List[CatalogEntry]:
    entries: List[CatalogEntry] = []
    for name, line1, line2 in _iter_tle_blocks(lines):
        norad_id = line1[2:7].strip()
        tle = parse_tle_text(norad_id, "\n".join(filter(None, [name, line1, line2])), source)
        entries.append(
            CatalogEntry(
                source=source,
                norad_id=tle.norad_id or norad_id,
                name=tle.name,
                line1=tle.line1,
                line2=tle.line2,
                epoch=tle_epoch(tle.line1),
            )
        )
    return entries


class CelesTrakSource(CatalogSource):
    name = "celestrak"
    attribution = "Data courtesy of CelesTrak (https://celestrak.org)."
    supports_since = False

    def __init__(self, group: str = "active") -> None:
        self.group = group

    def build_url(self, since: Optional[dt.datetime]) -> str:  # pragma: no cover - trivial
        params = {
            "GROUP": self.group,
            "FORMAT": "tle",
        }
        return "https://celestrak.org/NORAD/elements/gp.php?" + urllib.parse.urlencode(params)

    def parse(self, payload: str) -> List[CatalogEntry]:
        lines = [ln.strip() for ln in payload.splitlines() if ln.strip()]
        return _entries_from_lines(lines, self.name)


class IvanSource(CatalogSource):
    name = "ivan"
    attribution = "Data courtesy of Ivan Stanojević (https://tle.ivanstanojevic.me)."
    supports_since = False

    def build_url(self, since: Optional[dt.datetime]) -> str:  # pragma: no cover - trivial
        return "https://tle.ivanstanojevic.me/api/tle"

    def parse(self, payload: str) -> List[CatalogEntry]:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            lines = [ln.strip() for ln in payload.splitlines() if ln.strip()]
            return _entries_from_lines(lines, self.name)

        entries: List[CatalogEntry] = []
        if isinstance(data, dict) and "member" in data:
            iterable = data["member"]
        else:
            iterable = data
        for item in iterable:
            if not isinstance(item, dict):
                continue
            line1 = item.get("line1")
            line2 = item.get("line2")
            if not (isinstance(line1, str) and isinstance(line2, str)):
                continue
            name = item.get("name") if isinstance(item.get("name"), str) else None
            norad = item.get("satelliteId") or item.get("satellite_id") or ""
            if not isinstance(norad, str):
                norad = str(norad)
            tle = parse_tle_text(
                norad,
                json.dumps({"name": name, "line1": line1, "line2": line2}),
                self.name,
            )
            timestamp = item.get("timestamp") or item.get("epoch")
            if isinstance(timestamp, str):
                try:
                    epoch = dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                except ValueError:
                    epoch = tle_epoch(tle.line1)
            else:
                epoch = tle_epoch(tle.line1)
            entries.append(
                CatalogEntry(
                    source=self.name,
                    norad_id=tle.norad_id or norad.strip(),
                    name=tle.name,
                    line1=tle.line1,
                    line2=tle.line2,
                    epoch=epoch,
                )
            )
        return entries


SOURCES: Dict[str, CatalogSource] = {
    "celestrak": CelesTrakSource(),
    "ivan": IvanSource(),
}

__all__ = [
    "CatalogEntry",
    "CatalogResponseCache",
    "CatalogSource",
    "CelesTrakSource",
    "IvanSource",
    "SOURCES",
]
