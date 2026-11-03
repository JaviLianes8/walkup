from __future__ import annotations

import importlib.resources

import walkupward

# The public API. Add every exported name here as the library grows; this list is the
# contract and the test below fails if the module and this list disagree.
PUBLIC_API: list[str] = [
    "InvalidMarkerError",
    "Kind",
    "Marker",
    "MarkerNotFoundError",
    "Match",
    "Mode",
    "StartNotFoundError",
    "WalkupError",
    "WalkupPermissionError",
    "editorconfig_chain",
    "find",
    "find_all",
    "find_up",
    "git_root",
    "iter_git_roots",
    "iter_matches",
    "node_root",
    "python_root",
    "require",
    "walk_up",
]


def test_all_lists_exactly_the_public_api() -> None:
    assert sorted(walkupward.__all__) == sorted(PUBLIC_API)
    assert {name for name in vars(walkupward) if not name.startswith("_")} == set(PUBLIC_API)


def test_every_exported_name_resolves() -> None:
    for name in walkupward.__all__:
        assert hasattr(walkupward, name)


def test_version_is_a_three_part_string() -> None:
    parts = walkupward.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_the_package_ships_type_information() -> None:
    assert importlib.resources.files("walkupward").joinpath("py.typed").is_file()
