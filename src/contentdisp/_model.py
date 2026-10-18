"""The structured result of parsing a Content-Disposition header."""

from __future__ import annotations

from dataclasses import dataclass, field

from ._errors import show, type_name
from ._grammar import is_token


@dataclass(frozen=True)
class ContentDisposition:
    """A parsed Content-Disposition header, as ``parse`` returns it.

    ``type`` is the disposition type and ``params`` maps parameter names to their values;
    ``parse`` lower-cases both and stores a decoded ``name*`` value under ``name``, where
    it overrides the plain one. The value is frozen (its fields cannot be reassigned), but
    ``params`` is the plain ``dict`` it was given, so the value is not hashable. A value
    built by hand is stored as given; its fields must be ``str`` (``TypeError``).

    >>> from contentdisp import ContentDisposition, parse
    >>> parse('Attachment; FileName="report.pdf"; size=1024')
    ContentDisposition(type='attachment', params={'filename': 'report.pdf', 'size': '1024'})
    >>> ContentDisposition("inline").is_attachment
    False
    """

    type: str
    params: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.type, str):
            raise TypeError(f"type must be a str, not {type_name(self.type)}")
        if not isinstance(self.params, dict):
            raise TypeError(f"params must be a dict, not {type_name(self.params)}")
        for name, value in self.params.items():
            if not isinstance(name, str) or not isinstance(value, str):
                raise TypeError(f"params must map str to str, not {show(name)}: {show(value)}")

    @property
    def filename(self) -> str | None:
        """The advisory file name, preferring ``filename*``, or ``None``.

        It comes from the server: pass it to ``safe_filename`` before using it on disk.

        >>> from contentdisp import parse
        >>> parse("attachment; filename=plain.txt; filename*=UTF-8''%E2%82%AC.txt").filename
        '€.txt'
        >>> print(parse("inline").filename)
        None
        """
        return self.params.get("filename")

    @property
    def is_attachment(self) -> bool:
        """Whether the type asks to save the content rather than display it.

        True for ``attachment`` and any other token but ``inline`` (case-insensitive):
        RFC 6266 section 4.2 treats unknown types as ``attachment``. False for ``inline``
        and for a type that is not a token, which only lenient parsing produces: such a
        header is invalid, and RFC 6266 section 3 says invalid headers are ignored.

        >>> from contentdisp import parse
        >>> [parse(header).is_attachment for header in ("attachment", "x-zip", "INLINE")]
        [True, True, False]
        >>> parse('"attachment"; filename=a.txt').is_attachment
        False
        """
        return is_token(self.type) and self.type.lower() != "inline"
