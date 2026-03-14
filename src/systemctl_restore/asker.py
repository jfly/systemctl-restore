import builtins
from typing import Callable

from rich import print

Asker = Callable[[str], bool]


def input(msg: str) -> str:  # pragma: no cover
    print(msg, end="")
    return builtins.input()


def build_asker(always_yes: bool) -> Asker:  # pragma: no cover
    def ask(question: str) -> bool:
        value_by_choice = {
            "y": True,
            "n": False,
        }

        short_choices = "/".join(
            f"[green]{choice}[/green]" for choice in value_by_choice.keys()
        )
        prompt = f"{question} ({short_choices}): "

        if always_yes:
            choice = "y"
            print(prompt + choice)
        else:
            while (choice := input(prompt)) not in value_by_choice:  # pragma: no cover
                print("[red]Please select a valid choice[/red]")

        return value_by_choice[choice]

    return ask
