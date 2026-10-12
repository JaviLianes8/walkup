"""Iterate a directory and its ancestors under ceiling, boundary and symlink rules."""

from __future__ import annotations

import os
from collections.abc import Iterable, Iterator
from pathlib import Path

StrPath = str | os.PathLike[str]


def walk_up(
    start: StrPath = ".",
    *,
    ceilings: Iterable[StrPath] = (),
    stop_at: StrPath | None = None,
    same_filesystem: bool = False,
    resolve: bool = True,
) -> Iterator[Path]:
    """Yield the start directory and each ancestor, nearest first.

    A path that exists but is not a directory (a file, a device) starts the walk at its
    parent directory, and every yielded path is absolute. With no options the walk ends
    at the filesystem root (``/``, ``C:\\`` or the share root of a UNC path).

    ``ceilings`` follows git's ``GIT_CEILING_DIRECTORIES``: the walk never enters a
    ceiling or anything above it. A ceiling only applies when it is a proper ancestor of
    the start, so starting inside a ceiling directory itself still searches it, and
    ceilings elsewhere on disk are ignored.

    ``stop_at`` is inclusive: that directory is yielded and the walk ends there. It has
    no effect when it is not the start or one of its ancestors.

    ``same_filesystem`` stops before yielding a directory on a different device from
    the start (or one whose device cannot be read), like git discovery without
    ``GIT_DISCOVERY_ACROSS_FILESYSTEM``.

    ``resolve`` picks the symlink policy. ``True`` resolves symlinks and junctions first
    and walks the physical path, as ``pwd -P`` and git do. On Windows, ``Path.resolve``
    collapses ``..`` before following a junction, so ``link/..`` names the directory
    holding the link rather than the parent of its target. ``False`` walks the lexical
    path: the start is made absolute and normalised, ``..`` is collapsed textually, and
    symlinked components stay in place, as ``pwd -L`` does. Ceilings and ``stop_at`` are
    normalised with the same policy before they are compared.
    """
    origin = _normalise(start, resolve)
    if origin.exists() and not origin.is_dir():
        origin = origin.parent
    ceiling = _nearest_ceiling(origin, ceilings, resolve)
    boundary = _normalise(stop_at, resolve) if stop_at is not None else None
    device = _device(origin) if same_filesystem else None
    current = origin
    while True:
        yield current
        if boundary is not None and current == boundary:
            return
        parent = current.parent
        if parent in (current, ceiling):
            return
        if same_filesystem and (device is None or _device(parent) != device):
            return
        current = parent


def _normalise(path: StrPath, resolve: bool) -> Path:
    if resolve:
        return Path(path).resolve()
    return Path(os.path.normpath(Path(path).absolute()))


def _nearest_ceiling(origin: Path, ceilings: Iterable[StrPath], resolve: bool) -> Path | None:
    nearest: Path | None = None
    ancestors = set(origin.parents)
    for raw in ceilings:
        ceiling = _normalise(raw, resolve)
        if ceiling in ancestors and (nearest is None or len(ceiling.parts) > len(nearest.parts)):
            nearest = ceiling
    return nearest


def _device(path: Path) -> int | None:
    try:
        return os.stat(path).st_dev
    except OSError:
        return None
