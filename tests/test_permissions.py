"""Permission errors on real files and directories: skipped by default, raised on request."""

from __future__ import annotations

import os
import pickle
import subprocess
import sys
from pathlib import Path

import pytest

from walkup import Marker, WalkupPermissionError, find

from conftest import IS_WINDOWS


def test_a_check_that_hits_a_permission_error_follows_the_policy(tmp_path: Path) -> None:
    def denied(path: Path) -> bool:
        raise PermissionError(13, "denied", str(path))

    (tmp_path / "x").write_text("")
    assert find(Marker("x", check=denied), start=tmp_path, stop_at=tmp_path) is None
    with pytest.raises(WalkupPermissionError):
        find(Marker("x", check=denied), start=tmp_path, on_error="raise")


def _deny_read(path: Path) -> None:
    if IS_WINDOWS:
        subprocess.run(
            ["icacls", str(path), "/deny", "*S-1-1-0:(R)"], check=True, capture_output=True
        )
    else:
        path.chmod(0)


def _allow_read(path: Path) -> None:
    if IS_WINDOWS:
        subprocess.run(["icacls", str(path), "/remove:d", "*S-1-1-0"], capture_output=True)
    else:
        path.chmod(0o700)


def _readable(path: Path) -> bool:
    try:
        path.read_bytes()
    except PermissionError:
        return False
    return True


def test_an_unreadable_candidate_is_skipped_or_raised(tmp_path: Path) -> None:
    secret = tmp_path / "settings.toml"
    secret.write_text("[tool]\n")
    marker = Marker.file("settings.toml", lambda p: "[tool]" in p.read_text())
    _deny_read(secret)
    try:
        if _readable(secret):
            pytest.skip("this account can read files regardless of permissions")
        assert find(marker, start=tmp_path, stop_at=tmp_path) is None
        with pytest.raises(WalkupPermissionError) as info:
            find(marker, start=tmp_path, on_error="raise")
        assert isinstance(info.value, PermissionError)
        assert info.value.path == tmp_path.resolve() / "settings.toml"
        copy = pickle.loads(pickle.dumps(info.value))
        assert copy.path == info.value.path
    finally:
        _allow_read(secret)


@pytest.mark.skipif(
    IS_WINDOWS, reason="Windows grants traverse bypass by default, so stat is never denied"
)
def test_an_untraversable_directory_is_skipped_or_raised(tmp_path: Path) -> None:
    locked = tmp_path / "locked"
    locked.mkdir()
    (locked / "inner.toml").write_text("")
    locked.chmod(0)
    try:
        if os.access(locked, os.X_OK) or (sys.platform != "win32" and os.geteuid() == 0):
            pytest.skip("this account ignores directory permissions")
        assert find("locked/inner.toml", start=tmp_path, stop_at=tmp_path) is None
        with pytest.raises(WalkupPermissionError):
            find("locked/inner.toml", start=tmp_path, on_error="raise")
    finally:
        locked.chmod(0o700)
