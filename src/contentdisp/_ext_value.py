"""Encode and decode RFC 8187 extended parameter values (charset'language'value-chars)."""

from __future__ import annotations

import re
from urllib.parse import quote, unquote_to_bytes

from ._errors import ContentDispositionError
from ._langtag import is_language_tag, tag_prefix_length

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
# The controls a value may not hold, whatever its charset: those build refuses (all but
# HTAB, which a quoted-string takes too). ISO/IEC 8859-1 has no graphic character there,
# and UTF-8 carrying them would make a name valid or not by its charset label alone.
_CONTROL = re.compile("[\x00-\x08\x0a-\x1f\x7f-\x9f]")


_BAD_TAG = "malformed language tag in extended value"


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
    language part must be a well-formed RFC 5646 tag, reported at its start even when a
    later character breaks the grammar too (when the part is not closed by its quote, at
    its first character that no tag can continue with). In either charset the decoded text may hold
    no control other than HTAB. Messages never quote ``raw``.
    """
    match = _EXT_VALUE.fullmatch(raw)
    if match is None:
        position = _first_bad(raw)
        if strict:
            _check_language(raw, position)
        raise ContentDispositionError("malformed extended value", position=position)
    language = match.group("language")
    if strict and language and not is_language_tag(language):
        raise ContentDispositionError(_BAD_TAG, position=match.start("language"))
    charset = match.group("charset").lower()
    octets = unquote_to_bytes(match.group("chars"))
    if charset == "utf-8":
        try:
            text = octets.decode("utf-8")
        except UnicodeDecodeError:
            raise ContentDispositionError("invalid UTF-8 in extended value") from None
    elif charset == "iso-8859-1":
        text = octets.decode("latin-1")
    else:
        raise UnsupportedCharsetError("unsupported charset in extended value")
    if _CONTROL.search(text):
        raise ContentDispositionError("control character in extended value")
    return text


def _check_language(raw: str, position: int) -> None:
    """Raise the tag error for a language part that breaks RFC 5646 before ``position``.

    A part closed by its quote that is not a tag is reported at its start; a part the
    value grammar cut short, at its first character no tag can continue with.
    """
    charset = _PARTS[0][0].match(raw)
    if charset is None or not raw.startswith("'", charset.end()):
        return
    start = charset.end() + 1
    language = _PARTS[1][0].match(raw, start)
    if language is None or not language.group():
        return
    text = language.group()
    if raw.startswith("'", language.end()):
        bad = None if is_language_tag(text) else start
    else:
        length = tag_prefix_length(text)
        bad = start + length if length < len(text) else None
    if bad is not None and bad < position:
        raise ContentDispositionError(_BAD_TAG, position=bad)


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
