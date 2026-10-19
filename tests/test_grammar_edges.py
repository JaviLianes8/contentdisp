"""Edges of the RFC 6266, RFC 9110 and RFC 5646 rules, written by hand from the grammar.

None of these need a fetched file. Sources: RFC 6266 section 4.1
(https://www.rfc-editor.org/rfc/rfc6266), RFC 9110 section 5.6.2
(https://www.rfc-editor.org/rfc/rfc9110), RFC 5646 section 2.1
(https://www.rfc-editor.org/rfc/rfc5646).
"""

from __future__ import annotations

import string

import pytest

from contentdisp import ContentDispositionError, parse

TCHAR = set(string.ascii_letters + string.digits + "!#$%&'*+-.^_`|~")


@pytest.mark.parametrize("strict", [False, True])
def test_a_bare_star_is_an_ordinary_parameter(strict: bool) -> None:
    # ext-token is a token followed by "*", so "*" alone is a plain token name.
    assert parse("attachment; *=foo", strict=strict).params == {"*": "foo"}
    assert parse("attachment; *=UTF-8''x", strict=strict).params == {"*": "UTF-8''x"}


@pytest.mark.parametrize("strict", [False, True])
def test_a_double_star_is_the_extended_form_of_star(strict: bool) -> None:
    assert parse("attachment; **=UTF-8''%41", strict=strict).params == {"*": "A"}


@pytest.mark.parametrize("char", [chr(code) for code in range(0x21, 0x7F)])
def test_the_token_characters_are_exactly_the_tchar_set(char: str) -> None:
    header = f"attachment; filename=a{char}b"
    if char in TCHAR:
        assert parse(header, strict=True).filename == f"a{char}b"
    else:
        with pytest.raises(ContentDispositionError):
            parse(header, strict=True)


def test_a_lenient_unquoted_value_keeps_its_spaces() -> None:
    assert parse("attachment; filename=a b.txt").filename == "a b.txt"


def test_an_empty_charset_is_refused_in_strict_mode() -> None:
    with pytest.raises(ContentDispositionError, match="malformed extended value"):
        parse("attachment; filename*=''abc", strict=True)


# RFC 5646 section 2.1, the "irregular" and "regular" grandfathered tags, written by hand
# (tests/test_spec_grammar.py compares the parser with the rules of the fetched text).
GRANDFATHERED = [
    "en-GB-oed",
    "i-ami",
    "i-bnn",
    "i-default",
    "i-enochian",
    "i-hak",
    "i-klingon",
    "i-lux",
    "i-mingo",
    "i-navajo",
    "i-pwn",
    "i-tao",
    "i-tay",
    "i-tsu",
    "sgn-BE-FR",
    "sgn-BE-NL",
    "sgn-CH-DE",
    "art-lojban",
    "cel-gaulish",
    "no-bok",
    "no-nyn",
    "zh-guoyu",
    "zh-hakka",
    "zh-min",
    "zh-min-nan",
    "zh-xiang",
]
WELL_FORMED = [
    *GRANDFATHERED,
    "zh-abc",
    "zh-abc-def",
    "zh-abc-def-ghi",
    "en-US",
    "es-419",
    "abcd",
    "abcde",
    "abcdefgh",
    "en-a-bb",
    "en-a-bbbbbbbb",
    "en-x-a",
]
ILL_FORMED = [
    "zh-abc-def-ghi-jkl",
    "en-12",
    "en-1234-",
    "abcdefghi",
    "en-a-b",
    "en-a-bbbbbbbbb",
    "en-x-abcdefghi",
]


@pytest.mark.parametrize("tag", WELL_FORMED)
def test_a_well_formed_language_tag_is_accepted(tag: str) -> None:
    header = f"attachment; filename*=UTF-8'{tag}'a.txt"
    assert parse(header, strict=True).filename == "a.txt"


@pytest.mark.parametrize("tag", ILL_FORMED)
def test_an_ill_formed_language_tag_is_refused(tag: str) -> None:
    with pytest.raises(ContentDispositionError, match="malformed language tag"):
        parse(f"attachment; filename*=UTF-8'{tag}'a.txt", strict=True)
