"""Parse a Content-Disposition header into a structured value."""

from __future__ import annotations

from ._model import ContentDisposition
from ._rfc5987 import decode_ext_value


def parse(header: str) -> ContentDisposition:
    """Parse ``header`` into a :class:`ContentDisposition`, tolerating malformed parameters."""
    segments = _split_segments(header)
    disposition_type = segments[0].strip().lower()
    plain: dict[str, str] = {}
    extended: dict[str, str] = {}
    for segment in segments[1:]:
        if "=" not in segment:
            continue
        name, _, value = segment.partition("=")
        name = name.strip().lower()
        value = value.strip()
        if not name:
            continue
        if name.endswith("*"):
            extended[name[:-1]] = decode_ext_value(value)
        else:
            plain[name] = _unquote(value)
    return ContentDisposition(type=disposition_type, params={**plain, **extended})


def _split_segments(header: str) -> list[str]:
    """Split on semicolons that sit outside a quoted-string."""
    segments: list[str] = []
    buffer: list[str] = []
    in_quotes = False
    escaped = False
    for char in header:
        if escaped:
            buffer.append(char)
            escaped = False
        elif char == "\\" and in_quotes:
            buffer.append(char)
            escaped = True
        elif char == '"':
            in_quotes = not in_quotes
            buffer.append(char)
        elif char == ";" and not in_quotes:
            segments.append("".join(buffer))
            buffer = []
        else:
            buffer.append(char)
    segments.append("".join(buffer))
    return segments


def _unquote(value: str) -> str:
    """Strip surrounding quotes and unescape a quoted-string value."""
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return _unescape(value[1:-1])
    return value


def _unescape(text: str) -> str:
    out: list[str] = []
    escaped = False
    for char in text:
        if escaped:
            out.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        else:
            out.append(char)
    if escaped:
        out.append("\\")
    return "".join(out)
