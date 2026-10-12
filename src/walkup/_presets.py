"""Ready-made finders for Python projects, Node projects and EditorConfig files."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from walkup._search import find, iter_matches
from walkup._types import Marker, Match
from walkup._walk import StrPath

PYTHON_MARKERS = (
    Marker.file("pyproject.toml"),
    Marker.file("setup.cfg"),
    Marker.file("setup.py"),
)
"""Files that mark a Python project, in order of preference within one directory."""

NODE_MARKERS = (Marker.file("package.json"),)
"""The file that marks a Node project."""

EDITORCONFIG_MARKER = Marker.file(".editorconfig")
"""The EditorConfig file name."""


def python_root(
    start: StrPath = ".",
    *,
    ceilings: Iterable[StrPath] = (),
    stop_at: StrPath | None = None,
    same_filesystem: bool = False,
    resolve: bool = True,
) -> Match | None:
    """Return the nearest directory holding ``pyproject.toml``, ``setup.cfg`` or ``setup.py``.

    The nearest configuration file wins, the way formatters and linters stop at the first
    one they meet; ``match.names`` tells which of the three files are present. Options
    behave as in ``walk_up``. Raises ``StartNotFoundError`` when ``start`` does not exist.
    """
    return find(
        *PYTHON_MARKERS,
        start=start,
        ceilings=ceilings,
        stop_at=stop_at,
        same_filesystem=same_filesystem,
        resolve=resolve,
    )


def node_root(
    start: StrPath = ".",
    *,
    ceilings: Iterable[StrPath] = (),
    stop_at: StrPath | None = None,
    same_filesystem: bool = False,
    resolve: bool = True,
) -> Match | None:
    """Return the nearest directory holding a ``package.json`` file.

    This is the project a ``package.json`` based tool would pick. npm's own prefix lookup
    also stops at a ``node_modules`` directory; add ``Marker.dir("node_modules")`` to a
    ``find`` call for that behaviour.

    Options behave as in ``walk_up``. Raises ``StartNotFoundError`` when ``start`` does
    not exist.
    """
    return find(
        *NODE_MARKERS,
        start=start,
        ceilings=ceilings,
        stop_at=stop_at,
        same_filesystem=same_filesystem,
        resolve=resolve,
    )


def editorconfig_chain(
    start: StrPath = ".",
    *,
    ceilings: Iterable[StrPath] = (),
    stop_at: StrPath | None = None,
    same_filesystem: bool = False,
    resolve: bool = True,
) -> list[Path]:
    """Return every ``.editorconfig`` file that applies at ``start``, nearest first.

    Following the EditorConfig specification, the search continues upward until it reads
    a file whose preamble (the lines before the first ``[section]``) sets
    ``root = true``; that file is the last one returned. Keys and values are compared
    without regard to case, and ``#`` or ``;`` lines are comments. Inline comments are not
    recognised, as in the current specification, so ``root = true # x`` is not a root. A
    file that cannot be read is still listed but is not a root. Options behave as in
    ``walk_up``. Raises ``StartNotFoundError`` when ``start`` does not exist.
    """
    chain: list[Path] = []
    found = iter_matches(
        EDITORCONFIG_MARKER,
        start=start,
        ceilings=ceilings,
        stop_at=stop_at,
        same_filesystem=same_filesystem,
        resolve=resolve,
    )
    for match in found:
        chain.append(match.path)
        if declares_root(match.path):
            break
    return chain


def declares_root(path: Path) -> bool:
    """Return whether an ``.editorconfig`` preamble contains ``root = true``."""
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line[0] in "#;":
            continue
        if line.startswith("["):
            return False
        key, sep, value = line.partition("=")
        if sep and key.strip().lower() == "root" and value.strip().lower() == "true":
            return True
    return False
