from __future__ import annotations

import datetime as dt

from hypothesis import given, strategies as st


SECONDS_PER_DAY = 86_400
MICROS_PER_DAY = SECONDS_PER_DAY * 1_000_000

from tle_fetcher.core import epoch

BASE_LINE1 = "1 25544U 98067A   20344.91719907  .00001264  00000-0  29621-4 0  9993"
PREFIX = BASE_LINE1[:18]
SUFFIX = BASE_LINE1[32:]


def build_line1(year: int, day: int, seconds: int, micros: int) -> str:
    total_micro = seconds * 1_000_000 + micros
    frac_scaled = round(total_micro * 100_000_000 / MICROS_PER_DAY)
    adj_day = day
    if frac_scaled >= 100_000_000:
        adj_day += 1
        frac_scaled -= 100_000_000
    epoch_field = f"{year % 100:02d}{adj_day:03d}.{frac_scaled:08d}"
    return f"{PREFIX}{epoch_field}{SUFFIX}"


@given(
    st.integers(min_value=1957, max_value=2056),
    st.integers(min_value=1, max_value=366),
    st.integers(min_value=0, max_value=86399),
    st.integers(min_value=0, max_value=999_999),
)
def test_epoch_matches_manual(year: int, day: int, seconds: int, micros: int) -> None:
    line1 = build_line1(year, day, seconds, micros)
    result = epoch(line1)
    expected_year = year
    expected = dt.datetime(expected_year, 1, 1, tzinfo=dt.timezone.utc) + dt.timedelta(
        days=day - 1, seconds=seconds, microseconds=micros
    )
    assert result.tzinfo is dt.timezone.utc
    assert result.year == expected_year
    delta = abs(result - expected)
    assert delta <= dt.timedelta(microseconds=900)
