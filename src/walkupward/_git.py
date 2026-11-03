"""Find a git working tree the way git discovery does, worktrees and submodules included."""

from __future__ import annotations

import os
from collections.abc import Iterable, Iterator
from pathlib import Path

from walkupward._gitconfig import parse_bool
from walkupward._gitdir import has_work_tree, is_git_directory, read_gitfile
from walkupward._probe import probe_start
from walkupward._types import Marker, Match
from walkupward._walk import StrPath, start_directory, walk_up


def env_ceilings(start: StrPath = ".") -> list[Path]:
    """Return the ceilings ``GIT_CEILING_DIRECTORIES`` sets for a search from ``start``.

    Like git, relative entries are ignored and absolute ones are resolved, except that
    entries after an empty one are kept literally: such an entry only applies when its
    text, minus one trailing ``/``, equals an ancestor of the physical start written
    with ``/`` separators, case included.
    """
    raw = os.environ.get("GIT_CEILING_DIRECTORIES", "")
    found: list[Path] = []
    literal = False
    origin: str | None = None
    for entry in raw.split(os.pathsep):
        if not entry:
            literal = True
        elif not (os.path.isabs(entry) or entry[0] in "/\\"):
            continue
        elif not literal:
            found.append(Path(entry).resolve())
        else:
            if origin is None:
                origin = str(start_directory(start, True)).replace(os.sep, "/")
            text = entry[:-1] if entry.endswith("/") else entry
            rest = origin[len(text) :]
            if origin.startswith(text) and rest[:1] == "/" and rest[1:]:
                found.append(Path(text + "/"))
    return found


def env_across_filesystems() -> bool | None:
    """Return git's reading of ``GIT_DISCOVERY_ACROSS_FILESYSTEM`` (false when unset).

    ``None`` means the value is not a git boolean, which makes git stop with an error.
    """
    value = os.environ.get("GIT_DISCOVERY_ACROSS_FILESYSTEM")
    return False if value is None else parse_bool(value)


def is_git_marker(path: Path) -> bool:
    """Return whether a ``.git`` entry is a repository directory or a valid link to one."""
    if path.is_dir():
        return is_git_directory(path) and has_work_tree(path)
    target = read_gitfile(path)
    return target is not None and has_work_tree(target)


GIT_MARKER = Marker(".git", check=is_git_marker)
"""The ``.git`` marker: a repository directory, or a file whose ``gitdir:`` names one."""


def git_root(
    start: StrPath = ".",
    *,
    ceilings: Iterable[StrPath] | None = None,
    across_filesystems: bool | None = None,
) -> Match | None:
    """Return the git working tree enclosing ``start``, or ``None``.

    ``match.directory`` is what ``git rev-parse --show-toplevel`` prints: the main
    working tree, a linked worktree (its ``.git`` is a file), or a submodule checkout.
    Discovery follows git step by step on the physical path. In each directory, a
    ``.git`` directory that is not a valid repository is skipped, but a ``.git`` file
    that is not a valid ``gitdir:`` link ends the search with ``None``, where git stops
    with an error. A directory that is itself a repository directory (inside ``.git``
    or a bare repository) also gives ``None``, since it has no working tree.

    A repository whose config sets ``core.bare`` (or a config git refuses) has no
    working tree either, so it also gives ``None``. ``GIT_COMMON_DIR`` and
    ``GIT_OBJECT_DIRECTORY`` are honoured where git reads them.

    ``ceilings`` defaults to ``GIT_CEILING_DIRECTORIES`` and ``across_filesystems`` to
    ``GIT_DISCOVERY_ACROSS_FILESYSTEM``; when false, the walk stops at a filesystem
    boundary. When that variable is not a git boolean, git stops with an error and the
    result is ``None``. ``GIT_DIR``, ``GIT_WORK_TREE``, ``core.worktree``, config
    includes and git's ``safe.directory`` ownership check are not consulted. Raises
    ``StartNotFoundError`` when ``start`` does not exist and ``TypeError`` when it is
    not a path.

    >>> match = git_root(".")
    >>> match is None or match.directory.is_absolute()
    True
    """
    return next(
        iter_git_roots(start, ceilings=ceilings, across_filesystems=across_filesystems), None
    )


def iter_git_roots(
    start: StrPath = ".",
    *,
    ceilings: Iterable[StrPath] | None = None,
    across_filesystems: bool | None = None,
) -> Iterator[Match]:
    """Yield every enclosing git working tree, nearest first (a submodule, then its parent).

    Each step follows ``git_root``; the walk ends where git discovery would stop with an
    error or without a working tree.

    >>> all(m.directory.is_absolute() for m in iter_git_roots("."))
    True
    """
    probe_start(start)
    if ceilings is None:
        ceilings = env_ceilings(start)
    if across_filesystems is None:
        across_filesystems = env_across_filesystems()
        if across_filesystems is None:
            return iter(())
    walk = walk_up(start, ceilings=tuple(ceilings), same_filesystem=not across_filesystems)
    return _discover(walk)


def _discover(walk: Iterator[Path]) -> Iterator[Match]:
    for directory in walk:
        dot_git = directory / ".git"
        if dot_git.is_file():
            target = read_gitfile(dot_git)
            if target is None or not has_work_tree(target):
                return
            yield Match(directory, (GIT_MARKER,), (dot_git,))
        elif dot_git.is_dir() and is_git_directory(dot_git):
            if not has_work_tree(dot_git):
                return
            yield Match(directory, (GIT_MARKER,), (dot_git,))
        elif is_git_directory(directory):
            return
