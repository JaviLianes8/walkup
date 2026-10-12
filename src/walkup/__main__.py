"""Allow ``python -m walkup``."""

from __future__ import annotations

import sys

from walkup._cli import main

if __name__ == "__main__":
    sys.exit(main())
