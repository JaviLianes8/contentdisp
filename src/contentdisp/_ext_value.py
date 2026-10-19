"""Encode and decode RFC 8187 extended parameter values (charset'language'value-chars)."""

from __future__ import annotations

import re
from urllib.parse import quote, unquote_to_bytes

from ._errors import ContentDispositionError
from ._langtag import is_language_tag

# RFC 8187 3.2.1. Every well-formed language tag is made of letters, digits and hyphens,
# so this pattern reads it; strict parsing then checks the RFC 5646 grammar, while
# lenient parsing skips it, as recipients ignore the language.
_CHARSET = r"[A-Za-z0-9!#$%&+\-^_`{}~]+"
_LANGUAGE = r"[A-Za-z0-9\-]*"
_CHARS = r"(?:%[0-9A-Fa-f]{2}|[A-Za-z0-9!#$&+\-.^_`|~])*"
_EXT_VALUE = re.compile(rf"(?P<charset>{_CHARSET})'(?P<language>{_LANGUAGE})'(?P<chars>{_CHARS})")
# The three parts in order, each with the delimiter that must follow it.
_PARTS = [(re.compile(_CHARSET), "'"), (re.compile(_LANGUAGE), "'"), (re.compile(_CHARS), "")]
_HEX = "0123456789ABCDEFabcdef"
ATTR_CHAR_PUNCTUATION = "!#$&+-.^_`|~"
# ISO/IEC 8859-1 gives graphic characters only to 0x20-0x7E and 0xA0-0xFF; the controls
# around them come from other standards, and the browser corpus treats 0x82 as illegal.
_LATIN1_CONTROL = re.compile(rb"[\x00-\x1f\x7f-\x9f]")


class UnsupportedCharsetError(ContentDispositionError):
    """A well-formed extended value in a charset this library does not decode."""


def encode_ext_value(value: str) -> str:
    """Return ``value`` as a ``UTF-8''pct-encoded`` extended value (producers MUST use UTF-8).

    ``value`` holds no lone surrogate: ``build`` refuses those before encoding.
    """
    return "UTF-8''" + quote(value, safe=ATTR_CHAR_PUNCTUATION, encoding="utf-8")


def decode_ext_value(raw: str, *, strict: bool) -> str:
    """Decode an extended value, raising ``ContentDispositionError`` when it is invalid.

    Only UTF-8 (required by RFC 8187) and ISO-8859-1 (encouraged for compatibility) are
    understood; any other charset raises ``UnsupportedCharsetError``. With ``strict`` the
    language part must be a well-formed RFC 5646 tag. Messages never quote ``raw``.
    """
    match = _EXT_VALUE.fullmatch(raw)
    if match is None:
        raise ContentDispositionError("malformed extended value", position=_first_bad(raw))
    language = match.group("language")
    if strict and language and not is_language_tag(language):
        start = match.start("language")
        raise ContentDispositionError("malformed language tag in extended value", position=start)
    charset = match.group("charset").lower()
    octets = unquote_to_bytes(match.group("chars"))
    if charset == "utf-8":
        try:
            return octets.decode("utf-8")
        except UnicodeDecodeError:
            raise ContentDispositionError("invalid UTF-8 in extended value") from None
    if charset == "iso-8859-1":
        if _LATIN1_CONTROL.search(octets):
            raise ContentDispositionError("octet outside ISO-8859-1 in extended value")
        return octets.decode("latin-1")
    raise UnsupportedCharsetError("unsupported charset in extended value")


def _first_bad(raw: str) -> int:
    """The index in ``raw`` of the first character the grammar cannot take (or its length)."""
    pos = 0
    for part, delimiter in _PARTS:
        match = part.match(raw, pos)
        end = match.end() if match else pos
        if delimiter and match and raw.startswith(delimiter, end):
            pos = end + 1
            continue
        if not delimiter and raw.startswith("%", end):
            # A broken pct-encoding: the first of the two places that is not a hex digit.
            end += 2 if raw[end + 1 : end + 2] and raw[end + 1] in _HEX else 1
        return end
    return len(raw)
