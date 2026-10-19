"""Strict positions inside extended values and around CR, LF and NUL (positions by hand)."""

from __future__ import annotations

import pytest

from contentdisp import ContentDispositionError, parse

# (header, start of the message, index of the first character that breaks the grammar)
CASES = [
    # A grammar error before a CR, LF or NUL is the one reported.
    ("a b\n", "expected ';'", 2),
    ('"x\r', "missing disposition type", 0),
    ("attachment; filename=a b\0", "expected ';'", 23),
    ('attachment; filename="a\x01\r"', "invalid character '\\x01'", 23),
    # A CR, LF or NUL that is the first offending character keeps its own message.
    ("attachment; filename=a\r\n", "CR, LF and NUL are not allowed", 22),
    ("attachment; filename*=UTF-8''a\rb", "CR, LF and NUL are not allowed", 30),
    ("attachment; filename*=UTF-8''%4\n", "CR, LF and NUL are not allowed", 31),
    # Inside an extended value: the character that breaks the RFC 8187 grammar.
    ("attachment; filename*=UTF-8''%G0", "malformed extended value", 30),
    ("attachment; filename*=UTF-8''%4G", "malformed extended value", 31),
    ("attachment; filename*=UTF-8''%", "malformed extended value", 30),
    ("attachment; filename*=UTF-8''a%; x=1", "malformed extended value", 31),
    ("attachment; filename*=UTF-8''a\"b", "malformed extended value", 30),
    ("attachment; filename*=UTF-8'en_US'a", "malformed extended value", 30),
    ("attachment; filename*=UTF-8", "malformed extended value", 27),
    ("attachment; filename*=UTF-8'en", "malformed extended value", 30),
    ("attachment; filename*='en'a", "malformed extended value", 22),
    ("attachment; filename*=utf.8''abc", "malformed extended value", 25),
    ("attachment; filename=a; filename*=utf.8''b", "malformed extended value", 37),
    # A language part of letters, digits and hyphens that is not a tag: its first character.
    ("attachment; filename*= UTF-8'-en'a", "malformed language tag", 29),
    ("attachment; filename*=UTF-8'1'a", "malformed language tag", 28),
    # Octets invalid in their charset: the start of the value.
    ("attachment; filename*=UTF-8''ok%E4", "invalid UTF-8 in extended value", 22),
    ("attachment; filename*=iso-8859-1''ok%85", "octet outside ISO-8859-1", 22),
]


@pytest.mark.parametrize(("header", "message", "position"), CASES)
def test_strict_errors_point_at_the_character_that_breaks_the_grammar(
    header: str, message: str, position: int
) -> None:
    with pytest.raises(ContentDispositionError) as caught:
        parse(header, strict=True)
    assert caught.value.position == position, str(caught.value)
    assert str(caught.value).startswith(message), str(caught.value)
    assert str(caught.value).endswith(f" at offset {position}")


@pytest.mark.parametrize("charset", ["utf.8", "utf/8", "utf:8", "utf(8", "utf@8", "utf 8"])
def test_a_charset_outside_mime_charsetc_is_an_error(charset: str) -> None:
    header = f"attachment; filename*={charset}''abc"
    with pytest.raises(ContentDispositionError, match="malformed extended value"):
        parse(header, strict=True)
    assert parse(header).params == {}


def test_a_well_formed_unknown_charset_is_ignored() -> None:
    assert parse("attachment; filename*=koi8-r''abc", strict=True).params == {}
    assert parse("attachment; filename=a; filename*=koi8-r''b", strict=True).filename == "a"


@pytest.mark.parametrize("octet", ["00", "09", "1B", "1F", "7F", "80", "85", "9F"])
def test_iso_8859_1_control_octets_are_invalid(octet: str) -> None:
    header = f"attachment; filename=\"plain\"; filename*=iso-8859-1''a%{octet}"
    with pytest.raises(ContentDispositionError, match="octet outside ISO-8859-1") as caught:
        parse(header, strict=True)
    assert caught.value.position == header.index("iso")
    assert parse(header).filename == "plain"


@pytest.mark.parametrize(("octets", "text"), [("%20%7E", " ~"), ("%A0%FF", "\xa0\xff")])
def test_iso_8859_1_graphic_octets_decode(octets: str, text: str) -> None:
    header = f"attachment; filename*=ISO-8859-1''{octets}"
    assert parse(header, strict=True).filename == text
    assert parse(header).filename == text


def test_utf8_keeps_every_code_point() -> None:
    # UTF-8 is not ISO-8859-1: every scalar value, controls included, is a character.
    assert parse("attachment; x*=UTF-8''%00%C2%85", strict=True).params == {"x": "\x00\x85"}
