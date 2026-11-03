# walkup

[![Lianes8 Certified](https://lianes8studio.com/certified/lianes8-certified-badge.svg)](https://lianes8studio.com/certified)

Walk up from a start directory to find a marker file or directory, typed and dependency free.

## Install

```
pip install walkup
```

## Usage

```python
from walkup import Marker, find, find_all, git_root, python_root, require

# Nearest directory holding pyproject.toml or setup.cfg, and which one was there.
match = find("pyproject.toml", "setup.cfg")
if match:
    print(match.directory, match.names)

# Nearest directory holding both markers, or a clear error.
root = require("pyproject.toml", Marker.dir(".git"), mode="all").directory

# Every package.json from here up to (and including) the workspace root.
packages = find_all("package.json", stop_at="/home/me/workspace")

# The repository top level, linked worktrees and submodules included.
repo = git_root()

# The Python project that owns this file.
project = python_root(__file__)
```

The original two functions keep their behaviour:

```python
from walkup import find_up, walk_up

config = find_up(["pyproject.toml", "setup.cfg"])  # a Path or None
for directory in walk_up("src/pkg"):  # start, then every ancestor
    print(directory)
```

## Command line

```
walkup pyproject.toml               # nearest directory holding pyproject.toml
walkup --every pyproject.toml .git  # nearest directory holding both
walkup --all package.json           # every enclosing directory with package.json
walkup --preset git                 # repository top level
walkup --preset editorconfig --path # the .editorconfig files that apply here
root=$(walkup --preset git) && cd "$root"
```

It prints one directory per line (matched paths with `--path`), exits 0 when something matched and 1 when nothing did.
Errors go to stderr with exit status 1. `walkup --help` lists every option.

## What you get

- `find`, `find_all`, `iter_matches`, `require`: one marker or several, any-of or
  all-of, returning a typed `Match` that names the directory and the markers present.
- `Marker`: a name plus a kind (`"any"`, `"file"`, `"dir"`) and an optional content check.
- Walk options for the general searches and Python/Node/EditorConfig presets: git style `ceilings`, an inclusive `stop_at`,
  `same_filesystem`, and `resolve` to choose physical or lexical symlink handling.
- Presets: `git_root` and `iter_git_roots` (discovery step by step like git, honouring
  `GIT_CEILING_DIRECTORIES` and `GIT_DISCOVERY_ACROSS_FILESYSTEM`), `python_root`,
  `node_root`, `editorconfig_chain`.
- Typed errors that are also the builtin you would expect: `MarkerNotFoundError`
  (`LookupError`), `StartNotFoundError` (`FileNotFoundError`), `InvalidMarkerError`
  (`ValueError`), `WalkupPermissionError` (`PermissionError`), all under `WalkupError`.

See [GUIDE](https://github.com/JaviLianes8/walkup/blob/main/GUIDE.md) for every option, the exact ceiling and symlink rules, and recipes.

## Why

For a one-off search, a loop over `pathlib.Path.parents` is often enough. `walkup`
adds ordered markers, file/directory filters, inclusive boundaries, ceilings, typed
results and a CLI. Use Git itself when you need its complete repository configuration
and ownership policy: the Git preset only implements the discovery subset described in
the [GUIDE](https://github.com/JaviLianes8/walkup/blob/main/GUIDE.md).
Use an [EditorConfig core](https://editorconfig.org/) to resolve settings for a file;
`editorconfig_chain` only finds the enclosing configuration files. Runtime dependencies: none.

## Development

Install `walkup[dev]`, then run `ruff format --check .`, `ruff check .`,
`mypy --strict src tests` and `pytest --basetemp=<scratch-directory>`.
Tests use a 300-second per-test timeout. Git tests invoke a real local Git installation.
To check the pinned specification, run `python scripts/fetch_upstream.py <scratch-directory>`
and set `WALKUP_TRUTH` to that directory. Installing `editorconfig==0.17.1` enables the
optional reference-parser tests. Both sets skip cleanly when unavailable.
The [CHANGELOG](https://github.com/JaviLianes8/walkup/blob/main/CHANGELOG.md) lists the
1.0.0 behavior changes.

## License

MIT. See [LICENSE](https://github.com/JaviLianes8/walkup/blob/main/LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
