"""Behaviour of parse in both modes, one promise per test."""

from __future__ import annotations

import pytest

from contentdisp import ContentDisposition, parse


def test_plain_attachment_with_filename() -> None:
    result = parse('attachment; filename="report.pdf"')
    assert result == ContentDisposition("attachment", {"filename": "report.pdf"})


def test_inline_without_parameters() -> None:
    result = parse("inline")
    assert (result.type, result.filename, result.params) == ("inline", None, {})


def test_extended_filename_wins_over_plain_in_either_order() -> None:
    ext = "filename*=UTF-8''%E2%82%AC%20rates.txt"
    for header in (f'attachment; filename="EURO"; {ext}', f'attachment; {ext}; filename="EURO"'):
        assert parse(header).filename == "\u20ac rates.txt"
        assert parse(header, strict=True).filename == "\u20ac rates.txt"


def test_undecodable_extended_value_leaves_the_plain_fallback() -> None:
    header = 'attachment; filename="plain.txt"; filename*=UTF-8\'missing-quote'
    assert parse(header).filename == "plain.txt"


def test_unsupported_charset_is_ignored_in_both_modes() -> None:
    header = "attachment; filename=\"plain.txt\"; filename*=ISO-8859-15''%A4"
    assert parse(header).filename == "plain.txt"
    assert parse(header, strict=True).filename == "plain.txt"


def test_semicolon_and_escaped_quote_inside_a_quoted_value() -> None:
    assert parse('attachment; filename="a;b\\".txt"', strict=True).filename == 'a;b".txt'


def test_names_and_type_are_case_insensitive() -> None:
    result = parse('ATTACHMENT; FileName="a.txt"', strict=True)
    assert (result.type, result.params) == ("attachment", {"filename": "a.txt"})


def test_whitespace_around_equals_and_semicolons_is_allowed() -> None:
    result = parse(' attachment ;\tfilename = "a.txt" ; name=x\t', strict=True)
    assert result.params == {"filename": "a.txt", "name": "x"}


def test_bytes_are_decoded_as_latin_1() -> None:
    assert parse(b'attachment; filename="caf\xe9.txt"').filename == "caf\xe9.txt"


def test_other_argument_types_are_rejected() -> None:
    with pytest.raises(TypeError):
        parse(None)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("header", "reason"),
    [
        ("", "missing disposition type"),
        ('"attachment"', "missing disposition type"),
        ("attachment;", "expected a parameter name"),
        ("attachment; ; filename=a", "expected a parameter name"),
        ("attachment filename=a", "expected ';'"),
        ("attachment; filename", "expected '='"),
        ("attachment; filename=", "expected a token"),
        ("attachment; filename=a b", "expected ';'"),
        ('attachment; filename="a', "unterminated"),
        ('attachment; filename="a"b', "expected ';'"),
        ("attachment; filename=a; FILENAME=b", "more than once"),
        ("attachment; filename*=\"UTF-8''a\"", "malformed extended value"),
        ("attachment; filename*=UTF-8''%E4", "invalid UTF-8"),
        ("attachment; filename*=ISO-8859-1''%82", "outside ISO-8859-1"),
        ('attachment; filename="a\x01"', "invalid character"),
        ("attachment; filename=a\r\n", "CR, LF and NUL"),
    ],
)
def test_strict_mode_rejects(header: str, reason: str) -> None:
    with pytest.raises(ValueError, match=reason):
        parse(header, strict=True)


def test_lenient_mode_keeps_the_first_of_repeated_parameters() -> None:
    assert parse("attachment; filename=a; filename=b").filename == "a"


def test_lenient_mode_skips_parameters_it_cannot_read() -> None:
    result = parse('attachment; broken; filename *=x; =y; filename="a.txt"')
    assert result.params == {"filename": "a.txt"}


def test_lenient_mode_reads_an_unterminated_quote_to_the_end() -> None:
    assert parse('attachment; filename="a;b').filename == "a;b"


def test_lenient_mode_replaces_cr_lf_and_nul_with_space() -> None:
    assert parse('attachment; filename="a\r\nb\0c"').filename == "a  b c"


def test_lenient_mode_keeps_non_token_text_of_an_unquoted_value() -> None:
    assert parse("attachment; filename=foo[1].html").filename == "foo[1].html"


def test_unknown_types_count_as_attachment() -> None:
    assert parse("attachment").is_attachment
    assert parse("x-custom").is_attachment
    assert not parse("INLINE").is_attachment


def test_rfc_2231_continuations_stay_extension_parameters() -> None:
    result = parse('attachment; filename*0="a"; filename*1="b"', strict=True)
    assert result.filename is None
    assert result.params == {"filename*0": "a", "filename*1": "b"}


def test_strict_mode_rejects_a_quoted_pair_of_a_control_character() -> None:
    with pytest.raises(ValueError, match="quoted-pair"):
        parse('attachment; filename="a\\\x01b"', strict=True)
    assert parse('attachment; filename="a\\\tb"', strict=True).filename == "a\tb"


@pytest.mark.parametrize("charset", ["UTF-16", "utf-7", "UTF8", "latin1", "unicode_escape"])
def test_only_utf8_and_iso_8859_1_are_decoded(charset: str) -> None:
    header = f"attachment; filename=\"plain\"; filename*={charset}''%41%00"
    assert parse(header).filename == "plain"
    assert parse(header, strict=True).filename == "plain"


def test_decoded_non_ascii_text_counts_as_obs_text() -> None:
    # A str holds already-decoded text; whatever its encoding, the octets were obs-text.
    assert parse('form-data; name="f"; filename="\u20ac.txt"', strict=True).filename == "\u20ac.txt"
    with pytest.raises(ValueError, match="token or quoted-string"):
        parse("attachment; filename=\u20ac.txt", strict=True)
