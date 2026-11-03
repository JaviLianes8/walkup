"""Fetch the pinned specification to a caller-selected local evidence directory."""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path


def main() -> None:
    destination = Path(sys.argv[1])
    destination.mkdir(parents=True, exist_ok=True)
    manifest = Path(__file__).resolve().parents[1] / "GROUND-TRUTH.json"
    for entry in json.loads(manifest.read_text(encoding="utf-8")):
        with urllib.request.urlopen(entry["url"], timeout=60) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError("download does not match the recorded specification")
        (destination / entry["file"]).write_bytes(data)


if __name__ == "__main__":
    main()
