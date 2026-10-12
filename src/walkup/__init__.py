"""Walk up from a start directory to find a marker file or directory, typed and dependency free."""

from __future__ import annotations

from walkup._core import find_up
from walkup._git import git_root
from walkup._presets import editorconfig_chain, node_root, python_root
from walkup._search import find, find_all, iter_matches, require
from walkup._types import (
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
from walkup._walk import walk_up

__version__ = "0.2.0"

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
    "iter_matches",
    "node_root",
    "python_root",
    "require",
    "walk_up",
]
