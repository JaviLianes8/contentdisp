"""Strict mode against a grammar oracle on seeded random headers.

The oracle below is a regular expression derived by hand from the RFC 6266 section 4.1
ABNF, with token, quoted-string and OWS from RFC 9110 and ext-value from RFC 8187, whose
language part is checked by a walk over the RFC 5646 section 2.1 subtags written by hand.
It is written independently of the parser: no code is shared. A name ending in "*" (even
"*" alone) is read as an extended parameter, as the parser documents.
"""

from __future__ import annotations

import random
import re
from urllib.parse import unquote_to_bytes

from contentdisp import parse
from langtag_oracle import language_tag_ok

TCHAR = r"[!#$%&'*+\-.^_`|~0-9A-Za-z]"
OWS = r"[ \t]*"
QUOTED = r'"(?:[\t !#-\[\]-~\x80-\U0010ffff]|\\[\t -~\x80-\U0010ffff])*"'
EXT = r"[A-Za-z0-9!#$%&+\-^_`{}~]+'[A-Za-z0-9\-]*'(?:%[0-9A-Fa-f]{2}|[A-Za-z0-9!#$&+\-.^_`|~])*"
PLAIN_NAME = rf"(?:{TCHAR}*[!#$%&'+\-.^_`|~0-9A-Za-z])"
PARM = rf"(?:{PLAIN_NAME}{OWS}={OWS}(?:{TCHAR}+|{QUOTED})|{TCHAR}*\*{OWS}={OWS}{EXT})"
HEADER = re.compile(rf"{OWS}{TCHAR}+(?:{OWS};{OWS}{PARM})*{OWS}")
NAME = re.compile(rf";{OWS}({TCHAR}+){OWS}=")

PIECES = [
    "attachment",
    "inline",
    "x",
    '"q"',
    ";",
    "; ",
    " ;",
    "=",
    " = ",
    "filename",
    "filename*",
    "FILENAME",
    "name",
    "a*b",
    "*",
    '"a b"',
    '"a;b"',
    '"\\""',
    '"\\',
    "tok",
    "UTF-8''%41",
    "utf-8'en'a%20b",
    "ISO-8859-1''%E4",
    "ISO-8859-1''%85",
    "UTF-8''%C3",
    "''x",
    "%4",
    "UTF-8'",
    "\t",
    " ",
    "\xe9",
    "\u20ac",
    ",",
    "\r\n",
    "UTF-8'en-US'%41",
    "UTF-8'x-a'b",
    "UTF-8'1'b",
    "a=b",
    '""',
    "foo.html",
    "%",
]


NAMES = ["filename", "FileName", "name", "a*b", "filename*", "title*", "x"]
VALUES = ["tok", '"a b"', '"a;b"', "UTF-8''%41", "ISO-8859-1''%85", "UTF-8''%C3", "x'y'z"]
VALUES += ["UTF-8'de-CH-1901'%41", "utf-8'i-klingon'a", "UTF-8'en-a-bb-x-1'a", "UTF-8'en-'a"]


def _structured(rng: random.Random) -> str:
    params = [
        f"{rng.choice(NAMES)}{rng.choice(['=', ' = '])}{rng.choice(VALUES)}"
        for _ in range(rng.randint(0, 3))
    ]
    return "; ".join(["attachment", *params])


def _random_header(rng: random.Random) -> str:
    if rng.random() < 0.5:
        text = _structured(rng)
    else:
        text = "".join(rng.choice(PIECES) for _ in range(rng.randint(1, 9)))
    if rng.random() < 0.3:
        index = rng.randrange(len(text) + 1)
        text = text[:index] + rng.choice("\";=\\ '%*") + text[index + 1 :]
    return text


def _oracle(header: str) -> bool:
    if HEADER.fullmatch(header) is None:
        return False
    names = [name.lower() for name in NAME.findall(_without_quoted(header))]
    if len(names) != len(set(names)):
        return False
    return all(_ext_ok(value) for value in re.findall(rf"\*{OWS}={OWS}({EXT})", header))


def _without_quoted(header: str) -> str:
    return re.sub(QUOTED, '""', header)


def _ext_ok(value: str) -> bool:
    charset, _, rest = value.partition("'")
    language, _, chars = rest.partition("'")
    if language and not language_tag_ok(language):
        return False
    octets = unquote_to_bytes(chars)
    if charset.lower() == "utf-8":
        try:
            octets.decode("utf-8")
        except UnicodeDecodeError:
            return False
    if charset.lower() == "iso-8859-1":
        return not any(0x80 <= octet <= 0x9F for octet in octets)
    return True


def test_strict_mode_accepts_exactly_what_the_oracle_accepts() -> None:
    rng = random.Random(6266)
    accepted = 0
    for _ in range(20000):
        header = _random_header(rng)
        expected = _oracle(header)
        try:
            parse(header, strict=True)
        except ValueError:
            assert not expected, header
        else:
            assert expected, header
            accepted += 1
    assert accepted > 1000


def test_lenient_mode_agrees_with_strict_mode_on_valid_headers() -> None:
    rng = random.Random(8187)
    compared = 0
    for _ in range(20000):
        header = _random_header(rng)
        try:
            strict = parse(header, strict=True)
        except ValueError:
            continue
        assert parse(header) == strict, header
        compared += 1
    assert compared > 1000
