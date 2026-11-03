"""Rare filesystem boundaries exercised with an injected device probe."""

from __future__ import annotations

from pathlib import Path

import pytest

from walkupward import _walk, find_all, walk_up


@pytest.mark.parametrize("device", [None, 2])
def test_walk_never_enters_a_different_or_unreadable_device(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, device: int | None
) -> None:
    start = tmp_path / "child"
    start.mkdir()
    monkeypatch.setattr(_walk, "_device", lambda path: 1 if path == start else device)
    assert list(walk_up(start, same_filesystem=True)) == [start]
    (tmp_path / "marker").touch()
    assert find_all("marker", start=start, same_filesystem=True) == []


def test_an_unreadable_start_device_still_yields_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_walk, "_device", lambda path: None)
    assert list(walk_up(tmp_path, same_filesystem=True)) == [tmp_path]


def test_duplicate_markers_keep_their_positions(tmp_path: Path) -> None:
    (tmp_path / "x").touch()
    match = find_all("x", "x", start=tmp_path, stop_at=tmp_path, mode="all")[0]
    assert match.names == ("x", "x")
    assert match.paths == (tmp_path / "x", tmp_path / "x")
