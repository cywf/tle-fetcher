import logging
from pathlib import Path
from urllib.error import URLError

import pytest

from tle_fetcher.config import load_config, redact_secret
from tle_fetcher.connectors import notion_sync
from tle_fetcher.connectors.notion_sync import NotionSync


def _base_env(tmp_path: Path) -> dict:
    return {
        "TLE_FETCHER_BASE_DIR": str(tmp_path),
        "TLE_FETCHER_DATA_DIR": str(tmp_path / "data"),
    }


def test_notion_sync_disabled_without_credentials(monkeypatch, tmp_path, caplog):
    env = _base_env(tmp_path)
    caplog.set_level(logging.INFO)

    config = load_config(env)
    connector = NotionSync(config)
    assert connector.enabled is False

    result = connector.pull(tmp_path / "out.json")
    assert result.status == "skipped"
    assert result.reason == "disabled"
    assert "Notion sync disabled" in caplog.text


def test_notion_sync_offline_is_noop(monkeypatch, tmp_path):
    env = _base_env(tmp_path)
    env.update({
        "TLE_FETCHER_NOTION_TOKEN": "secret-token",
        "TLE_FETCHER_NOTION_DATABASE_ID": "db123",
    })

    config = load_config(env)
    connector = NotionSync(config)

    def fake_urlopen(*args, **kwargs):
        raise URLError("offline")

    monkeypatch.setattr(notion_sync, "urlopen", fake_urlopen)

    result = connector.pull(tmp_path / "out.json")
    assert result.status == "skipped"
    assert result.reason == "offline"

    # Ensure nothing was written when offline
    assert not (tmp_path / "out.json").exists()


def test_redact_secret_masks_values():
    assert redact_secret("secret-value") == "secr****"
    assert redact_secret("") == "<redacted>"
