from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from walkup import __version__
from walkup._cli import main

from conftest import GitRunner, link_dir, make_repo, needs_git


def run(capsys: pytest.CaptureFixture[str], *argv: str | Path) -> tuple[int, str, str]:
    code = main([str(a) for a in argv])
    out, err = capsys.readouterr()
    return code, out, err


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text("")
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "pkg" / "src").mkdir(parents=True)
    (tmp_path / "pkg" / "pyproject.toml").write_text("")
    (tmp_path / "pkg" / "setup.cfg").write_text("")
    return tmp_path


def test_prints_the_nearest_directory(capsys: pytest.CaptureFixture[str], tree: Path) -> None:
    code, out, err = run(capsys, "-s", tree / "pkg" / "src", "pyproject.toml")
    assert (code, out, err) == (0, f"{(tree / 'pkg').resolve()}\n", "")


def test_all_prints_every_match(capsys: pytest.CaptureFixture[str], tree: Path) -> None:
    code, out, _ = run(capsys, "--all", "--start", tree / "pkg", "pyproject.toml")
    assert code == 0
    assert out.splitlines()[:2] == [str((tree / "pkg").resolve()), str(tree.resolve())]


def test_every_requires_all_markers(capsys: pytest.CaptureFixture[str], tree: Path) -> None:
    code, out, _ = run(capsys, "-e", "-s", tree / "pkg", "pyproject.toml", "package.json")
    assert (code, out) == (0, f"{tree.resolve()}\n")


def test_path_prints_matched_paths(capsys: pytest.CaptureFixture[str], tree: Path) -> None:
    code, out, _ = run(capsys, "--path", "-s", tree / "pkg", "pyproject.toml", "setup.cfg")
    pkg = (tree / "pkg").resolve()
    assert (code, out.splitlines()) == (0, [str(pkg / "pyproject.toml"), str(pkg / "setup.cfg")])


def test_kind_filters_files_and_directories(capsys: pytest.CaptureFixture[str], tree: Path) -> None:
    (tree / "pkg" / "out").mkdir()
    code, out, _ = run(capsys, "--kind", "file", "-s", tree / "pkg", "--stop-at", tree, "out")
    assert (code, out) == (1, "")
    code, out, _ = run(capsys, "-k", "dir", "-s", tree / "pkg", "out")
    assert (code, out) == (0, f"{(tree / 'pkg').resolve()}\n")


def test_ceiling_and_same_filesystem(capsys: pytest.CaptureFixture[str], tree: Path) -> None:
    start = tree / "pkg" / "src"
    code, out, _ = run(capsys, "--ceiling", tree, "--same-filesystem", "-s", start, "package.json")
    assert (code, out) == (1, "")


def test_lexical_keeps_a_linked_path(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    (tmp_path / "real").mkdir()
    (tmp_path / "side").mkdir()
    (tmp_path / "side" / "here.marker").write_text("")
    link_dir(tmp_path / "real", tmp_path / "side" / "link")
    start = tmp_path / "side" / "link"
    assert run(capsys, "-s", start, "--stop-at", tmp_path, "here.marker")[0] == 1
    code, out, _ = run(capsys, "--lexical", "-s", start, "here.marker")
    assert code == 0 and Path(out.strip()).name == "side"


def test_python_and_node_presets(capsys: pytest.CaptureFixture[str], tree: Path) -> None:
    assert run(capsys, "-p", "python", "-s", tree / "pkg" / "src")[1].strip() == str(
        (tree / "pkg").resolve()
    )
    assert run(capsys, "--preset", "node", "-s", tree / "pkg")[1].strip() == str(tree.resolve())


def test_editorconfig_preset(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    (tmp_path / ".editorconfig").write_text("root = true\n")
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / ".editorconfig").write_text("[*]\n")
    code, out, _ = run(capsys, "-p", "editorconfig", "--path", "-s", tmp_path / "a")
    expected = [
        str(tmp_path.resolve() / "a" / ".editorconfig"),
        str(tmp_path.resolve() / ".editorconfig"),
    ]
    assert (code, out.splitlines()) == (0, expected)


@needs_git
def test_git_preset_lists_submodule_then_superproject(
    capsys: pytest.CaptureFixture[str], git: GitRunner, tmp_path: Path
) -> None:
    lib = make_repo(git, tmp_path / "lib")
    repo = make_repo(git, tmp_path / "repo")
    git("-C", repo, "-c", "protocol.file.allow=always", "submodule", "add", "-q", lib, "sub")
    code, out, _ = run(capsys, "-p", "git", "--all", "-s", repo / "sub")
    assert code == 0
    assert out.splitlines() == [str((repo / "sub").resolve()), str(repo.resolve())]


def test_nothing_found_exits_one_quietly(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    assert run(capsys, "-s", tmp_path, "--stop-at", tmp_path, "nothing.zz") == (1, "", "")


@pytest.mark.parametrize(
    "argv",
    [[], ["--preset", "git", "x"], ["-s", "definitely/missing/dir", "x"], ["--kind", "pipe", "x"]],
)
def test_errors_go_to_stderr_with_exit_one(
    capsys: pytest.CaptureFixture[str], argv: list[str]
) -> None:
    try:
        code, out, err = run(capsys, *argv)
    except SystemExit as exc:
        code, (out, err) = int(exc.code or 0), capsys.readouterr()
    assert code == 1 and out == ""
    assert "error" in err


def test_help_shows_runnable_examples(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as info:
        main(["--help"])
    out = capsys.readouterr().out
    assert info.value.code == 0
    assert "walkup --preset git" in out and "exit status" in out


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--version"])
    assert capsys.readouterr().out.strip() == f"walkup {__version__}"


def test_python_dash_m_runs_the_tool(tree: Path) -> None:
    src = Path(__file__).resolve().parents[1] / "src"
    done = subprocess.run(
        [sys.executable, "-m", "walkup", "-s", str(tree / "pkg"), "setup.cfg"],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(src)},
        check=False,
    )
    assert (done.returncode, done.stdout.strip()) == (0, str((tree / "pkg").resolve()))
