"""Build a Content-Disposition header from its parts."""

from __future__ import annotations

import re
import unicodedata

from ._ext_value import encode_ext_value
from ._grammar import is_token

# Appendix D of RFC 6266: some agents percent-decode "%HH" in the plain filename.
_PERCENT_ESCAPE = re.compile(r"%(?=[0-9A-Fa-f]{2})")
# WHATWG HTML, multipart/form-data encoding: browsers escape LF, CR and DQUOTE. A
# backslash is escaped too, as RFC 7578 4.2 allows: left raw it would escape the closing
# quote for a quoted-string parser and swallow the next parameter.
_FORM_DATA_ESCAPES = {"\n": "%0A", "\r": "%0D", '"': "%22", "\\": "%5C"}


def build(type: str, filename: str | None = None, **params: str) -> str:
    """Build a Content-Disposition header value.

    When the ASCII ``filename="..."`` form cannot carry a value faithfully (non-ASCII,
    ``\\``, ``"`` or a ``%HH`` sequence, all avoided by RFC 6266 Appendix D) a transliterated
    fallback is written first and the exact value follows as ``filename*``. For
    ``form-data`` no ``*`` parameter is written (RFC 7578 4.2): values stay UTF-8 text and
    CR, LF, ``"`` and ``\\`` are percent-escaped, as browsers do for the first three.
    Keyword names use ``-`` for ``_``. Raises ``ValueError`` for a type or name that is not
    a token, a name given twice (names are case-insensitive), or a value with control
    characters other than tab (CR and LF are escaped for ``form-data``).
    """
    if not isinstance(type, str):
        raise TypeError(f"type must be a str, not {type.__class__.__name__}")
    if not is_token(type.strip()):
        raise ValueError(f"disposition type must be a token: {type!r}")
    disposition_type = type.strip().lower()
    form_data = disposition_type == "form-data"
    items = [] if filename is None else [("filename", filename)]
    items.extend((name.replace("_", "-"), value) for name, value in params.items())
    parts = [disposition_type]
    seen: set[str] = set()
    for raw_name, value in items:
        if not is_token(raw_name) or raw_name.endswith("*"):
            raise ValueError(f"parameter name must be a token without '*': {raw_name!r}")
        name = raw_name.lower()
        if name in seen:
            raise ValueError(f"parameter {name!r} is given more than once")
        seen.add(name)
        if not isinstance(value, str):
            raise TypeError(f"parameter {name!r} must be a str, not {value.__class__.__name__}")
        _check_controls(name, value, allow_newlines=form_data)
        parts.extend(_render_form_data(name, value) if form_data else _render(name, value))
    return "; ".join(parts)


def _check_controls(name: str, value: str, *, allow_newlines: bool) -> None:
    allowed = "\t\r\n" if allow_newlines else "\t"
    for char in value:
        if char not in allowed and unicodedata.category(char) in ("Cc", "Cs"):
            raise ValueError(f"parameter {name!r} contains a control character: {char!r}")


def _render(name: str, value: str) -> list[str]:
    fallback = ascii_fallback(value)
    if fallback == value:
        return [f'{name}="{value}"']
    return [f'{name}="{fallback}"', f"{name}*={encode_ext_value(value)}"]


def _render_form_data(name: str, value: str) -> list[str]:
    escaped = "".join(_FORM_DATA_ESCAPES.get(char, char) for char in value)
    return [f'{name}="{escaped}"']


def ascii_fallback(value: str) -> str:
    """An ASCII stand-in safe in a quoted-string without escapes (RFC 6266 Appendix D)."""
    decomposed = unicodedata.normalize("NFKD", value)
    letters = "".join(char for char in decomposed if not unicodedata.combining(char))
    text = "".join(char if char.isascii() and char not in '\\"' else "_" for char in letters)
    return _PERCENT_ESCAPE.sub("_", text)
