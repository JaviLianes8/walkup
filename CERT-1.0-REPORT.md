# walkup 1.0.0 certification report

Date: 2026-11-03.

Progress:
- [x] Inspect main and create `release/1.0.0` from `0319afc`.
- [x] Check PyPI: https://pypi.org/pypi/walkup/json returned HTTP 404 on 2026-11-03.
- [x] Review public API, examples, annotations and error contracts.
- [x] Fetch the EditorConfig specification and run Git/reference-parser comparisons.
- [x] Add seeded filesystem/preamble properties and bounded-diagnostic contracts.
- [x] Update README, GUIDE, CHANGELOG and 1.0.0 metadata.
- [ ] Inspect final wheel/sdist and run isolated installed consumers.
- [ ] Run all available supported interpreters.
- [ ] Complete the deliberate mutation round and final gates.
- [ ] Independent review and five QA lenses (separate stage).
- [ ] PR and final repository guard; merge and publication remain pending.

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
2026-11-03: https://git-scm.com/docs/git. No remembered command output is used.

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
