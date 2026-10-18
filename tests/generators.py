"""Seeded random inputs shared by the fuzz, oracle and upgrade tests (hand-written)."""

from __future__ import annotations

import random

# Pieces that make valid headers likely and break them in every way the grammar allows.
PIECES = [
    "attachment",
    "inline",
    "form-data",
    "x",
    ";",
    "; ",
    " ;",
    "=",
    " = ",
    "\t",
    " ",
    "filename",
    "filename*",
    "FILENAME",
    "name",
    "title*",
    "a*b",
    "*",
    '"',
    '"a b"',
    '"a;b"',
    '"\\""',
    '"\\\\"',
    "\\",
    "'",
    "%",
    "%41",
    "%e2%82%ac",
    "%C3",
    "%85",
    "UTF-8''",
    "utf-8'en'",
    "ISO-8859-1''",
    "x-ext''",
    "UTF-8'en-US'",
    "''",
    ",",
    "\xe9",
    "\u20ac",
    "\x00",
    "\r",
    "\n",
    "\x7f",
    "\x85",
    "tok",
    "foo.html",
    "a/b",
]
NAMES = ["filename", "FileName", "name", "title", "a*b", "size", "x", "creation-date"]
TOKENS = ["tok", "foo.html", "a", "!#$%&'*+-.^_`|~", "42", "UTF-8''%41"]
QUOTED = ['""', '"a b"', '"a;b"', '"\\""', '"\\\\"', '"caf\xe9"', '"\u20ac"', '"a\\b"']
EXT = ["UTF-8''%41", "utf-8'en'%e2%82%ac", "ISO-8859-1''%E9", "UTF-8''", "UTF-8''%FF"]
EXT += ["iso-8859-1''%85", "x-ext''%41", "UTF-8'de-CH-1901'a", "UTF-8'1'a", "utf8''a"]


def noise(rng: random.Random, pieces: int = 9) -> str:
    """Any string at all, made mostly of meaningful pieces."""
    text = "".join(rng.choice(PIECES) for _ in range(rng.randint(0, pieces)))
    if rng.random() < 0.2:
        index = rng.randrange(len(text) + 1)
        text = text[:index] + chr(rng.randrange(0x110000)) + text[index:]
    return text


def header(rng: random.Random) -> str:
    """A header that is valid more often than not."""
    parts = [rng.choice(["attachment", "inline", "form-data", "x-custom", "Attachment"])]
    for _ in range(rng.randint(0, 4)):
        name = rng.choice(NAMES)
        if rng.random() < 0.3:
            value, name = rng.choice(EXT), name.rstrip("*") + "*"
        else:
            value = rng.choice(TOKENS + QUOTED)
        parts.append(f"{name}{rng.choice(['=', ' =', '= ', ' = '])}{value}")
    separator = rng.choice(["; ", ";", " ; ", ";\t"])
    return separator.join(parts) + rng.choice(["", " ", "\t"])


def unicode_text(rng: random.Random, size: int = 12) -> str:
    """Text a file name could hold: ASCII, Latin-1, other scripts, emoji, odd characters."""
    pools = [
        (0x20, 0x7F),
        (0xA0, 0x100),
        (0x370, 0x400),
        (0x4E00, 0x4F00),
        (0x1F600, 0x1F650),
        (0x0300, 0x0370),
        (0x2000, 0x2070),
        (0xFF00, 0xFF60),
        (0x10000, 0x10100),
    ]
    chars = []
    for _ in range(rng.randint(0, size)):
        low, high = rng.choice(pools)
        chars.append(chr(rng.randrange(low, high)))
    for special in ("%41", "\\", '"', "%", "'", "\t", "/", "..", "CON", "."):
        if rng.random() < 0.05:
            chars.insert(rng.randint(0, len(chars)), special)
    return "".join(chars)
