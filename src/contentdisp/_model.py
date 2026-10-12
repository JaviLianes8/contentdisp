"""The structured result of parsing a Content-Disposition header."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContentDisposition:
    """A parsed Content-Disposition header.

    ``type`` is lower-cased. ``params`` maps lower-cased parameter names to their values;
    a decoded ``name*`` value is stored under ``name`` and overrides the plain one.
    """

    type: str
    params: dict[str, str] = field(default_factory=dict)

    @property
    def filename(self) -> str | None:
        """The advisory file name, preferring ``filename*``. Pass it to ``safe_filename``."""
        return self.params.get("filename")

    @property
    def is_attachment(self) -> bool:
        """True unless the type is ``inline``: unknown types count as attachment (RFC 6266 4.2)."""
        return self.type != "inline"
