"""The documented promise of every public name, checked on one real workspace tree.

The tree is a git repository holding a Python package and a Node app:

    ws/ .git/ pyproject.toml .editorconfig(root)
    ws/packages/core/ setup.cfg
    ws/packages/core/src/core/ (start for Python questions)
    ws/apps/web/ package.json .editorconfig
    ws/apps/web/src/ (start for Node questions)
"""

from __future__ import annotations

from pathlib import Path

import pytest

import walkup

from conftest import GitRunner, make_repo, needs_git


@pytest.fixture
def ws(git: GitRunner, tmp_path: Path) -> Path:
    root = make_repo(git, tmp_path / "ws")
    (root / "pyproject.toml").write_text("[project]\nname = 'ws'\n")
    (root / ".editorconfig").write_text("root = true\n[*]\nindent_style = space\n")
    core = root / "packages" / "core"
    (core / "src" / "core").mkdir(parents=True)
    (core / "setup.cfg").write_text("[metadata]\nname = core\n")
    web = root / "apps" / "web"
    (web / "src").mkdir(parents=True)
    (web / "package.json").write_text("{}")
    (web / ".editorconfig").write_text("[*.js]\nindent_size = 2\n")
    return root.resolve()


pytestmark = needs_git


def test_walk_up_yields_nearest_first_and_honours_every_option(ws: Path) -> None:
    start = ws / "packages" / "core" / "src"
    walked = list(walkup.walk_up(start))
    assert walked[:3] == [start, start.parent, start.parent.parent]
    assert list(walkup.walk_up(start, ceilings=[ws])) == walked[:3]
    assert list(walkup.walk_up(start, stop_at=ws)) == walked[:4]
    assert list(walkup.walk_up(start, same_filesystem=True)) == walked
    assert list(walkup.walk_up(start, resolve=False)) == walked


def test_find_up_keeps_its_original_contract(ws: Path) -> None:
    start = ws / "packages" / "core" / "src"
    assert walkup.find_up(["pyproject.toml", "setup.cfg"], start) == start.parent / "setup.cfg"
    assert walkup.find_up(".git", start, kind="dir") == ws / ".git"
    assert walkup.find_up("pyproject.toml", start, root=start.parent) is None


def test_find_returns_a_typed_match_naming_the_markers(ws: Path) -> None:
    match = walkup.find(walkup.Marker.dir(".git"), "pyproject.toml", start=ws / "apps")
    assert isinstance(match, walkup.Match)
    assert (match.directory, match.names, match.path) == (
        ws,
        (".git", "pyproject.toml"),
        ws / ".git",
    )
    assert match.marker.kind == "dir"


def test_find_all_and_iter_matches_agree_nearest_first(ws: Path) -> None:
    start = ws / "apps" / "web" / "src"
    found = walkup.find_all(".editorconfig", start=start)
    assert [m.directory for m in found][:2] == [ws / "apps" / "web", ws]
    assert list(walkup.iter_matches(".editorconfig", start=start))[:2] == found[:2]


def test_all_mode_and_require(ws: Path) -> None:
    start = ws / "apps" / "web" / "src"
    both = walkup.require("package.json", ".editorconfig", start=start, mode="all")
    assert both.directory == ws / "apps" / "web"
    with pytest.raises(walkup.MarkerNotFoundError):
        walkup.require("package.json", "pyproject.toml", start=start, mode="all", stop_at=ws)


def test_presets_answer_project_questions(ws: Path) -> None:
    git_match = walkup.git_root(ws / "apps" / "web" / "src")
    python_match = walkup.python_root(ws / "packages" / "core" / "src" / "core")
    node_match = walkup.node_root(ws / "apps" / "web" / "src")
    assert git_match is not None and git_match.directory == ws
    assert python_match is not None and python_match.names == ("setup.cfg",)
    assert node_match is not None and node_match.directory == ws / "apps" / "web"
    chain = walkup.editorconfig_chain(ws / "apps" / "web" / "src")
    assert chain == [ws / "apps" / "web" / ".editorconfig", ws / ".editorconfig"]


def test_every_error_is_a_walkup_error_and_a_builtin(ws: Path) -> None:
    pairs = [
        (walkup.InvalidMarkerError, ValueError),
        (walkup.StartNotFoundError, FileNotFoundError),
        (walkup.MarkerNotFoundError, LookupError),
        (walkup.WalkupPermissionError, PermissionError),
    ]
    for error, builtin in pairs:
        assert issubclass(error, walkup.WalkupError) and issubclass(error, builtin)
    with pytest.raises(walkup.StartNotFoundError):
        walkup.find("x", start=ws / "missing")
    with pytest.raises(walkup.InvalidMarkerError):
        walkup.find(start=ws)


def test_kind_and_mode_literals_are_exported() -> None:
    assert walkup.Kind.__args__ == ("any", "file", "dir")  # type: ignore[attr-defined]
    assert walkup.Mode.__args__ == ("any", "all")  # type: ignore[attr-defined]
