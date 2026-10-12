"""Encode and decode RFC 8187 extended parameter values (charset'language'value-chars)."""

from __future__ import annotations

import re
from urllib.parse import quote, unquote_to_bytes

# RFC 8187 3.2.1. The language part is simplified to letters, digits and hyphens instead
# of the full RFC 5646 Language-Tag grammar: recipients ignore it, it only has to be skipped.
_EXT_VALUE = re.compile(
    r"(?P<charset>[A-Za-z0-9!#$%&+\-^_`{}~]+)"
    r"'(?P<language>[A-Za-z0-9\-]*)'"
    r"(?P<chars>(?:%[0-9A-Fa-f]{2}|[A-Za-z0-9!#$&+\-.^_`|~])*)"
)
ATTR_CHAR_PUNCTUATION = "!#$&+-.^_`|~"
# ISO-8859-1 has no characters at 0x80-0x9F; the browser corpus treats them as illegal.
_LATIN1_HOLE = re.compile(rb"[\x80-\x9f]")


class UnsupportedCharsetError(ValueError):
    """A well-formed extended value in a charset this library does not decode."""


def encode_ext_value(value: str) -> str:
    """Return ``value`` as a ``UTF-8''pct-encoded`` extended value (producers MUST use UTF-8)."""
    try:
        encoded = quote(value, safe=ATTR_CHAR_PUNCTUATION, encoding="utf-8", errors="strict")
    except UnicodeEncodeError as error:
        raise ValueError(f"value cannot be encoded as UTF-8: {value!r}") from error
    return f"UTF-8''{encoded}"


def decode_ext_value(raw: str) -> str:
    """Decode an extended value, raising ``ValueError`` when it is malformed or undecodable.

    Only UTF-8 (required by RFC 8187) and ISO-8859-1 (encouraged for compatibility) are
    understood; any other charset raises ``UnsupportedCharsetError``.
    """
    match = _EXT_VALUE.fullmatch(raw)
    if match is None:
        raise ValueError(f"malformed extended value: {raw!r}")
    charset = match.group("charset").lower()
    octets = unquote_to_bytes(match.group("chars"))
    if charset == "utf-8":
        try:
            return octets.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError(f"invalid UTF-8 in extended value: {raw!r}") from error
    if charset == "iso-8859-1":
        if _LATIN1_HOLE.search(octets):
            raise ValueError(f"octet outside ISO-8859-1 in extended value: {raw!r}")
        return octets.decode("latin-1")
    raise UnsupportedCharsetError(
        f"unsupported charset {match.group('charset')!r} in extended value"
    )
