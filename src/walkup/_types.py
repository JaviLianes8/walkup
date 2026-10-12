"""Typed values shared across walkup: markers, matches and errors."""

from __future__ import annotations

import errno
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Literal

Kind = Literal["any", "file", "dir"]
"""What a marker must be: anything that exists, a regular file, or a directory."""

Mode = Literal["any", "all"]
"""Whether one marker is enough for a directory to match, or every marker is required."""

_KINDS = ("any", "file", "dir")


class WalkupError(Exception):
    """Base class for every error walkup raises on purpose."""


class InvalidMarkerError(WalkupError, ValueError):
    """A marker is empty, absolute, has an unknown kind, or no marker was given."""


class StartNotFoundError(WalkupError, FileNotFoundError):
    """The start path does not exist, so there is nothing to walk up from."""

    def __init__(self, start: Path) -> None:
        super().__init__(errno.ENOENT, "start path does not exist", str(start))
        self.start = start


class WalkupPermissionError(WalkupError, PermissionError):
    """A candidate could not be inspected and ``on_error="raise"`` was requested."""

    def __init__(self, path: Path) -> None:
        super().__init__(errno.EACCES, "permission denied while probing", str(path))
        self.path = path


@dataclass(frozen=True)
class Marker:
    """A name to look for in each directory on the walk.

    ``name`` is joined to every directory, so it may be a plain name such as
    ``"pyproject.toml"`` or a relative path such as ``"src/__init__.py"``. It must not
    be empty or absolute. ``kind`` restricts the match to regular files (``"file"``) or
    directories (``"dir"``); ``"any"`` accepts anything that exists (a broken symlink
    does not exist). ``check``, when given, runs after the kind test with the candidate
    path and must return ``True`` to accept it; use it to look inside a file.

    >>> Marker.file("package.json")
    Marker(name='package.json', kind='file', check=None)
    """

    name: str
    kind: Kind = "any"
    check: Callable[[Path], bool] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name or "\0" in self.name:
            raise InvalidMarkerError("a marker name must be a non-empty string without NUL")
        if PurePath(self.name).anchor:
            raise InvalidMarkerError(f"a marker name must be relative, got {self.name!r}")
        if self.kind not in _KINDS:
            raise InvalidMarkerError(f"kind must be one of {_KINDS}, got {self.kind!r}")

    @classmethod
    def file(cls, name: str, check: Callable[[Path], bool] | None = None) -> Marker:
        """Return a marker that only matches a regular file called ``name``."""
        return cls(name, "file", check)

    @classmethod
    def dir(cls, name: str, check: Callable[[Path], bool] | None = None) -> Marker:
        """Return a marker that only matches a directory called ``name``."""
        return cls(name, "dir", check)


MarkerLike = str | Marker
"""A marker, or a plain name that becomes ``Marker(name)``."""


def coerce_markers(markers: tuple[MarkerLike, ...]) -> tuple[Marker, ...]:
    """Turn names into markers and reject an empty selection."""
    if not markers:
        raise InvalidMarkerError("at least one marker is required")
    return tuple(m if isinstance(m, Marker) else Marker(m) for m in markers)


@dataclass(frozen=True)
class Match:
    """A directory on the walk that satisfied the search.

    ``markers`` lists every requested marker present in ``directory``, in the order they
    were requested, and ``paths`` holds the matching path for each one. ``marker`` and
    ``path`` are shortcuts for the first entry.
    """

    directory: Path
    markers: tuple[Marker, ...]
    paths: tuple[Path, ...]

    @property
    def marker(self) -> Marker:
        """The first requested marker present in ``directory``."""
        return self.markers[0]

    @property
    def path(self) -> Path:
        """The path of the first requested marker present in ``directory``."""
        return self.paths[0]

    @property
    def names(self) -> tuple[str, ...]:
        """The names of the markers present in ``directory``."""
        return tuple(marker.name for marker in self.markers)


class MarkerNotFoundError(WalkupError, LookupError):
    """No directory on the walk satisfied the search passed to ``require``."""

    def __init__(self, markers: tuple[Marker, ...], start: Path, mode: Mode) -> None:
        names = ", ".join(marker.name for marker in markers)
        joiner = "all of" if mode == "all" else "any of"
        super().__init__(f"no directory from {start} upward contains {joiner}: {names}")
        self.markers = markers
        self.start = start
        self.mode = mode
