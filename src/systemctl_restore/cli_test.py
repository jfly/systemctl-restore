import textwrap
from pathlib import Path

import pytest
import typer

from . import systemd
from .cli import parse_empty_or_nonexistent_path, restore
from .directory_tree import DirectoryTree


def test_restore_all(tmp_path: Path):
    # Set up directory structure for the test.
    backup_dir = tmp_path / "backup"
    (restore_dir := tmp_path / "restore").mkdir()
    (restore_dir / "nested/state").mkdir(parents=True)
    (restore_dir / "nested/state/nested-statefile").touch()
    assert DirectoryTree(restore_dir).pretty_tree(force=True) == textwrap.dedent("""\
        restore
        └── nested
            └── state
                └── nested-statefile
        """)

    state_directory_by_service = {
        # This service is not backed up. That's fine.
        systemd.Service("bluetooth.service"): Path("/var/lib/bluetooth"),
        systemd.Service("nested.service"): Path("/var/lib/nested/state"),
    }

    warnings = restore(
        restore_dir, backup_dir, state_directory_by_service, dry_run=True, yes_all=True
    )
    assert warnings == []


def test_unhandled_directories(tmp_path: Path):
    # Set up directory structure for the test.
    backup_dir = tmp_path / "backup"
    (restore_dir := tmp_path / "restore").mkdir()
    (restore_dir / "bluetooth").mkdir()
    (restore_dir / "bluetooth/tooth-statefile").touch()
    (restore_dir / "nested/state").mkdir(parents=True)
    (restore_dir / "nested/state/nested-statefile").touch()
    (restore_dir / "what-is-this").touch()
    (restore_dir / "unexpected-file").touch()
    (restore_dir / "unexpected-dir").touch()
    assert DirectoryTree(restore_dir).pretty_tree(force=True) == textwrap.dedent("""\
        restore
        ├── bluetooth
        │   └── tooth-statefile
        ├── nested
        │   └── state
        │       └── nested-statefile
        ├── unexpected-dir
        ├── unexpected-file
        └── what-is-this
        """)

    state_directory_by_service = {
        systemd.Service("bluetooth.service"): Path("/var/lib/bluetooth"),
        systemd.Service("nested.service"): Path("/var/lib/nested/state"),
    }

    warnings = restore(
        restore_dir, backup_dir, state_directory_by_service, dry_run=True, yes_all=True
    )
    assert warnings == [
        f"There is some stuff left in {restore_dir} that I don't know how to handle:\n"
        "restore\n"
        "├── unexpected-dir\n"
        "├── unexpected-file\n"
        "└── what-is-this\n",
    ]


def test_parse_empty_or_nonexistent_path(tmp_path: Path):
    nonexistent = tmp_path / "nonexistent"
    assert nonexistent == parse_empty_or_nonexistent_path(str(nonexistent))

    (empty := tmp_path / "empty").mkdir()
    assert empty == parse_empty_or_nonexistent_path(str(empty))

    with pytest.raises(typer.BadParameter, match=r"must be a directory"):
        (file := tmp_path / "file").touch()
        assert file == parse_empty_or_nonexistent_path(str(file))

    with pytest.raises(typer.BadParameter, match=r"must be empty"):
        (nonempty := tmp_path / "nonempty").mkdir()
        (nonempty / "file").touch()
        assert nonempty == parse_empty_or_nonexistent_path(str(nonempty))
