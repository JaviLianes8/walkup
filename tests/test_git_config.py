"""core.bare and the storage variables, each cross-checked against real git."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from walkupward import git_root, iter_git_roots
from walkupward._gitconfig import core_bare

from conftest import GitRunner, make_repo, needs_git

pytestmark = needs_git


def toplevel(git: GitRunner, start: Path, **env: str) -> Path | None:
    done = git("-C", start, "rev-parse", "--show-toplevel", check=False, **env)
    return Path(done.stdout.strip()).resolve() if done.returncode == 0 else None


def ours(start: Path) -> Path | None:
    match = git_root(start)
    return match.directory if match is not None else None


def set_bare(config: Path, line: str) -> None:
    text = config.read_text()
    config.write_text(text.replace("\tbare = false", line))


@pytest.mark.parametrize("gitfile", [False, True])
@pytest.mark.parametrize(
    ("line", "bare"),
    [
        ("\tbare = true", True),
        ("\tbare", True),
        ('\tBARE = "yes" # comment', True),
        ("\tbare = 1k", True),
        ("\tbare = false", False),
        ("\tbare = off ; comment", False),
        ("\tbare = maybe", True),
        ('\tbare = "true', True),
        ("[core.x]\n\tbare = true", False),
        ('[core "x"]\n\tbare = true', False),
    ],
)
def test_core_bare_ends_discovery_like_git(
    git: GitRunner, tmp_path: Path, gitfile: bool, line: str, bare: bool
) -> None:
    repo = make_repo(git, tmp_path / "repo")
    metadata = repo / ".git"
    if gitfile:
        metadata = tmp_path / "metadata"
        shutil.move(repo / ".git", metadata)
        (repo / ".git").write_text(f"gitdir: {metadata}\n")
    set_bare(metadata / "config", line)
    start = repo / "sub"
    start.mkdir()
    expected = None if bare else repo.resolve()
    assert toplevel(git, start) == expected
    assert ours(start) == expected
    assert [m.directory for m in iter_git_roots(start)] == ([] if bare else [repo.resolve()])


def test_a_gitfile_into_a_real_bare_repository_has_no_work_tree(
    git: GitRunner, tmp_path: Path
) -> None:
    git("init", "-q", "--bare", tmp_path / "store")
    work = tmp_path / "work"
    work.mkdir()
    (work / ".git").write_text(f"gitdir: {tmp_path / 'store'}\n")
    assert toplevel(git, work) is None and ours(work) is None


def test_core_bare_reads_the_config_grammar(tmp_path: Path) -> None:
    config = tmp_path / "config"
    cases = {
        "": False,
        "[core]\n": False,
        "\ufeff[core]\nbare = true\n": True,
        "[core] bare = true": True,
        "[core]\nbare = tr\\\nue\n": True,
        "[core]\nbare = tr\\nue\n": None,
        "[core]\nbare = true\nbare = false\n": False,
        "[Core]\n\tBare = On\n": True,
        "[core]\nbare = \\q\n": None,
        "[core\nbare = true\n": None,
        "%bad\n": None,
    }
    for text, expected in cases.items():
        config.write_bytes(text.encode("utf-8"))
        assert core_bare(config) is expected, text
    assert core_bare(tmp_path / "missing") is False


@pytest.mark.parametrize("variable", ["GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR"])
def test_storage_variables_are_honoured_like_git(
    git: GitRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variable: str
) -> None:
    repo = make_repo(git, tmp_path / "repo")
    if variable == "GIT_OBJECT_DIRECTORY":
        target = tmp_path / "objects"
        shutil.move(repo / ".git" / "objects", target)
    else:
        target = tmp_path / "common"
        git("init", "-q", "--bare", target)
        shutil.move(repo / ".git" / "objects", tmp_path / "objects-aside")
        shutil.move(repo / ".git" / "refs", tmp_path / "refs-aside")
    start = repo / "sub"
    start.mkdir()
    assert toplevel(git, start) is None and ours(start) is None
    monkeypatch.setenv(variable, str(target))
    assert toplevel(git, start, **{variable: str(target)}) == repo.resolve()
    assert ours(start) == repo.resolve()
    monkeypatch.setenv(variable, os.fspath(tmp_path / "absent"))
    assert ours(start) is None
