"""Shared helpers for tests that build real directory trees and real repositories."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

GIT = shutil.which("git")
IS_WINDOWS = sys.platform == "win32"

needs_git = pytest.mark.skipif(GIT is None, reason="git is not installed")


def link_dir(target: Path, link: Path) -> None:
    """Create a directory link: a junction on Windows, a symlink elsewhere."""
    if IS_WINDOWS:
        import _winapi

        _winapi.CreateJunction(str(target), str(link))
        return
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlinks are not available here: {exc}")


def symlink(target: Path, link: Path) -> None:
    """Create a real symlink or skip when the platform does not allow it."""
    try:
        os.symlink(target, link)
    except OSError as exc:
        pytest.skip(f"symlinks are not available here: {exc}")


def git_env(home: Path) -> dict[str, str]:
    """Return an environment that isolates git from the user's and system's settings."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    config = home / "gitconfig"
    config.touch()
    env.update(
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=str(config),
        GIT_AUTHOR_NAME="Test",
        GIT_AUTHOR_EMAIL="test@example.com",
        GIT_COMMITTER_NAME="Test",
        GIT_COMMITTER_EMAIL="test@example.com",
    )
    return env


GitRunner = Callable[..., subprocess.CompletedProcess[str]]


@pytest.fixture
def git(tmp_path_factory: pytest.TempPathFactory) -> GitRunner:
    """Run real git commands in an isolated configuration."""
    if GIT is None:
        pytest.skip("git is not installed")
    env = git_env(tmp_path_factory.mktemp("githome"))

    def run(
        *args: str | Path, check: bool = True, **extra: str
    ) -> subprocess.CompletedProcess[str]:
        assert GIT is not None
        return subprocess.run(
            [GIT, "-c", "init.defaultBranch=main", *map(str, args)],
            env={**env, **extra},
            capture_output=True,
            text=True,
            check=check,
        )

    return run


def make_repo(git: GitRunner, path: Path) -> Path:
    """Create a repository at ``path`` with one commit and return it."""
    path.mkdir(parents=True, exist_ok=True)
    git("init", "-q", path)
    (path / "README").write_text("x\n")
    git("-C", path, "add", "README")
    git("-C", path, "commit", "-q", "-m", "init")
    return path


@pytest.fixture(autouse=True)
def _no_git_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("GIT_CEILING_DIRECTORIES", "GIT_DISCOVERY_ACROSS_FILESYSTEM", "GIT_DIR"):
        monkeypatch.delenv(name, raising=False)
