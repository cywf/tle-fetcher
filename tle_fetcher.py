#!/usr/bin/env python3
"""Compatibility wrapper for legacy entrypoint.

This script simply defers to :mod:`tle_fetcher.fetcher` so existing
workflows that run ``python tle_fetcher.py`` continue to function.
"""
from tle_fetcher.fetcher import main

if __name__ == "__main__":
    main()
