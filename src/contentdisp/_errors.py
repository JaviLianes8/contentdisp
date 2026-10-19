"""The error raised for an invalid header, parameter or argument value."""

from __future__ import annotations

# Messages quote at most this many characters of any input, so a huge or sensitive value
# never ends up whole in a log line.
LIMIT = 40


class ContentDispositionError(ValueError):
    """Raised when a header, a parameter or an argument value is invalid.

    It is a ``ValueError``, so code written for ``except ValueError`` keeps working.
    ``position`` is the index in the header of the first character that breaks the
    grammar when the error comes from ``parse(header, strict=True)`` (``parse`` names two
    errors that point at the start of a value or of its language tag instead; the GUIDE
    lists them), and ``None`` for
    errors that do not come from reading a header (``build``, ``safe_filename``).
    Messages quote at most 40 characters of any input.

    >>> from contentdisp import ContentDispositionError, parse
    >>> try:
    ...     parse("attachment; filename=a b", strict=True)
    ... except ContentDispositionError as error:
    ...     print(error.position, isinstance(error, ValueError))
    23 True
    """

    def __init__(self, message: str, *, position: int | None = None) -> None:
        super().__init__(message)
        # Kept in the instance dict, which the default exception pickling restores.
        self.position = position


def show(value: object) -> str:
    """``repr(value)`` cut to the message limit; never raises."""
    try:
        text = repr(value)
    except Exception:
        return f"<{type_name(value)}>"
    return text if len(text) <= LIMIT else text[: LIMIT - 3] + "..."


# The descriptor of type itself: a metaclass cannot override it, so reading the name of a
# class never runs code that belongs to the value.
_NAME = type.__dict__["__name__"]


def type_name(value: object) -> str:
    """The class name of ``value``, cut to the message limit; never raises."""
    name = str.__str__(_NAME.__get__(type(value)))
    return name if len(name) <= LIMIT else name[: LIMIT - 3] + "..."
