"""Recognise repository directories and ``.git`` files byte for byte as git does."""

from __future__ import annotations

import os
import re
from pathlib import Path

from walkupward._gitconfig import core_bare

_OBJECT_ID = re.compile(rb"[0-9a-fA-F]{40}")
_GITDIR = b"gitdir: "
# git reads at most this many bytes of HEAD and of a symlink target.
_HEAD_LIMIT = 255


def _valid_head(path: Path) -> bool:
    if path.is_symlink():
        target = os.readlink(path)[:_HEAD_LIMIT]
        return target.replace("\\", "/").startswith("refs/")
    with open(path, "rb") as handle:
        head = handle.read(_HEAD_LIMIT).split(b"\0", 1)[0]
    if head.startswith(b"ref:") and head[4:].lstrip(b" \t\n\r").startswith(b"refs/"):
        return True
    return _OBJECT_ID.match(head) is not None


def _metadata_path(raw: bytes) -> str:
    # git strips trailing line breaks, then uses the bytes as a C string, so a NUL
    # ends the path and anything after it is ignored.
    return os.fsdecode(raw.rstrip(b"\r\n").split(b"\0", 1)[0])


def common_dir(path: Path) -> Path:
    """Return the directory holding a repository's shared ``objects``, ``refs`` and config.

    ``GIT_COMMON_DIR`` wins when set; otherwise a linked worktree names it in its
    ``commondir`` file, relative to ``path`` unless absolute.
    """
    env = os.environ.get("GIT_COMMON_DIR")
    if env is not None:
        return Path(env)
    if (path / "commondir").is_file():
        return path / _metadata_path((path / "commondir").read_bytes())
    return path


def is_git_directory(path: Path) -> bool:
    """Return whether ``path`` looks like a repository directory to git.

    Mirrors git's own test: a valid ``HEAD`` (``ref:`` followed by ``refs/...`` within
    the first 255 bytes, a symlink into ``refs/``, or an object id), an object store
    (``GIT_OBJECT_DIRECTORY`` when set, else ``objects``) and ``refs`` in the common
    directory.
    """
    try:
        if not _valid_head(path / "HEAD"):
            return False
        common = common_dir(path)
        objects = os.environ.get("GIT_OBJECT_DIRECTORY")
        if objects is not None:
            has_objects = os.access(objects, os.X_OK)
        else:
            has_objects = (common / "objects").is_dir()
        return has_objects and (common / "refs").is_dir()
    except (OSError, ValueError):
        return False


def has_work_tree(path: Path) -> bool:
    """Return whether git gives the repository directory ``path`` a working tree.

    False when its config sets ``core.bare`` or when git would refuse that config. Like
    git, the setting is ignored when the repository borrows a common directory (a
    linked worktree, or ``GIT_COMMON_DIR``), since it then belongs to another checkout.
    """
    try:
        if "GIT_COMMON_DIR" in os.environ or os.path.exists(path / "commondir"):
            return True
        return core_bare(path / "config") is False
    except (OSError, ValueError):
        return False


def read_gitfile(path: Path) -> Path | None:
    """Return the repository directory named by a ``.git`` file, or ``None`` if invalid.

    Like git, the file must start with ``gitdir: `` (one space); the rest of the file,
    minus trailing line breaks and anything from a NUL on, is the path, taken from the
    file's directory when relative, and it must be a repository directory.
    """
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if not data.startswith(_GITDIR) or not data[len(_GITDIR) :].rstrip(b"\r\n"):
        return None
    try:
        target = Path(_metadata_path(data[len(_GITDIR) :]))
    except UnicodeDecodeError:
        # Bytes the platform cannot decode name no directory that could exist.
        return None
    target = target if target.is_absolute() else path.parent / target
    return target if is_git_directory(target) else None
