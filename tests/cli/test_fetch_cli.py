import os
from pathlib import Path

from tle_fetcher.cli import fetch as fetch_cli


TLE_TEXT = """ISS (ZARYA)
1 25544U 98067A   24157.20856222  .00006411  00000+0  11842-3 0  9996
2 25544  51.6412 205.1217 0004225 113.2939 306.8174 15.50073703551595
"""


class StubClient:
    def __init__(self, payload: str):
        self.name = "stub"
        self.payload = payload
        self.calls = 0

    def fetch(self, norad_id: str) -> str:
        self.calls += 1
        return self.payload


def test_cli_respects_offline_mode_and_warns(monkeypatch, tmp_path, capsys):
    state_dir = tmp_path / "state"
    monkeypatch.setenv("TLE_FETCHER_STATE_DIR", str(state_dir))

    client = StubClient(TLE_TEXT)

    def fake_build(order):  # pragma: no cover - exercised via CLI
        return [client]

    monkeypatch.setattr(fetch_cli, "build_clients", fake_build)

    exit_code = fetch_cli.main(["--ids", "25544", "--source-order", "stub"])
    assert exit_code == 0
    out, err = capsys.readouterr()
    assert "ISS (ZARYA)" in out
    assert err == ""
    assert client.calls == 1

    monkeypatch.setenv("TLE_FETCHER_OFFLINE", "1")

    exit_code = fetch_cli.main(["--ids", "25544", "--cache-ttl", "0", "--source-order", "stub"])
    assert exit_code == 0
    out, err = capsys.readouterr()
    assert "ISS (ZARYA)" in out
    assert "warning" in err.lower()
    assert "offline" in err.lower()
    assert client.calls == 1  # offline run should not hit network

    monkeypatch.delenv("TLE_FETCHER_OFFLINE", raising=False)
    monkeypatch.delenv("TLE_FETCHER_STATE_DIR", raising=False)
