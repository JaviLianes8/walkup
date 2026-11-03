"""Read the two git settings discovery needs: a boolean grammar and ``core.bare``."""

from __future__ import annotations

import re
from pathlib import Path

_INT_MAX = 2**31 - 1
_NUMBER = re.compile(r"[ \t\n\v\f\r]*([+-]?)(0[xX][0-9a-fA-F]+|0[0-7]*|[1-9][0-9]*)([kKmMgG]?)")
_FACTORS = {"": 1, "k": 1024, "m": 1024**2, "g": 1024**3}
# git swaps the C character classes for its own, where only these four are space.
_SPACE = " \t\n\r"


def parse_bool(value: str | None) -> bool | None:
    """Read ``value`` with git's boolean grammar; ``None`` when git would reject it.

    A missing value (a bare key in a config file) is true and an empty one is false.
    Numbers follow C ``strtoimax`` with base detection and an optional ``k``, ``m`` or
    ``g`` factor, and must fit in a 32-bit ``int`` like git's own parser requires.
    """
    if value is None:
        return True
    if value == "":
        return False
    word = value.lower() if value.isascii() else value
    if word in ("true", "yes", "on"):
        return True
    if word in ("false", "no", "off"):
        return False
    found = _NUMBER.fullmatch(value)
    if found is None:
        return None
    sign, digits, unit = found.groups()
    del sign  # git bounds both signs by the same magnitude, so only the size matters
    base = 16 if digits[:2].lower() == "0x" else 8 if digits[0] == "0" else 10
    number = int(digits, base)
    if number > _INT_MAX // _FACTORS[unit.lower()]:
        return None
    return number != 0


def core_bare(config: Path) -> bool | None:
    """Return ``core.bare`` from a repository config: ``None`` when git would stop.

    An unreadable or missing file means not bare. A malformed file or an invalid boolean
    gives ``None``, since git refuses the repository then. Includes are not followed, as
    git does not follow them while it checks the repository format.
    """
    try:
        text = config.read_bytes().decode("utf-8", errors="surrogateescape")
    except OSError:
        return False
    text = text.removeprefix("﻿").replace("\r\n", "\n")
    try:
        entries = _entries(text + "\n\n")
    except ValueError:
        return None
    bare: bool | None = False
    for section, key, value in entries:
        if section == "core" and key == "bare":
            bare = parse_bool(value)
            if bare is None:
                return None
    return bare


def _entries(text: str) -> list[tuple[str, str, str | None]]:
    found: list[tuple[str, str, str | None]] = []
    section, at, end = "", 0, len(text)
    while at < end:
        char = text[at]
        if char in _SPACE:
            at += 1
        elif char in "#;":
            at = text.index("\n", at) + 1
        elif char == "[":
            section, at = _section(text, at + 1)
        elif char.isascii() and char.isalpha():
            key, value, at = _variable(text, at)
            found.append((section, key, value))
        else:
            raise ValueError("bad config line")
    return found


def _section(text: str, at: int) -> tuple[str, int]:
    name = ""
    while text[at] != "]":
        char = text[at]
        if char in _SPACE:
            return _subsection(text, at, name)
        if not (char.isascii() and (char.isalnum() or char in "-.")):
            raise ValueError("bad section")
        name += char.lower()
        at += 1
    return name, at + 1


def _subsection(text: str, at: int, name: str) -> tuple[str, int]:
    while text[at] in _SPACE and text[at] != "\n":
        at += 1
    if text[at] != '"':
        raise ValueError("bad section")
    at += 1
    sub = ""
    while text[at] != '"':
        if text[at] == "\n":
            raise ValueError("bad section")
        if text[at] == "\\":
            at += 1
            if text[at] == "\n":
                raise ValueError("bad section")
        sub += text[at]
        at += 1
    if text[at + 1] != "]":
        raise ValueError("bad section")
    return f"{name}.{sub}", at + 2


def _variable(text: str, at: int) -> tuple[str, str | None, int]:
    start = at
    while text[at].isascii() and (text[at].isalnum() or text[at] == "-"):
        at += 1
    key = text[start:at].lower()
    while text[at] in " \t":
        at += 1
    if text[at] == "\n":
        return key, None, at + 1
    if text[at] != "=":
        raise ValueError("bad config line")
    value, at = _value(text, at + 1)
    return key, value, at


def _value(text: str, at: int) -> tuple[str, int]:
    out: list[str] = []
    quote = comment = False
    trim: int | None = None
    while True:
        char = text[at]
        at += 1
        if char == "\n":
            if quote:
                raise ValueError("unterminated quote")
            return "".join(out[:trim] if trim is not None else out), at
        if comment:
            continue
        if char in _SPACE and not quote:
            if trim is None:
                trim = len(out)
            if out:
                out.append(char)
            continue
        if not quote and char in "#;":
            comment = True
            continue
        trim = None
        if char == "\\":
            char = text[at]
            at += 1
            if char == "\n":
                continue
            if char not in 'tbn\\"':
                raise ValueError("unknown escape")
            out.append({"t": "\t", "b": "\b", "n": "\n"}.get(char, char))
        elif char == '"':
            quote = not quote
        else:
            out.append(char)
