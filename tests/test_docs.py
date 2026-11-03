"""Execute the examples and keep every public callable documented."""

from __future__ import annotations

import doctest
import importlib
import inspect
import re
from pathlib import Path

import pytest

import walkupward


@pytest.mark.parametrize(
    "module", ["walkupward", "_core", "_walk", "_search", "_presets", "_git", "_types", "_errors"]
)
def test_docstrings_run(module: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    imported = importlib.import_module(module if module == "walkupward" else f"walkupward.{module}")
    result = doctest.testmod(imported)
    assert result.failed == 0
    # Re-exported classes belong to walkupward so their examples run in that module.
    if module not in ("_types", "_errors"):
        assert result.attempted > 0


def test_every_public_callable_and_property_has_an_example() -> None:
    for name in walkupward.__all__:
        if name in ("Kind", "Mode"):
            assert ">>>" in walkupward.__test__[name]
            continue
        value = getattr(walkupward, name)
        assert ">>>" in (inspect.getdoc(value) or ""), name
    for owner, names in (
        (walkupward.Marker, ("file", "dir")),
        (walkupward.Match, ("marker", "path", "names")),
    ):
        for name in names:
            doc = inspect.getdoc(getattr(owner, name)) or ""
            assert ">>>" in doc
            example = doctest.DocTestParser().get_doctest(
                doc, vars(walkupward).copy(), f"{owner.__name__}.{name}", None, 0
            )
            assert doctest.DocTestRunner().run(example).failed == 0


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
