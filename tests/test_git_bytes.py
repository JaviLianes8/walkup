"""HEAD, gitfile and commondir contents read byte for byte, cross-checked against git."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from walkupward import git_root

from conftest import GitRunner, make_repo, needs_git

pytestmark = needs_git


def agree(git: GitRunner, start: Path) -> Path | None:
    done = git("-C", start, "rev-parse", "--show-toplevel", check=False)
    expected = Path(done.stdout.strip()).resolve() if done.returncode == 0 else None
    match = git_root(start)
    assert (match.directory if match is not None else None) == expected, start
    return expected


@pytest.mark.parametrize(
    ("head", "valid"),
    [
        (b"ref: refs/heads/main\n", True),
        (b"ref:\t\r\nrefs/heads/main\n", True),
        (b"ref: \xc2\xa0refs/heads/main\n", False),
        (b"ref: \x0brefs/heads/main\n", False),
        (b"ref:" + b" " * 245 + b"refs/heads/main\n", True),
        (b"ref:" + b" " * 300 + b"refs/heads/main\n", False),
        (b"ref:\0 refs/heads/main\n", False),
        (b"0" * 40 + b"\n", True),
        (b"0" * 39 + b"\0" + b"0\n", False),
    ],
)
def test_head_is_validated_like_git(
    git: GitRunner, tmp_path: Path, head: bytes, valid: bool
) -> None:
    repo = make_repo(git, tmp_path / "repo")
    (repo / ".git" / "HEAD").write_bytes(head)
    assert (agree(git, repo) is not None) is valid


@pytest.mark.parametrize("suffix", [b"", b"\n", b"\r\n", b"\0junk\n", b"\0\n"])
def test_a_nul_ends_the_gitfile_path_like_git(
    git: GitRunner, tmp_path: Path, suffix: bytes
) -> None:
    repo = make_repo(git, tmp_path / "repo")
    metadata = tmp_path / "metadata"
    shutil.move(repo / ".git", metadata)
    (repo / ".git").write_bytes(b"gitdir: " + str(metadata).encode() + suffix)
    assert agree(git, repo) == repo.resolve()


@pytest.mark.parametrize("suffix", [b"\n", b"\0junk\n"])
def test_a_nul_ends_the_commondir_path_like_git(
    git: GitRunner, tmp_path: Path, suffix: bytes
) -> None:
    repo = make_repo(git, tmp_path / "repo")
    git("-C", repo, "worktree", "add", "-q", "-b", "side", tmp_path / "wt")
    admin = repo / ".git" / "worktrees" / "wt"
    (admin / "commondir").write_bytes(str(repo / ".git").encode() + suffix)
    assert agree(git, tmp_path / "wt") == (tmp_path / "wt").resolve()
