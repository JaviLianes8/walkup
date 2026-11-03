"""Handwritten cases derived from the fetched specification, with an optional oracle."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from walkup import editorconfig_chain

# https://spec.editorconfig.org/ sections File Format and File Processing, 2026-11-03.
# These are derived cases, not copied upstream vectors. The Python reference still
# accepts inline comments; the current specification does not, so that case is separate.
CASES = [
    ("root=true\n", True),
    ("root=true\nroot=false\n", False),
    ("root=false\nROOT=TRUE\n", True),
    ("root=true\nroot=unset\n", False),
    ("; comment\nroot = TrUe\n[*]\nroot=false\n", True),
    ("[*]\nroot=true\n", False),
    ("#root=true\nroot=false\n", False),
    ("\ufeffroot=true\r\n", True),
]


@pytest.mark.parametrize(("preamble", "root"), CASES)
def test_root_processing_contract(tmp_path: Path, preamble: str, root: bool) -> None:
    outer = tmp_path / ".editorconfig"
    outer.write_text("root=true\n", encoding="utf-8")
    inner = tmp_path / "sub"
    inner.mkdir()
    path = inner / ".editorconfig"
    path.write_text(preamble, encoding="utf-8")
    assert editorconfig_chain(inner) == ([path] if root else [path, outer])


@pytest.mark.parametrize(("preamble", "root"), CASES)
def test_reference_parser_agrees(tmp_path: Path, preamble: str, root: bool) -> None:
    reference = pytest.importorskip("editorconfig.ini")
    path = tmp_path / ".editorconfig"
    path.write_text(preamble, encoding="utf-8")
    parser = reference.EditorConfigParser(str(tmp_path / "example.py"))
    parser.read(str(path))
    assert parser.root_file is root


@pytest.mark.parametrize("suffix", ["# comment", "; comment", "\vroot=true", "\x85root=true"])
def test_inline_comments_and_non_lf_separators_are_not_root(tmp_path: Path, suffix: str) -> None:
    outer = tmp_path / ".editorconfig"
    outer.write_text("root=true\n", encoding="utf-8")
    inner = tmp_path / "sub"
    inner.mkdir()
    path = inner / ".editorconfig"
    path.write_text("root=true " + suffix + "\n", encoding="utf-8")
    assert editorconfig_chain(inner) == [path, outer]


def test_fetched_specification_has_the_recorded_hash() -> None:
    source = os.environ.get("WALKUP_TRUTH")
    if not source:
        pytest.skip("set WALKUP_TRUTH to the fetched specification directory")
    manifest = Path(__file__).resolve().parents[1] / "GROUND-TRUTH.json"
    for entry in json.loads(manifest.read_text(encoding="utf-8")):
        data = (Path(source) / entry["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry["sha256"]
        assert len(data) == entry["size"]
        # Locate the relevant rules in the fetched source rather than a local paraphrase.
        text = " ".join(data.decode("utf-8").split())
        assert "most recent pairs found take precedence" in text
        assert "No inline comments" in text
