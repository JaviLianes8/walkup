"""Command line interface: print the directory that holds a marker, nearest first."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterator, Sequence
from typing import NoReturn

from walkup import __version__
from walkup._git import GIT_MARKER, env_across_filesystems, env_ceilings
from walkup._presets import NODE_MARKERS, PYTHON_MARKERS, editorconfig_chain
from walkup._search import iter_matches
from walkup._types import Marker, Match, WalkupError

EXAMPLES = """\
examples:
  walkup pyproject.toml               nearest directory holding pyproject.toml
  walkup pyproject.toml setup.cfg     nearest directory holding either one
  walkup --every pyproject.toml .git  nearest directory holding both
  walkup --all package.json           every enclosing directory with package.json
  walkup --kind dir .venv             nearest .venv that is a directory
  walkup --preset git                 git top level (worktrees and submodules too)
  walkup --preset editorconfig --path the .editorconfig files that apply here
  walkup --path --start src setup.cfg print the file path instead of its directory
  cd "$(walkup --preset git)"         jump to the repository root

exit status: 0 when something matched, 1 when nothing matched or on an error.
"""

PRESETS = ("git", "python", "node", "editorconfig")


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser behind the ``walkup`` command."""
    parser = _Parser(
        prog="walkup",
        description="Walk up from a directory and print the nearest one holding a marker.",
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add = parser.add_argument
    add("markers", nargs="*", metavar="MARKER", help="file or directory name to look for")
    add("-s", "--start", default=".", metavar="DIR", help="where to start (default: .)")
    add("-a", "--all", action="store_true", help="print every match, nearest first")
    add("-e", "--every", action="store_true", help="require every MARKER in one directory")
    add("-k", "--kind", choices=("any", "file", "dir"), default="any", help="what MARKER is")
    add("-p", "--preset", choices=PRESETS, help="use a ready-made finder instead of MARKER")
    add("--ceiling", action="append", default=[], metavar="DIR", help="never enter DIR")
    add("--stop-at", metavar="DIR", help="search DIR last (inclusive boundary)")
    add("--same-filesystem", action="store_true", help="stop at a filesystem boundary")
    add("--lexical", action="store_true", help="keep symlinks in the path (no resolving)")
    add("--path", action="store_true", help="print the matched path, not its directory")
    add("--version", action="version", version=f"walkup {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line tool and return its exit status."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if bool(args.markers) == bool(args.preset):
        parser.error("give one or more MARKER names, or --preset, but not both")
    try:
        lines = list(_lines(args))
    except (WalkupError, OSError) as exc:
        print(f"walkup: error: {exc}", file=sys.stderr)
        return 1
    for line in lines:
        print(line)
    return 0 if lines else 1


def _lines(args: argparse.Namespace) -> Iterator[str]:
    ceilings: list[str] = list(args.ceiling)
    same_filesystem: bool = args.same_filesystem
    resolve = not args.lexical
    if args.preset == "editorconfig":
        chain = editorconfig_chain(
            args.start,
            ceilings=ceilings,
            stop_at=args.stop_at,
            same_filesystem=same_filesystem,
            resolve=resolve,
        )
        yield from (str(path if args.path else path.parent) for path in chain)
        return
    markers: tuple[Marker, ...]
    if args.preset == "git":
        markers = (GIT_MARKER,)
        ceilings = env_ceilings() + ceilings
        same_filesystem = same_filesystem or not env_across_filesystems()
        resolve = True
    elif args.preset == "python":
        markers = PYTHON_MARKERS
    elif args.preset == "node":
        markers = NODE_MARKERS
    else:
        markers = tuple(Marker(name, args.kind) for name in args.markers)
    found = iter_matches(
        *markers,
        start=args.start,
        mode="all" if args.every else "any",
        ceilings=ceilings,
        stop_at=args.stop_at,
        same_filesystem=same_filesystem,
        resolve=resolve,
    )
    for match in found:
        yield from _render(match, args.path)
        if not args.all:
            return


def _render(match: Match, as_path: bool) -> Iterator[str]:
    if as_path:
        yield from (str(path) for path in match.paths)
    else:
        yield str(match.directory)
