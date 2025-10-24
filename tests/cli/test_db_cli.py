import pytest

import importlib.util
import sys
from pathlib import Path

from tle_fetcher.cli import db as db_cli


def test_db_cli_init_verify_backup(tmp_path):
    db_path = tmp_path / "cli.sqlite3"

    exit_code = db_cli.main(["--db-path", str(db_path), "init"])
    assert exit_code == 0

    exit_code = db_cli.main(["--db-path", str(db_path), "verify"])
    assert exit_code == 0

    backup_path = tmp_path / "backup.sqlite3"
    exit_code = db_cli.main(["--db-path", str(db_path), "backup", str(backup_path)])
    assert exit_code == 0
    assert backup_path.exists()

    # With no new migrations this should be a no-op but still succeed.
    exit_code = db_cli.main(["--db-path", str(db_path), "migrate"])
    assert exit_code == 0


def test_legacy_entry_point_delegates(tmp_path):
    db_path = tmp_path / "legacy.sqlite3"
    # First initialize via the CLI module.
    db_cli.main(["--db-path", str(db_path), "init"])

    spec = importlib.util.spec_from_file_location("legacy_cli", Path.cwd() / "tle_fetcher.py")
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    with pytest.raises(SystemExit) as exc:
        module.main(["db", "--db-path", str(db_path), "verify"])
    assert exc.value.code == 0
