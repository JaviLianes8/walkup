"""The original one-call lookup, kept stable on top of ``walk_up``."""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from walkup._types import Kind
from walkup._walk import walk_up


def find_up(
    names: str | Iterable[str],
    start: str | os.PathLike[str] = ".",
    root: str | os.PathLike[str] | None = None,
    *,
    kind: Kind = "any",
) -> Path | None:
    """Return the first ``names`` match found walking up from ``start``, or ``None``.

    ``names`` is one name or several, tried in order within each directory before moving
    up. ``root``, when given, is the last directory searched. ``kind`` restricts matches
    to regular files (``"file"``) or directories (``"dir"``); the default accepts either.
    For the matched marker, every match, ceilings or typed errors, see ``find``.
    """
    wanted: tuple[str, ...] = (names,) if isinstance(names, str) else tuple(names)
    boundary = Path(root).resolve() if root is not None else None
    for directory in walk_up(start):
        for name in wanted:
            candidate = directory / name
            if _matches(candidate, kind):
                return candidate
        if boundary is not None and directory == boundary:
            break
    return None


def _matches(path: Path, kind: Kind) -> bool:
    if kind == "file":
        return path.is_file()
    if kind == "dir":
        return path.is_dir()
    return path.exists()
