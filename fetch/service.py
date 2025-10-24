"""High level orchestration for fetching TLEs."""
from __future__ import annotations

import dataclasses
import datetime as dt
import random
from typing import Callable, Iterable, List, Optional, Protocol, Sequence

from fetch.cache import CacheEntry, InMemoryCache
from fetch.sources import SourceClient, SourceError
from tle_fetcher.tle import TLE, parse_tle_text


@dataclasses.dataclass
class FetchResult:
    tle: TLE
    source: str
    fetched_at: dt.datetime
    stale: bool = False
    verified: bool = False
    warnings: List[str] = dataclasses.field(default_factory=list)

    def age(self, now: Optional[dt.datetime] = None) -> dt.timedelta:
        now = now or dt.datetime.utcnow()
        return now - self.fetched_at


class Repository(Protocol):
    def get(self, norad_id: str) -> Optional[CacheEntry]:
        ...

    def save(self, entry: CacheEntry) -> None:
        ...


class FetchService:
    """Coordinates cache, repository, and source lookups."""

    def __init__(
        self,
        cache: Optional[InMemoryCache] = None,
        repository: Optional[Repository] = None,
        sources: Optional[Sequence[SourceClient]] = None,
        clock: Optional[Callable[[], dt.datetime]] = None,
        rng: Optional[Callable[[], float]] = None,
    ) -> None:
        self.cache = cache or InMemoryCache()
        self.repository = repository
        self.sources = list(sources or [])
        self._clock = clock or (lambda: dt.datetime.now(dt.timezone.utc).replace(tzinfo=None))
        self._rng = rng or random.random

    def fetch_many(
        self,
        norad_ids: Iterable[str],
        cache_ttl: dt.timedelta,
        verify_percent: float = 0.0,
        offline: bool = False,
    ) -> List[FetchResult]:
        results = []
        for norad_id in norad_ids:
            results.append(
                self.fetch_one(
                    norad_id=str(norad_id),
                    cache_ttl=cache_ttl,
                    verify_percent=verify_percent,
                    offline=offline,
                )
            )
        return results

    def fetch_one(
        self,
        norad_id: str,
        cache_ttl: dt.timedelta,
        verify_percent: float = 0.0,
        offline: bool = False,
    ) -> FetchResult:
        now = self._clock()
        ttl = cache_ttl
        warnings: List[str] = []

        cache_entry = self.cache.get(norad_id, ttl=ttl, allow_stale=True)
        if cache_entry and not cache_entry.is_stale(ttl, now):
            result = FetchResult(
                tle=cache_entry.tle,
                source="cache",
                fetched_at=cache_entry.fetched_at,
            )
            if self._should_verify(verify_percent):
                refreshed = self._fetch_from_network(norad_id, allow_failure=True)
                if refreshed:
                    result.verified = True
                    if (refreshed.tle.line1, refreshed.tle.line2) != (
                        cache_entry.tle.line1,
                        cache_entry.tle.line2,
                    ):
                        warnings.append("Cache entry replaced after verification")
                        result.tle = refreshed.tle
                        result.source = refreshed.source
                        result.fetched_at = refreshed.fetched_at
                    else:
                        # refresh timestamps for good measure
                        self.cache.set(refreshed)
                        if self.repository:
                            self.repository.save(refreshed)
            result.warnings.extend(warnings)
            return result

        repo_entry = self.repository.get(norad_id) if self.repository else None
        if repo_entry and not repo_entry.is_stale(ttl, now):
            self.cache.set(repo_entry)
            result = FetchResult(
                tle=repo_entry.tle,
                source=repo_entry.source,
                fetched_at=repo_entry.fetched_at,
            )
            if self._should_verify(verify_percent):
                refreshed = self._fetch_from_network(norad_id, allow_failure=True)
                if refreshed:
                    result.verified = True
                    if (refreshed.tle.line1, refreshed.tle.line2) != (
                        repo_entry.tle.line1,
                        repo_entry.tle.line2,
                    ):
                        warnings.append("Repository entry replaced after verification")
                        result.tle = refreshed.tle
                        result.source = refreshed.source
                        result.fetched_at = refreshed.fetched_at
                    else:
                        self.cache.set(refreshed)
                        if self.repository:
                            self.repository.save(refreshed)
            result.warnings.extend(warnings)
            return result

        # Stale data handling
        stale_candidates = [entry for entry in [cache_entry, repo_entry] if entry]
        freshest_stale = None
        if stale_candidates:
            freshest_stale = max(stale_candidates, key=lambda entry: entry.fetched_at)

        if offline:
            if freshest_stale:
                warnings.append("Operating offline with stale TLE")
                return FetchResult(
                    tle=freshest_stale.tle,
                    source=freshest_stale.source,
                    fetched_at=freshest_stale.fetched_at,
                    stale=True,
                    warnings=warnings,
                )
            raise RuntimeError("Offline mode requested but no cached TLE available")

        network_entry = self._fetch_from_network(norad_id)
        result = FetchResult(
            tle=network_entry.tle,
            source=network_entry.source,
            fetched_at=network_entry.fetched_at,
        )

        if freshest_stale and freshest_stale.is_stale(ttl, now):
            warnings.append("Replaced stale TLE with fresh network result")
            result.warnings.extend(warnings)
        return result

    def _should_verify(self, percent: float) -> bool:
        if percent <= 0:
            return False
        return self._rng() < (percent / 100.0 if percent > 1 else percent)

    def _fetch_from_network(self, norad_id: str, allow_failure: bool = False) -> Optional[CacheEntry]:
        errors = {}
        for client in self.sources:
            try:
                payload = client.fetch(norad_id)
                tle = parse_tle_text(norad_id, payload, source=client.name)
                entry = CacheEntry(tle=tle, fetched_at=self._clock(), source=client.name)
                self.cache.set(entry)
                if self.repository:
                    self.repository.save(entry)
                return entry
            except SourceError as exc:
                errors[client.name] = str(exc)
            except ValueError as exc:
                errors[client.name] = f"{exc}"  # parsing failed
        if allow_failure:
            return None
        joined = " | ".join(f"{k}: {v}" for k, v in errors.items()) or "no sources"
        raise SourceError(f"All sources failed for {norad_id}: {joined}")


__all__ = ["FetchResult", "FetchService"]
