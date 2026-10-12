from __future__ import annotations

import pickle
from pathlib import Path

import pytest

from walkup import (
    InvalidMarkerError,
    Marker,
    MarkerNotFoundError,
    StartNotFoundError,
    WalkupError,
    find,
    find_all,
    iter_matches,
    require,
)

from conftest import IS_WINDOWS, symlink


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """tmp/pyproject.toml + .git/, tmp/pkg/setup.cfg, tmp/pkg/src/deep (start)."""
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    (tmp_path / ".git").mkdir()
    (tmp_path / "pkg" / "src" / "deep").mkdir(parents=True)
    (tmp_path / "pkg" / "setup.cfg").write_text("[metadata]\n")
    return tmp_path


def test_find_reports_the_directory_and_every_marker_present(tree: Path) -> None:
    match = find(".git", "pyproject.toml", start=tree)
    assert match is not None
    assert match.directory == tree.resolve()
    assert match.names == (".git", "pyproject.toml")
    assert match.marker == Marker(".git")
    assert match.path == tree.resolve() / ".git"
    assert match.paths[1] == tree.resolve() / "pyproject.toml"


def test_any_mode_takes_the_nearest_directory_with_one_marker(tree: Path) -> None:
    match = find("pyproject.toml", "setup.cfg", start=tree / "pkg" / "src" / "deep")
    assert match is not None
    assert match.directory == (tree / "pkg").resolve()
    assert match.names == ("setup.cfg",)


def test_all_mode_requires_every_marker_in_one_directory(tree: Path) -> None:
    start = tree / "pkg" / "src" / "deep"
    (tree / "pkg" / ".git").write_text("not a dir")
    match = find("setup.cfg", "pyproject.toml", start=start, mode="all")
    assert match is None
    match = find(Marker.dir(".git"), "pyproject.toml", start=start, mode="all")
    assert match is not None and match.directory == tree.resolve()


def test_find_all_lists_matches_nearest_first(tree: Path) -> None:
    (tree / "pkg" / "pyproject.toml").write_text("")
    matches = find_all("pyproject.toml", start=tree / "pkg" / "src")
    assert [m.directory for m in matches][:2] == [(tree / "pkg").resolve(), tree.resolve()]
    assert find_all("nothing-here.zz", start=tree) == []


def test_iter_matches_is_lazy_but_checks_arguments_at_call_time(tree: Path) -> None:
    found = iter_matches("pyproject.toml", start=tree / "pkg")
    assert next(found).directory == tree.resolve()
    with pytest.raises(StartNotFoundError):
        iter_matches("x", start=tree / "missing")
    with pytest.raises(InvalidMarkerError):
        iter_matches(start=tree)
    with pytest.raises(ValueError):
        iter_matches("x", start=tree, mode="some")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        iter_matches("x", start=tree, on_error="ignore")  # type: ignore[arg-type]


def test_require_returns_or_raises_a_lookup_error(tree: Path) -> None:
    assert require("setup.cfg", start=tree / "pkg" / "src").directory == (tree / "pkg").resolve()
    with pytest.raises(MarkerNotFoundError) as info:
        require("a.zz", "b.zz", start=tree, mode="all", stop_at=tree)
    assert isinstance(info.value, LookupError) and isinstance(info.value, WalkupError)
    assert info.value.mode == "all" and info.value.start == tree
    assert [m.name for m in info.value.markers] == ["a.zz", "b.zz"]
    assert "all of: a.zz, b.zz" in str(info.value)


def test_a_missing_start_is_a_file_not_found_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError) as info:
        find("x", start=tmp_path / "nope")
    assert isinstance(info.value, StartNotFoundError)
    assert info.value.start == tmp_path / "nope"


def test_kinds_separate_files_from_directories(tmp_path: Path) -> None:
    (tmp_path / "out").mkdir()
    (tmp_path / "cfg").write_text("")
    assert find(Marker.file("out"), start=tmp_path, stop_at=tmp_path) is None
    assert find(Marker.dir("cfg"), start=tmp_path, stop_at=tmp_path) is None
    assert find(Marker.dir("out"), start=tmp_path) is not None
    assert find(Marker("cfg", "file"), start=tmp_path) is not None


def test_a_check_looks_inside_the_candidate(tmp_path: Path) -> None:
    inner = tmp_path / "inner"
    inner.mkdir()
    (inner / "tox.ini").write_text("[flake8]\n")
    (tmp_path / "tox.ini").write_text("[tox]\nenvlist = py\n")
    seen: list[Path] = []

    def has_tox(path: Path) -> bool:
        seen.append(path)
        return "[tox]" in path.read_text()

    match = find(Marker.file("tox.ini", has_tox), start=inner)
    assert match is not None and match.directory == tmp_path.resolve()
    assert seen[0] == inner.resolve() / "tox.ini"


def test_a_marker_may_be_a_relative_path(tmp_path: Path) -> None:
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "__init__.py").write_text("")
    match = find("src/pkg/__init__.py", start=tmp_path / "src" / "pkg")
    assert match is not None and match.directory == tmp_path.resolve()


@pytest.mark.parametrize("name", ["", "/etc", "a\0b", *(["C:\\x", "C:x"] if IS_WINDOWS else [])])
def test_invalid_marker_names_are_rejected(name: str) -> None:
    with pytest.raises(InvalidMarkerError) as info:
        Marker(name)
    assert isinstance(info.value, ValueError)


def test_an_unknown_kind_is_rejected() -> None:
    with pytest.raises(InvalidMarkerError):
        Marker("x", "socket")  # type: ignore[arg-type]


def test_a_broken_symlink_does_not_count_as_present(tmp_path: Path) -> None:
    symlink(tmp_path / "gone", tmp_path / "dangling")
    assert find("dangling", start=tmp_path, stop_at=tmp_path) is None


def test_errors_survive_pickling(tmp_path: Path) -> None:
    errors = [
        StartNotFoundError(tmp_path),
        MarkerNotFoundError((Marker("a"),), tmp_path, "any"),
        InvalidMarkerError("bad"),
    ]
    for error in errors:
        copy = pickle.loads(pickle.dumps(error))
        assert type(copy) is type(error) and str(copy) == str(error)


def test_the_not_found_message_names_the_absolute_start(tmp_path: Path) -> None:
    with pytest.raises(MarkerNotFoundError) as info:
        require("nothing.zz", start=".", stop_at=".")
    assert str(Path.cwd()) in str(info.value)
