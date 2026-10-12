import importlib.resources

import walkup

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
    "iter_matches",
    "node_root",
    "python_root",
    "require",
    "walk_up",
]


def test_all_lists_exactly_the_public_api() -> None:
    assert sorted(walkup.__all__) == sorted(PUBLIC_API)


def test_every_exported_name_resolves() -> None:
    for name in walkup.__all__:
        assert hasattr(walkup, name)


def test_version_is_a_three_part_string() -> None:
    parts = walkup.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_the_package_ships_type_information() -> None:
    assert importlib.resources.files("walkup").joinpath("py.typed").is_file()
