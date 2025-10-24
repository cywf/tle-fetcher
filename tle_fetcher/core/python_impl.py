"""Pure Python implementation of the TLE core primitives."""

from __future__ import annotations

import datetime as dt
import json
from typing import Optional

from .types import TLE


def checksum(line: str) -> bool:
    """Validate checksum per CelesTrak spec."""
    line = line.rstrip()
    if not line:
        return False
    try:
        expected = int(line[-1])
    except ValueError:
        return False
    total = 0
    for ch in line[:-1]:
        if ch.isdigit():
            total += int(ch)
        elif ch == "-":
            total += 1
    return (total % 10) == expected


def _catnum_field(line: str) -> str:
    return line[2:7].strip()


def _ensure_source(source: str) -> str:
    return source or "unknown"


def parse(text: str, *, norad_id: str = "", source: str = "") -> TLE:
    """Parse raw payload text (or Ivan JSON) into a :class:`TLE`."""

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    name: Optional[str] = None
    line1: Optional[str] = None
    line2: Optional[str] = None

    for idx in range(len(lines)):
        if lines[idx].startswith("1 ") and idx + 1 < len(lines) and lines[idx + 1].startswith("2 "):
            if idx - 1 >= 0 and not lines[idx - 1].startswith(("1 ", "2 ")):
                name = lines[idx - 1]
            line1, line2 = lines[idx], lines[idx + 1]
            break

    if line1 is None or line2 is None:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("Could not locate TLE line pair in response") from exc
        if not isinstance(data, dict) or "line1" not in data or "line2" not in data:
            raise ValueError("Could not locate TLE line pair in response")
        line1 = str(data["line1"])
        line2 = str(data["line2"])
        if "name" in data:
            name_val = data.get("name")
            name = None if name_val is None else str(name_val)

    if not line1 or not line2:
        raise ValueError("Empty TLE line detected")
    if not line1.startswith("1 ") or not line2.startswith("2 "):
        raise ValueError("Bad TLE line prefixes")
    if not checksum(line1) or not checksum(line2):
        raise ValueError("Checksum failed")

    cat1 = _catnum_field(line1)
    cat2 = _catnum_field(line2)
    if cat1 != cat2:
        raise ValueError("Catalog numbers differ between L1 and L2")

    if norad_id and norad_id.isdigit():
        cat_digits = cat1.replace(" ", "")
        if cat_digits.isdigit() and int(cat_digits) != int(norad_id):
            raise ValueError("Catalog number does not match requested NORAD ID")

    resolved_id = norad_id or cat1.strip()
    return TLE(norad_id=resolved_id, name=name, line1=line1, line2=line2, source=_ensure_source(source))


def epoch(line1: str) -> dt.datetime:
    """Parse epoch from line 1 into a timezone-aware UTC datetime."""

    year2 = int(line1[18:20])
    doy = float(line1[20:32])
    year = 1900 + year2 if year2 >= 57 else 2000 + year2
    day_int = int(doy)
    frac = doy - day_int
    base = dt.datetime(year, 1, 1, tzinfo=dt.timezone.utc) + dt.timedelta(days=day_int - 1)
    return base + dt.timedelta(seconds=frac * 86400.0)


def sgp4(*_args: object, **_kwargs: object) -> None:
    """Placeholder for future SGP4 propagation API."""

    raise NotImplementedError("Rust extension not built with SGP4 support")


__all__ = ["TLE", "parse", "checksum", "epoch", "sgp4"]
