"""Smoke tests for the :mod:`tle_fetcher.cli` entrypoints."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tle_fetcher.cli import bootstrap_cli, legacy


def test_bootstrap_cli_executes_with_stubbed_fetch(monkeypatch) -> None:
    calls: Dict[str, str] = {}

    def fake_fetch(norad_id: str, **_: object) -> legacy.TLE:
        calls["norad_id"] = norad_id
        return legacy.TLE(
            norad_id=norad_id,
            name="ISS (ZARYA)",
            line1="1 25544U 98067A   20338.91667824  .00001264  00000-0  29671-4 0  9993",
            line2="2 25544  51.6443 139.1843 0001367  82.0849  21.6946 15.48965419256344",
            source="stub",
        )

    monkeypatch.setattr(legacy, "fetch_with_fallback", fake_fetch)

    exit_code = bootstrap_cli(["25544"])

    assert exit_code == 0
    assert calls["norad_id"] == "25544"
