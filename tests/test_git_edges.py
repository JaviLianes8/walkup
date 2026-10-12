"""Edge cases of git discovery, each cross-checked against real git."""

from __future__ import annotations

from pathlib import Path

import pytest

from walkup import git_root, iter_git_roots

from conftest import GitRunner, make_repo, needs_git

pytestmark = needs_git


def toplevel(git: GitRunner, start: Path) -> Path | None:
    done = git("-C", start, "rev-parse", "--show-toplevel", check=False)
    return Path(done.stdout.strip()).resolve() if done.returncode == 0 else None


def ours(start: Path) -> Path | None:
    match = git_root(start)
    return match.directory if match is not None else None


def agree(git: GitRunner, start: Path) -> Path | None:
    expected = toplevel(git, start)
    assert ours(start) == expected, start
    return expected


@pytest.mark.parametrize(
    "text",
    ["gitdir: ../nowhere\n", "hello\n", "", "\ngitdir: ../real/.git\n", "gitdir:../real/.git\n"],
)
def test_an_invalid_git_file_stops_discovery_like_git(
    git: GitRunner, tmp_path: Path, text: str
) -> None:
    repo = make_repo(git, tmp_path / "repo")
    make_repo(git, repo / "real")
    inner = repo / "inner"
    inner.mkdir()
    (inner / ".git").write_text(text)
    assert agree(git, inner) is None


def test_a_valid_git_file_with_crlf_is_followed(git: GitRunner, tmp_path: Path) -> None:
    repo = make_repo(git, tmp_path / "repo")
    real = make_repo(git, tmp_path / "real")
    linked = repo / "linked"
    linked.mkdir()
    (linked / ".git").write_bytes(b"gitdir: " + str(real / ".git").encode() + b"\r\n")
    assert agree(git, linked) == linked.resolve()


@pytest.mark.parametrize(
    "head",
    ["ref:refs/heads/main\n", "ref:  refs/heads/main\n", "A" * 40 + "\n", "a" * 40 + " junk\n"],
)
def test_head_forms_that_git_accepts(git: GitRunner, tmp_path: Path, head: str) -> None:
    outer = make_repo(git, tmp_path / "outer")
    nested = make_repo(git, outer / "nested")
    (nested / ".git" / "HEAD").write_text(head)
    assert agree(git, nested) == nested.resolve()


def test_a_broken_head_makes_git_skip_the_nested_repo(git: GitRunner, tmp_path: Path) -> None:
    outer = make_repo(git, tmp_path / "outer")
    nested = make_repo(git, outer / "nested")
    (nested / ".git" / "HEAD").write_text("garbage\n")
    assert agree(git, nested) == outer.resolve()


def test_a_commondir_that_is_not_utf8_does_not_crash(git: GitRunner, tmp_path: Path) -> None:
    repo = make_repo(git, tmp_path / "repo")
    git("-C", repo, "worktree", "add", "-q", "-b", "side", tmp_path / "wt")
    admin = next((repo / ".git" / "worktrees").iterdir())
    (admin / "commondir").write_bytes(b"\xff\xfe../..\n")
    assert agree(git, tmp_path / "wt") is None


@pytest.mark.parametrize("relative", [".git", ".git/objects", ".git/refs/heads"])
def test_inside_the_git_directory_there_is_no_work_tree(
    git: GitRunner, tmp_path: Path, relative: str
) -> None:
    repo = make_repo(git, tmp_path / "repo")
    assert agree(git, repo / relative) is None


def test_a_bare_repository_inside_a_work_tree_has_no_top_level(
    git: GitRunner, tmp_path: Path
) -> None:
    repo = make_repo(git, tmp_path / "repo")
    git("init", "-q", "--bare", repo / "store.git")
    (repo / "store.git" / "refs" / "x").mkdir()
    assert agree(git, repo / "store.git" / "refs" / "x") is None


def test_iter_git_roots_lists_submodule_then_superproject(git: GitRunner, tmp_path: Path) -> None:
    lib = make_repo(git, tmp_path / "lib")
    repo = make_repo(git, tmp_path / "repo")
    git("-C", repo, "-c", "protocol.file.allow=always", "submodule", "add", "-q", lib, "m/lib")
    roots = [m.directory for m in iter_git_roots(repo / "m" / "lib")]
    assert roots[:2] == [(repo / "m" / "lib").resolve(), repo.resolve()]
    assert list(iter_git_roots(repo, ceilings=[tmp_path])) == [git_root(repo)]
