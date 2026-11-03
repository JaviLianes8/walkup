"""Allow ``python -m walkupward``."""

from __future__ import annotations

import sys

from walkupward._cli import main

if __name__ == "__main__":
    sys.exit(main())
