"""Utilities for working with Two-Line Element (TLE) records."""
from __future__ import annotations

import dataclasses
import datetime as dt
import json
from typing import Optional


@dataclasses.dataclass(frozen=True)
class TLE:
    """Normalized representation of a TLE.

    The ``name`` attribute is optional because some sources return only the
    two TLE lines.  ``source`` indicates which provider yielded the record and
    is primarily for diagnostics/logging purposes.
    """

    norad_id: str
    name: Optional[str]
    line1: str
    line2: str
    source: str

    def as_text(self, include_name: bool = True) -> str:
        lines = []
        if include_name and self.name:
            lines.append(self.name)
        lines.extend([self.line1, self.line2])
        return "\n".join(lines) + "\n"


def tle_checksum_ok(line: str) -> bool:
    """Return ``True`` when ``line`` satisfies the NORAD checksum rule."""

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


def parse_tle_text(norad_id: str, text: str, source: str) -> TLE:
    """Parse *text* into a :class:`TLE` instance.

    The parser understands both the traditional three-line format (name + two
    element lines) and Ivan Stanojević's JSON API that returns ``line1`` and
    ``line2`` keys.
    """

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        raise ValueError("empty TLE payload")

    name: Optional[str] = None
    line1 = line2 = None  # type: ignore[assignment]

    for i in range(len(lines)):
        if lines[i].startswith("1 ") and i + 1 < len(lines) and lines[i + 1].startswith("2 "):
            if i - 1 >= 0 and not lines[i - 1].startswith(("1 ", "2 ")):
                name = lines[i - 1]
            line1, line2 = lines[i], lines[i + 1]
            break

    if line1 is None or line2 is None:
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "line1" in data and "line2" in data:
                name = data.get("name")
                line1 = str(data["line1"])
                line2 = str(data["line2"])
            else:
                raise ValueError
        except Exception as exc:  # pragma: no cover - defensive
            raise ValueError("could not locate TLE line pair in response") from exc

    if not (line1.startswith("1 ") and line2.startswith("2 ")):
        raise ValueError("bad TLE prefixes")
    if not tle_checksum_ok(line1) or not tle_checksum_ok(line2):
        raise ValueError("checksum failed")
    if _catnum_field(line1) != _catnum_field(line2):
        raise ValueError("catalog numbers differ between lines")

    if norad_id and norad_id.isdigit():
        try:
            field = _catnum_field(line1).strip()
            if field.isdigit() and int(field) != int(norad_id):
                raise ValueError("catalog number does not match requested NORAD ID")
        except ValueError:
            pass

    return TLE(norad_id=norad_id, name=name, line1=line1, line2=line2, source=source)


def tle_epoch(line1: str) -> dt.datetime:
    """Return the epoch encoded in ``line1`` as a naive UTC datetime."""

    year2 = int(line1[18:20])
    day_of_year = float(line1[20:32])

    year = 2000 + year2 if year2 < 57 else 1900 + year2
    day = int(day_of_year)
    frac = day_of_year - day
    base = dt.datetime(year, 1, 1, tzinfo=dt.timezone.utc) + dt.timedelta(days=day - 1)
    seconds = frac * 86400
    result = base + dt.timedelta(seconds=seconds)
    return result.replace(tzinfo=None)


__all__ = ["TLE", "parse_tle_text", "tle_checksum_ok", "tle_epoch"]
