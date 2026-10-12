"""Command line interface: print the directory that holds a marker, nearest first."""

from __future__ import annotations

import argparse
import io
import os
import sys
from collections.abc import Iterator, Sequence
from typing import NoReturn

from walkup import __version__
from walkup._git import env_ceilings, iter_git_roots
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
  root=$(walkup --preset git) && cd "$root"   jump to the repository root

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


# Options each preset cannot honour; passing one is a usage error.
_PRESET_CONFLICTS = {
    "git": ("every", "kind", "lexical", "stop_at"),
    "python": ("every", "kind"),
    "node": ("every", "kind"),
    "editorconfig": ("all", "every", "kind"),
}
_DEFAULTS = {"all": False, "every": False, "kind": "any", "lexical": False, "stop_at": None}


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line tool and return its exit status."""
    parser = build_parser()
    args = parser.parse_args(argv)
    _validate(parser, args)
    try:
        lines = list(_lines(args))
    except (WalkupError, OSError) as exc:
        print(f"walkup: error: {exc}", file=sys.stderr)
        return 1
    if lines and not _emit("".join(line + "\n" for line in lines)):
        return 1
    return 0 if lines else 1


def _validate(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if not args.markers and not args.preset:
        parser.error("give one or more MARKER names, or --preset")
    if args.markers and args.preset:
        parser.error("MARKER names and --preset cannot be combined")
    for name in _PRESET_CONFLICTS.get(args.preset or "", ()):
        if getattr(args, name) != _DEFAULTS[name]:
            flag = "--" + name.replace("_", "-")
            parser.error(f"{flag} does not apply to --preset {args.preset}")


def _emit(text: str) -> bool:
    out = sys.stdout
    if os.name != "nt" and isinstance(out, io.TextIOWrapper):
        out.reconfigure(errors="surrogateescape")
    try:
        out.write(text)
        out.flush()
    except UnicodeEncodeError:
        encoding = getattr(out, "encoding", None) or "unknown"
        print(
            f"walkup: error: a path cannot be written in the output encoding ({encoding}); "
            "set PYTHONIOENCODING=utf-8 or PYTHONUTF8=1",
            file=sys.stderr,
        )
        return False
    return True


def _lines(args: argparse.Namespace) -> Iterator[str]:
    ceilings: list[str] = list(args.ceiling)
    resolve = not args.lexical
    if args.preset == "editorconfig":
        chain = editorconfig_chain(
            args.start,
            ceilings=ceilings,
            stop_at=args.stop_at,
            same_filesystem=args.same_filesystem,
            resolve=resolve,
        )
        yield from (str(path if args.path else path.parent) for path in chain)
        return
    found: Iterator[Match]
    if args.preset == "git":
        across = None if not args.same_filesystem else False
        found = iter_git_roots(
            args.start, ceilings=env_ceilings() + ceilings, across_filesystems=across
        )
    else:
        markers: tuple[Marker, ...]
        if args.preset == "python":
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
            same_filesystem=args.same_filesystem,
            resolve=resolve,
        )
    for match in found:
        yield from (str(p) for p in match.paths) if args.path else (str(match.directory),)
        if not args.all:
            return
