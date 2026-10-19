"""Character classes and scanners for the RFC 9110 token and quoted-string rules."""

from __future__ import annotations

import string

from ._errors import ContentDispositionError

# RFC 9110 5.6.2: any VCHAR except the delimiters.
TCHAR = frozenset(string.ascii_letters + string.digits + "!#$%&'*+-.^_`|~")
OWS = " \t"


def is_token(text: str) -> bool:
    """True when ``text`` is one or more tchar."""
    return bool(text) and all(char in TCHAR for char in text)


def is_ext_name(name: str) -> bool:
    """True for an RFC 6266 ext-token: a token followed by ``*`` (so ``*`` alone is not)."""
    return len(name) > 1 and name.endswith("*")


def skip_ows(text: str, pos: int) -> int:
    while pos < len(text) and text[pos] in OWS:
        pos += 1
    return pos


def read_token(text: str, pos: int) -> tuple[str, int]:
    end = pos
    while end < len(text) and text[end] in TCHAR:
        end += 1
    return text[pos:end], end


def _qdtext(char: str) -> bool:
    # HTAB / SP / %x21 / %x23-5B / %x5D-7E / obs-text (%x80-FF)
    code = ord(char)
    return char in "\t " or (0x21 <= code <= 0x7E and char not in '"\\') or code >= 0x80


def _pair_char(char: str) -> bool:
    code = ord(char)
    return char in "\t " or 0x21 <= code <= 0x7E or code >= 0x80


def read_quoted(text: str, pos: int, *, strict: bool) -> tuple[str, int]:
    """Read the quoted-string that starts at ``text[pos]`` (a DQUOTE).

    Returns the unescaped content and the index after the closing quote. In strict mode
    a character outside the grammar or a missing closing quote raises
    ``ContentDispositionError`` with its index in ``text``; otherwise the string runs to
    the end of the text and odd characters are kept.
    """
    out: list[str] = []
    pos += 1
    while pos < len(text):
        char = text[pos]
        if char == '"':
            return "".join(out), pos + 1
        if char == "\\":
            if pos + 1 == len(text):
                break  # a quoted-pair cut off by the end of the text
            char = text[pos + 1]
            if strict and not _pair_char(char):
                raise error(f"invalid quoted-pair {char!r}", pos + 1)
            out.append(char)
            pos += 2
            continue
        if strict and not _qdtext(char):
            raise error(f"invalid character {char!r} in quoted-string", pos)
        out.append(char)
        pos += 1
    if strict:
        raise error("unterminated quoted-string", len(text))
    return "".join(out), len(text)


def error(message: str, position: int) -> ContentDispositionError:
    """A parse error at ``position`` of the header, with the offset in its message."""
    return ContentDispositionError(f"{message} at offset {position}", position=position)
