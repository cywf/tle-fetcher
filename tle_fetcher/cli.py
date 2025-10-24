"""Command line interface for the TLE fetcher utility."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .core import TLE, epoch, parse

USER_AGENT = "TLE-Fetcher/2.0 (+https://example.local) Python-urllib"
DEFAULT_TIMEOUT = 10.0
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 0.8  # seconds (exponential with jitter)
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "tle-fetcher")
CACHE_TTL_SECS = 2 * 60 * 60  # 2 hours


# ------------------------------- Utilities -------------------------------- #

def http_get(
    url: str,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    backoff: float = DEFAULT_BACKOFF,
    headers: Optional[Dict[str, str]] = None,
) -> bytes:
    """GET with simple exponential backoff + jitter and explicit timeout."""

    hdrs = dict(headers or {})
    hdrs.setdefault("User-Agent", USER_AGENT)
    req = urllib.request.Request(url, headers=hdrs, method="GET")

    attempt = 0
    last_exc: Optional[Exception] = None
    while attempt <= retries:
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = getattr(resp, "status", None) or resp.getcode()
                if status != 200:
                    raise urllib.error.HTTPError(url, status, f"HTTP {status}", hdrs=resp.headers, fp=None)
                return resp.read()
        except Exception as exc:  # urllib can raise URLError or HTTPError
            last_exc = exc
            if attempt == retries:
                break
            sleep = (backoff * (2 ** attempt)) + random.uniform(0, 0.125)
            time.sleep(sleep)
            attempt += 1
    if last_exc is None:
        raise RuntimeError("HTTP request failed without exception")
    raise last_exc


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
        tle = parse(txt, norad_id=norad_id, source="cache")
        return TLE(
            norad_id=tle.norad_id,
            name=tle.name,
            line1=tle.line1,
            line2=tle.line2,
            source="cache",
        )
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
    return parse(payload, norad_id=norad_id, source="celestrak")


def fetch_ivan(norad_id: str, **http_opts) -> TLE:
    url = f"https://tle.ivanstanojevic.me/satellite/{urllib.parse.quote(norad_id)}"
    payload = http_get(url, **http_opts).decode("utf-8", errors="replace")
    return parse(payload, norad_id=norad_id, source="ivan")


def fetch_n2yo(norad_id: str, **http_opts) -> TLE:
    api_key = os.getenv("N2YO_API_KEY")
    if not api_key:
        raise RuntimeError("N2YO_API_KEY not set")
    url = (
        "https://api.n2yo.com/rest/v1/satellite/tle/"
        f"{urllib.parse.quote(norad_id)}&apiKey={urllib.parse.quote(api_key)}"
    )
    payload = http_get(url, **http_opts).decode("utf-8", errors="replace")
    data = json.loads(payload)
    tle_text = data.get("tle")
    if not tle_text:
        raise ValueError("N2YO: 'tle' not present in response")
    tle_text = str(tle_text).replace("\r\n", "\n")
    return parse(tle_text, norad_id=norad_id, source="n2yo")


def fetch_spacetrack(norad_id: str, **http_opts) -> TLE:
    user = os.getenv("SPACETRACK_USER")
    pw = os.getenv("SPACETRACK_PASS")
    if not user or not pw:
        raise RuntimeError("SPACETRACK_USER/PASS not set")
    query_url = (
        "https://www.space-track.org/basicspacedata/query/class/gp/NORAD_CAT_ID/"
        f"{urllib.parse.quote(norad_id)}/orderby/EPOCH%20desc/limit/1/format/tle"
    )
    post_data = urllib.parse.urlencode(
        {"identity": user, "password": pw, "query": query_url}
    ).encode("ascii")
    req = urllib.request.Request(
        "https://www.space-track.org/ajaxauth/login",
        data=post_data,
        headers={"User-Agent": USER_AGENT},
        method="POST",
    )
    attempt = 0
    last_exc: Optional[Exception] = None
    retries = http_opts.get("retries", DEFAULT_RETRIES)
    backoff = http_opts.get("backoff", DEFAULT_BACKOFF)
    timeout = http_opts.get("timeout", DEFAULT_TIMEOUT)

    while attempt <= retries:
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = getattr(resp, "status", None) or resp.getcode()
                if status != 200:
                    raise urllib.error.HTTPError(
                        req.full_url,
                        resp.getcode(),
                        "Space-Track login failed",
                        hdrs=resp.headers,
                        fp=None,
                    )
                payload = resp.read().decode("utf-8", errors="replace")
                if "Login failed" in payload or payload.strip().startswith("{"):
                    raise ValueError("Space-Track auth or query error")
                return parse(payload, norad_id=norad_id, source="spacetrack")
        except Exception as exc:
            last_exc = exc
            if attempt == retries:
                break
            time.sleep((backoff * (2 ** attempt)) + random.uniform(0, 0.125))
            attempt += 1
    if last_exc is None:
        raise RuntimeError("Space-Track request failed")
    raise last_exc


SOURCE_FUNCS = {
    "spacetrack": fetch_spacetrack,
    "celestrak": fetch_celestrak,
    "ivan": fetch_ivan,
    "n2yo": fetch_n2yo,
}


# ------------------------------ Orchestration ------------------------------ #

def fetch_with_fallback(
    norad_id: str,
    sources: Iterable[str],
    timeout: float,
    retries: int,
    backoff: float,
    cache_ttl: int,
    verify_with: int = 0,
) -> TLE:
    cached = read_cache(norad_id, cache_ttl)
    if cached:
        return cached

    http_opts = {"timeout": timeout, "retries": retries, "backoff": backoff}
    errors: Dict[str, str] = {}
    got: List[TLE] = []

    source_list = list(sources)
    for src in source_list:
        func = SOURCE_FUNCS.get(src)
        if not func:
            continue
        try:
            tle = func(norad_id, **http_opts)
            got.append(tle)
            if verify_with > 0:
                others = [s for s in source_list if s != src]
                for other in others:
                    if len(got) >= (1 + verify_with):
                        break
                    other_func = SOURCE_FUNCS.get(other)
                    if not other_func:
                        continue
                    try:
                        got.append(other_func(norad_id, **http_opts))
                    except Exception:
                        pass
            break
        except Exception as exc:
            errors[src] = f"{exc.__class__.__name__}: {exc}"

    if not got:
        msgs = " | ".join(f"{k} -> {v}" for k, v in errors.items()) or "no sources attempted"
        raise RuntimeError(f"All sources failed: {msgs}")

    latest = max(got, key=lambda t: epoch(t.line1))
    write_cache(latest)
    return latest


# --------------------------------- CLI ------------------------------------ #

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reliable TLE fetcher with multi-source fallback."
    )
    parser.add_argument("ids", nargs="*", help="NORAD catalog IDs (one or more).")
    parser.add_argument(
        "--source-order",
        default="spacetrack,celestrak,ivan,n2yo",
        help="Comma-separated source priority.",
    )
    parser.add_argument(
        "--ids-file",
        "-f",
        help="Path to file with NORAD IDs (one per line, '#' comments allowed).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="HTTP timeout (seconds).",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help="HTTP retries per source.",
    )
    parser.add_argument(
        "--backoff",
        type=float,
        default=DEFAULT_BACKOFF,
        help="Base backoff (seconds).",
    )
    parser.add_argument(
        "--cache-ttl",
        type=int,
        default=CACHE_TTL_SECS,
        help="Cache TTL in seconds.",
    )
    parser.add_argument(
        "--verify",
        type=int,
        default=0,
        help="Fetch from up to N additional sources to cross-verify (0=off).",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="-",
        help=(
            "Output path or pattern. Use '-' for stdout. Pattern supports "
            "{id}, {name}, {epoch:%%Y%%m%%d%%H%%M%%S}."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON to stdout.",
    )
    parser.add_argument(
        "--no-name",
        action="store_true",
        help="Save as 2-line TLE (omit name line).",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress extra logs.",
    )
    return parser.parse_args(argv)


def format_output_path(pattern: str, tle: TLE) -> str:
    if pattern == "-":
        return "-"
    try:
        ep = epoch(tle.line1)
        name = (tle.name or "").replace("/", "-").replace(" ", "_")
        return pattern.format(id=tle.norad_id, name=name, epoch=ep)
    except Exception:
        return pattern


def save_tle(tle: TLE, path: str, three_line: bool) -> None:
    txt = tle.as_text(three_line=three_line)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)


def _load_ids_from_file(path: Path) -> List[str]:
    loaded: List[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            loaded.append(line)
    return loaded


def run_cli(ns: argparse.Namespace) -> int:
    if ns.ids_file:
        p = Path(ns.ids_file)
        if not p.exists():
            print(f"IDs file not found: {p}", file=sys.stderr)
            return 2
        ns.ids = list(dict.fromkeys([*ns.ids, *_load_ids_from_file(p)]))

    if not ns.ids:
        print("TLE Fetcher Utility (robust)")
        print("Enter a NORAD catalog ID (or 'q' to quit):")
        while True:
            user_input = input("> ").strip()
            if user_input.lower() in {"q", "quit", "exit"}:
                return 0
            if not user_input.isdigit():
                print("Please enter a numeric NORAD catalog ID.")
                continue
            ns.ids = [user_input]
            break

    sources = [s.strip().lower() for s in ns.source_order.split(",") if s.strip()]
    if not sources:
        sources = ["spacetrack", "celestrak", "ivan", "n2yo"]

    exit_code = 0
    for sat_id in ns.ids:
        try:
            tle = fetch_with_fallback(
                sat_id,
                sources=sources,
                timeout=ns.timeout,
                retries=ns.retries,
                backoff=ns.backoff,
                cache_ttl=ns.cache_ttl,
                verify_with=ns.verify,
            )
            if ns.json:
                payload = {
                    "id": tle.norad_id,
                    "name": tle.name,
                    "line1": tle.line1,
                    "line2": tle.line2,
                    "source": tle.source,
                    "epoch": epoch(tle.line1).isoformat(),
                }
                print(json.dumps(payload, ensure_ascii=False))
            else:
                if not ns.quiet:
                    ep = epoch(tle.line1).strftime("%Y-%m-%d %H:%M:%S UTC")
                    print(f"\n[{tle.source}] {tle.name or ''} (NORAD {tle.norad_id}) epoch {ep}")
                print(tle.as_text(three_line=not ns.no_name), end="")
            out_path = format_output_path(ns.output, tle)
            if out_path != "-":
                save_tle(tle, out_path, three_line=not ns.no_name)
                if not ns.quiet:
                    print(f"Saved -> {out_path}")
        except Exception as exc:
            exit_code = 2
            print(f"ERROR[{sat_id}]: {exc}", file=sys.stderr)
    return exit_code


def main() -> None:
    ns = parse_args()
    sys.exit(run_cli(ns))


if __name__ == "__main__":
    main()
