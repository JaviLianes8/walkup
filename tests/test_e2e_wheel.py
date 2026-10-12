"""Build the wheel, install it in a fresh virtual environment, and drive the real script."""

from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _bin(env_dir: Path, name: str) -> Path:
    folder = env_dir / ("Scripts" if sys.platform == "win32" else "bin")
    return folder / (name + (".exe" if sys.platform == "win32" else ""))


@pytest.fixture(scope="module")
def installed(tmp_path_factory: pytest.TempPathFactory) -> Path:
    work = tmp_path_factory.mktemp("e2e")
    built = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--no-deps", "-q", "-w", str(work), str(ROOT)],
        capture_output=True,
        text=True,
        check=False,
    )
    if built.returncode != 0:
        pytest.fail(f"building the wheel failed:\n{built.stdout}\n{built.stderr}")
    wheels = list(work.glob("walkup-*.whl"))
    assert len(wheels) == 1, wheels
    env_dir = work / "venv"
    venv.create(env_dir, with_pip=True)
    python = _bin(env_dir, "python")
    subprocess.run(
        [str(python), "-m", "pip", "install", "-q", "--no-index", str(wheels[0])],
        check=True,
        capture_output=True,
    )
    return env_dir


def _walkup(env_dir: Path, *args: str | Path, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "VIRTUAL_ENV")}
    return subprocess.run(
        [str(_bin(env_dir, "walkup")), *map(str, args)],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
        check=False,
    )


def test_the_installed_script_finds_a_marker(installed: Path, tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("")
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    done = _walkup(installed, "pyproject.toml", cwd=deep)
    assert (done.returncode, done.stdout.strip(), done.stderr) == (0, str(tmp_path.resolve()), "")


def test_the_installed_script_reports_absence_and_errors(installed: Path, tmp_path: Path) -> None:
    done = _walkup(installed, "--stop-at", tmp_path, "absent.zz", cwd=tmp_path)
    assert (done.returncode, done.stdout) == (1, "")
    done = _walkup(installed, cwd=tmp_path)
    assert done.returncode == 1 and "error" in done.stderr


def test_the_installed_script_shows_help_and_version(installed: Path, tmp_path: Path) -> None:
    done = _walkup(installed, "--help", cwd=tmp_path)
    assert done.returncode == 0 and "examples:" in done.stdout
    version = _walkup(installed, "--version", cwd=tmp_path)
    python = _bin(installed, "python")
    code = "import walkup; print(walkup.__version__)"
    expected = subprocess.run(
        [str(python), "-c", code], capture_output=True, text=True, cwd=tmp_path
    )
    assert version.stdout.strip() == f"walkup {expected.stdout.strip()}"


def test_the_installed_package_is_typed(installed: Path, tmp_path: Path) -> None:
    python = _bin(installed, "python")
    code = (
        "import importlib.resources as r; print(r.files('walkup').joinpath('py.typed').is_file())"
    )
    done = subprocess.run([str(python), "-c", code], capture_output=True, text=True, cwd=tmp_path)
    assert done.stdout.strip() == "True"
