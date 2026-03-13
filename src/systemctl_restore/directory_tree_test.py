import textwrap
from pathlib import Path

import pytest

from .directory_tree import ChildNotFoundError, DirectoryTree


def test_laziness(tmp_path: Path):
    root = tmp_path / "root"
    (root / "foo/bar").mkdir(parents=True)
    (root / "foo/bar/file1").touch()
    (root / "foo/bar/file2").touch()
    (root / "foo/baz").touch()

    dt = DirectoryTree(root)
    assert dt.pretty_tree() == textwrap.dedent("""\
        root (not traversed)
    """)

    # Force traversal of the root.
    dt.children()
    assert dt.pretty_tree() == textwrap.dedent("""\
        root
        └── foo (not traversed)
    """)

    # Force traversal of root/foo.
    (dt / "foo").children()
    assert dt.pretty_tree() == textwrap.dedent("""\
        root
        └── foo
            ├── bar (not traversed)
            └── baz
    """)

    # Force traversal of root/foo/bar.
    (dt / "foo/bar").children()
    assert dt.pretty_tree() == textwrap.dedent("""\
        root
        └── foo
            ├── bar
            │   ├── file1
            │   └── file2
            └── baz
    """)


def test_leaf(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    file1 = root / "file1"
    file1.touch()

    dt = DirectoryTree(root)
    assert (dt / "file1").is_leaf()
    assert (dt / "file1").to_path() == file1


def test_nonexistent_path(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    dt = DirectoryTree(root)

    with pytest.raises(ChildNotFoundError) as exc_info:
        assert dt / "nonexistent" is not None

    assert f"Path does not exist: {root / 'nonexistent'}" == str(exc_info.value)


def test_forget(tmp_path: Path):
    root = tmp_path / "root"
    (root / "foo/bar").mkdir(parents=True)
    (root / "foo/bar/file1").touch()
    (root / "foo/bar/file2").touch()
    (root / "foo/baz").touch()
    dt = DirectoryTree(root)

    assert dt.pretty_tree(force=True) == textwrap.dedent("""\
        root
        └── foo
            ├── bar
            │   ├── file1
            │   └── file2
            └── baz
    """)

    (dt / "foo" / "bar").forget()

    assert dt.pretty_tree(force=True) == textwrap.dedent("""\
        root
        └── foo
            └── baz
    """)
