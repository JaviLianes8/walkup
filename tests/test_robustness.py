"""Bounded diagnostics, runtime annotations and value contracts."""

from __future__ import annotations

import inspect
import pickle
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import get_type_hints

import pytest

import walkup
from walkup._cli import main


def test_error_messages_do_not_echo_private_or_large_inputs(tmp_path: Path) -> None:
    secret = "private-token-" + "x" * 100_000
    errors = [
        walkup.StartNotFoundError(Path(secret)),
        walkup.WalkupPermissionError(Path(secret)),
        walkup.MarkerNotFoundError((walkup.Marker(secret),), Path(secret), "all"),
    ]
    for error in errors:
        assert len(str(error)) < 100 and "private-token" not in str(error)
        copied = pickle.loads(pickle.dumps(error))
        assert copied.__dict__ == error.__dict__
        assert str(copied) == str(error)
    for name in ("/" + secret, secret + "\0"):
        with pytest.raises(walkup.InvalidMarkerError) as info:
            walkup.Marker(name)
        assert len(str(info.value)) < 100 and "private-token" not in str(info.value)
    for option in ("mode", "on_error"):
        with pytest.raises(walkup.InvalidMarkerError) as info:
            walkup.find("x", start=tmp_path, **{option: secret})  # type: ignore[arg-type]
        assert len(str(info.value)) < 100 and "private-token" not in str(info.value)


def test_marker_check_must_be_callable() -> None:
    with pytest.raises(walkup.InvalidMarkerError, match="callable"):
        walkup.Marker("x", check=42)  # type: ignore[arg-type]


def test_values_are_frozen_hashable_and_pickle_by_public_name(tmp_path: Path) -> None:
    marker = walkup.Marker.file("x")
    match = walkup.Match(tmp_path, (marker,), (tmp_path / "x",))
    for value in (marker, match):
        assert value.__class__.__module__ == "walkup"
        assert pickle.loads(pickle.dumps(value)) == value
        assert hash(value) == hash(pickle.loads(pickle.dumps(value)))
        with pytest.raises(FrozenInstanceError):
            value.directory = tmp_path  # type: ignore[union-attr,misc]


def test_public_annotations_resolve_without_private_imports() -> None:
    for name in walkup.__all__:
        value = getattr(walkup, name)
        if inspect.isfunction(value):
            assert get_type_hints(value)
        elif inspect.isclass(value):
            get_type_hints(value)
            if inspect.isfunction(value.__init__):
                assert get_type_hints(value.__init__)


def test_cli_usage_errors_never_echo_input(capsys: pytest.CaptureFixture[str]) -> None:
    secret = "private-token-" + "x" * 100_000
    for args in (["--kind", secret], ["--" + secret], ["--preset", secret]):
        with pytest.raises(SystemExit) as info:
            main(args)
        output = capsys.readouterr()
        assert info.value.code == 1 and output.out == ""
        assert "private-token" not in output.err and len(output.err) < 1000


def test_callback_exceptions_are_not_relabelled(tmp_path: Path) -> None:
    (tmp_path / "x").touch()

    def check(path: Path) -> bool:
        raise RuntimeError("callback failed")

    with pytest.raises(RuntimeError, match="callback failed"):
        walkup.find(walkup.Marker("x", check=check), start=tmp_path)
