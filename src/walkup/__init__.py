"""Walk up from a start directory to find a marker file or directory, typed and dependency free."""

from __future__ import annotations

from walkup._core import find_up, walk_up

__version__ = "0.1.0"

__all__ = ["find_up", "walk_up"]
