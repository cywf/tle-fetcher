"""Application configuration loader for tle_fetcher."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

__all__ = [
    "FeatureFlags",
    "NotionSettings",
    "AppConfig",
    "load_config",
    "redact_secret",
]


@dataclass(frozen=True)
class FeatureFlags:
    """Feature toggles used throughout the application."""

    notion_sync: bool = False


@dataclass(frozen=True)
class NotionSettings:
    """Secrets and options for the Notion connector."""

    api_token: Optional[str]
    database_id: Optional[str]
    timeout: float = 10.0

    def is_configured(self) -> bool:
        return bool(self.api_token and self.database_id)


@dataclass(frozen=True)
class AppConfig:
    """Container for derived application configuration."""

    base_dir: Path
    data_dir: Path
    feature_flags: FeatureFlags
    notion: NotionSettings

    def redact(self, value: Optional[str], keep: int = 4) -> str:
        return redact_secret(value, keep=keep)

    @property
    def notion_enabled(self) -> bool:
        return self.feature_flags.notion_sync and self.notion.is_configured()


_TRUE_SET = {"1", "true", "yes", "on"}
_FALSE_SET = {"0", "false", "no", "off"}


def _to_bool(value: Optional[str], default: Optional[bool] = None) -> Optional[bool]:
    if value is None:
        return default
    lowered = value.strip().lower()
    if lowered in _TRUE_SET:
        return True
    if lowered in _FALSE_SET:
        return False
    return default


def redact_secret(value: Optional[str], keep: int = 4) -> str:
    """Redact a secret value for safe logging."""

    if not value:
        return "<redacted>"
    keep = max(0, keep)
    if len(value) <= keep:
        return "*" * len(value)
    return f"{value[:keep]}{'*' * 4}"


def load_config(env: Optional[Mapping[str, str]] = None) -> AppConfig:
    """Load configuration from environment variables."""

    env_map: Mapping[str, str]
    if env is None:
        env_map = os.environ
    else:
        env_map = env

    base_dir = Path(env_map.get("TLE_FETCHER_BASE_DIR", Path(__file__).resolve().parent.parent))
    data_dir = Path(env_map.get("TLE_FETCHER_DATA_DIR", base_dir / "data"))

    token = env_map.get("TLE_FETCHER_NOTION_TOKEN")
    db_id = env_map.get("TLE_FETCHER_NOTION_DATABASE_ID")
    timeout_raw = env_map.get("TLE_FETCHER_NOTION_TIMEOUT")
    timeout = float(timeout_raw) if timeout_raw else 10.0

    flag = _to_bool(env_map.get("TLE_FETCHER_FEATURE_NOTION_SYNC"), default=None)
    if flag is None:
        flag = bool(token and db_id)

    feature_flags = FeatureFlags(notion_sync=flag)
    notion_settings = NotionSettings(api_token=token, database_id=db_id, timeout=timeout)

    return AppConfig(
        base_dir=base_dir,
        data_dir=data_dir,
        feature_flags=feature_flags,
        notion=notion_settings,
    )
