"""Every code point and octet against the control rule of extended values (exhaustive)."""

from __future__ import annotations

import pytest

from contentdisp import ContentDispositionError, parse


def _refused(code: int) -> bool:
    # C0 but HTAB, DEL and C1: the controls build refuses too.
    return (code < 0x20 and code != 0x09) or 0x7F <= code <= 0x9F


def _encoded(octets: bytes) -> str:
    return "".join(f"%{octet:02X}" for octet in octets)


# Every code point but the surrogates, which UTF-8 cannot carry.
CODE_POINTS = [code for code in range(0x110000) if not 0xD800 <= code <= 0xDFFF]
REFUSED = [code for code in CODE_POINTS if _refused(code)]
KEPT = [code for code in CODE_POINTS if not _refused(code)]


def _check(charset: str, octets: bytes, text: str, refused: bool) -> None:
    value = f"{charset}''{_encoded(octets)}"
    header = f"attachment; filename*={value}"
    if refused:
        with pytest.raises(ContentDispositionError, match="control character") as caught:
            parse(header, strict=True)
        assert caught.value.position == 22
    else:
        assert parse(header, strict=True).filename == text
    fallback = parse(f"attachment; filename=a; filename*={value}")
    assert fallback.filename == ("a" if refused else text)


def test_utf8_refuses_each_c0_control_but_htab_del_and_each_c1_control() -> None:
    assert len(REFUSED) == 0x20 - 1 + 0x9F - 0x7F + 1
    for code in REFUSED:
        _check("UTF-8", chr(code).encode("utf-8"), chr(code), refused=True)


@pytest.mark.parametrize("part", range(4))
def test_utf8_keeps_every_other_code_point(part: int) -> None:
    # A value holding a refused code point is refused whole, so a value made of a block
    # of code points that decodes to that block shows each of them is kept.
    codes = KEPT[part::4]
    for start in range(0, len(codes), 512):
        text = "".join(map(chr, codes[start : start + 512]))
        _check("UTF-8", text.encode("utf-8"), text, refused=False)


def test_iso_8859_1_refuses_exactly_the_same_octets() -> None:
    for octet in range(0x100):
        _check("ISO-8859-1", bytes([octet]), chr(octet), _refused(octet))
