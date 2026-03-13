from pathlib import Path
from typing import Generator, Self


class ChildNotFoundError(Exception):
    pass


class DirectoryTree:
    """
    A mutable, lazily built tree representation of all files/directories under some root.

    If the root directory changes during the lifetime of the DirectoryTree, be prepared for weirdness.

    Mutating this does *not* affect the underlying filesystem! It's just a tool to do some bookkeeping.
    """

    _children: dict[str, Self] | None

    def __init__(self, root: Path, parent: Self | None = None):
        self._root = root
        self._parent = parent
        self._children = None

    @property
    def name(self) -> str:
        return self._root.name

    @property
    def parent(self) -> Self | None:
        return self._parent

    def is_leaf(self) -> bool:
        return not self._root.is_dir()

    def to_path(self) -> Path:
        return self._root

    def forget(self):
        assert self._parent is not None
        assert self._parent._children is not None
        del self._parent._children[self.name]

    def children(self) -> dict[str, Self]:
        assert not self.is_leaf()

        if self._children is None:
            cls = type(self)
            self._children = {
                c.name: cls(c, parent=self) for c in sorted(self._root.iterdir())
            }

        return self._children

    def _pretty_tree_lines(
        self,
        force: bool,
        first_prefix: str = "",
        rest_prefix: str = "",
    ) -> Generator[str, None, None]:
        if self._children is None and force:
            self.children()
            assert self._children is not None

        if self._children is None:
            yield f"{first_prefix}{self._root.name} (not traversed)"
        else:
            yield f"{first_prefix}{self._root.name}"

            for i, child in enumerate(self._children.values()):
                is_last_child = i == len(self._children) - 1

                joint1 = "└── " if is_last_child else "├── "
                joint2 = "    " if is_last_child else "│   "

                if child.is_leaf():
                    yield f"{rest_prefix}{joint1}{child.name}"
                else:
                    yield from child._pretty_tree_lines(
                        force=force,
                        first_prefix=rest_prefix + joint1,
                        rest_prefix=rest_prefix + joint2,
                    )

    def traverse(self, *children: str) -> Self:
        if len(children) == 0:
            return self

        child_name, *rest = children

        child = self.children().get(child_name)
        if child is None:
            raise ChildNotFoundError(f"Path does not exist: {self._root / child_name}")

        return child.traverse(*rest)

    def __truediv__(self, childs: str) -> Self:
        return self.traverse(*childs.split("/"))

    def pretty_tree(self, force: bool = False) -> str:
        return "\n".join(self._pretty_tree_lines(force=force)) + "\n"
