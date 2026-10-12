"""Parse a Content-Disposition header into a structured value."""

from __future__ import annotations

from ._ext_value import UnsupportedCharsetError, decode_ext_value
from ._grammar import OWS, is_token, read_quoted, read_token, skip_ows
from ._model import ContentDisposition


def parse(header: str | bytes, *, strict: bool = False) -> ContentDisposition:
    """Parse a Content-Disposition field value.

    ``bytes`` are decoded as ISO-8859-1, so obs-text survives. With ``strict=True`` a
    departure from the RFC 6266 grammar, a repeated parameter, or a ``name*`` value that
    is malformed or holds octets invalid in its charset raises ``ValueError``. A ``name*``
    in a charset other than UTF-8 or ISO-8859-1 is ignored in both modes. The default
    lenient mode gives the same result on every valid header and never raises
    ``ValueError``: it skips parameters it cannot read, ignores a ``name*`` value that
    does not decode (so a plain fallback wins), keeps the first of repeated parameters and
    replaces CR, LF and NUL with a space (RFC 9110 5.5).
    """
    if isinstance(header, bytes):
        header = header.decode("latin-1")
    elif not isinstance(header, str):
        raise TypeError(f"header must be str or bytes, not {type(header).__name__}")
    if strict:
        return _parse_strict(header)
    return _parse_lenient(header)


def _parse_strict(header: str) -> ContentDisposition:
    if any(char in header for char in "\r\n\0"):
        raise ValueError("CR, LF and NUL are not allowed in a field value")
    text = header.strip(OWS)
    disposition_type, pos = read_token(text, 0)
    if not disposition_type:
        raise ValueError("missing disposition type")
    pairs: list[tuple[str, str]] = []
    seen: set[str] = set()
    while True:
        pos = skip_ows(text, pos)
        if pos == len(text):
            break
        if text[pos] != ";":
            raise ValueError(f"expected ';' at offset {pos}")
        name, pos = read_token(text, skip_ows(text, pos + 1))
        if not name:
            raise ValueError(f"expected a parameter name at offset {pos}")
        pos = skip_ows(text, pos)
        if pos == len(text) or text[pos] != "=":
            raise ValueError(f"expected '=' after parameter {name!r}")
        pos = skip_ows(text, pos + 1)
        name = name.lower()
        if name in seen:
            raise ValueError(f"parameter {name!r} appears more than once")
        seen.add(name)
        if name.endswith("*"):
            end = pos
            while end < len(text) and text[end] not in OWS + ";":
                end += 1
            raw, pos = text[pos:end], end
            try:
                pairs.append((name, decode_ext_value(raw)))
            except UnsupportedCharsetError:
                continue  # well-formed, just not understood: ignored like an unknown parameter
        elif pos < len(text) and text[pos] == '"':
            value, pos = read_quoted(text, pos, strict=True)
            pairs.append((name, value))
        else:
            value, pos = read_token(text, pos)
            if not value:
                raise ValueError(f"expected a token or quoted-string for {name!r}")
            pairs.append((name, value))
    return _resolve(disposition_type.lower(), pairs)


def _parse_lenient(header: str) -> ContentDisposition:
    for char in "\r\n\0":
        header = header.replace(char, " ")
    segments = _split_segments(header)
    pairs: list[tuple[str, str]] = []
    seen: set[str] = set()
    for segment in segments[1:]:
        name, equals, value = segment.partition("=")
        name = name.strip(OWS).lower()
        if not equals or not is_token(name) or name in seen:
            continue
        value = value.strip(OWS)
        if name.endswith("*"):
            try:
                pairs.append((name, decode_ext_value(value)))
            except ValueError:
                continue
        elif value.startswith('"'):
            pairs.append((name, read_quoted(value, 0, strict=False)[0]))
        else:
            pairs.append((name, value))
        seen.add(name)
    return _resolve(segments[0].strip(OWS).lower(), pairs)


def _resolve(disposition_type: str, pairs: list[tuple[str, str]]) -> ContentDisposition:
    # RFC 6266 4.3 and RFC 8187 4.2: the extended form takes precedence over the plain one.
    params = {name: value for name, value in pairs if not name.endswith("*")}
    params.update((name[:-1], value) for name, value in pairs if name.endswith("*"))
    return ContentDisposition(type=disposition_type, params=params)


def _split_segments(header: str) -> list[str]:
    """Split on semicolons outside a quoted-string; an unterminated quote runs to the end."""
    segments: list[str] = []
    start = 0
    in_quotes = False
    escaped = False
    for index, char in enumerate(header):
        if escaped:
            escaped = False
        elif in_quotes and char == "\\":
            escaped = True
        elif char == '"':
            in_quotes = not in_quotes
        elif char == ";" and not in_quotes:
            segments.append(header[start:index])
            start = index + 1
    segments.append(header[start:])
    return segments
