"""Probe filesystem candidates under the requested error policy."""

from __future__ import annotations

import os
import stat
from collections.abc import Iterator
from pathlib import Path
from typing import Literal

from walkupward._types import Marker, Match, Mode, StartNotFoundError, WalkupPermissionError
from walkupward._walk import StrPath

OnError = Literal["skip", "raise"]


def probe_start(start: StrPath) -> None:
    """Raise ``TypeError`` for a non-path ``start`` and ``StartNotFoundError`` when missing."""
    # Path() rejects integers first; os.path.exists would read them as file descriptors.
    path = Path(start)
    if not os.path.exists(path):
        raise StartNotFoundError(path)


def matches(
    walk: Iterator[Path], wanted: tuple[Marker, ...], mode: Mode, on_error: OnError
) -> Iterator[Match]:
    for directory in walk:
        hits = [(m, p) for m in wanted if (p := probe(m, directory, on_error)) is not None]
        if hits and (mode == "any" or len(hits) == len(wanted)):
            yield Match(directory, tuple(m for m, _ in hits), tuple(p for _, p in hits))


def probe(marker: Marker, directory: Path, on_error: OnError = "skip") -> Path | None:
    """Return ``directory / marker.name`` when it satisfies ``marker``, else ``None``."""
    candidate = directory / marker.name
    try:
        try:
            info = os.stat(candidate)
        except ValueError:
            # A name the platform cannot express as a path (too long, for example)
            # cannot exist; errors raised by ``check`` still propagate below.
            return None
        if marker.kind == "file" and not stat.S_ISREG(info.st_mode):
            return None
        if marker.kind == "dir" and not stat.S_ISDIR(info.st_mode):
            return None
        if marker.check is not None and not marker.check(candidate):
            return None
    except PermissionError:
        if on_error == "raise":
            # The original stays in __context__ but is not displayed, since its message
            # may carry private paths or text of any size.
            raise WalkupPermissionError(candidate) from None
        return None
    except OSError:
        return None
    return candidate
