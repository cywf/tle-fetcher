#!/usr/bin/env python3
"""Legacy CLI entrypoint for the ``tle_fetcher`` package."""

from __future__ import annotations

import pathlib
from typing import Optional, Sequence

_PACKAGE_DIR = pathlib.Path(__file__).with_name("tle_fetcher")
__path__ = [str(_PACKAGE_DIR)]  # type: ignore[var-annotated]

# Execute the package ``__init__`` in this module namespace so imports behave
# as though the directory were imported directly.
_namespace = globals()
_init_file = _PACKAGE_DIR / "__init__.py"
with _init_file.open("r", encoding="utf-8") as _fh:
    exec(compile(_fh.read(), str(_init_file), "exec"), _namespace, _namespace)

def main(argv: Optional[Sequence[str]] = None) -> None:
    """Invoke the package CLI, preserving the historical entrypoint."""
    raise SystemExit(bootstrap_cli(argv))


if __name__ == "__main__":  # pragma: no cover - manual execution shim
    main()
