# walkup 1.0.0 certification report

Date: 2026-11-03.

Progress:
- [x] Inspect main and create `release/1.0.0` from `0319afc`.
- [x] Check PyPI: https://pypi.org/pypi/walkup/json returned HTTP 404 on 2026-11-03.
- [x] Review public API, examples, annotations and error contracts.
- [x] Fetch the EditorConfig specification and run Git/reference-parser comparisons.
- [x] Add seeded filesystem/preamble properties and bounded-diagnostic contracts.
- [x] Update README, GUIDE, CHANGELOG and 1.0.0 metadata.
- [x] Inspect wheel/sdist and run isolated installed consumers.
- [ ] Run all available supported interpreters.
- [x] Complete the deliberate mutation round.
- [x] Four gates and strict typing of tests pass.
- [ ] Independent review and five QA lenses (separate stage).
- [ ] PR; merge and publication remain pending.

## API and behavior

The twenty names in `__all__` retain their signatures and defaults. `__version__` is
1.0.0. `Marker` and `Match` remain frozen dataclasses; exception attributes, builtin
base classes, and pickle round trips are tested. Public types pickle through `walkup`;
old private paths remain importable. Runtime type hints resolve without private imports.
Literal aliases have executable module examples because their runtime objects belong
to `typing`; every public callable and property has a runnable docstring.

Behavior changes, all documented in CHANGELOG: safe diagnostic text, typed invalid
search-option errors, eager callable validation, EditorConfig last-assignment semantics
and LF/CRLF processing, and clean CLI failures for closed output pipes/path errors.
`find_up` retains its legacy permissiveness. `Match` constructor invariants and native
filesystem/callback exception boundaries are documented in GUIDE.

## Ground truth

Fetched 2026-11-03: https://spec.editorconfig.org/ and the source at
https://raw.githubusercontent.com/editorconfig/specification/f58051318a657b52b73ff2d7774a66fa6c296bd8/index.rst.
`GROUND-TRUTH.json` records revision, URL, date, license, size and SHA-256. The downloaded
text stays outside the repository. `scripts/fetch_upstream.py` refetches and verifies it;
`WALKUP_TRUTH` enables its hash and rule-presence test. Derived cases are explicitly
labelled as handwritten, not copied vectors. The Python EditorConfig 0.17.1 reference
parser agrees on eight preamble cases. Its obsolete inline-comment behavior is excluded
from the oracle subset; current specification contracts cover that difference.

Git 2.54.0.windows.1 ran in this session. `test_git`, `test_git_edges` and `test_promise`
construct real repositories, worktrees and submodules and compare with actual
`git rev-parse --show-toplevel` output: ordinary discovery, ceilings, invalid gitfiles,
HEAD forms, common directories and bare repositories. Documentation checked on
2026-11-03: https://git-scm.com/docs/git.

## Properties and robustness

Three seeds (7, 191, 20261103) exercise 600 any/all searches against an independent
parent scan, with marker order and boundaries. Another 1,000 seeded preambles exercise
last-assignment semantics. Files with 10,000, 100,000 and 1,000,000-character comments
and values exercise large input. Errors and CLI arguments receive 100,000-character
private strings and must produce bounded messages without input contents.
All tests have a 300-second timeout. Filesystem tests use explicitly selected scratch
directories. Cross-device stopping is also tested with an injected device probe.

## Pending independent stages

Items 16 and 19 have not been run. No independent reviewer or lens verdict is claimed.
Merge and publication (item 17) remain the maintainer's responsibility.

## Preparation scorecard

| Item | Result | Evidence |
| --- | --- | --- |
| 1 | PASS | Same twenty public names, signatures and defaults; behavior changes in CHANGELOG. |
| 2 | PASS | Exact exports and no incidental public attributes, tested in `test_contract`. |
| 3 | PASS | Every callable/property example and both README/GUIDE Python blocks executed in the module/public namespace; no skipped doctests. |
| 4 | PASS | `mypy --strict src tests`; runtime annotations; installed `py.typed`. |
| 5 | PASS | Typed errors, builtin bases, fixed diagnostics and pickle attributes tested; native exception boundaries documented. |
| 6 | PASS | Search, marker, match, walk, preset, error, CLI and installed consumer contracts. |
| 7 | PASS | Fetched specification, real Git commands and EditorConfig reference parser, detailed above. |
| 8 | PASS | Isolated wheel consumers and CLI; no PyPI release exists to upgrade. |
| 9 | PASS | Seeded trees, preambles and 500 malformed gitfiles; large files and diagnostics. |
| 10 | pending | Twelve builds passed the first matrix and final CLI/doc checks; full final-wheel matrix in progress. |
| 11 | PASS | README problem, scoped comparisons, absolute links, exact badge and strict twine checks. |
| 12 | PASS | Dated 2026-11-03 section with all behavior changes. |
| 13 | PASS | 1.0.0, stable classifier, Python 3.10 through 3.14, MIT, project URLs, no runtime dependencies. |
| 14 | PASS | Wheel: 17 package/metadata/license entries. Sdist: source, tests, docs, manifest/refetch script and metadata; no fetched text or scratch files. |
| 15 | PASS | Format, lint, source types and pytest each exit zero separately; test types also clean. |
| 16 | pending | Separate independent review. |
| 17 | pending | PR preparation only; merge and publication not performed. |
| 18 | PASS | Mutation table below: all intentional defects detected. |
| 19 | pending | Five separate QA lenses. |

## Mutation round

Each defect was applied alone in an isolated source copy, with bytecode disabled, a
300-second per-test timeout and the relevant contract module or test selected. Every
failure below is an assertion failure or an unexpected exception in a collected test,
not an import/collection failure. Each source file was restored before the next mutation.
The original suite passed before the round and the full expanded suite passed afterward.

| Id | Deliberate defect | Caught by |
| --- | --- | --- |
| W01 | yield parent instead of start | `test_walk.py::test_a_ceiling_is_never_entered` |
| W02 | ignore ceilings | `test_walk.py::test_a_ceiling_is_never_entered` |
| W03 | ignore inclusive stop | `test_walk.py::test_stop_at_is_inclusive_and_ignored_off_the_path` |
| W04 | invert filesystem boundary | `test_boundaries.py::test_walk_never_enters_a_different_or_unreadable_device[None]` |
| F01 | legacy lookup returns directory | `test_find.py::test_finds_a_marker_in_a_parent_directory` |
| S01 | nearest search always absent | `test_search.py::test_find_reports_the_directory_and_every_marker_present` |
| S02 | reverse matches | `test_search.py::test_find_all_lists_matches_nearest_first` |
| S03 | wrong required-match exception | `test_search.py::test_require_returns_or_raises_a_lookup_error` |
| P01 | all mode accepts one marker | `test_search.py::test_all_mode_requires_every_marker_in_one_directory` |
| P02 | file marker accepts directory | `test_search.py::test_kinds_separate_files_from_directories` |
| P03 | directory marker accepts file | `test_search.py::test_kinds_separate_files_from_directories` |
| P04 | ignore callback rejection | `test_search.py::test_a_check_looks_inside_the_candidate` |
| T01 | accept absolute marker | `test_search.py::test_invalid_marker_names_are_rejected[/etc]` |
| T02 | accept unknown kind | `test_search.py::test_an_unknown_kind_is_rejected` |
| T03 | first marker becomes last | `test_search.py::test_find_reports_the_directory_and_every_marker_present` |
| E01 | leak start in error text | `test_robustness.py::test_error_messages_do_not_echo_private_or_large_inputs` |
| C01 | first true wins preamble | `test_editorconfig_truth.py::test_root_processing_contract[root=true\nroot=false\n-False]` |
| C02 | ignore EditorConfig root | `test_presets.py::test_the_chain_stops_at_the_first_root_file` |
| G01 | reject symbolic Git HEAD | `test_git.py::test_a_plain_repository_matches_git` |
| L01 | absence exits success | `test_cli.py::test_nothing_found_exits_one_quietly` |
| L02 | retry broken pipe at shutdown | `test_cli_rules.py::test_a_closed_output_pipe_exits_one_without_a_traceback` |
| L03 | bypass help/version output handling | `test_cli_rules.py::test_a_closed_output_pipe_exits_one_without_a_traceback[args1]` |

## Packaging and installed consumers

The wheel and sdist both pass `twine check --strict`. Archive entries and metadata
were inspected: LICENSE and `py.typed` are present, runtime dependencies are absent,
and the package contains no tests or downloaded content. The sdist contains the useful
test suite, but excludes release/process notes and local evidence.

The sdist tests were extracted without `src`, installed-wheel locations were printed
and checked, and the full suite ran from that external directory. The e2e fixture also
creates another fresh venv, installs the wheel without an index, drives the actual
console script, and runs an isolated `python -I` consumer plus `python -I -m walkup`.

The final source suite has 188 passing tests and four platform skips: undecodable POSIX
names, POSIX directory traversal denial, unavailable symlink privileges, and a second
physical volume. Junction traversal and an injected cross-device probe do run on Windows.
The reference parser emits eight deprecation warnings on Python 3.14, with no failures.

There are 22 killed mutations and no survivors. A separate large-file run used a comment
and value each of 100,000, 1,000,000 and 10,000,000 characters. Median lookup times over
seven runs were 0.0020, 0.0085 and 0.0570 seconds respectively on this machine.
