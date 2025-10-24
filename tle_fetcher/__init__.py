#!/usr/bin/env python3
"""
Robust TLE fetcher with multi-source fallback, validation, caching, and CLI.

Sources supported (in configurable priority order):
  - celestrak   : https://celestrak.org/NORAD/elements/gp.php?CATNR={id}&FORMAT=tle
  - spacetrack  : https://www.space-track.org (requires credentials)
  - ivan        : https://tle.ivanstanojevic.me/satellite/{id}
  - n2yo        : https://api.n2yo.com/rest/v1/satellite/tle/{id}&apiKey=...

Environment variables (optional):
  SPACETRACK_USER, SPACETRACK_PASS
  N2YO_API_KEY

References:
  - TLE format & checksum: CelesTrak NORAD TLE spec
  - CelesTrak GP API usage: Skyfield docs
  - Space-Track GP API + Alpha-5: Space-Track documentation
  - N2YO TLE endpoint: N2YO API docs
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import io
import json
import os
import random
import time
import urllib.parse
import urllib.request
from typing import Dict, Iterable, List, Optional, Tuple

# ------------------------------- Utilities -------------------------------- #

USER_AGENT = "TLE-Fetcher/2.0 (+https://example.local) Python-urllib"
DEFAULT_TIMEOUT = 10.0
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 0.8  # seconds (exponential with jitter)
CACHE_TTL_SECS = 2 * 60 * 60  # 2 hours
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "tle-fetcher")


def configure_cache_dir(path: str) -> None:
    """Override the global cache directory used for on-disk TLE storage."""

    global CACHE_DIR
    CACHE_DIR = os.path.abspath(os.path.expanduser(path))

@dataclasses.dataclass(frozen=True)
class TLE:
    norad_id: str
    name: Optional[str]
    line1: str
    line2: str
    source: str  # 'celestrak' | 'spacetrack' | 'ivan' | 'n2yo'

    def as_text(self, three_line: bool = True) -> str:
        if three_line and self.name:
            return f"{self.name}\n{self.line1}\n{self.line2}\n"
        return f"{self.line1}\n{self.line2}\n"

def http_get(url: str, timeout: float = DEFAULT_TIMEOUT, retries: int = DEFAULT_RETRIES,
             backoff: float = DEFAULT_BACKOFF, headers: Optional[Dict[str, str]] = None) -> bytes:
    """GET with simple exponential backoff + jitter and explicit timeout."""
    headers = dict(headers or {})
    headers.setdefault("User-Agent", USER_AGENT)
    req = urllib.request.Request(url, headers=headers, method="GET")

    attempt = 0
    last_exc = None
    while attempt <= retries:
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = getattr(resp, "status", None) or resp.getcode()
                if status != 200:
                    raise urllib.error.HTTPError(url, status, f"HTTP {status}", hdrs=resp.headers, fp=None)
                return resp.read()
        except Exception as e:  # urllib can raise URLError or HTTPError
            last_exc = e
            if attempt == retries:
                break
            sleep = (backoff * (2 ** attempt)) + random.uniform(0, 0.125)
            time.sleep(sleep)
            attempt += 1
    raise last_exc  # type: ignore[misc]

# ------------------------------ Validation --------------------------------- #

def tle_checksum_ok(line: str) -> bool:
    """Validate checksum per CelesTrak spec: sum of digits + count('-') mod 10 equals last char."""
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
        elif ch == '-':
            total += 1
    return (total % 10) == expected

def _catnum_field(line: str) -> str:
    # Columns 3-7 (1-based) are catnum; tolerate Alpha-5 A–Z per Space-Track.
    # Zero-based slice indices: [2:7)
    return line[2:7].strip()

def parse_tle_text(norad_id: str, text: str, source: str) -> TLE:
    """Extract (optional) name + two lines; tolerate 2-line and 3-line input."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        raise ValueError("Empty TLE payload")
    # Pick the first pair of lines that start with '1' and '2'
    name: Optional[str] = None
    line1 = line2 = None  # type: ignore[assignment]
    for i in range(len(lines)):
        if lines[i].startswith("1 ") and i + 1 < len(lines) and lines[i + 1].startswith("2 "):
            # If a name precedes line1, capture it.
            if i - 1 >= 0 and not lines[i - 1].startswith(("1 ", "2 ")):
                name = lines[i - 1]
            line1, line2 = lines[i], lines[i + 1]
            break
    if line1 is None or line2 is None:
        # try Ivan's JSON style with explicit keys
        try:
            data = json.loads(text)
            # Ivan API returns a dict with 'line1','line2' (and 'name')
            if isinstance(data, dict) and "line1" in data and "line2" in data:
                name = data.get("name")
                line1, line2 = data["line1"], data["line2"]
            else:
                raise ValueError
        except Exception:
            raise ValueError("Could not locate TLE line pair in response")

    # Basic structural checks
    if not (line1.startswith("1 ") and line2.startswith("2 ")):
        raise ValueError("Bad TLE line prefixes")
    if not tle_checksum_ok(line1) or not tle_checksum_ok(line2):
        raise ValueError("Checksum failed")
    if _catnum_field(line1) != _catnum_field(line2):
        raise ValueError("Catalog numbers differ between L1 and L2")

    # If caller supplied NORAD ID, try to assert it matches (best-effort; Alpha-5 may differ)
    try:
        if norad_id and norad_id.isdigit():
            # catnum may be padded; compare numeric prefix (ignore Alpha-5)
            if _catnum_field(line1).replace(" ", "").isdigit():
                if int(_catnum_field(line1)) != int(norad_id):
                    raise ValueError("Catalog number does not match requested NORAD ID")
    except ValueError:
        # If Alpha-5 is present we can skip strict numeric match; validation above suffices.
        pass

    return TLE(norad_id=norad_id, name=name, line1=line1, line2=line2, source=source)

def tle_epoch(line1: str) -> dt.datetime:
    """Parse epoch from line 1: YY + day-of-year.fraction → UTC datetime."""
    # Columns 19-20: year (2-digit); 21-32: day-of-year with fraction (1-based indices)
    year2 = int(line1[18:20])
    doy = float(line1[20:32])
    year = 1900 + year2 if year2 >= 57 else 2000 + year2  # per spec
    day_int = int(doy)
    frac = doy - day_int
    base = dt.datetime(year, 1, 1, tzinfo=dt.timezone.utc) + dt.timedelta(days=day_int - 1)
    return base + dt.timedelta(seconds=frac * 86400.0)

# ------------------------------ Cache layer -------------------------------- #

def cache_path(norad_id: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{norad_id}.tle")

def read_cache(norad_id: str, max_age_secs: int) -> Optional[TLE]:
    path = cache_path(norad_id)
    try:
        st = os.stat(path)
        if (time.time() - st.st_mtime) > max_age_secs:
            return None
        with open(path, "r", encoding="utf-8") as f:
            txt = f.read()
        tle = parse_tle_text(norad_id, txt, source="cache")
        return dataclasses.replace(tle, source="cache")
    except Exception:
        return None

def write_cache(tle: TLE) -> None:
    path = cache_path(tle.norad_id)
    with open(path, "w", encoding="utf-8") as f:
        f.write(tle.as_text(three_line=True))

# --------------------------- Source implementations ------------------------ #

def fetch_celestrak(norad_id: str, **http_opts) -> TLE:
    url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={urllib.parse.quote(norad_id)}&FORMAT=tle"
    payload = http_get(url, **http_opts).decode("utf-8", errors="replace")
    return parse_tle_text(norad_id, payload, source="celestrak")

def fetch_ivan(norad_id: str, **http_opts) -> TLE:
    url = f"https://tle.ivanstanojevic.me/satellite/{urllib.parse.quote(norad_id)}"
    payload = http_get(url, **http_opts).decode("utf-8", errors="replace")
    return parse_tle_text(norad_id, payload, source="ivan")

def fetch_n2yo(norad_id: str, **http_opts) -> TLE:
    api_key = os.getenv("N2YO_API_KEY")
    if not api_key:
        raise RuntimeError("N2YO_API_KEY not set")
    url = f"https://api.n2yo.com/rest/v1/satellite/tle/{urllib.parse.quote(norad_id)}&apiKey={urllib.parse.quote(api_key)}"
    payload = http_get(url, **http_opts).decode("utf-8", errors="replace")
    # Response JSON with "tle": "line1\r\nline2"
    data = json.loads(payload)
    tle_text = data.get("tle")
    if not tle_text:
        raise ValueError("N2YO: 'tle' not present in response")
    # Ensure we have \n line endings
    tle_text = tle_text.replace("\r\n", "\n")
    return parse_tle_text(norad_id, tle_text, source="n2yo")

def fetch_spacetrack(norad_id: str, **http_opts) -> TLE:
    user = os.getenv("SPACETRACK_USER")
    pw = os.getenv("SPACETRACK_PASS")
    if not user or not pw:
        raise RuntimeError("SPACETRACK_USER/PASS not set")
    # Use "single POST" login+query method to avoid cookie handling.
    # Query: latest GP in TLE format for this NORAD ID.
    query_url = f"https://www.space-track.org/basicspacedata/query/class/gp/NORAD_CAT_ID/{urllib.parse.quote(norad_id)}/orderby/EPOCH%20desc/limit/1/format/tle"
    post_data = urllib.parse.urlencode({
        "identity": user,
        "password": pw,
        "query": query_url,
    }).encode("ascii")
    req = urllib.request.Request("https://www.space-track.org/ajaxauth/login",
                                 data=post_data,
                                 headers={"User-Agent": USER_AGENT},
                                 method="POST")
    attempt = 0
    last_exc = None
    retries = http_opts.get("retries", DEFAULT_RETRIES)
    backoff = http_opts.get("backoff", DEFAULT_BACKOFF)
    timeout = http_opts.get("timeout", DEFAULT_TIMEOUT)

    while attempt <= retries:
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if (resp.status or resp.getcode()) != 200:
                    raise urllib.error.HTTPError(req.full_url, resp.getcode(), "Space-Track login failed", hdrs=resp.headers, fp=None)
                payload = resp.read().decode("utf-8", errors="replace")
                # Space-Track returns TLE directly on success; errors are in JSON or HTML.
                if "Login failed" in payload or payload.strip().startswith("{"):
                    raise ValueError("Space-Track auth or query error")
                return parse_tle_text(norad_id, payload, source="spacetrack")
        except Exception as e:
            last_exc = e
            if attempt == retries:
                break
            time.sleep((backoff * (2 ** attempt)) + random.uniform(0, 0.125))
            attempt += 1
    raise last_exc  # type: ignore[misc]

SOURCE_FUNCS = {
    "spacetrack": fetch_spacetrack,
    "celestrak": fetch_celestrak,
    "ivan": fetch_ivan,
    "n2yo": fetch_n2yo,
}

# ------------------------------ Orchestration ------------------------------ #

def fetch_with_fallback(norad_id: str, sources: List[str],
                        timeout: float, retries: int, backoff: float,
                        cache_ttl: int, verify_with: int = 0) -> TLE:
    # 1) cache
    cached = read_cache(norad_id, cache_ttl)
    if cached:
        return cached

    http_opts = {"timeout": timeout, "retries": retries, "backoff": backoff}
    errors: Dict[str, str] = {}
    got: List[TLE] = []

    for src in sources:
        func = SOURCE_FUNCS.get(src)
        if not func:
            continue
        try:
            tle = func(norad_id, **http_opts)
            got.append(tle)
            # cross-verify by sampling additional sources if requested
            if verify_with > 0:
                others = [s for s in sources if s != src]
                for s in others:
                    if len(got) >= (1 + verify_with):
                        break
                    try:
                        t2 = SOURCE_FUNCS[s](norad_id, **http_opts)
                        got.append(t2)
                    except Exception:
                        pass
            break
        except Exception as e:
            errors[src] = f"{e.__class__.__name__}: {e}"

    if not got:
        msgs = " | ".join(f"{k} -> {v}" for k, v in errors.items()) or "no sources attempted"
        raise RuntimeError(f"All sources failed: {msgs}")

    # Choose the most recent epoch among gathered TLEs (protects against stale mirrors)
    latest = max(got, key=lambda t: tle_epoch(t.line1))
    write_cache(latest)
    return latest

# --------------------------------- CLI ------------------------------------ #

def format_output_path(pattern: str, tle: TLE) -> str:
    if pattern == "-":
        return "-"
    try:
        epoch = tle_epoch(tle.line1)
        name = (tle.name or "").replace("/", "-").replace(" ", "_")
        return pattern.format(id=tle.norad_id, name=name, epoch=epoch)
    except Exception:
        return pattern

def save_tle(tle: TLE, path: str, three_line: bool) -> None:
    txt = tle.as_text(three_line=three_line)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)

# The CLI implementation lives in :mod:`tle_fetcher.cli`. The legacy module
# retained these helper utilities for external callers.
