"""Lenient parsing: what it reads from invalid headers, and what counts as an attachment."""

from __future__ import annotations

import pytest

from contentdisp import ContentDisposition, parse


@pytest.mark.parametrize(
    "header", ["", "   ", '"attachment"', "attachment filename=a.txt", "; filename=a.txt", ": x"]
)
def test_a_type_that_is_not_a_token_is_not_an_attachment(header: str) -> None:
    # RFC 6266 section 3: an invalid header is ignored, so the content is shown.
    assert not parse(header).is_attachment


@pytest.mark.parametrize("disposition", ["attachment", "ATTACHMENT", "x-custom", "formdata", "a*b"])
def test_any_other_token_than_inline_is_an_attachment(disposition: str) -> None:
    assert parse(disposition).is_attachment
    assert parse(disposition, strict=True).is_attachment


def test_inline_is_compared_without_case_even_when_built_by_hand() -> None:
    assert not ContentDisposition("INLINE").is_attachment
    assert not ContentDisposition("Inline", {"filename": "a"}).is_attachment
    assert ContentDisposition("inline x").is_attachment is False


def test_the_type_is_the_text_before_the_first_semicolon() -> None:
    assert parse("  Attachment Filename=a.txt ; x=1").type == "attachment filename=a.txt"
    assert parse('"inline"; filename=a').type == '"inline"'
    assert parse("").type == ""


@pytest.mark.parametrize(
    ("header", "params"),
    [
        ("filename=a.txt", {"filename": "a.txt"}),
        ('filename="a b.txt"; size=3', {"filename": "a b.txt", "size": "3"}),
        ("x=y; filename=a.txt", {"x": "y", "filename": "a.txt"}),
        ("filename*=UTF-8''%E2%82%AC.txt", {"filename": "\u20ac.txt"}),
        ("filename=a.txt; attachment", {"filename": "a.txt"}),
    ],
)
def test_a_header_without_a_type_still_names_a_file(header: str, params: dict[str, str]) -> None:
    result = parse(header)
    assert result.params == params
    assert result.type == header.split(";")[0].strip().lower()
    assert not result.is_attachment


@pytest.mark.parametrize("header", ['"foo; filename=bar"', "attachment filename=bar", "=x"])
def test_a_first_segment_that_is_not_a_parameter_names_nothing(header: str) -> None:
    assert parse(header).params == {}


def test_a_valid_header_never_reads_its_type_as_a_parameter() -> None:
    assert parse("attachment; filename=a").params == {"filename": "a"}


def test_names_are_checked_before_case_folding() -> None:
    # The Kelvin sign lower-cases to "k" but is not a tchar.
    assert parse("attachment; \u212aey=v; key=w").params == {"key": "w"}


def test_the_first_readable_extended_value_wins() -> None:
    header = "attachment; filename*=UTF-8''%FF; filename*=UTF-8''ok; filename*=UTF-8''late"
    assert parse(header).filename == "ok"


def test_a_lenient_language_part_may_be_any_letters_digits_and_hyphens() -> None:
    header = "attachment; filename=plain; filename*=UTF-8'1-x-'%41"
    assert parse(header).filename == "A"
    assert parse("attachment; filename=plain; filename*=UTF-8'en_US'%41").filename == "plain"


def test_a_quoted_value_ends_at_its_closing_quote() -> None:
    assert parse('attachment; filename="a.txt"junk; x=1').params == {"filename": "a.txt", "x": "1"}


def test_a_trailing_lone_backslash_in_an_open_quote_is_dropped() -> None:
    assert parse('attachment; filename="abc\\').filename == "abc"


@pytest.mark.parametrize(
    ("header", "params"),
    [
        (r"attachment; filename=C:\dir\;size=3", {"filename": "C:\\dir\\", "size": "3"}),
        (r"attachment; filename=a\; size=3", {"filename": "a\\", "size": "3"}),
        (r"attachment; x=\;y=\\", {"x": "\\", "y": "\\\\"}),
    ],
)
def test_a_backslash_outside_quotes_never_hides_the_next_semicolon(
    header: str, params: dict[str, str]
) -> None:
    assert parse(header).params == params
