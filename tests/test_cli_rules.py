"""Command line usage rules and output encoding."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from walkup._cli import main

SRC = Path(__file__).resolve().parents[1] / "src"


@pytest.mark.parametrize(
    "argv",
    [
        ["--preset", "git", "--every"],
        ["--preset", "git", "--lexical"],
        ["--preset", "git", "--stop-at", "."],
        ["--preset", "python", "--kind", "dir"],
        ["--preset", "node", "--every"],
        ["--preset", "editorconfig", "--all"],
    ],
)
def test_flags_a_preset_cannot_honour_are_rejected(
    capsys: pytest.CaptureFixture[str], argv: list[str]
) -> None:
    with pytest.raises(SystemExit) as info:
        main(argv)
    assert info.value.code == 1
    err = capsys.readouterr().err
    assert "does not apply to --preset" in err


def test_missing_arguments_get_a_precise_message(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main([])
    assert "give one or more MARKER names, or --preset" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        main(["--preset", "git", "x"])
    assert "cannot be combined" in capsys.readouterr().err


def _run(start: Path, **env: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-m", "walkup", "-s", str(start), "marker.txt"],
        capture_output=True,
        env={**os.environ, "PYTHONPATH": str(SRC), **env},
        check=False,
    )


def test_a_path_the_output_encoding_cannot_hold_is_a_clean_error(tmp_path: Path) -> None:
    odd = tmp_path / "check✓mark"
    odd.mkdir()
    (odd / "marker.txt").write_text("")
    done = _run(odd, PYTHONIOENCODING="ascii", PYTHONUTF8="0")
    assert done.returncode == 1 and done.stdout == b""
    assert b"PYTHONIOENCODING=utf-8" in done.stderr and b"Traceback" not in done.stderr
    done = _run(odd, PYTHONIOENCODING="utf-8")
    assert done.returncode == 0
    assert done.stdout.decode("utf-8").strip() == str(odd.resolve())


@pytest.mark.skipif(sys.platform == "win32", reason="undecodable file names are a POSIX case")
def test_undecodable_posix_names_round_trip(tmp_path: Path) -> None:
    raw = os.fsencode(tmp_path) + b"/bad\xff"
    try:
        os.mkdir(raw)
    except OSError as exc:
        pytest.skip(f"this filesystem rejects undecodable names: {exc}")
    open(raw + b"/marker.txt", "wb").close()
    done = _run(Path(os.fsdecode(raw)), PYTHONIOENCODING="utf-8")
    assert done.returncode == 0
    assert done.stdout.strip() == os.fsencode(Path(os.fsdecode(raw)).resolve())
