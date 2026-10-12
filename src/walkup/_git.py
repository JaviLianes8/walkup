"""Find a git working tree the way git discovery does, worktrees and submodules included."""

from __future__ import annotations

import os
import re
from collections.abc import Iterable, Iterator
from pathlib import Path

from walkup._search import probe_start
from walkup._types import Marker, Match
from walkup._walk import StrPath, walk_up

_TRUE = frozenset({"true", "yes", "on"})
_OBJECT_ID = re.compile(r"[0-9a-fA-F]{40}")
_GITDIR = "gitdir: "


def _valid_head(path: Path) -> bool:
    if path.is_symlink():
        return os.readlink(path).replace("\\", "/").startswith("refs/")
    head = path.read_text(encoding="utf-8", errors="replace")
    if head.startswith("ref:"):
        return head[4:].lstrip().startswith("refs/")
    return _OBJECT_ID.match(head) is not None


def is_git_directory(path: Path) -> bool:
    """Return whether ``path`` looks like a repository directory to git.

    Mirrors git's own test: a valid ``HEAD`` (``ref:`` followed by ``refs/...``, a
    symlink into ``refs/``, or an object id), plus ``objects`` and ``refs`` directories,
    found through ``commondir`` for a linked worktree.
    """
    try:
        if not _valid_head(path / "HEAD"):
            return False
        common = path
        if (path / "commondir").is_file():
            raw = (path / "commondir").read_text(encoding="utf-8", errors="replace")
            common = path / raw.rstrip("\r\n")
        return (common / "objects").is_dir() and (common / "refs").is_dir()
    except OSError:
        return False


def read_gitfile(path: Path) -> Path | None:
    """Return the repository directory named by a ``.git`` file, or ``None`` if invalid.

    Like git, the file must start with ``gitdir: `` (one space); the rest of the file,
    minus trailing line breaks, is the path, taken from the file's directory when
    relative, and it must be a repository directory.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if not text.startswith(_GITDIR):
        return None
    raw = text[len(_GITDIR) :].rstrip("\r\n")
    if not raw:
        return None
    target = Path(raw)
    target = target if target.is_absolute() else path.parent / target
    return target if is_git_directory(target) else None


def env_ceilings() -> list[str]:
    """Return the absolute entries of ``GIT_CEILING_DIRECTORIES``; git ignores the rest.

    Every entry is resolved before use, including those after an empty entry, which git
    itself compares without resolving symlinks.
    """
    raw = os.environ.get("GIT_CEILING_DIRECTORIES", "")
    return [e for e in raw.split(os.pathsep) if e and (os.path.isabs(e) or e[0] in "/\\")]


def env_across_filesystems() -> bool:
    """Return git's reading of ``GIT_DISCOVERY_ACROSS_FILESYSTEM`` (false when unset)."""
    value = os.environ.get("GIT_DISCOVERY_ACROSS_FILESYSTEM", "").strip().lower()
    if value in _TRUE:
        return True
    try:
        return int(value) != 0
    except ValueError:
        return False


def is_git_marker(path: Path) -> bool:
    """Return whether a ``.git`` entry is a repository directory or a valid link to one."""
    return is_git_directory(path) if path.is_dir() else read_gitfile(path) is not None


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

    ``ceilings`` defaults to ``GIT_CEILING_DIRECTORIES`` and ``across_filesystems`` to
    ``GIT_DISCOVERY_ACROSS_FILESYSTEM``; when false, the walk stops at a filesystem
    boundary. ``GIT_DIR``, ``GIT_WORK_TREE``, ``core.worktree`` and git's
    ``safe.directory`` ownership check are not consulted. Raises ``StartNotFoundError``
    when ``start`` does not exist.
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
    """
    probe_start(start)
    if ceilings is None:
        ceilings = env_ceilings()
    if across_filesystems is None:
        across_filesystems = env_across_filesystems()
    walk = walk_up(start, ceilings=tuple(ceilings), same_filesystem=not across_filesystems)
    return _discover(walk)


def _discover(walk: Iterator[Path]) -> Iterator[Match]:
    for directory in walk:
        dot_git = directory / ".git"
        if dot_git.is_file():
            if read_gitfile(dot_git) is None:
                return
            yield Match(directory, (GIT_MARKER,), (dot_git,))
        elif dot_git.is_dir() and is_git_directory(dot_git):
            yield Match(directory, (GIT_MARKER,), (dot_git,))
        elif is_git_directory(directory):
            return
