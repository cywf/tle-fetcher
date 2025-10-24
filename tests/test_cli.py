from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "tle_fetcher.py"), *args],
        cwd=cwd or REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _finalize_tle_line(line: str) -> str:
    body = line[:-1]
    total = 0
    for ch in body:
        if ch.isdigit():
            total += int(ch)
        elif ch == "-":
            total += 1
    return body + str(total % 10)


def _write_tle(db_path: Path, norad_id: str, epoch: str, name: str) -> None:
    line1 = _finalize_tle_line(
        f"1 {norad_id}U 58002B   {epoch}  .00000000  00000-0  00000-0 0  9990"
    )
    line2 = _finalize_tle_line(
        f"2 {norad_id}  34.2682 348.7242 1859667 331.7664  19.3264 10.82419157413660"
    )
    payload = f"{name}\n{line1}\n{line2}\n"
    (db_path / f"{norad_id}.tle").write_text(payload, encoding="utf-8")


def test_help_snapshot() -> None:
    result = _run_cli("--help")
    assert result.returncode == 0, result.stderr
    output = result.stdout.replace(str(Path.home()), "<HOME>")
    expected_lines = [
        "usage: tle_fetcher.py [-h] [--mode {fetch,report}] [--log-level {CRITICAL,DEBUG,ERROR,INFO,WARNING}] [--db-path DB_PATH]",
        "                      [--ids-file IDS_FILE] [--source-order SOURCE_ORDER] [--timeout TIMEOUT] [--retries RETRIES]",
        "                      [--backoff BACKOFF] [--cache-ttl CACHE_TTL] [--verify VERIFY] [--output OUTPUT] [--json] [--no-name]",
        "                      [--quiet] [--report [DEST]]",
        "                      [ids ...]",
        "",
        "Reliable TLE fetcher with multi-source fallback.",
        "",
        "positional arguments:",
        "  ids                   NORAD catalog IDs (one or more). (default: None)",
        "",
        "options:",
        "  -h, --help            show this help message and exit",
        "  --mode {fetch,report}",
        "                        Select CLI mode. 'fetch' performs network retrievals, 'report' summarises cached data. (default:",
        "                        fetch)",
        "  --log-level {CRITICAL,DEBUG,ERROR,INFO,WARNING}",
        "                        Logging verbosity (default: INFO). (default: INFO)",
        "  --db-path DB_PATH     Directory containing cached TLE files and generated reports. (default: <HOME>/.cache/tle-fetcher)",
        "  --ids-file IDS_FILE, -f IDS_FILE",
        "                        Path to file with NORAD IDs (one per line, '#' comments allowed). (default: None)",
        "  --source-order SOURCE_ORDER",
        "                        Comma-separated source priority. (default: spacetrack,celestrak,ivan,n2yo)",
        "  --timeout TIMEOUT     HTTP timeout (seconds). (default: 10.0)",
        "  --retries RETRIES     HTTP retries per source. (default: 3)",
        "  --backoff BACKOFF     Base backoff (seconds). (default: 0.8)",
        "  --cache-ttl CACHE_TTL",
        "                        Cache TTL in seconds. (default: 7200)",
        "  --verify VERIFY       Fetch from up to N additional sources to cross-verify (0=off). (default: 0)",
        "  --output OUTPUT, -o OUTPUT",
        "                        Output path or pattern. Use '-' for stdout. Pattern supports {id}, {name}, {epoch:%Y%m%d%H%M%S}.",
        "                        (default: -)",
        "  --json                Emit machine-readable JSON to stdout. (default: False)",
        "  --no-name             Save as 2-line TLE (omit name line). (default: False)",
        "  --quiet, -q           Suppress extra logs. (default: False)",
        "  --report [DEST]       Emit a JSON summary of cached TLEs to DEST (default: stdout). (default: None)",
    ]
    expected = "\n".join(expected_lines) + "\n"
    assert output == expected


def test_report_snapshot(tmp_path: Path) -> None:
    db_path = tmp_path / "cache"
    db_path.mkdir()
    _write_tle(db_path, "00005", "20001.00000000", "VANGUARD 1")
    _write_tle(db_path, "12345", "20002.00000000", "TEST SAT")

    result = _run_cli("--mode", "report", "--db-path", str(db_path), "--report", "-")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    data["generated"] = "<generated>"
    normalised_entries = []
    for entry in data["entries"]:
        normalised = dict(entry)
        normalised["path"] = str(Path(entry["path"]).relative_to(db_path))
        normalised_entries.append(normalised)
    data["entries"] = normalised_entries
    canonical = json.dumps(data, indent=2, sort_keys=True)
    expected = textwrap.dedent(
        """
        {
          "count": 2,
          "entries": [
            {
              "epoch": "2020-01-01T00:00:00+00:00",
              "id": "00005",
              "name": "VANGUARD 1",
              "path": "00005.tle",
              "source": "cache"
            },
            {
              "epoch": "2020-01-02T00:00:00+00:00",
              "id": "12345",
              "name": "TEST SAT",
              "path": "12345.tle",
              "source": "cache"
            }
          ],
          "generated": "<generated>",
          "ids": [
            "00005",
            "12345"
          ],
          "latest_epoch": "2020-01-02T00:00:00+00:00",
          "sources": [
            "cache"
          ]
        }
        """
    ).strip()
    assert canonical == expected
