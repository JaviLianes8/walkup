"""Find a git working tree the way git discovery does, worktrees and submodules included."""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from pathlib import Path

from walkup._search import find
from walkup._types import Marker, Match
from walkup._walk import StrPath

_TRUE = frozenset({"true", "yes", "on", "1"})
_OBJECT_ID = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")


def is_git_directory(path: Path) -> bool:
    """Return whether ``path`` looks like a repository directory to git.

    Mirrors git's own test: a valid ``HEAD`` (a ``ref: refs/...`` line or an object id),
    plus ``objects`` and ``refs`` directories, found through ``commondir`` for a linked
    worktree.
    """
    try:
        head = (path / "HEAD").read_text(encoding="utf-8", errors="replace").strip()
        common = path
        if (path / "commondir").is_file():
            target = (path / "commondir").read_text(encoding="utf-8").strip()
            common = path / target
    except OSError:
        return False
    valid_head = head.startswith("ref: refs/") or _OBJECT_ID.fullmatch(head) is not None
    return valid_head and (common / "objects").is_dir() and (common / "refs").is_dir()


def is_git_marker(path: Path) -> bool:
    """Return whether a ``.git`` entry marks a working tree.

    A directory must be a repository directory. A file, as left by ``git worktree add``
    and by submodules, must start with ``gitdir: <path>`` naming one; a relative path is
    taken from the directory holding the file.
    """
    if path.is_dir():
        return is_git_directory(path)
    try:
        first = path.read_text(encoding="utf-8", errors="replace").splitlines()[0]
    except (OSError, IndexError):
        return False
    if not first.startswith("gitdir:"):
        return False
    target = Path(first[len("gitdir:") :].strip())
    return is_git_directory(target if target.is_absolute() else path.parent / target)


GIT_MARKER = Marker(".git", check=is_git_marker)
"""The marker used by ``git_root``: a validated ``.git`` directory or ``gitdir:`` file."""


def env_ceilings() -> list[str]:
    """Return the absolute entries of ``GIT_CEILING_DIRECTORIES``; git ignores the rest."""
    raw = os.environ.get("GIT_CEILING_DIRECTORIES", "")
    return [entry for entry in raw.split(os.pathsep) if entry and os.path.isabs(entry)]


def env_across_filesystems() -> bool:
    """Return git's reading of ``GIT_DISCOVERY_ACROSS_FILESYSTEM`` (false when unset)."""
    return os.environ.get("GIT_DISCOVERY_ACROSS_FILESYSTEM", "").strip().lower() in _TRUE


def git_root(
    start: StrPath = ".",
    *,
    ceilings: Iterable[StrPath] | None = None,
    across_filesystems: bool | None = None,
) -> Match | None:
    """Return the git working tree enclosing ``start``, or ``None``.

    ``match.directory`` is what ``git rev-parse --show-toplevel`` prints: the main
    working tree, a linked worktree (its ``.git`` is a file), or a submodule checkout.
    Like git, the walk follows the physical path and an invalid ``.git`` entry (an empty
    directory, a file without a valid ``gitdir:`` line) is ignored.

    ``ceilings`` defaults to ``GIT_CEILING_DIRECTORIES`` and ``across_filesystems`` to
    ``GIT_DISCOVERY_ACROSS_FILESYSTEM``; when false, the walk stops at a filesystem
    boundary. ``GIT_DIR`` and ``GIT_WORK_TREE`` are not consulted. Raises
    ``StartNotFoundError`` when ``start`` does not exist.
    """
    if ceilings is None:
        ceilings = env_ceilings()
    if across_filesystems is None:
        across_filesystems = env_across_filesystems()
    return find(GIT_MARKER, start=start, ceilings=ceilings, same_filesystem=not across_filesystems)
