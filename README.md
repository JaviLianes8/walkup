# walkup

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
- Walk options shared by every function: git style `ceilings`, an inclusive `stop_at`,
  `same_filesystem`, and `resolve` to choose physical or lexical symlink handling.
- Presets: `git_root` and `iter_git_roots` (discovery step by step like git, honouring
  `GIT_CEILING_DIRECTORIES` and `GIT_DISCOVERY_ACROSS_FILESYSTEM`), `python_root`,
  `node_root`, `editorconfig_chain`.
- Typed errors that are also the builtin you would expect: `MarkerNotFoundError`
  (`LookupError`), `StartNotFoundError` (`FileNotFoundError`), `InvalidMarkerError`
  (`ValueError`), `WalkupPermissionError` (`PermissionError`), all under `WalkupError`.

See [GUIDE.md](GUIDE.md) for every option, the exact ceiling and symlink rules, and recipes.

## Why

JavaScript has [find-up](https://www.npmjs.com/package/find-up) for locating a config or a
project root, but Python has no clean, typed peer. The nearest package on PyPI stopped at a
single release in 2014, pattern based and untyped. `walkup` is a small, modern take: full
type hints, `py.typed`, no runtime dependencies, presets checked against the real tools,
and a command line tool for shell scripts.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
