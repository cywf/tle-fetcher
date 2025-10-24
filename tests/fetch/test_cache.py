import datetime as dt

from fetch.cache import CacheEntry, InMemoryCache
from tle_fetcher.tle import TLE


ISS_TLE = TLE(
    norad_id="25544",
    name="ISS (ZARYA)",
    line1="1 25544U 98067A   24157.20856222  .00006411  00000+0  11842-3 0  9996",
    line2="2 25544  51.6412 205.1217 0004225 113.2939 306.8174 15.50073703551595",
    source="test",
)


def test_in_memory_cache_respects_ttl():
    now = dt.datetime(2024, 6, 5, 12, 0, 0)
    clock_now = [now]

    def clock():
        return clock_now[0]

    cache = InMemoryCache(clock=clock)
    entry = CacheEntry(tle=ISS_TLE, fetched_at=now, source="celestrak")
    cache.set(entry)

    ttl = dt.timedelta(seconds=10)
    assert cache.get("25544", ttl=ttl) is entry

    clock_now[0] = now + dt.timedelta(seconds=11)
    assert cache.get("25544", ttl=ttl) is None

    stale_entry = cache.get("25544", ttl=ttl, allow_stale=True)
    assert stale_entry is entry
    assert stale_entry.is_stale(ttl, now=clock())
