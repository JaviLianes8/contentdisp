"""The structured result of parsing a Content-Disposition header."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContentDisposition:
    """A parsed Content-Disposition header.

    ``params`` holds the resolved parameters; an RFC 5987 ``filename*`` value
    overrides a plain ``filename`` so the decoded name is the one kept.
    """

    type: str
    params: dict[str, str] = field(default_factory=dict)

    @property
    def filename(self) -> str | None:
        """The file name, preferring the decoded ``filename*`` form when present."""
        return self.params.get("filename")
