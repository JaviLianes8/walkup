from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path, PureWindowsPath

import pytest

from walkup import find, walk_up

from conftest import IS_WINDOWS, link_dir


def _tree(tmp_path: Path) -> Path:
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    return deep


def test_a_ceiling_is_never_entered(tmp_path: Path) -> None:
    deep = _tree(tmp_path)
    walked = list(walk_up(deep, ceilings=[tmp_path / "a"]))
    assert walked == [deep.resolve(), deep.parent.resolve()]


def test_the_nearest_of_several_ceilings_wins(tmp_path: Path) -> None:
    deep = _tree(tmp_path)
    walked = list(walk_up(deep, ceilings=[tmp_path, tmp_path / "a" / "b"]))
    assert walked == [deep.resolve()]


def test_a_ceiling_that_is_not_an_ancestor_is_ignored(tmp_path: Path) -> None:
    deep = _tree(tmp_path)
    (tmp_path / "elsewhere").mkdir()
    assert list(walk_up(deep, ceilings=[tmp_path / "elsewhere"])) == list(walk_up(deep))


def test_starting_at_a_ceiling_searches_it_and_keeps_climbing(tmp_path: Path) -> None:
    start = tmp_path / "a"
    start.mkdir()
    assert list(walk_up(start, ceilings=[start])) == list(walk_up(start))


def test_stop_at_is_inclusive_and_ignored_off_the_path(tmp_path: Path) -> None:
    deep = _tree(tmp_path)
    walked = list(walk_up(deep, stop_at=tmp_path / "a"))
    assert walked[-1] == (tmp_path / "a").resolve()
    assert len(walked) == 3
    assert list(walk_up(deep, stop_at=tmp_path / "zzz")) == list(walk_up(deep))


def test_the_walk_ends_at_the_drive_or_filesystem_root(tmp_path: Path) -> None:
    walked = list(walk_up(tmp_path))
    anchor = Path(tmp_path.resolve().anchor)
    assert walked[-1] == anchor
    assert list(walk_up(anchor)) == [anchor]


def test_find_works_from_the_root_itself(tmp_path: Path) -> None:
    anchor = Path(tmp_path.resolve().anchor)
    assert find("this-marker-does-not-exist.zz", start=anchor) is None


@pytest.mark.skipif(not IS_WINDOWS, reason="UNC paths only exist on Windows")
def test_a_lexical_unc_walk_stops_at_the_share_root() -> None:
    walked = list(walk_up(r"\\server\share\a\b", resolve=False))
    assert [str(p) for p in walked] == [
        r"\\server\share\a\b",
        r"\\server\share\a",
        "\\\\server\\share\\",
    ]


@pytest.mark.skipif(not IS_WINDOWS, reason="UNC paths only exist on Windows")
def test_a_real_unc_walk_stops_at_the_share_root(tmp_path: Path) -> None:
    local = PureWindowsPath(tmp_path.resolve())
    unc = Path("\\\\localhost\\" + local.drive[0] + "$" + str(local)[2:])
    if not unc.is_dir():
        pytest.skip("the administrative share of the local drive is not reachable")
    (tmp_path / "marker.txt").write_text("")
    walked = list(walk_up(unc / "x", resolve=False))
    assert str(walked[-1]).lower() == ("\\\\localhost\\" + local.drive[0] + "$\\").lower()
    assert find("marker.txt", start=unc, resolve=False) is not None


def _linked_layout(tmp_path: Path) -> tuple[Path, Path]:
    real = tmp_path / "physical" / "real"
    real.mkdir(parents=True)
    (tmp_path / "physical" / "phys.marker").write_text("")
    (tmp_path / "logical").mkdir()
    (tmp_path / "logical" / "logic.marker").write_text("")
    link = tmp_path / "logical" / "link"
    link_dir(real, link)
    return real, link


def test_resolve_walks_the_physical_path_through_a_link(tmp_path: Path) -> None:
    real, link = _linked_layout(tmp_path)
    assert next(walk_up(link)) == real.resolve()
    assert find("phys.marker", start=link) is not None
    assert find("logic.marker", start=link) is None


def test_lexical_walks_keep_the_link_in_the_path(tmp_path: Path) -> None:
    _, link = _linked_layout(tmp_path)
    walked = list(walk_up(link, resolve=False))
    assert walked[0] == Path(os.path.normpath(link.absolute()))
    assert walked[1] == Path(os.path.normpath((tmp_path / "logical").absolute()))
    assert find("logic.marker", start=link, resolve=False) is not None
    assert find("phys.marker", start=link, resolve=False) is None


def test_lexical_walks_collapse_dot_dot_textually(tmp_path: Path) -> None:
    _, link = _linked_layout(tmp_path)
    first = next(walk_up(link / "..", resolve=False))
    assert first == Path(os.path.normpath((tmp_path / "logical").absolute()))
    # Win32 collapses ".." before the path reaches the filesystem, so even a resolved
    # walk lands on the lexical parent there; POSIX follows the link first.
    expected = "logical" if IS_WINDOWS else "physical"
    assert next(walk_up(link / "..")) == (tmp_path / expected).resolve()


def test_same_filesystem_does_not_stop_on_one_device(tmp_path: Path) -> None:
    deep = _tree(tmp_path)
    assert list(walk_up(deep, same_filesystem=True)) == list(walk_up(deep))


def _other_volume() -> Path | None:
    here = os.stat(tempfile.gettempdir()).st_dev
    candidates = ["D:\\", "E:\\"] if IS_WINDOWS else ["/dev/shm", "/run/user"]
    for raw in candidates:
        path = Path(raw)
        try:
            if path.is_dir() and os.stat(path).st_dev != here and os.access(path, os.W_OK):
                return path
        except OSError:
            continue
    return None


def test_same_filesystem_stops_before_another_device(tmp_path: Path) -> None:
    volume = _other_volume()
    if volume is None:
        pytest.skip("no second writable filesystem is mounted on this machine")
    remote = Path(tempfile.mkdtemp(dir=volume))
    try:
        (remote / "sub").mkdir()
        link = tmp_path / "bridge"
        link_dir(remote, link)
        walked = list(walk_up(link / "sub", resolve=False, same_filesystem=True))
        assert [p.name for p in walked] == ["sub", "bridge"]
        loose = list(walk_up(link / "sub", resolve=False))
        assert len(loose) > 2
    finally:
        shutil.rmtree(remote, ignore_errors=True)
