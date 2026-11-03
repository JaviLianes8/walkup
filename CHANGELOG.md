# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-11-04

- Renamed from `walkup` to `walkupward`: the distribution, the import package, the command and `python -m walkupward`.
- Stabilize the twenty exported names, their signatures and defaults, ordered nearest-first
  discovery, marker filters, walk boundaries, presets, typed results and CLI exit statuses.
- Error messages no longer echo paths, marker names or invalid option values. Original
  inputs remain available in error attributes. CLI usage errors use a fixed diagnostic;
  filesystem failures are reported without a traceback or input contents.
- Invalid `mode` and `on_error` values now raise `InvalidMarkerError` (still a `ValueError`).
  Non-callable marker checks are rejected at construction instead of failing during search.
- The last `root` assignment in an EditorConfig preamble now wins. Only LF/CRLF split
  preamble lines; a section must have both opening and closing brackets. Inline comments
  remain part of values. The optional UTF-8 BOM remains accepted.
- A closed CLI output pipe returns failure instead of propagating `BrokenPipeError`.
- Malformed gitfiles containing NUL are ignored as invalid instead of raising `ValueError`.
- Public classes now pickle by their `walkupward` names; old private import paths remain
  available for existing pickles. Public annotations resolve at runtime.
- Remove the incidental `annotations` attribute from the package namespace.
- `git_root` and `iter_git_roots` now follow git more closely: a repository whose config
  sets `core.bare` (or a config git refuses) has no working tree and gives `None`;
  `GIT_COMMON_DIR` and `GIT_OBJECT_DIRECTORY` are honoured; `GIT_CEILING_DIRECTORIES`
  entries after an empty entry are compared literally; an invalid
  `GIT_DISCOVERY_ACROSS_FILESYSTEM` value gives `None` instead of being read as false or
  trimmed; `HEAD` is validated on its first 255 bytes with ASCII whitespace; a NUL ends the
  path in a `.git` file or `commondir`.
- `walk_up` and `iter_matches` check `start`, ceilings and `stop_at` when called: a value
  that is not a path raises `TypeError` before the first item. Every search raises
  `TypeError` for a non-path `start` such as an integer, instead of `OverflowError` or
  treating it as a file descriptor.
- A marker name too long for the platform to express as a path counts as absent instead of
  raising `ValueError`.
- `WalkupPermissionError` no longer displays the original `PermissionError` in tracebacks
  (it stays available as `__context__`), so its text cannot leak.
- Choosing the nearest ceiling no longer builds every ancestor of the start, removing
  quadratic time and memory on very deep paths.
- The CLI rejects an explicit `--kind` with a preset even when its value is `any`.
- Add executable public examples, seeded properties, specification/reference checks,
  strict typing contracts, and wheel/sdist validation. Ship the `py.typed` marker.

## [0.2.0]

- `find`, `find_all`, `iter_matches` and `require` search for one marker or several, in
  any-of or all-of mode, and return a typed `Match` naming the directory and the markers
  present there.
- `Marker` describes a name, a kind (`"any"`, `"file"`, `"dir"`) and an optional check that
  inspects the candidate path.
- `walk_up`, `find`, `find_all`, `iter_matches`, `require` and the non-git presets accept `ceilings` (git `GIT_CEILING_DIRECTORIES` semantics),
  an inclusive `stop_at`, `same_filesystem`, and `resolve` for physical or lexical walks.
- Presets: `git_root` and `iter_git_roots` (worktrees and submodules, discovery step by
  step like git, honouring the git ceiling and filesystem variables), `python_root`, `node_root` and `editorconfig_chain`.
- Typed errors: `WalkupError`, `InvalidMarkerError`, `StartNotFoundError`,
  `MarkerNotFoundError` and `WalkupPermissionError`, each also a matching builtin.
- A command line tool (now `walkupward`, also `python -m walkupward`) with `--all`, `--every`,
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
