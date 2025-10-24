"""Dynamic dispatch to the optional Rust extension or the Python fallback."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from .types import TLE

try:  # pragma: no cover - exercised in runtime environments with the extension
    _native = import_module("tle_fetcher.core._tle_core")
except Exception:  # pragma: no cover - default in pure Python envs
    from . import python_impl as _backend
else:  # pragma: no cover - exercised in wheels with the extension
    _backend = None


if _backend is None:

    def parse(text: str, *, norad_id: str = "", source: str = "") -> TLE:
        norad, name, line1, line2, src = _native.parse(text, norad_id, source)
        return TLE(norad_id=norad, name=name, line1=line1, line2=line2, source=src)

    def checksum(line: str) -> bool:
        return bool(_native.checksum(line))

    def epoch(line1: str):
        return _native.epoch(line1)

    def sgp4(*args: Any, **kwargs: Any):
        return _native.sgp4(*args, **kwargs)

else:
    parse = _backend.parse
    checksum = _backend.checksum
    epoch = _backend.epoch
    sgp4 = _backend.sgp4


__all__ = ["parse", "checksum", "epoch", "sgp4", "TLE"]
