"""Marker searches up the tree: nearest match, every match, or an error."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Literal

from walkup._probe import matches, probe_start
from walkup._types import (
    InvalidMarkerError,
    MarkerLike,
    MarkerNotFoundError,
    Match,
    Mode,
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

    >>> [m.names for m in iter_matches(".", stop_at=".")]
    [('.',)]
    """
    wanted = coerce_markers(markers)
    probe_start(start)
    if mode not in ("any", "all"):
        raise InvalidMarkerError("mode must be any or all")
    if on_error not in ("skip", "raise"):
        raise InvalidMarkerError("on_error must be skip or raise")
    walk = walk_up(
        start,
        ceilings=tuple(ceilings),
        stop_at=stop_at,
        same_filesystem=same_filesystem,
        resolve=resolve,
    )
    return matches(walk, wanted, mode, on_error)


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

    >>> match = find(".", stop_at=".")
    >>> match is not None and match.directory == Path.cwd()
    True
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

    >>> len(find_all(".", stop_at="."))
    1
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

    >>> require(".", stop_at=".").names
    ('.',)
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
