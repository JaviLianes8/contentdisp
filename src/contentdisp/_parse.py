"""Parse a Content-Disposition header into a structured value."""

from __future__ import annotations

from ._errors import ContentDispositionError, show, type_name
from ._ext_value import UnsupportedCharsetError, decode_ext_value
from ._grammar import OWS, error, is_ext_name, is_token, read_quoted, read_token, skip_ows
from ._model import ContentDisposition


def parse(header: str | bytes, *, strict: bool = False) -> ContentDisposition:
    """Parse a Content-Disposition field value.

    ``bytes`` are decoded as ISO-8859-1, so obs-text survives; a multipart part header
    in UTF-8 should be decoded by the caller and passed as ``str``, whose non-ASCII
    characters count as obs-text inside a quoted-string.

    With ``strict=True`` anything outside the RFC 6266 grammar (token and quoted-string
    as RFC 9110 defines them, ext-value as RFC 8187 does, with an RFC 5646 language tag),
    a repeated parameter, or a ``name*`` value whose octets are invalid in its charset
    raises ``ContentDispositionError`` with the ``position`` of the first offending
    character (for octets invalid in their charset or a malformed language tag, the
    start of that value or tag). A ``name*`` in a charset other than UTF-8 or ISO-8859-1
    is ignored in both modes.

    The default lenient mode gives the same result on every valid header and never
    raises ``ContentDispositionError``: it skips parameters it cannot read, ignores a
    ``name*`` value that does not decode (so a plain fallback wins), keeps the first of
    repeated parameters and replaces CR, LF and NUL with a space (RFC 9110 5.5). The type
    is the text before the first ``;`` outside quotes, whatever it holds; when that text
    has the form ``name=value`` (a header without a type) it is read as a parameter too.

    >>> from contentdisp import parse
    >>> parse("attachment; filename=\\"EURO rates\\"; filename*=utf-8''%e2%82%ac%20rates")
    ContentDisposition(type='attachment', params={'filename': '€ rates'})
    >>> parse('attachment; filename="report.pdf"; filename="other.pdf"').filename
    'report.pdf'
    >>> parse('filename="report.pdf"')
    ContentDisposition(type='filename="report.pdf"', params={'filename': 'report.pdf'})
    >>> parse(b'inline; filename="caf\\xe9.txt"').filename
    'café.txt'
    """
    # Plain copies: a subclass could override decode, replace or indexing to change the result.
    if isinstance(header, bytes):
        header = bytes.decode(header, "latin-1")
    elif isinstance(header, str):
        header = str.__str__(header)
    else:
        raise TypeError(f"header must be str or bytes, not {type_name(header)}")
    if strict:
        return _parse_strict(header)
    return _parse_lenient(header)


def _parse_strict(header: str) -> ContentDisposition:
    try:
        return _read_strict(header)
    except ContentDispositionError as problem:
        # CR, LF and NUL break the grammar like any other character; when one of them is
        # the first offending character, the message names the rule it breaks.
        position = problem.position
        if position is not None and position < len(header) and header[position] in "\r\n\0":
            raise error("CR, LF and NUL are not allowed in a field value", position) from None
        raise


def _read_strict(header: str) -> ContentDisposition:
    disposition_type, pos = read_token(header, skip_ows(header, 0))
    if not disposition_type:
        raise error("missing disposition type", pos)
    pairs: list[tuple[str, str]] = []
    seen: set[str] = set()
    while True:
        pos = skip_ows(header, pos)
        if pos == len(header):
            break
        if header[pos] != ";":
            raise error("expected ';'", pos)
        start = skip_ows(header, pos + 1)
        name, pos = read_token(header, start)
        if not name:
            raise error("expected a parameter name", start)
        pos = skip_ows(header, pos)
        if pos == len(header) or header[pos] != "=":
            raise error(f"expected '=' after parameter {show(name)}", pos)
        pos = skip_ows(header, pos + 1)
        name = name.lower()
        if name in seen:
            raise error(f"parameter {show(name)} appears more than once", start)
        seen.add(name)
        if is_ext_name(name):
            value_start = pos
            while pos < len(header) and header[pos] not in OWS + ";":
                pos += 1
            try:
                pairs.append((name, decode_ext_value(header[value_start:pos], strict=True)))
            except UnsupportedCharsetError:
                continue  # well-formed, just not understood: ignored like an unknown parameter
            except ContentDispositionError as problem:
                at = value_start + (problem.position or 0)
                raise error(f"{problem} for {show(name)}", at) from None
        elif pos < len(header) and header[pos] == '"':
            value, pos = read_quoted(header, pos, strict=True)
            pairs.append((name, value))
        else:
            value, pos = read_token(header, pos)
            if not value:
                raise error(f"expected a token or quoted-string for {show(name)}", pos)
            pairs.append((name, value))
    return _resolve(disposition_type.lower(), pairs)


def _parse_lenient(header: str) -> ContentDisposition:
    for char in "\r\n\0":
        header = header.replace(char, " ")
    segments = _split_segments(header)
    first = segments[0].strip(OWS)
    # A header without a type ("filename=a.txt") still names a file, as browsers read it;
    # a valid type is a token, which never holds "=", so valid headers are unaffected.
    pairs: list[tuple[str, str]] = []
    seen: set[str] = set()
    for segment in segments if "=" in first else segments[1:]:
        raw_name, equals, value = segment.partition("=")
        raw_name = raw_name.strip(OWS)
        name = raw_name.lower()
        if not equals or not is_token(raw_name) or name in seen:
            continue
        value = value.strip(OWS)
        if is_ext_name(name):
            try:
                pairs.append((name, decode_ext_value(value, strict=False)))
            except ContentDispositionError:
                continue
        elif value.startswith('"'):
            pairs.append((name, read_quoted(value, 0, strict=False)[0]))
        else:
            pairs.append((name, value))
        seen.add(name)
    return _resolve(first.lower(), pairs)


def _resolve(disposition_type: str, pairs: list[tuple[str, str]]) -> ContentDisposition:
    # RFC 6266 4.3 and RFC 8187 4.2: the extended form takes precedence over the plain one.
    params = {name: value for name, value in pairs if not is_ext_name(name)}
    params.update((name[:-1], value) for name, value in pairs if is_ext_name(name))
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
