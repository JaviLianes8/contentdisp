"""Turn an advisory file name into one that is safe to create inside a folder."""

from __future__ import annotations

import re
import unicodedata

# Characters Windows refuses in names; ":" also opens NTFS alternate data streams.
_RESERVED = re.compile(r'[<>:"|?*]')
# Joiners shape emoji and some scripts; every other format character (bidi controls such
# as U+202E, which shows "evil" + U+202E + "txt.exe" as "evilexe.txt", zero-width spaces,
# soft hyphens, byte order marks) only hides what the name really is.
_JOINERS = "\u200c\u200d"
_DEVICE = re.compile(r"(con|prn|aux|nul|conin\$|conout\$|(com|lpt)[0-9\u00b9\u00b2\u00b3])", re.I)
_LEADING = " .~-"
_TRAILING = " ."


def safe_filename(name: str | None, *, default: str = "download", max_bytes: int = 255) -> str:
    """Reduce ``name`` to a single, harmless file name, as RFC 6266 section 4.3 asks.

    The name is NFKC-normalised (so full-width slashes become real ones), cut to its last
    ``/`` or ``\\`` segment, and stripped of control and invisible format characters
    (bidi controls, zero-width spaces). Windows-reserved characters become ``_``. Leading
    dots, tildes, hyphens, spaces and combining marks and trailing dots and spaces go;
    Windows device names such as ``CON`` or ``com1.txt`` get a ``_`` prefix; the result is
    cut to ``max_bytes`` of UTF-8, keeping a short extension. ``default`` is returned, as
    given, when nothing usable is left (``None``, ``..``, ``/``).
    """
    if name is None:
        return default
    text = unicodedata.normalize("NFKC", name)
    text = re.split(r"[/\\]", text)[-1]
    text = _RESERVED.sub("_", "".join(_clean(char) for char in text))
    text = _trim(_truncate(_trim(text), max_bytes))
    if _DEVICE.fullmatch(text.split(".", 1)[0].rstrip(" ")):
        text = "_" + _truncate(text, max_bytes - 1)
    return text or default


def _clean(char: str) -> str:
    if char.isspace():
        return " "
    category = unicodedata.category(char)
    if category in ("Cc", "Cs") or (category == "Cf" and char not in _JOINERS):
        return ""
    return char


def _trim(text: str) -> str:
    # Combining marks and joiners in front of a dot would display as a hidden file name.
    start = 0
    while start < len(text) and (
        text[start] in _LEADING + _JOINERS or unicodedata.category(text[start]).startswith("M")
    ):
        start += 1
    return text[start:].rstrip(_TRAILING)


def _truncate(text: str, max_bytes: int) -> str:
    if max_bytes < 1:
        raise ValueError("max_bytes must be at least 1")
    if len(text.encode("utf-8")) <= max_bytes:
        return text
    stem, dot, extension = text.rpartition(".")
    suffix = dot + extension
    if not stem or len(suffix.encode("utf-8")) > min(16, max_bytes // 2):
        stem, suffix = text, ""
    cut = _cut(stem, max_bytes - len(suffix.encode("utf-8"))).rstrip(_TRAILING)
    if not cut:
        # Never let the extension alone remain: it would start with a dot.
        return _cut(text, max_bytes)
    return cut + suffix


def _cut(text: str, budget: int) -> str:
    return text.encode("utf-8")[:budget].decode("utf-8", errors="ignore")
