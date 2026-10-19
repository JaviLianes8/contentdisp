"""A decoded extended value holds no control but HTAB, whatever its charset."""

from __future__ import annotations

import pytest

from contentdisp import ContentDispositionError, parse

# C0 controls but HTAB, DEL and C1 controls as UTF-8 percent-encodings (written by hand).
UTF8_CONTROLS = ["%00", "%08", "%0A", "%0D", "%1B", "%1F", "%7F", "%C2%80", "%C2%85", "%C2%9F"]


@pytest.mark.parametrize("charset", ["UTF-8", "utf-8", "ISO-8859-1", "iso-8859-1"])
@pytest.mark.parametrize("control", ["%00", "%0A", "%0D", "%1F", "%7F"])
def test_a_c0_control_or_del_is_refused_in_every_charset(charset: str, control: str) -> None:
    header = f"attachment; filename=plain; filename*={charset}''a{control}b"
    with pytest.raises(ContentDispositionError, match="control character") as caught:
        parse(header, strict=True)
    assert caught.value.position == header.index(charset)
    assert parse(header).filename == "plain"


@pytest.mark.parametrize("control", UTF8_CONTROLS)
def test_a_utf8_control_is_refused_like_the_iso_8859_1_one(control: str) -> None:
    header = f"attachment; filename*=UTF-8''x{control}"
    with pytest.raises(ContentDispositionError, match="control character") as caught:
        parse(header, strict=True)
    assert caught.value.position == 22
    assert parse(header).params == {}


def test_lenient_parsing_never_returns_a_raw_cr_or_lf() -> None:
    header = "attachment; filename*=UTF-8''a%0D%0ASet-Cookie%3A%20x; filename=b"
    assert parse(header).filename == "b"
    assert parse("attachment; filename*=UTF-8''a%0D%0Ab").params == {}


@pytest.mark.parametrize(
    ("octets", "text"),
    [("%20%7E", " ~"), ("%C2%A0%C3%BF", "\xa0\xff"), ("%E2%80%8B%EF%BF%BF", "\u200b\uffff")],
)
def test_utf8_keeps_every_other_code_point(octets: str, text: str) -> None:
    header = f"attachment; filename*=UTF-8''{octets}"
    assert parse(header, strict=True).filename == text
    assert parse(header).filename == text


@pytest.mark.parametrize("charset", ["UTF-8", "ISO-8859-1"])
def test_htab_is_kept_as_in_a_quoted_string(charset: str) -> None:
    header = f"attachment; filename=plain; filename*={charset}''a%09b"
    assert parse(header, strict=True).filename == "a\tb"
    assert parse(header).filename == "a\tb"
