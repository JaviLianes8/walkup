# walkup

Walk up from a start directory to find a marker file or directory, typed and dependency free.

## Install

```
pip install walkup
```

## Usage

```python
from walkup import find_up, walk_up

# Find the nearest pyproject.toml from the current directory upward.
config = find_up("pyproject.toml")

# Try several markers; the first match within each directory wins.
project_root = find_up(["pyproject.toml", "setup.cfg", ".git"])

# Start elsewhere and stop at a boundary so the search never climbs past it.
found = find_up(".git", start="src/pkg", root="/home/me/project", kind="dir")

# Iterate a directory and every ancestor up to the filesystem root.
for directory in walk_up("src/pkg"):
    print(directory)
```

`find_up(names, start=".", root=None, *, kind="any")` returns a `pathlib.Path` for the
first match, or `None`. `names` is a single name or an iterable of names. `root`, when
given, is the last directory searched. `kind` is `"any"`, `"file"` or `"dir"`.

`walk_up(start=".")` yields the start directory, then each parent, ending at the root. A
file path begins the walk at its parent, and every yielded path is absolute.

## Why

JavaScript has [find-up](https://www.npmjs.com/package/find-up) for locating a config or a
project root, but Python has no clean, typed peer. The nearest package on PyPI stopped at a
single release in 2014, pattern based and untyped. `walkup` is a small, modern take: full
type hints, `py.typed`, no runtime dependencies, and a two function surface that covers the
common cases (one marker or several, a stop boundary, files versus directories).

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
