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
    ("attachment; filename*=UTF-8''%aZ", "malformed extended value", 31),
    ("attachment; filename*=UTF-8''%e", "malformed extended value", 31),
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
    # The tag is reported even when the value-chars after it break the grammar later.
    ("attachment; filename*=UTF-8'-en'%G0", "malformed language tag", 28),
    ("attachment; filename*=UTF-8'en-a'%G0", "malformed language tag", 28),
    ("attachment; filename*=UTF-8'1en'a\"", "malformed language tag", 28),
    ("Y.c&9+  ;\tfilename*\t= iso-8859-1'en-'!%E\x002%A01_|", "malformed language tag", 33),
    # A language part the value grammar cuts short: its first character no tag continues.
    ("attachment; filename*=UTF-8'-en", "malformed language tag", 28),
    ("attachment; filename*=UTF-8'-en)'a", "malformed language tag", 28),
    ("attachment; filename*=UTF-8'1en", "malformed language tag", 28),
    ("attachment; filename*=UTF-8'-en_US'a", "malformed language tag", 28),
    ("attachment; filename*=0%'c0", "malformed language tag", 26),
    ("attachment; filename*=UTF-8'g1", "malformed language tag", 29),
    ("attachment; filename*=UTF-8'en-US-a_b'a", "malformed extended value", 35),
    # A start that some tag continues is no tag error: the grammar error stands.
    ("attachment; filename*=UTF-8'x", "malformed extended value", 29),
    ("attachment; filename*=UTF-8'en-", "malformed extended value", 31),
    ("attachment; filename*=UTF-8'en-a", "malformed extended value", 32),
    ("attachment; filename*=UTF-8'aa-a0", "malformed extended value", 33),
    ("attachment; filename*=UTF-8'en-a-", "malformed extended value", 33),
    ("attachment; filename*=UTF-8'en-a0)", "malformed extended value", 33),
    # A later error in a well-formed tag's value keeps its own position.
    ("attachment; filename*=UTF-8'en'%G0", "malformed extended value", 32),
    # Octets invalid in their charset: the start of the value.
    ("attachment; filename*=UTF-8''ok%E4", "invalid UTF-8 in extended value", 22),
    ("attachment; filename*=iso-8859-1''ok%85", "control character in extended value", 22),
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


# RFC 8187 section 3.2.1: mime-charsetc is ALPHA / DIGIT and these punctuation characters.
MIME_CHARSETC = ["koi8-r", "a!#$%&+-^_`{}~z", "x{y}", "x`y", "x^y"]


@pytest.mark.parametrize("charset", MIME_CHARSETC)
def test_a_well_formed_unknown_charset_is_ignored(charset: str) -> None:
    assert parse(f"attachment; filename*={charset}''abc", strict=True).params == {}
    header = f"attachment; filename=a; filename*={charset}''b"
    assert parse(header, strict=True).filename == "a"
    assert parse(header).filename == "a"


@pytest.mark.parametrize("octet", ["00", "08", "0A", "1B", "1F", "7F", "80", "85", "9F"])
def test_iso_8859_1_control_octets_are_invalid(octet: str) -> None:
    header = f"attachment; filename=\"plain\"; filename*=iso-8859-1''a%{octet}"
    with pytest.raises(
        ContentDispositionError, match="control character in extended value"
    ) as caught:
        parse(header, strict=True)
    assert caught.value.position == header.index("iso")
    assert parse(header).filename == "plain"


@pytest.mark.parametrize(("octets", "text"), [("%20%7E", " ~"), ("%A0%FF", "\xa0\xff")])
def test_iso_8859_1_graphic_octets_decode(octets: str, text: str) -> None:
    header = f"attachment; filename*=ISO-8859-1''{octets}"
    assert parse(header, strict=True).filename == text
    assert parse(header).filename == text
