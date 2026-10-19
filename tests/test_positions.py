"""Strict errors: the type, the message and the position of the first offending character."""

from __future__ import annotations

import pytest

from contentdisp import ContentDispositionError, parse

# (header, start of the message, position in the header), positions counted by hand.
CASES = [
    ("attachment; filename=a\r\n", "CR, LF and NUL are not allowed", 22),
    ("\nattachment", "CR, LF and NUL are not allowed", 0),
    ('attachment; filename="a\0"', "CR, LF and NUL are not allowed", 23),
    ("", "missing disposition type", 0),
    ("   ", "missing disposition type", 3),
    ('"attachment"', "missing disposition type", 0),
    (" \t;x=y", "missing disposition type", 2),
    ("attachment;", "expected a parameter name", 11),
    ("attachment; ; filename=a", "expected a parameter name", 12),
    ("attachment filename=a", "expected ';'", 11),
    ("  attachment filename=a", "expected ';'", 13),
    ("attachment; filename", "expected '=' after parameter 'filename'", 20),
    ("attachment; filename x", "expected '=' after parameter 'filename'", 21),
    ("attachment; filename=", "expected a token or quoted-string for 'filename'", 21),
    ("attachment; filename=;", "expected a token or quoted-string for 'filename'", 21),
    ("attachment; filename=a b", "expected ';'", 23),
    ('attachment; filename="a', "unterminated quoted-string", 23),
    ('attachment; filename="abc\\', "unterminated quoted-string", 26),
    ('attachment; filename="a"b', "expected ';'", 24),
    ("attachment; filename=a; FILENAME=b", "parameter 'filename' appears more than once", 24),
    ("attachment; filename*=\"UTF-8''a\"", "malformed extended value for 'filename*'", 22),
    ("attachment; filename*=UTF-8''%E4", "invalid UTF-8 in extended value", 22),
    ("attachment; filename*=ISO-8859-1''%82", "control character in extended value", 22),
    ("attachment; filename*=UTF-8'1'a", "malformed language tag", 28),
    ("attachment; filename*= UTF-8'en_US'a", "malformed extended value", 31),
    ('attachment; filename="a\x01"', "invalid character '\\x01' in quoted-string", 23),
    ('attachment; filename="a\\\x01b"', "invalid quoted-pair '\\x01'", 24),
    ('attachment; filename="a\x7f"', "invalid character '\\x7f' in quoted-string", 23),
]


@pytest.mark.parametrize(("header", "message", "position"), CASES)
def test_strict_errors_point_at_the_first_offending_character(
    header: str, message: str, position: int
) -> None:
    with pytest.raises(ContentDispositionError) as caught:
        parse(header, strict=True)
    assert caught.value.position == position
    assert str(caught.value).startswith(message), str(caught.value)
    assert str(caught.value).endswith(f" at offset {position}")
    assert isinstance(caught.value, ValueError)


@pytest.mark.parametrize(("header", "message", "position"), CASES)
def test_the_same_headers_never_raise_in_lenient_mode(
    header: str, message: str, position: int
) -> None:
    parse(header)
    parse(header.encode("utf-8"))


def test_positions_in_bytes_are_byte_offsets() -> None:
    header = b'attachment; filename="caf\xe9" x'
    with pytest.raises(ContentDispositionError) as caught:
        parse(header, strict=True)
    assert caught.value.position == 28 == header.index(b"x")


def test_a_non_ascii_character_counts_once() -> None:
    with pytest.raises(ContentDispositionError) as caught:
        parse('attachment; filename="\u20ac\U0001f600" x', strict=True)
    assert caught.value.position == 26


@pytest.mark.parametrize("size", [1000, 100_000])
def test_messages_quote_at_most_forty_characters_of_the_input(size: int) -> None:
    name = "n" * size
    headers = [
        f"attachment; {name}=a; {name}=b",
        f"attachment; {name}",
        f"attachment; {name}=",
        f"attachment; {name}*=UTF-8''%FF",
    ]
    for header in headers:
        with pytest.raises(ContentDispositionError) as caught:
            parse(header, strict=True)
        assert len(str(caught.value)) < 120, str(caught.value)
        assert "n" * 41 not in str(caught.value)


def test_extended_value_errors_never_quote_the_value() -> None:
    secret = "token-" + "s3cr3t" * 20
    with pytest.raises(ContentDispositionError) as caught:
        parse(f"attachment; filename*=UTF-8''{secret}%", strict=True)
    assert "s3cr3t" not in str(caught.value)
