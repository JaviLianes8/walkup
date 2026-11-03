"""Typed search failures with private input retained in attributes, not messages."""

from __future__ import annotations

import errno
from pathlib import Path


class WalkupError(Exception):
    """Base class for every error walkup raises on purpose.

    >>> isinstance(WalkupError("search failed"), Exception)
    True
    """


class InvalidMarkerError(WalkupError, ValueError):
    """A marker is empty, absolute, has an unknown kind, or no marker was given.

    >>> isinstance(InvalidMarkerError("invalid marker"), ValueError)
    True
    """


class StartNotFoundError(WalkupError, FileNotFoundError):
    """The start path does not exist, so there is nothing to walk up from.

    >>> from pathlib import Path
    >>> error = StartNotFoundError(Path("missing"))
    >>> error.start == Path("missing") and isinstance(error, FileNotFoundError)
    True
    """

    def __init__(self, start: Path) -> None:
        super().__init__(errno.ENOENT, "start path does not exist", str(start))
        self.start = start

    def __str__(self) -> str:
        return "start path does not exist"

    def __reduce__(self) -> tuple[type[StartNotFoundError], tuple[Path]]:
        return (type(self), (self.start,))


class WalkupPermissionError(WalkupError, PermissionError):
    """A candidate could not be inspected and ``on_error="raise"`` was requested.

    >>> from pathlib import Path
    >>> error = WalkupPermissionError(Path("private"))
    >>> error.path == Path("private") and isinstance(error, PermissionError)
    True
    """

    def __init__(self, path: Path) -> None:
        super().__init__(errno.EACCES, "permission denied while probing", str(path))
        self.path = path

    def __str__(self) -> str:
        return "permission denied while probing"

    def __reduce__(self) -> tuple[type[WalkupPermissionError], tuple[Path]]:
        return (type(self), (self.path,))
