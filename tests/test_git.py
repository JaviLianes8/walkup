"""git_root cross-checked against ``git rev-parse --show-toplevel`` in real repositories."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from walkup import git_root
from walkup._git import env_across_filesystems, env_ceilings

from conftest import GitRunner, make_repo, needs_git

pytestmark = needs_git


def toplevel(git: GitRunner, start: Path, **env: str) -> Path | None:
    done = git("-C", start, "rev-parse", "--show-toplevel", check=False, **env)
    return Path(done.stdout.strip()).resolve() if done.returncode == 0 else None


def ours(start: Path, **kwargs: object) -> Path | None:
    match = git_root(start, **kwargs)  # type: ignore[arg-type]
    return match.directory if match is not None else None


def test_a_plain_repository_matches_git(git: GitRunner, tmp_path: Path) -> None:
    repo = make_repo(git, tmp_path / "repo")
    start = repo / "src" / "deep"
    start.mkdir(parents=True)
    assert ours(start) == toplevel(git, start) == repo.resolve()
    match = git_root(start)
    assert match is not None and match.path.is_dir()


def test_a_linked_worktree_is_its_own_top_level(git: GitRunner, tmp_path: Path) -> None:
    repo = make_repo(git, tmp_path / "repo")
    git("-C", repo, "worktree", "add", "-q", "-b", "side", tmp_path / "wt")
    start = tmp_path / "wt" / "sub"
    start.mkdir()
    assert ours(start) == toplevel(git, start) == (tmp_path / "wt").resolve()
    match = git_root(start)
    assert match is not None and match.path.is_file()
    assert match.path.read_text().startswith("gitdir:")


def test_a_submodule_checkout_is_its_own_top_level(git: GitRunner, tmp_path: Path) -> None:
    lib = make_repo(git, tmp_path / "lib")
    repo = make_repo(git, tmp_path / "repo")
    git("-C", repo, "-c", "protocol.file.allow=always", "submodule", "add", "-q", lib, "mods/lib")
    start = repo / "mods" / "lib" / "inner"
    start.mkdir()
    assert ours(start) == toplevel(git, start) == (repo / "mods" / "lib").resolve()
    assert ours(repo / "mods") == toplevel(git, repo / "mods") == repo.resolve()


def test_an_empty_git_directory_is_ignored_like_git(git: GitRunner, tmp_path: Path) -> None:
    repo = make_repo(git, tmp_path / "repo")
    inner = repo / "inner"
    (inner / ".git").mkdir(parents=True)
    assert ours(inner) == toplevel(git, inner) == repo.resolve()


def test_a_git_file_without_a_valid_target_is_ignored_like_git(
    git: GitRunner, tmp_path: Path
) -> None:
    repo = make_repo(git, tmp_path / "repo")
    for name, text in [("bogus", "gitdir: ../nowhere\n"), ("plain", "hello\n"), ("empty", "")]:
        inner = repo / name
        inner.mkdir()
        (inner / ".git").write_text(text)
        assert ours(inner) == repo.resolve()
        done = git("-C", inner, "rev-parse", "--show-toplevel", check=False)
        assert done.returncode != 0 or Path(done.stdout.strip()).resolve() == repo.resolve()


def test_no_repository_gives_none(git: GitRunner, tmp_path: Path) -> None:
    lonely = tmp_path / "lonely"
    lonely.mkdir()
    ceiling = str(tmp_path)
    assert ours(lonely, ceilings=[ceiling]) is None
    assert toplevel(git, lonely, GIT_CEILING_DIRECTORIES=ceiling) is None


@pytest.mark.parametrize("relative", ["", "sub", "sub/deeper"])
def test_ceiling_directories_match_git(git: GitRunner, tmp_path: Path, relative: str) -> None:
    repo = make_repo(git, tmp_path / "repo")
    (repo / "sub" / "deeper").mkdir(parents=True)
    start = repo / relative if relative else repo
    for ceiling in (repo, repo / "sub", tmp_path):
        expected = toplevel(git, start, GIT_CEILING_DIRECTORIES=str(ceiling))
        assert ours(start, ceilings=[ceiling]) == expected, (start, ceiling)


def test_the_ceiling_environment_variable_is_honoured(
    git: GitRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_repo(git, tmp_path / "repo")
    start = repo / "sub"
    start.mkdir()
    value = os.pathsep.join(["relative/ignored", "", str(repo)])
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", value)
    assert env_ceilings() == [str(repo)]
    assert ours(start) is None
    plain = os.pathsep.join(["relative/ignored", str(repo)])
    assert toplevel(git, start, GIT_CEILING_DIRECTORIES=plain) is None
    assert ours(start, ceilings=[]) == repo.resolve()


@pytest.mark.parametrize(
    ("value", "expected"),
    [("1", True), ("true", True), ("YES", True), ("on", True), ("0", False), ("no", False)],
)
def test_the_filesystem_discovery_variable_reads_like_git(
    monkeypatch: pytest.MonkeyPatch, value: str, expected: bool
) -> None:
    monkeypatch.setenv("GIT_DISCOVERY_ACROSS_FILESYSTEM", value)
    assert env_across_filesystems() is expected


def test_the_filesystem_discovery_variable_defaults_to_false() -> None:
    assert env_across_filesystems() is False
