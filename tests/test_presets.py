from __future__ import annotations

from pathlib import Path

import pytest

from walkup import StartNotFoundError, editorconfig_chain, node_root, python_root


def test_python_root_takes_the_nearest_configuration(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("")
    pkg = tmp_path / "packages" / "core"
    (pkg / "src").mkdir(parents=True)
    (pkg / "setup.cfg").write_text("")
    (pkg / "setup.py").write_text("")
    match = python_root(pkg / "src")
    assert match is not None
    assert match.directory == pkg.resolve()
    assert match.names == ("setup.cfg", "setup.py")
    top = python_root(tmp_path / "packages")
    assert top is not None and top.names == ("pyproject.toml",)


def test_python_root_ignores_a_directory_named_like_a_config(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("")
    inner = tmp_path / "inner"
    (inner / "pyproject.toml").mkdir(parents=True)
    match = python_root(inner)
    assert match is not None and match.directory == tmp_path.resolve()


def test_node_root_takes_the_nearest_package_json(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}")
    app = tmp_path / "apps" / "web"
    (app / "src").mkdir(parents=True)
    (app / "package.json").write_text("{}")
    match = node_root(app / "src")
    assert match is not None and match.path == app.resolve() / "package.json"
    assert node_root(tmp_path, stop_at=tmp_path) is not None
    assert node_root(app / "src", ceilings=[app]) is None


def _editorconfig(directory: Path, text: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ".editorconfig"
    path.write_text(text, encoding="utf-8")
    return path


def test_the_chain_stops_at_the_first_root_file(tmp_path: Path) -> None:
    _editorconfig(tmp_path, "root = true\n")
    root = _editorconfig(tmp_path / "repo", "# top\nroot = true\n\n[*]\nindent_size = 4\n")
    mid = _editorconfig(tmp_path / "repo" / "pkg", "[*.py]\nindent_size = 4\n")
    start = tmp_path / "repo" / "pkg" / "src"
    start.mkdir()
    assert editorconfig_chain(start) == [mid.resolve(), root.resolve()]


@pytest.mark.parametrize(
    ("text", "is_root"),
    [
        ("ROOT = True\n", True),
        ("; comment\nroot=true\n", True),
        ("﻿root = true\n", True),
        ("[*]\nroot = true\n", False),
        ("root = false\n", False),
        ("rooted = true\n", False),
    ],
)
def test_root_is_read_from_the_preamble_only(tmp_path: Path, text: str, is_root: bool) -> None:
    outer = _editorconfig(tmp_path, "root = true\n")
    inner = _editorconfig(tmp_path / "inner", text)
    chain = editorconfig_chain(tmp_path / "inner")
    assert chain == ([inner.resolve()] if is_root else [inner.resolve(), outer.resolve()])


def test_no_editorconfig_gives_an_empty_chain(tmp_path: Path) -> None:
    assert editorconfig_chain(tmp_path, stop_at=tmp_path) == []


def test_presets_reject_a_missing_start(tmp_path: Path) -> None:
    for preset in (python_root, node_root, editorconfig_chain):
        with pytest.raises(StartNotFoundError):
            preset(tmp_path / "missing")
