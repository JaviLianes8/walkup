"""Every search and preset passes its walk options through and keeps its marker kinds."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

import walkupward
from walkupward import Marker, MarkerNotFoundError, _walk, git_root, iter_git_roots

from conftest import GitRunner, make_repo, needs_git


def _first(found: object) -> object:
    if isinstance(found, list):
        return found[0] if found else None
    if isinstance(found, walkupward.Match) or found is None:
        return found
    return next(iter(found), None)  # type: ignore[call-overload]


def _require(*markers: Any, **options: Any) -> object:
    try:
        return walkupward.require(*markers, **options)
    except MarkerNotFoundError:
        return None


SEARCHES: dict[str, tuple[Callable[..., object], str]] = {
    "find": (lambda **o: walkupward.find("m", **o), "m"),
    "find_all": (lambda **o: walkupward.find_all("m", **o), "m"),
    "iter_matches": (lambda **o: walkupward.iter_matches("m", **o), "m"),
    "require": (lambda **o: _require("m", **o), "m"),
    "python_root": (lambda start, **o: walkupward.python_root(start, **o), "pyproject.toml"),
    "node_root": (lambda start, **o: walkupward.node_root(start, **o), "package.json"),
    "editorconfig_chain": (
        lambda start, **o: walkupward.editorconfig_chain(start, **o),
        ".editorconfig",
    ),
}


@pytest.fixture
def tree(tmp_path: Path) -> tuple[Path, Path]:
    parent = tmp_path.resolve()
    child = parent / "child"
    child.mkdir()
    return parent, child


@pytest.mark.parametrize("option", ["stop_at", "ceilings", "same_filesystem"])
@pytest.mark.parametrize("name", list(SEARCHES))
def test_walk_options_reach_the_walk(
    tree: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch, name: str, option: str
) -> None:
    parent, child = tree
    search, marker = SEARCHES[name]
    (parent / marker).write_text("")
    assert _first(search(start=child)) is not None
    monkeypatch.setattr(_walk, "_device", lambda path: 1 if path == child else 2)
    value: object = {"stop_at": child, "ceilings": [parent], "same_filesystem": True}[option]
    assert _first(search(start=child, **{option: value})) is None


@pytest.mark.parametrize("name", ["python_root", "node_root", "editorconfig_chain"])
def test_preset_markers_must_be_regular_files(tree: tuple[Path, Path], name: str) -> None:
    parent, child = tree
    search, marker = SEARCHES[name]
    (parent / marker).mkdir()
    assert _first(search(start=child)) is None


def test_marker_dir_keeps_and_runs_its_check(tree: tuple[Path, Path]) -> None:
    parent, child = tree
    (parent / "candidate").mkdir()
    seen: list[Path] = []

    def reject(path: Path) -> bool:
        seen.append(path)
        return False

    marker = Marker.dir("candidate", reject)
    assert marker.check is reject
    assert walkupward.find(marker, start=child) is None
    assert seen == [parent / "candidate"]
    assert Marker.file("candidate", reject).check is reject


@needs_git
@pytest.mark.parametrize(
    ("env", "across", "crosses"),
    [
        (None, None, False),
        (None, False, False),
        ("0", None, False),
        ("1", None, True),
        ("0", True, True),
    ],
)
def test_git_discovery_honours_the_filesystem_policy(
    git: GitRunner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    env: str | None,
    across: bool | None,
    crosses: bool,
) -> None:
    repo = make_repo(git, tmp_path / "repo").resolve()
    start = repo / "mount"
    start.mkdir()
    if env is not None:
        monkeypatch.setenv("GIT_DISCOVERY_ACROSS_FILESYSTEM", env)
    monkeypatch.setattr(_walk, "_device", lambda path: 1 if path == start else 2)
    match = git_root(start, across_filesystems=across)
    assert (match is not None and match.directory == repo) is crosses
    roots = [m.directory for m in iter_git_roots(start, across_filesystems=across)]
    assert roots == ([repo] if crosses else [])
