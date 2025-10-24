from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from propagate.frames import Frame
from propagate.service import PropagationBackend, propagate
from tle_fetcher.fetcher import TLE

FIXTURE_PATH = Path(__file__).with_name("golden_cases.json")


@pytest.fixture(scope="module")
def golden_cases():
    data = json.loads(FIXTURE_PATH.read_text())
    tle_info = data["tle"]
    tle = TLE(
        tle_info["norad_id"],
        tle_info.get("name"),
        tle_info["line1"],
        tle_info["line2"],
        tle_info.get("source", "fixture"),
    )
    return tle, data["cases"]


def parse_datetime(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError("fixture datetimes must be timezone aware")
    return dt


def parse_step(seconds: float) -> timedelta:
    return timedelta(seconds=seconds)


def approx_tuple(values, expected, rel=1e-9, abs=1e-9):
    return all(pytest.approx(e, rel=rel, abs=abs) == v for v, e in zip(values, expected))


def test_golden_cases(golden_cases):
    tle, cases = golden_cases
    for case in cases:
        frame = Frame.from_string(case["frame"])
        start = parse_datetime(case["start"])
        end = parse_datetime(case["end"])
        step = parse_step(case["step_seconds"])
        expected = case["expected"]
        for backend_name, samples in expected.items():
            backend = PropagationBackend.from_string(backend_name)
            result = propagate(
                tle,
                start=start,
                end=end,
                step=step,
                frame=frame,
                backend=backend,
            )
            assert len(result.samples) == len(samples)
            for actual, expected_sample in zip(result.samples, samples):
                assert actual.timestamp.isoformat() == expected_sample["timestamp"]
                assert approx_tuple(actual.state.position_km, expected_sample["position_km"])
                assert approx_tuple(actual.state.velocity_km_s, expected_sample["velocity_km_s"])


def test_python_matches_rust(golden_cases):
    tle, cases = golden_cases
    for case in cases:
        frame = Frame.from_string(case["frame"])
        start = parse_datetime(case["start"])
        end = parse_datetime(case["end"])
        step = parse_step(case["step_seconds"])
        res_py = propagate(
            tle,
            start=start,
            end=end,
            step=step,
            frame=frame,
            backend=PropagationBackend.PYTHON,
        )
        res_rs = propagate(
            tle,
            start=start,
            end=end,
            step=step,
            frame=frame,
            backend=PropagationBackend.RUST,
        )
        assert len(res_py.samples) == len(res_rs.samples)
        for sample_py, sample_rs in zip(res_py.samples, res_rs.samples):
            assert sample_py.timestamp == sample_rs.timestamp
            assert approx_tuple(sample_py.state.position_km, sample_rs.state.position_km)
            assert approx_tuple(sample_py.state.velocity_km_s, sample_rs.state.velocity_km_s)
