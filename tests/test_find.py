from __future__ import annotations

from pathlib import Path

from walkup import find_up, walk_up


def test_finds_a_marker_in_a_parent_directory(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    nested = tmp_path / "src" / "pkg"
    nested.mkdir(parents=True)
    found = find_up("pyproject.toml", start=nested)
    assert found == (tmp_path / "pyproject.toml").resolve()


def test_returns_none_when_nothing_matches(tmp_path: Path) -> None:
    assert find_up("missing.marker", start=tmp_path) is None


def test_stops_at_the_root_boundary(tmp_path: Path) -> None:
    (tmp_path / "marker").write_text("")
    boundary = tmp_path / "project"
    start = boundary / "deep"
    start.mkdir(parents=True)
    assert find_up("marker", start=start, root=boundary) is None
    assert find_up("marker", start=start) == (tmp_path / "marker").resolve()


def test_root_boundary_is_inclusive(tmp_path: Path) -> None:
    boundary = tmp_path / "project"
    start = boundary / "deep"
    start.mkdir(parents=True)
    (boundary / ".git").mkdir()
    assert find_up(".git", start=start, root=boundary) == (boundary / ".git").resolve()


def test_tries_several_names_in_order(tmp_path: Path) -> None:
    (tmp_path / "setup.cfg").write_text("")
    (tmp_path / "pyproject.toml").write_text("")
    found = find_up(["pyproject.toml", "setup.cfg"], start=tmp_path)
    assert found == (tmp_path / "pyproject.toml").resolve()


def test_can_require_a_directory(tmp_path: Path) -> None:
    (tmp_path / ".git").write_text("gitfile")
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    start = repo / "src"
    start.mkdir()
    assert find_up(".git", start=start, kind="dir") == (repo / ".git").resolve()


def test_can_require_a_file(tmp_path: Path) -> None:
    (tmp_path / "config").mkdir()
    found = find_up("config", start=tmp_path, kind="file")
    assert found is None


def test_walk_up_yields_ancestors_in_order(tmp_path: Path) -> None:
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    walked = list(walk_up(deep))
    assert walked[:4] == [
        deep.resolve(),
        (tmp_path / "a" / "b").resolve(),
        (tmp_path / "a").resolve(),
        tmp_path.resolve(),
    ]
    assert walked[-1] == walked[-1].parent


def test_walk_up_starts_at_the_parent_of_a_file(tmp_path: Path) -> None:
    marker = tmp_path / "file.txt"
    marker.write_text("")
    assert next(walk_up(marker)) == tmp_path.resolve()
