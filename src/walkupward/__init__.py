"""Walk up from a start directory to find a marker file or directory, typed and dependency free."""

from __future__ import annotations

from typing import get_type_hints as _get_type_hints

from walkupward._core import find_up
from walkupward._git import git_root, iter_git_roots
from walkupward._presets import editorconfig_chain, node_root, python_root
from walkupward._search import find, find_all, iter_matches, require
from walkupward._types import (
    InvalidMarkerError,
    Kind,
    Marker,
    MarkerNotFoundError,
    Match,
    Mode,
    StartNotFoundError,
    WalkupError,
    WalkupPermissionError,
)
from walkupward._walk import walk_up

__version__ = "1.0.0"

__all__ = [
    "InvalidMarkerError",
    "Kind",
    "Marker",
    "MarkerNotFoundError",
    "Match",
    "Mode",
    "StartNotFoundError",
    "WalkupError",
    "WalkupPermissionError",
    "editorconfig_chain",
    "find",
    "find_all",
    "find_up",
    "git_root",
    "iter_git_roots",
    "iter_matches",
    "node_root",
    "python_root",
    "require",
    "walk_up",
]

# Literal aliases use module doctests because their runtime objects belong to typing.
__test__ = {
    "Kind": ">>> from typing import get_args\n>>> get_args(Kind)\n('any', 'file', 'dir')",
    "Mode": ">>> from typing import get_args\n>>> get_args(Mode)\n('any', 'all')",
}

for _value in (
    Marker,
    Match,
    WalkupError,
    InvalidMarkerError,
    StartNotFoundError,
    MarkerNotFoundError,
    WalkupPermissionError,
):
    _value.__annotations__ = _get_type_hints(_value)
    _value.__module__ = __name__
del _value
del _get_type_hints
globals().pop("annotations", None)
