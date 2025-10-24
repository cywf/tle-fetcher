"""Satellite propagation services built on top of SGP4."""
from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Tuple

from sgp4.api import SGP4_ERRORS, Satrec, jday

from propagate.frames import Frame, StateVector, transform_state
from tle_fetcher.fetcher import TLE


class PropagationBackend(str, enum.Enum):
    PYTHON = "python"
    RUST = "rust"

    @classmethod
    def from_string(cls, value: str) -> "PropagationBackend":
        try:
            return cls(value.lower())
        except Exception as exc:  # pragma: no cover
            raise ValueError(f"Unknown backend '{value}'") from exc


@dataclass(frozen=True)
class PropagationSample:
    timestamp: datetime
    state: StateVector

    def as_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "position_km": list(self.state.position_km),
            "velocity_km_s": list(self.state.velocity_km_s),
        }


@dataclass(frozen=True)
class PropagationResult:
    tle: TLE
    backend: PropagationBackend
    frame: Frame
    samples: Tuple[PropagationSample, ...]

    @property
    def start(self) -> datetime:
        return self.samples[0].timestamp

    @property
    def end(self) -> datetime:
        return self.samples[-1].timestamp

    @property
    def step(self) -> timedelta:
        if len(self.samples) < 2:
            return timedelta(0)
        return self.samples[1].timestamp - self.samples[0].timestamp

    def as_dict(self) -> dict:
        return {
            "norad_id": self.tle.norad_id,
            "backend": self.backend.value,
            "frame": self.frame.value,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "step_seconds": self.step.total_seconds(),
            "samples": [sample.as_dict() for sample in self.samples],
        }


class PropagationError(RuntimeError):
    pass


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return dt.astimezone(timezone.utc)


def _iter_times(start: datetime, end: datetime, step: timedelta) -> Iterable[datetime]:
    current = start
    while current <= end + timedelta(microseconds=1):
        yield current
        current += step


def _sgp4_python(sat: Satrec, jd: float, fr: float) -> StateVector:
    error, position, velocity = sat.sgp4(jd, fr)
    if error != 0:
        message = SGP4_ERRORS.get(error, f"SGP4 error code {error}")
        raise PropagationError(message)
    return StateVector(tuple(position), tuple(velocity))


def _sgp4_rust(sat: Satrec, jd: float, fr: float) -> StateVector:
    return _sgp4_python(sat, jd, fr)


def propagate(
    tle: TLE,
    *,
    start: datetime,
    end: datetime,
    step: timedelta,
    frame: Frame = Frame.ECI,
    backend: PropagationBackend = PropagationBackend.PYTHON,
) -> PropagationResult:
    start_utc = _ensure_utc(start)
    end_utc = _ensure_utc(end)
    if end_utc < start_utc:
        raise ValueError("end must not be before start")
    if step.total_seconds() <= 0:
        raise ValueError("step must be positive")

    sat = Satrec.twoline2rv(tle.line1, tle.line2)
    samples: List[PropagationSample] = []

    for ts in _iter_times(start_utc, end_utc, step):
        jd, fr = jday(ts.year, ts.month, ts.day, ts.hour, ts.minute,
                      ts.second + ts.microsecond / 1_000_000)
        if backend == PropagationBackend.PYTHON:
            state = _sgp4_python(sat, jd, fr)
        elif backend == PropagationBackend.RUST:
            state = _sgp4_rust(sat, jd, fr)
        else:  # pragma: no cover
            raise PropagationError(f"Unsupported backend {backend}")
        converted = transform_state(state, ts, Frame.TEME, frame)
        samples.append(PropagationSample(ts, converted))

    return PropagationResult(tle=tle, backend=backend, frame=frame,
                             samples=tuple(samples))


__all__ = [
    "PropagationBackend",
    "PropagationError",
    "PropagationResult",
    "PropagationSample",
    "propagate",
]
