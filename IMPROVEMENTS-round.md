# Improvement round: ranked proposals

Ranked by user value. Every item is additive: `find_up` and `walk_up` keep their current
behaviour, and new parameters are keyword only.

1. **Typed match results.** `find` returns a `Match` that says which directory matched,
   which markers were present there and the full path of each. Callers stop guessing
   whether `pyproject.toml` or `setup.cfg` was the reason a directory won.
2. **Any-of and all-of searches.** `find(*markers, mode="any" | "all")`. All-of answers
   questions like "the nearest directory holding both `pyproject.toml` and `.git`".
3. **Rich markers.** `Marker` describes a name, a kind (`"any"`, `"file"`, `"dir"`) and an
   optional content check that receives the candidate path, so a marker can require
   `root = true` inside a file or a valid `gitdir:` line, not only a name.
4. **Every match up the tree.** `iter_matches` (lazy) and `find_all` (list), nearest
   first, for nested projects, monorepos and config cascades.
5. **Git compatible ceilings.** `ceilings=` follows `GIT_CEILING_DIRECTORIES`: a ceiling
   is never searched and never crossed, unless the walk starts there. `stop_at=` is the
   inclusive counterpart, matching the existing `root` argument of `find_up`.
6. **Filesystem boundary.** `same_filesystem=True` stops before entering a directory on
   another device, the default behaviour of git discovery.
7. **Symlink policy.** `resolve=True` walks the physical path (like `pwd -P` and git);
   `resolve=False` walks the lexical path, keeping symlinked and junctioned components
   (like `pwd -L` and Node based finders).
8. **Presets grounded in real tools.**
   - `git_root`: a `.git` directory or a `.git` file with a `gitdir:` line, validated the
     way git validates a repository (HEAD, objects, refs, `commondir` for worktrees), and
     honouring `GIT_CEILING_DIRECTORIES` and `GIT_DISCOVERY_ACROSS_FILESYSTEM`. Checked
     against `git rev-parse --show-toplevel` in repositories, worktrees and submodules.
   - `python_root`: nearest `pyproject.toml`, `setup.cfg` or `setup.py`; formatters and
     linters stop at the first configuration file they meet in the same way.
   - `node_root`: nearest `package.json`, the lookup npm uses for the project prefix.
   - `editorconfig_chain`: every `.editorconfig` that applies, nearest first, stopping at
     the first one whose preamble says `root = true`.
9. **Honest typed errors.** `require` raises `MarkerNotFoundError` (a `LookupError`);
   a missing start raises `StartNotFoundError` (a `FileNotFoundError`); bad markers raise
   `InvalidMarkerError` (a `ValueError`); `on_error="raise"` surfaces unreadable
   directories as `WalkupPermissionError` (a `PermissionError`). All share `WalkupError`.
10. **Command line tool.** `walkup MARKER...` prints the nearest directory and exits 1
    when nothing matches; `--all`, `--every`, `--kind`, `--preset`, `--ceiling`,
    `--stop-at`, `--same-filesystem`, `--lexical`, `--path`. Also `python -m walkup`.
11. **Documentation.** Full docstrings and a `GUIDE.md` covering every option, the
    symlink and ceiling semantics, and recipes.
12. **Real end to end coverage.** Contract tests over real temporary trees, git cross
    checks, and a test that builds the wheel, installs it in a fresh virtual environment
    and runs the installed `walkup` script.

Not taken this round: glob markers (patterns hide cost and ordering questions) and TOML
table checks for tool specific configuration (no parser on Python 3.10 without a
dependency; a `Marker` check covers it for callers who have one).
