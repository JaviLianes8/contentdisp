"""safe_filename turns advisory names into harmless ones (RFC 6266 section 4.3)."""

from __future__ import annotations

import pytest

from contentdisp import safe_filename


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("report.pdf", "report.pdf"),
        ("../../etc/passwd", "passwd"),
        ("/etc/passwd", "passwd"),
        ("C:\\Windows\\System32\\x.dll", "x.dll"),
        ("..\\..\\boot.ini", "boot.ini"),
        ("\uff0e\uff0e\uff0fsecret", "secret"),
        ("a\uff3cb.txt", "b.txt"),
        ("dir/", "download"),
        ("..", "download"),
        (".", "download"),
        ("~", "download"),
        ("", "download"),
    ],
)
def test_only_the_last_path_segment_survives(name: str, expected: str) -> None:
    assert safe_filename(name) == expected


def test_none_gives_the_default() -> None:
    assert safe_filename(None) == "download"
    assert safe_filename(None, default="file.bin") == "file.bin"


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        (".htaccess", "htaccess"),
        ("~root", "root"),
        ("-rf", "rf"),
        ("  name.txt  ", "name.txt"),
        ("name.txt...", "name.txt"),
        ("name. . .", "name"),
    ],
)
def test_leading_and_trailing_special_characters_are_stripped(name: str, expected: str) -> None:
    assert safe_filename(name) == expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("a\x00b\x1bc.txt", "abc.txt"),
        ("a\tb\nc.txt", "a b c.txt"),
        ("a\x85b.txt", "a b.txt"),
        ("evil\u202etxt.exe", "eviltxt.exe"),
        ("a\u2066b\u200fc", "abc"),
    ],
)
def test_control_and_bidi_characters_are_removed(name: str, expected: str) -> None:
    assert safe_filename(name) == expected


def test_windows_reserved_characters_are_replaced() -> None:
    assert safe_filename('a<b>c:d"e|f?g*h.txt') == "a_b_c_d_e_f_g_h.txt"
    assert safe_filename("file.txt:stream") == "file.txt_stream"


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("CON", "_CON"),
        ("con.txt", "_con.txt"),
        ("Nul .tar.gz", "_Nul .tar.gz"),
        ("COM1", "_COM1"),
        ("lpt9.log", "_lpt9.log"),
        ("COM\u00b9", "_COM1"),
        ("conin$", "_conin$"),
        ("console.txt", "console.txt"),
        ("com10", "com10"),
    ],
)
def test_windows_device_names_are_prefixed(name: str, expected: str) -> None:
    assert safe_filename(name) == expected


def test_compatibility_forms_are_normalised() -> None:
    assert safe_filename("\ufb01le.txt") == "file.txt"
    assert safe_filename("cafe\u0301.txt") == "caf\u00e9.txt"


def test_long_names_are_cut_in_utf8_bytes_keeping_the_extension() -> None:
    result = safe_filename("\u00e9" * 300 + ".txt")
    assert len(result.encode("utf-8")) <= 255
    assert result.endswith(".txt")
    assert result == "\u00e9" * 125 + ".txt"


def test_a_long_extension_is_not_kept_whole() -> None:
    result = safe_filename("a." + "b" * 300, max_bytes=20)
    assert result == "a." + "b" * 18


def test_truncation_never_splits_a_character_or_leaves_a_trailing_dot() -> None:
    assert safe_filename("ab.\u20ac\u20ac", max_bytes=4) == "ab"
    assert safe_filename("ab c.d", max_bytes=3) == "ab"


def test_a_device_name_prefix_stays_within_the_limit() -> None:
    assert safe_filename("con.txt", max_bytes=7) == "_con.tx"


def test_max_bytes_must_be_positive() -> None:
    with pytest.raises(ValueError):
        safe_filename("a" * 10, max_bytes=0)


def test_truncation_never_leaves_the_extension_alone() -> None:
    assert safe_filename("\U0001f600\U0001f600.ab", max_bytes=6) == "\U0001f600"


@pytest.mark.parametrize("prefix", ["\ufeff", "\u200b", "\u00ad", "\u0301", "\u200d", "\u2060"])
def test_invisible_characters_cannot_hide_a_leading_dot(prefix: str) -> None:
    assert safe_filename(prefix + ".env") == "env"


def test_format_characters_are_removed_but_joiners_inside_a_name_stay() -> None:
    assert safe_filename("a\u200bb\u00adc\ufeff.txt") == "abc.txt"
    assert safe_filename("\U0001f469\u200d\U0001f4bb.png") == "\U0001f469\u200d\U0001f4bb.png"


def test_the_cut_without_extension_is_trimmed_again() -> None:
    assert safe_filename("\U0001f600  .ab", max_bytes=6) == "\U0001f600"


def test_the_default_is_returned_as_given() -> None:
    assert safe_filename("..", default="download", max_bytes=3) == "download"
