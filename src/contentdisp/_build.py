"""Build a Content-Disposition header from its parts."""

from __future__ import annotations

from ._rfc5987 import encode_ext_value


def build(type: str, filename: str | None = None, **params: str) -> str:
    """Build a Content-Disposition header value.

    A non-ASCII ``filename`` (or parameter) emits both the plain form, with an
    ASCII fallback, and a correct RFC 5987 ``filename*`` extended form.
    """
    parts = [type.strip().lower()]
    if filename is not None:
        parts.extend(_render("filename", filename))
    for name, value in params.items():
        parts.extend(_render(name.replace("_", "-").lower(), value))
    return "; ".join(parts)


def _render(name: str, value: str) -> list[str]:
    if value.isascii():
        return [f"{name}={_quote(value)}"]
    return [
        f"{name}={_quote(_ascii_fallback(value))}",
        f"{name}*={encode_ext_value(value)}",
    ]


def _quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _ascii_fallback(value: str) -> str:
    return "".join(char if ord(char) < 128 else "_" for char in value)
