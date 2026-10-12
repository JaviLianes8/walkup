# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0]

- `find`, `find_all`, `iter_matches` and `require` search for one marker or several, in
  any-of or all-of mode, and return a typed `Match` naming the directory and the markers
  present there.
- `Marker` describes a name, a kind (`"any"`, `"file"`, `"dir"`) and an optional check that
  inspects the candidate path.
- `walk_up` and every search accept `ceilings` (git `GIT_CEILING_DIRECTORIES` semantics),
  an inclusive `stop_at`, `same_filesystem`, and `resolve` for physical or lexical walks.
- Presets: `git_root` and `iter_git_roots` (worktrees and submodules, discovery step by
  step like git, honouring the git ceiling and filesystem variables), `python_root`, `node_root` and `editorconfig_chain`.
- Typed errors: `WalkupError`, `InvalidMarkerError`, `StartNotFoundError`,
  `MarkerNotFoundError` and `WalkupPermissionError`, each also a matching builtin.
- A `walkup` command line tool (also `python -m walkup`) with `--all`, `--every`,
  `--kind`, `--preset`, `--ceiling`, `--stop-at`, `--same-filesystem`, `--lexical` and
  `--path`.
- `walk_up` starts at the parent of any existing start that is not a directory, such as a
  device, not only of a regular file.
- `GUIDE.md` documents every option and recipe.

## [0.1.0]

- First release: `find_up` to locate a marker file or directory by walking up toward the
  filesystem root, and `walk_up` to iterate a directory and its ancestors.
- `find_up` accepts one name or several, takes an optional `root` stop boundary, and can
  restrict matches to files or directories through `kind`.
