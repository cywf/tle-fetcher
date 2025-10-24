#!/usr/bin/env python3
"""Entry point wrapper for the tle_fetcher CLI."""

from __future__ import annotations

import importlib
import sys
from importlib.machinery import ModuleSpec
from pathlib import Path

_package_path = Path(__file__).resolve().parent / "tle_fetcher"

if __name__ != "__main__":
    __spec__ = ModuleSpec(__name__, loader=None, is_package=True)  # type: ignore[assignment]
    __path__ = [str(_package_path)]  # type: ignore[name-defined]
    _cli = importlib.import_module(".cli", __name__)

    for _name in dir(_cli):
        if _name.startswith("_"):
            continue
        globals().setdefault(_name, getattr(_cli, _name))
    del _cli, _name
else:
    from tle_fetcher.cli import main as _main  # noqa: E402
    sys.exit(_main())
