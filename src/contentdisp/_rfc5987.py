"""Encode and decode RFC 5987 extended header values (charset'lang'pct-encoded)."""

from __future__ import annotations

from urllib.parse import quote, unquote_to_bytes


def encode_ext_value(value: str, charset: str = "UTF-8") -> str:
    """Return ``value`` as a ``charset'lang'pct-encoded`` extended value."""
    encoded = quote(value, safe="", encoding=charset)
    return f"{charset}''{encoded}"


def decode_ext_value(raw: str) -> str:
    """Decode a ``charset'lang'pct-encoded`` value, returning the input if it is malformed."""
    parts = raw.split("'", 2)
    if len(parts) != 3:
        return raw
    charset, _language, encoded = parts
    try:
        return unquote_to_bytes(encoded).decode(charset or "utf-8")
    except (LookupError, UnicodeDecodeError):
        return raw
