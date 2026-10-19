"""Build a Content-Disposition header from its parts."""

from __future__ import annotations

import re
import unicodedata

from ._errors import ContentDispositionError, show, type_name
from ._ext_value import encode_ext_value
from ._grammar import is_ext_name, is_token
from ._model import ContentDisposition
from ._unicode import normalize

# Appendix D of RFC 6266: some agents percent-decode "%HH" in the plain filename.
_PERCENT_ESCAPE = re.compile(r"%(?=[0-9A-Fa-f]{2})")
# WHATWG HTML, multipart/form-data encoding: browsers escape LF, CR and DQUOTE. A
# backslash is escaped too, as RFC 7578 4.2 allows: left raw it would escape the closing
# quote for a quoted-string parser and swallow the next parameter.
_FORM_DATA_ESCAPES = {"\n": "%0A", "\r": "%0D", '"': "%22", "\\": "%5C"}


def build(type: str | ContentDisposition, /, filename: str | None = None, **params: str) -> str:
    """Build a Content-Disposition header value.

    The type is lower-cased (surrounding whitespace removed) and every value is written
    as a quoted-string, in the order given, ``filename`` first. Keyword names use ``-``
    for ``_`` and are lower-cased. Given a ``ContentDisposition`` instead of a type, its
    type and parameters are written, names as they are (lower-cased), before ``filename``
    and the keywords: ``build(parse(header))`` writes a parsed header again, unless the
    type is not a token or a value holds a control character (a C1 control is legal
    obs-text in a quoted-string), which ``build`` refuses. A name with ``_`` or one that
    is not a Python identifier can be written this way.

    When the ASCII ``filename="..."`` form cannot carry a value faithfully (non-ASCII,
    ``\\``, ``"`` or a ``%HH`` sequence, all avoided by RFC 6266 Appendix D) a
    transliterated fallback is written first and the exact value follows as ``filename*``
    in UTF-8; other parameters get the same treatment. For ``form-data`` no ``*``
    parameter is written (RFC 7578 4.2): values stay UTF-8 text and CR, LF, ``"`` and
    ``\\`` are percent-escaped, as browsers do for the first three.

    Raises ``ContentDispositionError`` for a type or name that is not a token, an extended
    name (a token followed by ``*``), a name given twice (names are case-insensitive), or
    a value with a control character other than tab (CR and LF are escaped for
    ``form-data``) or a lone surrogate; ``TypeError`` for an argument of the wrong type,
    including a parameter name that is not a ``str``.

    >>> from contentdisp import ContentDisposition, build, parse
    >>> build("attachment", "report.pdf")
    'attachment; filename="report.pdf"'
    >>> build("attachment", "€ rates.pdf")
    'attachment; filename="_ rates.pdf"; filename*=UTF-8\\'\\'%E2%82%AC%20rates.pdf'
    >>> build("form-data", "résumé.pdf", name="cv")
    'form-data; filename="résumé.pdf"; name="cv"'
    >>> build("inline", creation_date="Wed, 12 Feb 1997 16:29:51 -0500")
    'inline; creation-date="Wed, 12 Feb 1997 16:29:51 -0500"'
    >>> build(parse("Attachment; type=a; x_y=b"))
    'attachment; type="a"; x_y="b"'
    >>> build(ContentDisposition("inline", {"my_name": "x"}), "a.txt")
    'inline; my_name="x"; filename="a.txt"'
    """
    items: list[tuple[object, object]] = []
    if isinstance(type, ContentDisposition):
        items.extend(type.params.items())
        type = type.type
    if not isinstance(type, str):
        raise TypeError(f"type must be a str or ContentDisposition, not {type_name(type)}")
    # Plain copies: a str subclass could override __iter__ or strip to hide what it holds.
    type = str.__str__(type)
    if not is_token(type.strip()):
        raise ContentDispositionError(f"disposition type must be a token: {show(type)}")
    disposition_type = type.strip().lower()
    form_data = disposition_type == "form-data"
    if filename is not None:
        items.append(("filename", filename))
    items.extend((name.replace("_", "-"), value) for name, value in params.items())
    parts = [disposition_type]
    seen: set[str] = set()
    for raw_name, value in items:
        if not isinstance(raw_name, str):
            raise TypeError(f"parameter names must be str, not {type_name(raw_name)}")
        raw_name = str.__str__(raw_name)
        if not is_token(raw_name) or is_ext_name(raw_name):
            raise ContentDispositionError(
                f"parameter name must be a token, not an extended name: {show(raw_name)}"
            )
        name = raw_name.lower()
        if name in seen:
            raise ContentDispositionError(f"parameter {show(name)} is given more than once")
        seen.add(name)
        if not isinstance(value, str):
            raise TypeError(f"parameter {show(name)} must be a str, not {type_name(value)}")
        value = str.__str__(value)
        _check_controls(name, value, allow_newlines=form_data)
        parts.extend(_render_form_data(name, value) if form_data else _render(name, value))
    return "; ".join(parts)


def _check_controls(name: str, value: str, *, allow_newlines: bool) -> None:
    allowed = "\t\r\n" if allow_newlines else "\t"
    for char in value:
        category = unicodedata.category(char)
        if char not in allowed and category in ("Cc", "Cs"):
            kind = "a lone surrogate" if category == "Cs" else "a control character"
            raise ContentDispositionError(f"parameter {show(name)} contains {kind}: {char!r}")


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
    decomposed = normalize("NFKD", value)
    letters = "".join(char for char in decomposed if not unicodedata.combining(char))
    text = "".join(char if char.isascii() and char not in '\\"' else "_" for char in letters)
    return _PERCENT_ESCAPE.sub("_", text)
