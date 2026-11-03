"""Seeded, handwritten filesystem and preamble cases, independent of search internals."""

from __future__ import annotations

import os
import random
from pathlib import Path

import pytest

from walkup import Marker, editorconfig_chain, find, find_all, iter_matches, walk_up


@pytest.mark.parametrize("seed", [7, 191, 20261103])
def test_seeded_trees_match_an_independent_parent_scan(tmp_path: Path, seed: int) -> None:
    rng = random.Random(seed)
    directories = [tmp_path.resolve()]
    for depth in range(8):
        directories.append(directories[-1] / f"level{depth}")
        directories[-1].mkdir()
    names = ["first.cfg", "second.cfg", "folder"]
    for directory in directories:
        for name in names:
            if rng.randrange(2):
                path = directory / name
                path.mkdir() if name == "folder" else path.touch()
    for _ in range(100):
        start = rng.choice(directories)
        stop = rng.choice(directories[: directories.index(start) + 1])
        wanted = rng.sample(names, rng.randint(1, 3))
        markers = [Marker.dir(n) if n == "folder" else Marker.file(n) for n in wanted]
        walked: list[Path] = []
        current = str(start)
        while True:
            walked.append(Path(current))
            if current == str(stop):
                break
            current = os.path.dirname(current)
        assert list(walk_up(start, stop_at=stop)) == walked
        assert list(walk_up(start, ceilings=[stop])) == (
            walked[:-1] if stop != start else list(walk_up(start))
        )
        for mode in ("any", "all"):
            expected = []
            for directory in walked:
                hits = tuple(n for n in wanted if os.path.exists(os.path.join(directory, n)))
                if hits and (mode == "any" or len(hits) == len(wanted)):
                    expected.append((directory, hits))
            results = find_all(*markers, start=start, stop_at=stop, mode=mode)
            assert [(m.directory, m.names) for m in results] == expected
            assert list(iter_matches(*markers, start=start, stop_at=stop, mode=mode)) == results
            assert find(*markers, start=start, stop_at=stop, mode=mode) == (
                results[0] if results else None
            )


def test_seeded_preambles_use_the_last_assignment(tmp_path: Path) -> None:
    rng = random.Random(20261103)
    outer = tmp_path / ".editorconfig"
    outer.write_text("root = true\n", encoding="utf-8")
    inner = tmp_path / "inner"
    inner.mkdir()
    config = inner / ".editorconfig"
    for _ in range(1000):
        values = rng.choices(["true", "false", "TRUE", "unset", "true # comment"], k=10)
        text = "# comment\n" + "\n".join("ROOT = " + value for value in values)
        config.write_text(text + "\n[*]\nroot=true\n", encoding="utf-8")
        expected = [config] if values[-1].lower() == "true" else [config, outer]
        assert editorconfig_chain(inner, stop_at=tmp_path) == expected


@pytest.mark.parametrize("size", [10_000, 100_000, 1_000_000])
def test_long_editorconfig_values_and_comments_remain_safe(tmp_path: Path, size: int) -> None:
    path = tmp_path / ".editorconfig"
    path.write_text("#" + "x" * size + "\nroot=" + "x" * size + "\n", encoding="utf-8")
    assert editorconfig_chain(tmp_path, stop_at=tmp_path) == [path]
