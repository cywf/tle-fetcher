"""Notion connector used by the sync CLI."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..config import AppConfig

__all__ = ["ConnectorOfflineError", "NotionSync", "SyncResult"]

LOGGER = logging.getLogger(__name__)
NOTION_BASE_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


class ConnectorOfflineError(RuntimeError):
    """Raised when the remote service is unreachable."""


@dataclass
class SyncResult:
    status: str
    reason: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class NotionSync:
    """Push and pull records from a Notion database."""

    def __init__(self, config: AppConfig):
        self.config = config

    @property
    def enabled(self) -> bool:
        return self.config.notion_enabled

    def pull(self, output_path: Path, page_size: int = 50) -> SyncResult:
        """Fetch database rows and write them to *output_path*."""

        if not self.enabled:
            LOGGER.info("Notion sync disabled; skipping pull.")
            return SyncResult(status="skipped", reason="disabled")

        output_path = output_path.expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {"page_size": page_size}
        url = f"{NOTION_BASE_URL}/databases/{self.config.notion.database_id}/query"
        try:
            response = self._request("POST", url, payload)
        except ConnectorOfflineError:
            return SyncResult(status="skipped", reason="offline")
        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.error("Notion pull failed: %s", exc)
            return SyncResult(status="error", reason=str(exc))

        if response is None:
            return SyncResult(status="error", reason="empty-response")

        results = response.get("results", [])
        output_path.write_text(json.dumps({"results": results}, indent=2), encoding="utf-8")
        LOGGER.info("Pulled %s rows from Notion (saved to %s).", len(results), output_path)
        return SyncResult(status="ok", details={"count": len(results), "path": str(output_path)})

    def push(self, input_path: Path, limit: Optional[int] = None) -> SyncResult:
        """Read rows from *input_path* and push them to Notion."""

        if not self.enabled:
            LOGGER.info("Notion sync disabled; skipping push.")
            return SyncResult(status="skipped", reason="disabled")

        input_path = input_path.expanduser()
        if not input_path.exists():
            LOGGER.warning("Notion push skipped: input file %s not found.", input_path)
            return SyncResult(status="skipped", reason="missing-input")

        try:
            raw = json.loads(input_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            LOGGER.error("Invalid JSON payload for Notion push: %s", exc)
            return SyncResult(status="error", reason="invalid-json")

        records = self._extract_records(raw)
        if not records:
            LOGGER.info("Notion push skipped: no records to send from %s.", input_path)
            return SyncResult(status="skipped", reason="empty-input")

        sent = 0
        errors: List[str] = []
        for idx, record in enumerate(records):
            if limit is not None and sent >= limit:
                break
            payload = {
                "parent": {"database_id": self.config.notion.database_id},
                "properties": record,
            }
            try:
                self._request("POST", f"{NOTION_BASE_URL}/pages", payload)
                sent += 1
            except ConnectorOfflineError:
                return SyncResult(status="skipped", reason="offline", details={"attempted": sent})
            except HTTPError as exc:  # pragma: no cover - requires live service
                errors.append(f"http-{exc.code}")
            except Exception as exc:  # pragma: no cover - defensive
                errors.append(str(exc))

        if errors:
            LOGGER.error("Notion push completed with %s errors: %s", len(errors), ", ".join(errors))
            return SyncResult(status="error", reason="partial-failure", details={"sent": sent, "errors": errors})

        LOGGER.info("Pushed %s rows to Notion from %s.", sent, input_path)
        return SyncResult(status="ok", details={"sent": sent})

    def _request(self, method: str, url: str, payload: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            raise ConnectorOfflineError("connector disabled")

        data_bytes: Optional[bytes] = None
        if payload is not None:
            data_bytes = json.dumps(payload).encode("utf-8")

        headers = {
            "Authorization": f"Bearer {self.config.notion.api_token}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION,
        }

        LOGGER.debug("Notion request %s %s", method, url)
        req = Request(url, data=data_bytes, headers=headers, method=method)
        try:
            with urlopen(req, timeout=self.config.notion.timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                return json.loads(raw) if raw else {}
        except URLError as exc:
            LOGGER.warning("Notion service unreachable: %s", exc.reason or exc)
            raise ConnectorOfflineError(str(exc)) from exc

    def _extract_records(self, raw: Any) -> List[Dict[str, Any]]:
        if isinstance(raw, dict):
            if "results" in raw and isinstance(raw["results"], Iterable):
                return [self._coerce_properties(item) for item in raw["results"] if item]
            if "properties" in raw:
                return [self._coerce_properties(raw)]
        if isinstance(raw, list):
            return [self._coerce_properties(item) for item in raw if item]
        return []

    def _coerce_properties(self, item: Any) -> Dict[str, Any]:
        if isinstance(item, dict) and "properties" in item and isinstance(item["properties"], dict):
            return item["properties"]
        if isinstance(item, dict):
            return item
        raise ValueError("Record must be a mapping of properties")
