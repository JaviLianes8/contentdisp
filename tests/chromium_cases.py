"""Read the test tables out of Chromium's http_content_disposition_unittest.cc.

The file is fetched, not committed (tests/upstream/MANIFEST.json). Its tables hold C
string literals: adjacent literals are joined, escapes are decoded as a C compiler does,
and entries inside ``#ifdef`` blocks (not compiled by default) are left out.
"""

from __future__ import annotations

import re

_LITERAL = r'(?:L?"(?:[^"\\]|\\.)*"\s*)+'
_ESCAPE = re.compile(r"\\(x[0-9A-Fa-f]+|u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8}|[0-7]{1,3}|.)", re.S)
_SIMPLE = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", "\\": "\\", '"': '"', "'": "'", "?": "?"}


def _strip(source: str) -> str:
    """The source without comments and without #ifdef ... #endif blocks."""
    source = re.sub(r"^#if.*?^#endif.*?$", "", source, flags=re.M | re.S)
    out, index, quoted = [], 0, False
    while index < len(source):
        char = source[index]
        if quoted and char == "\\":
            out.append(source[index : index + 2])
            index += 2
            continue
        if char == '"':
            quoted = not quoted
        elif not quoted and source.startswith("//", index):
            index = source.index("\n", index)
            continue
        out.append(char)
        index += 1
    return "".join(out)


def _decode(literals: str) -> str:
    """Decode each C literal's escapes, then join them (code points; narrow = bytes).

    C joins adjacent literals after decoding escapes, which is why a hex escape stops at
    the end of its literal (``L"\\x8853" L"3.png"`` holds U+8853 then "3").
    """

    def one(match: re.Match[str]) -> str:
        escape = match.group(1)
        if escape[0] in "xuU":
            return chr(int(escape[1:], 16))
        if escape[0] in "01234567":
            return chr(int(escape, 8))
        return _SIMPLE[escape]

    parts = re.findall(r'L?"((?:[^"\\]|\\.)*)"', literals, re.S)
    return "".join(_ESCAPE.sub(one, part) for part in parts)


def _table(source: str, test: str) -> str:
    start = source.index(f"TEST_P(HttpContentDispositionTest, {test})")
    return source[start : source.index("};", start)]


def tc2231_port(source: str) -> list[tuple[bytes, bool, str]]:
    """(header bytes, Chrome treats it as an attachment, file name) per tc2231 entry."""
    table = _table(_strip(source), "tc2231")
    entry = rf"\{{\s*({_LITERAL}),\s*HttpContentDisposition::(\w+),\s*({_LITERAL})\}}"
    return [
        (_decode(header).encode("latin-1"), kind == "ATTACHMENT", _decode(name))
        for header, kind, name in re.findall(entry, table, re.S)
    ]


def filename_table(source: str) -> list[tuple[bytes, str, str]]:
    """(header bytes, referrer charset, file name) per entry of the Filename test."""
    table = _table(_strip(source), "Filename")
    entry = rf"\{{\s*({_LITERAL}),\s*({_LITERAL}),\s*({_LITERAL})\}}"
    return [
        (_decode(header).encode("latin-1"), _decode(charset), _decode(name))
        for header, charset, name in re.findall(entry, table, re.S)
    ]
