from __future__ import annotations

import json

from hypothesis import given, strategies as st

from tle_fetcher.core import TLE, checksum, parse

BASE_NAME = "ISS (ZARYA)"
BASE_LINE1 = "1 25544U 98067A   20344.91719907  .00001264  00000-0  29621-4 0  9993"
BASE_LINE2 = "2 25544  51.6466 223.8666 0002416  90.3778  30.6140 15.48970462256430"


def _text_payload(include_name: bool, prefix_blanks: int, suffix_blanks: int, trailing_space: bool) -> str:
    lines = []
    lines.extend("" for _ in range(prefix_blanks))
    if include_name:
        lines.append(BASE_NAME + (" " if trailing_space else ""))
    lines.append(BASE_LINE1 + (" " if trailing_space else ""))
    lines.append(BASE_LINE2 + (" " if trailing_space else ""))
    lines.extend("" for _ in range(suffix_blanks))
    return "\n".join(lines)


@st.composite
def tle_payloads(draw) -> str:
    variant = draw(st.sampled_from(["text", "json"]))
    if variant == "json":
        payload = {"name": BASE_NAME, "line1": BASE_LINE1, "line2": BASE_LINE2}
        if draw(st.booleans()):
            payload["extra"] = "ignored"
        return json.dumps(payload)
    return _text_payload(
        include_name=draw(st.booleans()),
        prefix_blanks=draw(st.integers(min_value=0, max_value=3)),
        suffix_blanks=draw(st.integers(min_value=0, max_value=3)),
        trailing_space=draw(st.booleans()),
    )


@given(tle_payloads())
def test_parse_handles_noise(payload: str) -> None:
    tle = parse(payload, norad_id="25544", source="test")
    assert isinstance(tle, TLE)
    assert tle.norad_id == "25544"
    assert tle.line1.strip() == BASE_LINE1
    assert tle.line2.strip() == BASE_LINE2
    assert checksum(tle.line1)
    assert checksum(tle.line2)
    round_trip = parse(tle.as_text(), norad_id="25544", source="cache")
    assert round_trip.line1 == tle.line1
    assert round_trip.line2 == tle.line2
