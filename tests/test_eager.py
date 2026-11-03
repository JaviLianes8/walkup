"""Arguments are checked when a search is called, not when its first item is requested."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

import walkupward
from walkupward import iter_git_roots, iter_matches, walk_up


@pytest.mark.parametrize("option", ["stop_at", "ceilings"])
def test_iter_matches_rejects_a_non_path_boundary_at_call_time(tmp_path: Path, option: str) -> None:
    value: object = 42 if option == "stop_at" else [42]
    with pytest.raises(TypeError):
        iter_matches("x", start=tmp_path, **{option: value})  # type: ignore[arg-type]


@pytest.mark.parametrize("option", ["stop_at", "ceilings"])
def test_walk_up_rejects_a_non_path_boundary_at_call_time(tmp_path: Path, option: str) -> None:
    value: object = 42 if option == "stop_at" else [42]
    with pytest.raises(TypeError):
        walk_up(tmp_path, **{option: value})  # type: ignore[arg-type]


def test_iter_git_roots_rejects_a_non_path_ceiling_at_call_time(tmp_path: Path) -> None:
    with pytest.raises(TypeError):
        iter_git_roots(tmp_path, ceilings=[42])  # type: ignore[list-item]


SEARCHES: list[Callable[..., Any]] = [
    lambda start: walkupward.find(".", start=start),
    lambda start: walkupward.find_all(".", start=start),
    lambda start: walkupward.iter_matches(".", start=start),
    lambda start: walkupward.require(".", start=start),
    walkupward.git_root,
    walkupward.iter_git_roots,
    walkupward.python_root,
    walkupward.node_root,
    walkupward.editorconfig_chain,
]


@pytest.mark.parametrize("search", SEARCHES)
@pytest.mark.parametrize("start", [2**32, 0, b"."])
def test_a_start_that_is_not_a_path_raises_type_error(
    search: Callable[..., Any], start: object
) -> None:
    # 0 names an open file descriptor, which os.path.exists would accept.
    with pytest.raises(TypeError):
        search(start)
