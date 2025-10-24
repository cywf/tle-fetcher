import io
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tle_fetcher.logging import configure_logging, get_logger, log_context


def _setup_logger():
    stream = io.StringIO()
    configure_logging(level="INFO", stream=stream, force=True)
    return get_logger("tests"), stream


def test_json_logging_includes_context_and_extras():
    logger, stream = _setup_logger()
    with log_context(norad_id="25544", attempt=1):
        logger.info("fetch_complete", extra={"source": "celestrak", "duration": 0.42})
    payload = json.loads(stream.getvalue())
    assert payload["message"] == "fetch_complete"
    assert payload["context"] == {"norad_id": "25544", "attempt": 1}
    assert payload["extra"]["source"] == "celestrak"
    assert payload["extra"]["duration"] == 0.42


def test_redaction_of_sensitive_fields():
    logger, stream = _setup_logger()
    logger.info(
        "credentials",
        extra={
            "api_key": "topsecret",
            "nested": {"token": "abc123", "visible": "ok"},
            "headers": [{"Authorization": "Bearer secret", "Other": "value"}],
        },
    )
    payload = json.loads(stream.getvalue())
    assert payload["extra"]["api_key"] == "***REDACTED***"
    assert payload["extra"]["nested"]["token"] == "***REDACTED***"
    header_entry = payload["extra"]["headers"][0]
    assert header_entry["Authorization"] == "***REDACTED***"
    assert header_entry["Other"] == "value"
