import shlex
import subprocess
from pathlib import Path
from typing import Literal

from . import systemd


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

    def __str__(self) -> str:  # pragma: no cover
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

    def __str__(self) -> str:  # pragma: no cover
        return f"{self._desc}: mv {shlex.quote(str(self._old))} {shlex.quote(str(self._new))}"


class RestoreService:
    def __init__(
        self,
        services: list[systemd.Service],
        restore_dir: Path,
        relative_paths_to_restore: list[Path],
        backup_dir: Path,
        dry_run: bool,
    ):
        self._services = services
        self._dry_run = dry_run

        self._steps = [
            ChangeServices("Stop affected services", self._services, "stop"),
            *[
                MoveDirectory(
                    "Backup current state",
                    Path("/") / rel_path_to_restore,
                    backup_dir / rel_path_to_restore,
                )
                for rel_path_to_restore in relative_paths_to_restore
            ],
            *[
                MoveDirectory(
                    "Restore state",
                    restore_dir / rel_path_to_restore,
                    Path("/") / rel_path_to_restore,
                )
                for rel_path_to_restore in relative_paths_to_restore
            ],
            ChangeServices("Start affected services", self._services, "start"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        pretty_services = ", ".join(self._services)
        return "\n".join(
            [
                f"Restore data for {pretty_services}:",
                *[f"  {i + 1}. {step}" for i, step in enumerate(self._steps)],
            ]
        )

    def doit(self):  # pragma: no cover
        if self._dry_run:
            pass
        else:
            for step in self._steps:
                step.doit()
