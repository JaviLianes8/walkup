"""Build the wheel, install it in a fresh virtual environment, and drive the real script."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import venv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_OFFLINE = ("NewConnectionError", "Could not find a version", "Name or service not known")


def _bin(env_dir: Path, name: str) -> Path:
    folder = env_dir / ("Scripts" if sys.platform == "win32" else "bin")
    return folder / (name + (".exe" if sys.platform == "win32" else ""))


@pytest.fixture(scope="module")
def installed(tmp_path_factory: pytest.TempPathFactory) -> Path:
    work = tmp_path_factory.mktemp("e2e")
    supplied = os.environ.get("WALKUPWARD_WHEEL")
    wheel = Path(supplied) if supplied else _build(work)
    assert wheel.is_file()
    env_dir = work / "venv"
    venv.create(env_dir, with_pip=True)
    python = _bin(env_dir, "python")
    subprocess.run(
        [str(python), "-m", "pip", "install", "-q", "--no-index", str(wheel)],
        check=True,
        capture_output=True,
        timeout=120,
    )
    return env_dir


def _build(work: Path) -> Path:
    command = [sys.executable, "-m", "pip", "wheel", "--no-deps", "-q", "-w", str(work)]
    if importlib.util.find_spec("hatchling") is not None:
        command.append("--no-build-isolation")
    built = subprocess.run([*command, str(ROOT)], capture_output=True, text=True, check=False)
    if built.returncode != 0:
        output = built.stdout + built.stderr
        if any(sign in output for sign in _OFFLINE):
            pytest.skip("the build backend could not be downloaded (offline)")
        pytest.fail(f"building the wheel failed: {output}")
    wheels = list(work.glob("walkupward-*.whl"))
    assert len(wheels) == 1, wheels
    return wheels[0]


def _walkupward(env_dir: Path, *args: str | Path, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "VIRTUAL_ENV")}
    return subprocess.run(
        [str(_bin(env_dir, "walkupward")), *map(str, args)],
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
    done = _walkupward(installed, "pyproject.toml", cwd=deep)
    assert (done.returncode, done.stdout.strip(), done.stderr) == (0, str(tmp_path.resolve()), "")


def test_the_installed_script_reports_absence_and_errors(installed: Path, tmp_path: Path) -> None:
    done = _walkupward(installed, "--stop-at", tmp_path, "absent.zz", cwd=tmp_path)
    assert (done.returncode, done.stdout) == (1, "")
    done = _walkupward(installed, cwd=tmp_path)
    assert done.returncode == 1 and "error" in done.stderr


def test_the_installed_script_shows_help_and_version(installed: Path, tmp_path: Path) -> None:
    done = _walkupward(installed, "--help", cwd=tmp_path)
    assert done.returncode == 0 and "examples:" in done.stdout
    version = _walkupward(installed, "--version", cwd=tmp_path)
    python = _bin(installed, "python")
    code = "import walkupward; print(walkupward.__version__)"
    expected = subprocess.run(
        [str(python), "-c", code], capture_output=True, text=True, cwd=tmp_path
    )
    assert version.stdout.strip() == f"walkupward {expected.stdout.strip()}"


def test_the_installed_package_is_typed(installed: Path, tmp_path: Path) -> None:
    python = _bin(installed, "python")
    code = (
        "import importlib.resources as r; "
        "print(r.files('walkupward').joinpath('py.typed').is_file())"
    )
    done = subprocess.run([str(python), "-c", code], capture_output=True, text=True, cwd=tmp_path)
    assert done.stdout.strip() == "True"


def test_installed_module_and_external_consumer(installed: Path, tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").touch()
    python = _bin(installed, "python")
    code = """
from pathlib import Path
from walkupward import Marker, find_all, find_up, python_root, require, walk_up
root = Path.cwd()
assert require(Marker.file('pyproject.toml'), stop_at=root).directory == root
assert find_up('pyproject.toml') == root / 'pyproject.toml'
assert python_root().names == ('pyproject.toml',)
assert len(find_all('pyproject.toml', stop_at=root)) == 1
assert next(walk_up()) == root
"""
    done = subprocess.run(
        [str(python), "-I", "-c", code], cwd=tmp_path, capture_output=True, text=True, timeout=60
    )
    assert done.returncode == 0, done.stderr
    done = subprocess.run(
        [str(python), "-I", "-m", "walkupward", "--path", "pyproject.toml"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert (done.returncode, done.stdout.strip(), done.stderr) == (
        0,
        str(tmp_path / "pyproject.toml"),
        "",
    )
