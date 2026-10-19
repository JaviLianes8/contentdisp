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
    later character breaks the grammar too. In either charset the decoded text may hold
    no control other than HTAB. Messages never quote ``raw``.
    """
    match = _EXT_VALUE.fullmatch(raw)
    if match is None:
        position = _first_bad(raw)
        tag = _delimited_language(raw) if strict else None
        if tag is not None and tag[0] < position and not is_language_tag(tag[1]):
            raise ContentDispositionError(_BAD_TAG, position=tag[0])
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


def _delimited_language(raw: str) -> tuple[int, str] | None:
    """The start and text of a non-empty language part closed by its quote, if there is one."""
    charset = _PARTS[0][0].match(raw)
    if charset is None or not raw.startswith("'", charset.end()):
        return None
    start = charset.end() + 1
    language = _PARTS[1][0].match(raw, start)
    if language is None or not language.group() or not raw.startswith("'", language.end()):
        return None
    return start, language.group()


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
