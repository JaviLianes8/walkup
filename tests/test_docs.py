"""Execute the examples and keep every public callable documented."""

from __future__ import annotations

import doctest
import importlib
import inspect
import re
from pathlib import Path

import pytest

import walkup


@pytest.mark.parametrize(
    "module", ["walkup", "_core", "_walk", "_search", "_presets", "_git", "_types", "_errors"]
)
def test_docstrings_run(module: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    imported = importlib.import_module(module if module == "walkup" else f"walkup.{module}")
    result = doctest.testmod(imported, globs=vars(imported) | {"Path": Path})
    assert result.failed == 0
    # Re-exported classes belong to walkup so their examples run in that module.
    if module not in ("_types", "_errors"):
        assert result.attempted > 0


def test_every_public_callable_and_property_has_an_example() -> None:
    for name in walkup.__all__:
        if name in ("Kind", "Mode"):
            assert ">>>" in walkup.__test__[name]
            continue
        value = getattr(walkup, name)
        assert ">>>" in (inspect.getdoc(value) or ""), name
    for owner, names in (
        (walkup.Marker, ("file", "dir")),
        (walkup.Match, ("marker", "path", "names")),
    ):
        for name in names:
            assert ">>>" in (inspect.getdoc(getattr(owner, name)) or "")


@pytest.mark.parametrize("name", ["README.md", "GUIDE.md"])
def test_documentation_python_blocks_run(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = Path(__file__).resolve().parents[1] / name
    text = source.read_text(encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / ".git").mkdir()
    (tmp_path / "sample.py").touch()
    namespace: dict[str, object] = {"__file__": str(tmp_path / "sample.py")}
    blocks = re.findall(r"```python\n(.*?)```", text, re.DOTALL)
    assert blocks
    for block in blocks:
        exec(compile(block, name, "exec"), namespace)
