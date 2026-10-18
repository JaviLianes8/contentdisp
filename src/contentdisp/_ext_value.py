"""Encode and decode RFC 8187 extended parameter values (charset'language'value-chars)."""

from __future__ import annotations

import re
from urllib.parse import quote, unquote_to_bytes

from ._errors import ContentDispositionError
from ._langtag import is_language_tag

# RFC 8187 3.2.1. Every well-formed language tag is made of letters, digits and hyphens,
# so this pattern reads it; strict parsing then checks the RFC 5646 grammar, while
# lenient parsing skips it, as recipients ignore the language.
_EXT_VALUE = re.compile(
    r"(?P<charset>[A-Za-z0-9!#$%&+\-^_`{}~]+)"
    r"'(?P<language>[A-Za-z0-9\-]*)'"
    r"(?P<chars>(?:%[0-9A-Fa-f]{2}|[A-Za-z0-9!#$&+\-.^_`|~])*)"
)
ATTR_CHAR_PUNCTUATION = "!#$&+-.^_`|~"
# ISO-8859-1 has no characters at 0x80-0x9F; the browser corpus treats them as illegal.
_LATIN1_HOLE = re.compile(rb"[\x80-\x9f]")


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
        raise ContentDispositionError("malformed extended value")
    language = match.group("language")
    if strict and language and not is_language_tag(language):
        raise ContentDispositionError("malformed language tag in extended value")
    charset = match.group("charset").lower()
    octets = unquote_to_bytes(match.group("chars"))
    if charset == "utf-8":
        try:
            return octets.decode("utf-8")
        except UnicodeDecodeError:
            raise ContentDispositionError("invalid UTF-8 in extended value") from None
    if charset == "iso-8859-1":
        if _LATIN1_HOLE.search(octets):
            raise ContentDispositionError("octet outside ISO-8859-1 in extended value")
        return octets.decode("latin-1")
    raise UnsupportedCharsetError("unsupported charset in extended value")
