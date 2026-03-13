import datetime as dt
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich import print

from systemctl_restore.directory_tree import ChildNotFoundError, DirectoryTree

from . import systemd
from .asker import build_asker
from .restore import RestoreService

app = typer.Typer()


def plural(count: int, thing: str) -> str:
    """
    Pluralize `thing`.

    >>> plural(0, "egg")
    '0 eggs'

    >>> plural(1, "egg")
    '1 egg'

    >>> plural(2, "egg")
    '2 eggs'
    """

    pluralize = count != 1

    if pluralize:
        thing += "s"

    return f"{count} {thing}"


def flip_dict[K, V](d: dict[K, V]) -> dict[V, list[K]]:
    """
    Give a dict mapping K -> V, flips it so V -> [K].

    >>> flip_dict({'a': 1, 'b': 2})
    {1: ['a'], 2: ['b']}

    >>> flip_dict({'a': 1, 'A': 1})
    {1: ['a', 'A']}
    """

    result: dict[V, list[K]] = {}
    for k, v in d.items():
        if v not in result:
            result[v] = []

        result[v].append(k)

    return result


def parse_empty_or_nonexistent_path(value: str) -> Path:
    p = Path(value)
    if p.exists():
        if not p.is_dir():
            raise typer.BadParameter("must be a directory")

        if len(list(p.iterdir())) > 0:
            raise typer.BadParameter("must be empty")

    return p


@app.command()
def main(
    restore_dir: Annotated[
        Path,
        typer.Argument(
            help="Backup of /var/lib to restore",
            exists=True,
            readable=True,
            file_okay=False,
            dir_okay=True,
        ),
    ],
    backup_dir: Annotated[
        Path,
        typer.Option(
            help="Directory to place backups of data before the restore. This lets you undo a problematic restore.",
            parser=parse_empty_or_nonexistent_path,
        ),
    ] = Path(f"/var/lib.bak-{dt.datetime.now().isoformat(timespec='seconds')}"),
    yes: Annotated[
        bool, typer.Option("--yes", "-y", help="Answer yes to every question.")
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Don't do anything destructive, just print what would happen.",
        ),
    ] = False,
):  # pragma: no cover # tested in e2e tests
    state_directory_by_service = systemd.get_state_directory_by_service()

    warnings = restore(
        restore_dir,
        backup_dir,
        state_directory_by_service,
        yes_all=yes,
        dry_run=dry_run,
    )
    print()
    if len(warnings) > 0:
        print(
            f"[yellow bold]Finished, but encountered {plural(len(warnings), 'warning')}. See above.[/yellow bold]"
        )
    else:
        print("[green]Success![/green]")

    print(
        f"In case anything went wrong, there are backups of the previous state directories in {backup_dir}."
    )
    print(f"To restore them: {sys.argv[0]} {backup_dir}")


def forget_and_any_empty_ancestors(forget_me: DirectoryTree):
    if parent := forget_me.parent:
        forget_me.forget()
        if len(parent.children()) == 0:
            forget_and_any_empty_ancestors(parent)


def restore(
    restore_dir: Path,
    backup_dir: Path,
    state_directory_by_service: dict[systemd.Service, Path],
    dry_run: bool,
    yes_all: bool,
) -> list[str]:
    ask = build_asker(yes_all)

    restore_dirtree = DirectoryTree(restore_dir)

    warnings = []

    def warn(msg):
        nonlocal warnings
        warnings.append(msg)
        print(f"[yellow]{msg}[/yellow]")

    to_restore: list[RestoreService] = []

    services_by_state_directory = flip_dict(state_directory_by_service)
    for state_directory, services in services_by_state_directory.items():
        relpath = state_directory.relative_to("/var/lib")
        try:
            restore_me = restore_dirtree / str(relpath)
        except ChildNotFoundError:
            # This service must not be backed up. That's fine, skip it.
            continue

        to_restore.append(
            RestoreService(
                services=services,
                state_directory=state_directory,
                state_to_restore=restore_me.to_path(),
                backup_dir=backup_dir,
                dry_run=dry_run,
            )
        )

        # Remove this folder (and any ancestors that are now empty) from the directory tree.
        # This doesn't actually mutate the filesystem: it just updates our bookkeeping so
        # we can check at the end if there is anything leftover we didn't handle.
        forget_and_any_empty_ancestors(restore_me)

    if len(restore_dirtree.children()) > 0:
        warn(
            f"There is some stuff left in {restore_dir} that I don't know how to handle:\n{restore_dirtree.pretty_tree()}"
        )

    for todo in to_restore:
        todo.doit(ask)

    return warnings


if __name__ == "__main__":
    app()  # pragma: no cover
