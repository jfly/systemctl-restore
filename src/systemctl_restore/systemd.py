import subprocess
from pathlib import Path
from typing import NewType

Service = NewType("Service", str)


def split_list[T](split_me: list[T], split_by: T) -> list[list[T]]:
    """Given a list of values and some value to split_by, return a list of lists.

    >>> split_list([1, 2, 2, 3, 4, 2, 5], split_by=2)
    [[1], [], [3, 4], [5]]
    """
    result: list[list[T]] = []

    so_far: list[T] = []
    for v in split_me:
        if v == split_by:
            result.append(so_far)
            so_far = []
            continue

        so_far.append(v)

    if len(so_far) > 0:
        result.append(so_far)

    return result


def parse_systemctl_show(sysctl_show_output: str) -> list[dict[str, str]]:
    """
    Parse the output of `systemctl show`.

    >>> parse_systemctl_show('''
    ... Id=fwupd.service
    ... StateDirectory=
    ...
    ... Id=nix-gc.timer
    ...
    ... Id=interception-tools.service
    ... StateDirectory=
    ...
    ... Id=accounts-daemon.service
    ... StateDirectory=AccountsService
    ... ''')
    [{'Id': 'fwupd.service', 'StateDirectory': ''}, {'Id': 'nix-gc.timer'}, {'Id': 'interception-tools.service', 'StateDirectory': ''}, {'Id': 'accounts-daemon.service', 'StateDirectory': 'AccountsService'}]
    """

    result: list[dict[str, str]] = []

    data_lineses = split_list(sysctl_show_output.splitlines(), split_by="")
    for data_lines in data_lineses:
        if len(data_lines) == 0:
            continue

        data = {}
        for line in data_lines:
            key, value = line.split("=")
            data[key] = value

        result.append(data)

    return result


def get_state_directory_by_service() -> dict[
    Service, Path
]:  # pragma: no cover # tested in e2e tests
    """Fetch the StateDirectory for all services."""

    cp = subprocess.run(
        ["systemctl", "show", "--property", "Id,StateDirectory", "*"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )

    state_dir_by_service: dict[Service, Path] = {}

    for service_info in parse_systemctl_show(cp.stdout):
        service = Service(service_info["Id"])
        state_dir_str = service_info.get("StateDirectory")
        if state_dir_str is not None and state_dir_str != "":
            state_dir = Path("/var/lib") / state_dir_str
            state_dir_by_service[service] = state_dir

    return state_dir_by_service
