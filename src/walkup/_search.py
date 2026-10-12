"""Marker searches up the tree: nearest match, every match, or an error."""

from __future__ import annotations

import os
import stat
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Literal

from walkup._types import (
    Marker,
    MarkerLike,
    MarkerNotFoundError,
    Match,
    Mode,
    StartNotFoundError,
    WalkupPermissionError,
    coerce_markers,
)
from walkup._walk import StrPath, walk_up

OnError = Literal["skip", "raise"]


def iter_matches(
    *markers: MarkerLike,
    start: StrPath = ".",
    mode: Mode = "any",
    ceilings: Iterable[StrPath] = (),
    stop_at: StrPath | None = None,
    same_filesystem: bool = False,
    resolve: bool = True,
    on_error: OnError = "skip",
) -> Iterator[Match]:
    """Yield a ``Match`` for every directory on the walk that satisfies the markers.

    Directories come nearest first. With ``mode="any"`` a directory matches when at
    least one marker is present; with ``mode="all"`` every marker must be present. Plain
    strings become ``Marker(name)``. ``ceilings``, ``stop_at``, ``same_filesystem`` and
    ``resolve`` shape the walk exactly as in ``walk_up``.

    A candidate that cannot be inspected because of a permission error counts as absent
    with ``on_error="skip"``; with ``on_error="raise"`` it raises
    ``WalkupPermissionError``. Raises ``StartNotFoundError`` when ``start`` does not
    exist and ``InvalidMarkerError`` when no marker is given. The arguments are checked
    when the call is made, before the first item is requested.
    """
    wanted = coerce_markers(markers)
    if not os.path.exists(start):
        raise StartNotFoundError(Path(start))
    if mode not in ("any", "all"):
        raise ValueError(f"mode must be 'any' or 'all', got {mode!r}")
    if on_error not in ("skip", "raise"):
        raise ValueError(f"on_error must be 'skip' or 'raise', got {on_error!r}")
    walk = walk_up(
        start,
        ceilings=tuple(ceilings),
        stop_at=stop_at,
        same_filesystem=same_filesystem,
        resolve=resolve,
    )
    return _matches(walk, wanted, mode, on_error)


def find(
    *markers: MarkerLike,
    start: StrPath = ".",
    mode: Mode = "any",
    ceilings: Iterable[StrPath] = (),
    stop_at: StrPath | None = None,
    same_filesystem: bool = False,
    resolve: bool = True,
    on_error: OnError = "skip",
) -> Match | None:
    """Return the nearest ``Match`` walking up from ``start``, or ``None``.

    Takes the same arguments as ``iter_matches``.

    >>> match = find("pyproject.toml", "setup.cfg")  # doctest: +SKIP
    >>> match.directory, match.names  # doctest: +SKIP
    (PosixPath('/home/me/project'), ('pyproject.toml',))
    """
    found = iter_matches(
        *markers,
        start=start,
        mode=mode,
        ceilings=ceilings,
        stop_at=stop_at,
        same_filesystem=same_filesystem,
        resolve=resolve,
        on_error=on_error,
    )
    return next(found, None)


def find_all(
    *markers: MarkerLike,
    start: StrPath = ".",
    mode: Mode = "any",
    ceilings: Iterable[StrPath] = (),
    stop_at: StrPath | None = None,
    same_filesystem: bool = False,
    resolve: bool = True,
    on_error: OnError = "skip",
) -> list[Match]:
    """Return every ``Match`` walking up from ``start``, nearest first.

    Takes the same arguments as ``iter_matches``; the list is empty when nothing matches.
    """
    found = iter_matches(
        *markers,
        start=start,
        mode=mode,
        ceilings=ceilings,
        stop_at=stop_at,
        same_filesystem=same_filesystem,
        resolve=resolve,
        on_error=on_error,
    )
    return list(found)


def require(
    *markers: MarkerLike,
    start: StrPath = ".",
    mode: Mode = "any",
    ceilings: Iterable[StrPath] = (),
    stop_at: StrPath | None = None,
    same_filesystem: bool = False,
    resolve: bool = True,
    on_error: OnError = "skip",
) -> Match:
    """Return the nearest ``Match``, raising ``MarkerNotFoundError`` when there is none.

    Takes the same arguments as ``iter_matches``. The error carries ``markers``,
    ``start`` and ``mode`` for a precise message.
    """
    found = find(
        *markers,
        start=start,
        mode=mode,
        ceilings=ceilings,
        stop_at=stop_at,
        same_filesystem=same_filesystem,
        resolve=resolve,
        on_error=on_error,
    )
    if found is None:
        raise MarkerNotFoundError(coerce_markers(markers), Path(start), mode)
    return found


def _matches(
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
        info = os.stat(candidate)
        if marker.kind == "file" and not stat.S_ISREG(info.st_mode):
            return None
        if marker.kind == "dir" and not stat.S_ISDIR(info.st_mode):
            return None
        if marker.check is not None and not marker.check(candidate):
            return None
    except PermissionError as exc:
        if on_error == "raise":
            raise WalkupPermissionError(candidate) from exc
        return None
    except OSError:
        return None
    return candidate
