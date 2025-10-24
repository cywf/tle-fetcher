import importlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))


def test_importable() -> None:
    module = importlib.import_module("tle_fetcher")
    assert hasattr(module, "fetch_with_fallback")
