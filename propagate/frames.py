"""Reference frame transformations for propagation outputs."""
from __future__ import annotations

import enum
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Tuple

from sgp4.api import jday

EARTH_ROT_RATE_RAD_PER_SEC = 7.2921150e-5


class Frame(str, enum.Enum):
    """Supported coordinate frames."""

    TEME = "teme"
    ECI = "eci"  # Alias for TEME for backward compatibility
    ECEF = "ecef"

    @classmethod
    def from_string(cls, value: str) -> "Frame":
        try:
            return cls(value.lower())
        except Exception as exc:  # pragma: no cover - defensive
            raise ValueError(f"Unsupported frame '{value}'") from exc


@dataclass(frozen=True)
class StateVector:
    """Position and velocity state vector (kilometres / kilometres per second)."""

    position_km: Tuple[float, float, float]
    velocity_km_s: Tuple[float, float, float]


Position = Tuple[float, float, float]
Velocity = Tuple[float, float, float]


def _gmst(dt: datetime) -> float:
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    jd, fr = jday(dt.year, dt.month, dt.day, dt.hour, dt.minute,
                  dt.second + dt.microsecond / 1_000_000)
    jd_ut1 = jd + fr
    t = (jd_ut1 - 2451545.0) / 36525.0
    gmst_sec = (
        67310.54841
        + (876600.0 * 3600 + 8640184.812866) * t
        + 0.093104 * t * t
        - 6.2e-6 * t * t * t
    )
    gmst_sec = gmst_sec % 86400.0
    if gmst_sec < 0:
        gmst_sec += 86400.0
    return math.radians(gmst_sec / 240.0)


def teme_to_ecef(state: StateVector, when: datetime) -> StateVector:
    theta = _gmst(when)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)

    x, y, z = state.position_km
    vx, vy, vz = state.velocity_km_s

    x_ecef = cos_t * x + sin_t * y
    y_ecef = -sin_t * x + cos_t * y
    z_ecef = z

    vx_rot = cos_t * vx + sin_t * vy
    vy_rot = -sin_t * vx + cos_t * vy
    vz_rot = vz

    omega = EARTH_ROT_RATE_RAD_PER_SEC
    vx_ecef = vx_rot + omega * y_ecef
    vy_ecef = vy_rot - omega * x_ecef
    vz_ecef = vz_rot

    return StateVector((x_ecef, y_ecef, z_ecef), (vx_ecef, vy_ecef, vz_ecef))


def ecef_to_teme(state: StateVector, when: datetime) -> StateVector:
    theta = _gmst(when)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)

    x, y, z = state.position_km
    vx, vy, vz = state.velocity_km_s

    x_teme = cos_t * x - sin_t * y
    y_teme = sin_t * x + cos_t * y
    z_teme = z

    omega = EARTH_ROT_RATE_RAD_PER_SEC
    vx_adj = vx - omega * y
    vy_adj = vy + omega * x

    vx_teme = cos_t * vx_adj - sin_t * vy_adj
    vy_teme = sin_t * vx_adj + cos_t * vy_adj
    vz_teme = vz

    return StateVector((x_teme, y_teme, z_teme), (vx_teme, vy_teme, vz_teme))


def transform_state(state: StateVector, when: datetime, source: Frame, target: Frame) -> StateVector:
    if source == target:
        return state
    if source in {Frame.TEME, Frame.ECI} and target == Frame.ECEF:
        return teme_to_ecef(state, when)
    if source == Frame.ECEF and target in {Frame.TEME, Frame.ECI}:
        return ecef_to_teme(state, when)
    if source == Frame.ECI and target == Frame.TEME:
        return state
    if source == Frame.TEME and target == Frame.ECI:
        return state
    raise ValueError(f"Unsupported transformation from {source.value} to {target.value}")


__all__ = [
    "Frame",
    "Position",
    "Velocity",
    "StateVector",
    "teme_to_ecef",
    "ecef_to_teme",
    "transform_state",
]
