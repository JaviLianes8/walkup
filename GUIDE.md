# walkup guide

## The walk

Every search walks from a start path toward the filesystem root, nearest directory first.
A file as the start begins the walk at its parent. Paths are always absolute. The walk ends
at `/`, at a drive root such as `C:\`, or at the share root of a UNC path such as
`\\server\share\`, unless an option stops it earlier.

`walk_up(start=".", *, ceilings=(), stop_at=None, same_filesystem=False, resolve=True)`
yields those directories. Every search function accepts the same four options.

### Ceilings and stop_at

`ceilings` behaves like git's `GIT_CEILING_DIRECTORIES`:

- the walk never enters a ceiling or anything above it;
- a ceiling only counts when it is a proper ancestor of the start, so starting in the
  ceiling directory itself still searches it (and keeps climbing, as git does);
- with several ceilings, the nearest applicable one wins; the others are ignored.

`stop_at` is the inclusive counterpart: that directory is searched last. It has no effect
when it is not on the walk. `find_up(..., root=...)` uses the same inclusive rule.

```python
walk_up("/w/a/b/c", ceilings=["/w/a"])  # /w/a/b/c, /w/a/b
walk_up("/w/a/b/c", stop_at="/w/a")  # /w/a/b/c, /w/a/b, /w/a
```

### Filesystem boundaries

`same_filesystem=True` stops before a directory whose device differs from the start's,
or whose device cannot be read. This is what git does unless
`GIT_DISCOVERY_ACROSS_FILESYSTEM` is set. On Windows the device is the volume.

### Symlinks and junctions

`resolve=True` (the default) resolves symlinks and Windows junctions in the start first and
walks the physical path, like `pwd -P` and git. `resolve=False` walks the lexical path: the
start is made absolute, `..` is collapsed as text, and linked directories stay in place,
like `pwd -L`. Ceilings and `stop_at` are normalised with the same policy.

```python
# /work/link -> /data/real
walk_up("/work/link")  # /data/real, /data, /
walk_up("/work/link", resolve=False)  # /work/link, /work, /
```

## Markers

A plain string is `Marker(name)`. A `Marker` has:

- `name`: joined to each directory; it may be a relative path such as `src/pkg/__init__.py`
  but never empty or absolute (`InvalidMarkerError`);
- `kind`: `"any"` (anything that exists; a broken symlink does not), `"file"` (a regular
  file) or `"dir"`; shortcuts `Marker.file(name)` and `Marker.dir(name)`;
- `check`: an optional function called with the candidate path after the kind test; return
  `True` to accept. Use it to look inside a file.

```python
tox = Marker.file("tox.ini", lambda path: "[tox]" in path.read_text())
```

## Searches

| Function | Returns |
| --- | --- |
| `find(*markers, ...)` | the nearest `Match`, or `None` |
| `find_all(*markers, ...)` | every `Match`, nearest first (a list) |
| `iter_matches(*markers, ...)` | the same, lazily |
| `require(*markers, ...)` | the nearest `Match`, or raises `MarkerNotFoundError` |

Keyword options: `start`, `mode`, `ceilings`, `stop_at`, `same_filesystem`, `resolve`,
`on_error`.

- `mode="any"` (default): a directory matches when at least one marker is present.
- `mode="all"`: every marker must be present in the same directory.

A `Match` has `directory`, `markers` and `paths` (every requested marker present in that
directory, in request order), plus `marker`, `path` and `names` shortcuts.

Arguments are validated when the call is made, even for the lazy `iter_matches`: a start
that does not exist raises `StartNotFoundError`, and no markers raises
`InvalidMarkerError`. `find_up` and `walk_up` keep their original lenient behaviour.

### Unreadable entries

`on_error="skip"` (default) treats a candidate that raises `PermissionError` while being
inspected, including inside a `check`, as absent. `on_error="raise"` raises
`WalkupPermissionError` with the offending `path`.

## Presets

- `git_root(start=".", *, ceilings=None, across_filesystems=None)` returns the `Match` whose
  `directory` is what `git rev-parse --show-toplevel` prints: the main working tree, a
  linked worktree, or a submodule checkout. A `.git` directory must hold a valid `HEAD`
  and `objects` and `refs` (through `commondir` for a worktree); a `.git` file must start
  with `gitdir:` naming such a directory. Invalid entries are skipped, as git skips them.
  `ceilings` defaults to `GIT_CEILING_DIRECTORIES` (relative entries ignored) and
  `across_filesystems` to `GIT_DISCOVERY_ACROSS_FILESYSTEM` (false when unset). The walk
  is always physical. `GIT_DIR` and `GIT_WORK_TREE` are not consulted.
- `python_root(start=".", ...)` returns the nearest directory with `pyproject.toml`,
  `setup.cfg` or `setup.py` (regular files). `match.names` tells which are present.
- `node_root(start=".", ...)` returns the nearest directory with a `package.json` file.
- `editorconfig_chain(start=".", ...)` returns the `.editorconfig` files that apply,
  nearest first, ending at the first file whose preamble (before any `[section]`) sets
  `root = true`, compared without regard to case.

## Errors

| Error | Also a | Raised when |
| --- | --- | --- |
| `InvalidMarkerError` | `ValueError` | a marker is empty, absolute or has a bad kind, or none given |
| `StartNotFoundError` | `FileNotFoundError` | the start does not exist (`.start`) |
| `MarkerNotFoundError` | `LookupError` | `require` found nothing (`.markers`, `.start`, `.mode`) |
| `WalkupPermissionError` | `PermissionError` | `on_error="raise"` and a candidate is unreadable (`.path`) |

All of them subclass `WalkupError`.

## Command line

```
walkup [options] MARKER...
walkup [options] --preset {git,python,node,editorconfig}
```

| Option | Meaning |
| --- | --- |
| `-s, --start DIR` | where to start (default `.`) |
| `-a, --all` | print every match, nearest first |
| `-e, --every` | require every MARKER in one directory |
| `-k, --kind {any,file,dir}` | what each MARKER must be |
| `-p, --preset NAME` | use a preset instead of MARKER |
| `--ceiling DIR` | never enter DIR (repeatable; added to the git environment for `git`) |
| `--stop-at DIR` | search DIR last |
| `--same-filesystem` | stop at a filesystem boundary |
| `--lexical` | keep symlinks in the path (ignored by `--preset git`) |
| `--path` | print matched paths instead of directories |

Exit status: 0 when something matched, 1 when nothing matched or on an error (the message
goes to stderr). `python -m walkup` runs the same tool.

## Recipes

```python
# Load settings from the project that owns this module.
here = python_root(__file__)

# A monorepo package: the nearest package.json below the repository root.
repo = git_root()
pkg = find("package.json", ceilings=[repo.directory.parent] if repo else ())

# Fail loudly in a build script.
root = require(Marker.dir(".git"), "pyproject.toml", mode="all").directory
```

```sh
# Run a command from the repository root.
cd "$(walkup --preset git)" && make test
```
