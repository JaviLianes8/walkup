"""Hostile inputs: very deep paths, overlong names and private exception text."""

from __future__ import annotations

import os
import traceback
import tracemalloc
from pathlib import Path

import pytest

from walkupward import Marker, WalkupPermissionError, find, find_up, walk_up


@pytest.mark.parametrize("with_ceiling", [False, True])
def test_a_very_deep_start_is_prepared_in_linear_memory(tmp_path: Path, with_ceiling: bool) -> None:
    deep = str(tmp_path) + "/a" * 4000
    ceilings = [str(tmp_path) + "/a" * 3999] if with_ceiling else []
    tracemalloc.start()
    try:
        first = next(walk_up(deep, ceilings=ceilings, stop_at=deep, resolve=False))
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert first == Path(os.path.normpath(deep))
    # Every ancestor at once would take tens of megabytes; one path is about 100 KB.
    assert peak < 5_000_000


def test_a_permission_failure_traceback_does_not_show_the_original_text(tmp_path: Path) -> None:
    (tmp_path / "cfg").touch()
    secret = "private-" + "x" * 50_000

    def deny(path: Path) -> bool:
        raise PermissionError(secret)

    with pytest.raises(WalkupPermissionError) as info:
        find(Marker("cfg", check=deny), start=tmp_path, stop_at=tmp_path, on_error="raise")
    shown = "".join(traceback.format_exception(info.value))
    assert "private-" not in shown and len(shown) < 5_000
    assert isinstance(info.value.__context__, PermissionError)


def test_an_overlong_marker_name_is_absent_not_a_raw_error(tmp_path: Path) -> None:
    name = "x" * 40_000
    assert find(name, start=tmp_path, stop_at=tmp_path) is None
    assert find(Marker.file(name), start=tmp_path, stop_at=tmp_path) is None
    assert find_up(name, tmp_path, tmp_path) is None


def test_a_check_raising_value_error_still_propagates(tmp_path: Path) -> None:
    (tmp_path / "cfg").touch()

    def broken(path: Path) -> bool:
        raise ValueError("from the callback")

    with pytest.raises(ValueError, match="from the callback"):
        find(Marker("cfg", check=broken), start=tmp_path, stop_at=tmp_path)
