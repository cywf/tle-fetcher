"""HTTP source wrappers for retrieving TLE payloads."""
from __future__ import annotations

import dataclasses
import time
import urllib.error
import urllib.request
from typing import Callable, Dict, Iterable, List, Optional, Sequence

DEFAULT_USER_AGENT = "TLE-Fetcher/3.0 (+https://example.local)"
ATTRIBUTION_HEADER = "X-TLE-Attribution"
DEFAULT_TIMEOUT = 10.0


class SourceError(RuntimeError):
    """Raised when a source fails to deliver a TLE payload."""


@dataclasses.dataclass
class SourceClient:
    """Wraps a single HTTP TLE endpoint with rate limiting and attribution."""

    name: str
    url_template: str
    user_agent: str = DEFAULT_USER_AGENT
    attribution: Optional[str] = None
    rate_limit_seconds: float = 0.0
    timeout: float = DEFAULT_TIMEOUT
    extra_headers: Optional[Dict[str, str]] = None
    opener: Optional[Callable[[urllib.request.Request, float], bytes]] = None
    monotonic: Callable[[], float] = time.monotonic
    sleeper: Callable[[float], None] = time.sleep

    _last_request: float = dataclasses.field(default=0.0, init=False, repr=False)

    def _build_request(self, norad_id: str) -> urllib.request.Request:
        url = self.url_template.format(id=norad_id)
        headers = {"User-Agent": self.user_agent}
        headers[ATTRIBUTION_HEADER] = self.attribution or self.name
        if self.extra_headers:
            headers.update(self.extra_headers)
        return urllib.request.Request(url, headers=headers, method="GET")

    def _enforce_rate_limit(self) -> None:
        if self.rate_limit_seconds <= 0:
            return
        now = self.monotonic()
        elapsed = now - self._last_request
        delay = self.rate_limit_seconds - elapsed
        if delay > 0:
            self.sleeper(delay)
            now = self.monotonic()
        self._last_request = now

    def _default_opener(self, request: urllib.request.Request, timeout: float) -> bytes:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            status = getattr(resp, "status", None) or resp.getcode()
            if status != 200:
                raise SourceError(f"{self.name} returned HTTP {status}")
            return resp.read()

    def fetch(self, norad_id: str) -> str:
        """Retrieve a TLE payload for ``norad_id`` as UTF-8 text."""

        self._enforce_rate_limit()
        request = self._build_request(norad_id)
        opener = self.opener or self._default_opener
        try:
            payload = opener(request, self.timeout)
        except urllib.error.URLError as exc:  # pragma: no cover - exercised via SourceError
            raise SourceError(f"{self.name} network error: {exc}") from exc
        except Exception as exc:  # pragma: no cover - defensive
            raise SourceError(f"{self.name} unexpected error: {exc}") from exc
        return payload.decode("utf-8", errors="replace")


@dataclasses.dataclass
class SourceDefinition:
    name: str
    url_template: str
    attribution: Optional[str] = None
    rate_limit_seconds: float = 0.0
    extra_headers: Optional[Dict[str, str]] = None
    timeout: float = DEFAULT_TIMEOUT


AVAILABLE_SOURCES: Dict[str, SourceDefinition] = {
    "celestrak": SourceDefinition(
        name="celestrak",
        url_template="https://celestrak.org/NORAD/elements/gp.php?CATNR={id}&FORMAT=tle",
        attribution="celestrak.org",
        rate_limit_seconds=1.0,
    ),
    "ivan": SourceDefinition(
        name="ivan",
        url_template="https://tle.ivanstanojevic.me/api/tle/{id}",
        attribution="tle.ivanstanojevic.me",
        rate_limit_seconds=0.5,
    ),
    "spacetrack": SourceDefinition(
        name="spacetrack",
        url_template="https://www.space-track.org/basicspacedata/query/class/tle_latest/NORAD_CAT_ID/{id}/ORDINAL/1/format/tle",
        attribution="space-track.org",
        rate_limit_seconds=2.0,
        extra_headers={"Pragma": "no-cache"},
    ),
    "n2yo": SourceDefinition(
        name="n2yo",
        url_template="https://api.n2yo.com/rest/v1/satellite/tle/{id}?apiKey={id}",
        attribution="n2yo.com",
        rate_limit_seconds=1.0,
    ),
}


def build_clients(order: Sequence[str]) -> List[SourceClient]:
    """Instantiate :class:`SourceClient` objects for ``order``.

    Unknown source names are ignored.  The resulting list preserves the input
    order and omits duplicates.
    """

    seen = set()
    clients: List[SourceClient] = []
    for name in order:
        if name in seen:
            continue
        seen.add(name)
        definition = AVAILABLE_SOURCES.get(name)
        if not definition:
            continue
        clients.append(
            SourceClient(
                name=definition.name,
                url_template=definition.url_template,
                attribution=definition.attribution,
                rate_limit_seconds=definition.rate_limit_seconds,
                extra_headers=definition.extra_headers,
                timeout=definition.timeout,
            )
        )
    return clients


def parse_source_order(text: str, default: Optional[Iterable[str]] = None) -> List[str]:
    if not text:
        return list(default or [])
    order = [item.strip() for item in text.split(",")]
    return [item for item in order if item]


__all__ = [
    "ATTRIBUTION_HEADER",
    "AVAILABLE_SOURCES",
    "DEFAULT_TIMEOUT",
    "DEFAULT_USER_AGENT",
    "SourceClient",
    "SourceDefinition",
    "SourceError",
    "build_clients",
    "parse_source_order",
]
