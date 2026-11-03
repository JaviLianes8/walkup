"""The ceiling and filesystem variables read exactly as git reads them."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from walkupward import git_root, iter_git_roots
from walkupward._gitconfig import parse_bool

from conftest import GitRunner, make_repo, needs_git


def toplevel(git: GitRunner, start: Path, **env: str) -> Path | None:
    done = git("-C", start, "rev-parse", "--show-toplevel", check=False, **env)
    return Path(done.stdout.strip()).resolve() if done.returncode == 0 else None


def ours(start: Path) -> Path | None:
    match = git_root(start)
    return match.directory if match is not None else None


def _variants(middle: Path) -> list[str]:
    slashed = str(middle).replace(os.sep, "/")
    sep = os.pathsep
    return [
        str(middle),
        sep + slashed,
        sep + slashed + "/",
        sep + slashed + "//",
        sep + slashed + "/../middle",
        sep + str(middle),
        sep + slashed.swapcase(),
        sep + slashed + "/.",
        sep + str(middle.parent) + "/middle/../middle",
        "relative" + sep + str(middle),
    ]


@needs_git
def test_ceiling_entries_after_an_empty_one_compare_literally(
    git: GitRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_repo(git, tmp_path / "repo").resolve()
    middle = repo / "middle"
    start = middle / "child"
    start.mkdir(parents=True)
    outcomes = set()
    for value in _variants(middle):
        expected = toplevel(git, start, GIT_CEILING_DIRECTORIES=value)
        monkeypatch.setenv("GIT_CEILING_DIRECTORIES", value)
        assert ours(start) == expected, value
        outcomes.add(expected)
    assert outcomes == {None, repo}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1", True),
        ("2", True),
        ("true", True),
        ("YES", True),
        ("on", True),
        (" 1", True),
        ("+1", True),
        ("-1", True),
        ("1k", True),
        ("0x10", True),
        ("010", True),
        ("0", False),
        ("0x0", False),
        ("00", False),
        ("no", False),
        ("Off", False),
        ("", False),
        ("garbage", None),
        (" true ", None),
        ("1 ", None),
        ("08", None),
        ("0x", None),
        ("1kb", None),
        ("2147483647", True),
        ("2147483648", None),
        ("-2147483648", None),
        ("2097152k", None),
        ("2097151k", True),
    ],
)
def test_the_boolean_grammar_matches_git(value: str, expected: bool | None) -> None:
    assert parse_bool(value) is expected


@needs_git
@pytest.mark.parametrize("value", ["garbage", " true ", "1 ", "2147483648", "0", "1"])
def test_an_invalid_filesystem_variable_fails_discovery_like_git(
    git: GitRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    repo = make_repo(git, tmp_path / "repo").resolve()
    expected = toplevel(git, repo, GIT_DISCOVERY_ACROSS_FILESYSTEM=value)
    monkeypatch.setenv("GIT_DISCOVERY_ACROSS_FILESYSTEM", value)
    assert ours(repo) == expected
    assert [m.directory for m in iter_git_roots(repo)] == ([] if expected is None else [repo])
    assert (expected is None) is (parse_bool(value) is None)
