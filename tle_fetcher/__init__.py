"""Core exports for the :mod:`tle_fetcher` package."""

from .fetcher import (
    CACHE_DIR,
    CACHE_TTL_SECS,
    TLE,
    cache_path,
    parse_tle_text,
    read_cache,
    write_cache,
    fetch_with_fallback,
)

__all__ = [
    "CACHE_DIR",
    "CACHE_TTL_SECS",
    "TLE",
    "cache_path",
    "parse_tle_text",
    "read_cache",
    "write_cache",
    "fetch_with_fallback",
]
