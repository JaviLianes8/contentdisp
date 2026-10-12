"""Behaviour of build: RFC 6266 Appendix D output, injection blocked, form-data per RFC 7578."""

from __future__ import annotations

import pytest

from contentdisp import build, parse


def test_ascii_filename_emits_no_extended_form() -> None:
    assert build("attachment", "report.pdf") == 'attachment; filename="report.pdf"'


def test_without_filename() -> None:
    assert build("Inline") == "inline"


def test_non_ascii_filename_emits_fallback_first_then_utf8_extended_form() -> None:
    header = build("attachment", "€ rates.txt")
    assert header == "attachment; filename=\"_ rates.txt\"; filename*=UTF-8''%E2%82%AC%20rates.txt"


def test_fallback_transliterates_accented_letters() -> None:
    header = build("attachment", "résumé ä.pdf")
    assert header.startswith("attachment; filename=\"resume a.pdf\"; filename*=UTF-8''")


@pytest.mark.parametrize(
    ("name", "fallback", "encoded"),
    [
        ('a"b.txt', "a_b.txt", "a%22b.txt"),
        ("a\\b.txt", "a_b.txt", "a%5Cb.txt"),
        ("foo-%41.txt", "foo-_41.txt", "foo-%2541.txt"),
    ],
)
def test_characters_appendix_d_avoids_move_to_the_extended_form(
    name: str, fallback: str, encoded: str
) -> None:
    expected = f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{encoded}"
    assert build("attachment", name) == expected


def test_a_lone_percent_sign_stays_plain() -> None:
    assert build("attachment", "50%.txt") == 'attachment; filename="50%.txt"'


def test_attr_chars_are_not_percent_encoded() -> None:
    header = build("attachment", "é!#$&+-.^_`|~")
    assert header.endswith("filename*=UTF-8''%C3%A9!#$&+-.^_`|~")


def test_extra_parameters_use_hyphens_and_lower_case() -> None:
    header = build("attachment", "a.txt", Creation_Date="Wed, 12 Feb 1997 16:29:51 -0500")
    assert header == (
        'attachment; filename="a.txt"; creation-date="Wed, 12 Feb 1997 16:29:51 -0500"'
    )


@pytest.mark.parametrize("value", ["a\r\nSet-Cookie: x", "a\nb", "a\rb", "a\0b", "a\x7fb", "\x85"])
def test_control_characters_are_rejected(value: str) -> None:
    with pytest.raises(ValueError, match="control character"):
        build("attachment", value)
    with pytest.raises(ValueError, match="control character"):
        build("attachment", "a.txt", title=value)


def test_lone_surrogates_are_rejected() -> None:
    with pytest.raises(ValueError):
        build("attachment", "a\ud800.txt")


@pytest.mark.parametrize("bad", ["", "attach ment", "attachment\r\nX: y", "a;b", '"a"'])
def test_type_must_be_a_token(bad: str) -> None:
    with pytest.raises(ValueError, match="token"):
        build(bad)


def test_parameter_names_must_be_tokens() -> None:
    with pytest.raises(ValueError, match="token"):
        build("attachment", **{"a b": "x"})
    with pytest.raises(ValueError, match="token"):
        build("attachment", **{"title*": "x"})


def test_non_string_values_are_rejected() -> None:
    with pytest.raises(TypeError):
        build("attachment", 3)  # type: ignore[arg-type]


def test_form_data_never_emits_an_extended_parameter() -> None:
    header = build("form-data", "€.txt", name="file")
    assert header == 'form-data; filename="€.txt"; name="file"'


def test_form_data_escapes_only_cr_lf_and_quote() -> None:
    header = build("form-data", 'a"b\r\nc\\%41.txt', name="f")
    assert header == 'form-data; filename="a%22b%0D%0Ac\\%41.txt"; name="f"'


@pytest.mark.parametrize(
    "name", ["report.pdf", "€ rates.txt", 'a"b\\c.txt', "50%41.txt", "\U0001f600", ""]
)
def test_built_headers_parse_back_strictly(name: str) -> None:
    parsed = parse(build("attachment", name, title=name), strict=True)
    assert parsed.filename == name
    assert parsed.params["title"] == name
