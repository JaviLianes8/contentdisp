"""Turn an advisory file name into one that is safe to create inside a folder."""

from __future__ import annotations

import re
import unicodedata

# Characters Windows refuses in names; ":" also opens NTFS alternate data streams.
_RESERVED = re.compile(r'[<>:"|?*]')
# Bidirectional controls: "evil" + U+202E + "txt.exe" displays as "evilexe.txt".
_BIDI = re.compile(r"[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]")
_DEVICE = re.compile(r"(con|prn|aux|nul|conin\$|conout\$|(com|lpt)[0-9\u00b9\u00b2\u00b3])", re.I)
_LEADING = " .~-"
_TRAILING = " ."


def safe_filename(name: str | None, *, default: str = "download", max_bytes: int = 255) -> str:
    """Reduce ``name`` to a single, harmless file name, as RFC 6266 section 4.3 asks.

    The name is NFKC-normalised (so full-width slashes become real ones), cut to its last
    ``/`` or ``\\`` segment, and stripped of control, format-direction and Windows-reserved
    characters (removed or replaced by ``_``). Leading dots, tildes, hyphens and spaces and
    trailing dots and spaces go; Windows device names such as ``CON`` or ``com1.txt`` get a
    ``_`` prefix; the result is cut to ``max_bytes`` of UTF-8, keeping a short extension.
    ``default`` is returned when nothing usable is left (``None``, ``..``, ``/``).
    """
    if name is None:
        return default
    text = unicodedata.normalize("NFKC", name)
    text = re.split(r"[/\\]", text)[-1]
    text = _BIDI.sub("", text)
    text = "".join(
        " " if char.isspace() else char
        for char in text
        if unicodedata.category(char) not in ("Cc", "Cs") or char.isspace()
    )
    text = _RESERVED.sub("_", text)
    text = text.lstrip(_LEADING).rstrip(_TRAILING)
    text = _truncate(text, max_bytes)
    if _DEVICE.fullmatch(text.split(".", 1)[0].rstrip(" ")):
        text = "_" + _truncate(text, max_bytes - 1)
    return text or default


def _truncate(text: str, max_bytes: int) -> str:
    if max_bytes < 1:
        raise ValueError("max_bytes must be at least 1")
    if len(text.encode("utf-8")) <= max_bytes:
        return text
    stem, dot, extension = text.rpartition(".")
    suffix = dot + extension
    if not stem or len(suffix.encode("utf-8")) > min(16, max_bytes // 2):
        stem, suffix = text, ""
    budget = max_bytes - len(suffix.encode("utf-8"))
    cut = stem.encode("utf-8")[:budget].decode("utf-8", errors="ignore")
    return (cut.rstrip(_TRAILING) + suffix).rstrip(_TRAILING)
