import datetime as dt

from fetch.cache import CacheEntry, InMemoryCache
from fetch.service import FetchService
from fetch.sources import SourceError
from tle_fetcher.tle import TLE


BASE_TLE = TLE(
    norad_id="25544",
    name="ISS (ZARYA)",
    line1="1 25544U 98067A   24157.20856222  .00006411  00000+0  11842-3 0  9996",
    line2="2 25544  51.6412 205.1217 0004225 113.2939 306.8174 15.50073703551595",
    source="cache",
)

UPDATED_TLE_TEXT = """ISS (ZARYA)
1 25544U 98067A   24158.20856222  .00006411  00000+0  11842-3 0  9997
2 25544  51.6412 210.1217 0004225 113.2939 306.8174 15.50073703551591
"""


class StubRepository:
    def __init__(self):
        self.entries = {}

    def get(self, norad_id: str):
        return self.entries.get(norad_id)

    def save(self, entry: CacheEntry) -> None:
        self.entries[entry.tle.norad_id] = entry


class StubSource:
    def __init__(self, name: str, responses):
        self.name = name
        self._responses = list(responses)
        self.calls = 0

    def fetch(self, norad_id: str) -> str:
        self.calls += 1
        if not self._responses:
            raise SourceError("no responses configured")
        return self._responses.pop(0)


def test_service_prefers_cache_over_network():
    now = dt.datetime(2024, 6, 5, 12, 0, 0)

    cache = InMemoryCache(clock=lambda: now)
    cache_entry = CacheEntry(tle=BASE_TLE, fetched_at=now, source="celestrak")
    cache.set(cache_entry)

    repo = StubRepository()
    source = StubSource("celestrak", responses=[UPDATED_TLE_TEXT])
    service = FetchService(cache=cache, repository=repo, sources=[source], clock=lambda: now, rng=lambda: 1.0)

    result = service.fetch_one("25544", cache_ttl=dt.timedelta(seconds=60))
    assert result.tle is BASE_TLE
    assert source.calls == 0


def test_service_uses_repository_when_cache_stale():
    now = dt.datetime(2024, 6, 5, 12, 0, 0)
    clock_values = [now]

    def clock():
        return clock_values[0]

    cache = InMemoryCache(clock=clock)
    stale_entry = CacheEntry(tle=BASE_TLE, fetched_at=now - dt.timedelta(hours=5), source="celestrak")
    cache.set(stale_entry)

    repo = StubRepository()
    repo_entry = CacheEntry(tle=BASE_TLE, fetched_at=now, source="local")
    repo.save(repo_entry)

    source = StubSource("celestrak", responses=[UPDATED_TLE_TEXT])
    service = FetchService(cache=cache, repository=repo, sources=[source], clock=clock, rng=lambda: 1.0)

    result = service.fetch_one("25544", cache_ttl=dt.timedelta(seconds=60))
    assert result.tle is repo_entry.tle
    assert source.calls == 0


def test_service_offline_returns_stale_with_warning():
    now = dt.datetime(2024, 6, 5, 12, 0, 0)
    cache = InMemoryCache(clock=lambda: now)

    repo = StubRepository()
    repo_entry = CacheEntry(tle=BASE_TLE, fetched_at=now - dt.timedelta(days=1), source="local")
    repo.save(repo_entry)

    service = FetchService(cache=cache, repository=repo, sources=[], clock=lambda: now)

    result = service.fetch_one("25544", cache_ttl=dt.timedelta(seconds=60), offline=True)
    assert result.stale is True
    assert any("offline" in msg for msg in result.warnings)


def test_service_verification_refreshes_changed_cache():
    now = dt.datetime(2024, 6, 5, 12, 0, 0)
    cache = InMemoryCache(clock=lambda: now)
    entry = CacheEntry(tle=BASE_TLE, fetched_at=now, source="celestrak")
    cache.set(entry)

    repo = StubRepository()
    source = StubSource("celestrak", responses=[UPDATED_TLE_TEXT])
    service = FetchService(cache=cache, repository=repo, sources=[source], clock=lambda: now, rng=lambda: 0.0)

    result = service.fetch_one("25544", cache_ttl=dt.timedelta(seconds=60), verify_percent=100)
    assert result.verified is True
    assert "replaced" in " ".join(result.warnings)
    assert source.calls == 1
    assert result.tle.line1 != BASE_TLE.line1
