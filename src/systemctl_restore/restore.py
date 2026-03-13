import shlex
import subprocess
from pathlib import Path
from typing import Literal

from rich import print

from . import systemd
from .asker import Asker


class RestoreStep:
    pass


class ChangeServices(RestoreStep):
    def __init__(
        self,
        desc: str,
        services: list[systemd.Service],
        action: Literal["start", "stop"],
    ):
        self._desc = desc
        self._cmd = ["systemctl", action, *services]

    def doit(self):  # pragma: no cover
        subprocess.run(self._cmd, check=True)

    def __str__(self) -> str:
        return f"{self._desc}: {shlex.join(self._cmd)}"


class MoveDirectory(RestoreStep):
    def __init__(self, desc: str, old: Path, new: Path):
        self._desc = desc
        self._old = old
        self._new = new

    def doit(self):  # pragma: no cover
        assert self._old.is_dir(), f"Must be a directory: {self._old}"
        assert not self._new.exists(), f"Must not exist: {self._new}"

        self._new.parent.mkdir(parents=True, exist_ok=True)
        self._old.rename(self._new)

    def __str__(self) -> str:
        return f"{self._desc}: mv {shlex.quote(str(self._old))} {shlex.quote(str(self._new))}"


class RestoreService:
    def __init__(
        self,
        services: list[systemd.Service],
        state_directory: Path,
        state_to_restore: Path,
        backup_dir: Path,
        dry_run: bool,
    ):
        self._services = services
        self._state_directory = state_directory
        self._relative_state_dir = self._state_directory.relative_to("/var/lib")
        self._state_to_restore = state_to_restore
        self._backup_dir = backup_dir
        self._dry_run = dry_run

    def doit(self, ask: Asker):
        steps = [
            ChangeServices("Stop affected services", self._services, "stop"),
            MoveDirectory(
                "Backup the current state (just in case!)",
                self._state_directory,
                self._backup_dir / self._relative_state_dir,
            ),
            MoveDirectory(
                "Restore state", self._state_to_restore, self._state_directory
            ),
            ChangeServices("Start affected services", self._services, "start"),
        ]

        pretty_services = ", ".join(self._services)
        print(
            "\n".join(
                [
                    f"I'm going to restore data for {pretty_services}:",
                    *[f"  {i + 1}. {step}" for i, step in enumerate(steps)],
                ]
            )
        )
        if not ask("Proceed?"):
            return  # pragma: no cover

        if self._dry_run:
            pass
        else:  # pragma: no cover
            for step in steps:
                step.doit()
