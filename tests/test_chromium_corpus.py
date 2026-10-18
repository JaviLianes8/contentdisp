"""Chrome's own expectations, read from Chromium's http_content_disposition_unittest.cc.

The file is fetched at a pinned commit (tests/upstream/MANIFEST.json); its two tables are
decoded by tests/chromium_cases.py. Chrome is a lenient reader, so the lenient mode is
compared: whether the content is an attachment must agree on every tc2231 entry, and the
file name must agree except where Chrome deliberately departs from RFC 6266 (decoding
RFC 2047, percent escapes, raw octets or other charsets, folding whitespace, normalising)
or where the header is invalid, for which RFC 6266 section 3 defines no recovery. Each
difference is put in exactly one category below, and the counts are pinned.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

import chromium_cases
import pytest
from conftest import upstream_text

from contentdisp import ContentDispositionError, parse


@pytest.fixture(scope="module")
def source() -> str:
    return upstream_text("chromium-http_content_disposition_unittest.cc")


def _valid(header: bytes) -> bool:
    try:
        parse(header, strict=True)
    except ContentDispositionError:
        return False
    return True


def _category(header: bytes, chrome: str, ours: str) -> str | None:
    extended = re.search(rb"filename\*=\s*([^']*)'", header)
    if not _valid(header):
        return "invalid header"
    if b"=?" in header:
        return "RFC 2047"  # RFC 6266 Appendix C.1: not for parameters
    if b"filename*" not in header and re.search(r"%[0-9A-Fa-f]{2}", ours):
        return "percent decoding"  # Appendix C.2; the corpus checks it is not applied
    if b"filename*" not in header and any(octet > 0x7F for octet in header):
        return "charset guessing"  # Appendix C.3: ISO-8859-1 is the plain encoding
    if extended and extended.group(1).lower() not in (b"utf-8", b"iso-8859-1"):
        return "other charset"  # RFC 8187 asks for UTF-8 and encourages ISO-8859-1
    if ours.replace("\t", " ") == chrome:
        return "whitespace folding"  # left to the caller (safe_filename)
    if unicodedata.normalize("NFC", ours) == chrome:
        return "normalisation"  # the exact decoded text is returned
    return None


def _differences(cases: list[tuple[bytes, str]]) -> Counter[str]:
    found: Counter[str] = Counter()
    for header, chrome in cases:
        ours = parse(header).filename or ""
        if ours != chrome:
            category = _category(header, chrome, ours)
            assert category is not None, (header, chrome, ours)
            found[category] += 1
    return found


def test_the_tables_hold_every_entry(source: str) -> None:
    assert len(chromium_cases.tc2231_port(source)) == 49
    assert len(chromium_cases.filename_table(source)) == 75


def test_chrome_and_lenient_mode_agree_on_what_is_an_attachment(source: str) -> None:
    for header, attachment, _ in chromium_cases.tc2231_port(source):
        assert parse(header).is_attachment is attachment, header


def test_an_invalid_disposition_type_is_inline_for_chrome_too(source: str) -> None:
    unreadable = [entry for entry in chromium_cases.tc2231_port(source) if not _valid(entry[0])]
    types = {parse(header).type for header, attachment, _ in unreadable if not attachment}
    assert {'"inline"', '"attachment"', "filename=foo.html", ""} <= types


def test_file_names_of_the_tc2231_port(source: str) -> None:
    cases = [(header, name) for header, _, name in chromium_cases.tc2231_port(source)]
    assert _differences(cases) == {
        "invalid header": 7,
        "percent decoding": 3,
        "charset guessing": 1,
    }


def test_file_names_of_the_filename_table(source: str) -> None:
    cases = [(header, name) for header, _, name in chromium_cases.filename_table(source)]
    assert _differences(cases) == {
        "invalid header": 16,
        "percent decoding": 7,
        "RFC 2047": 5,
        "other charset": 3,
        "whitespace folding": 1,
        "normalisation": 1,
    }


def test_every_rfc_5987_entry_of_chrome_that_follows_the_rfc_agrees(source: str) -> None:
    extended = [
        (header, name)
        for header, _, name in chromium_cases.filename_table(source)
        if b"filename*=" in header
    ]
    assert len(extended) == 28
    agreeing = [header for header, name in extended if (parse(header).filename or "") == name]
    assert len(agreeing) == 22  # the other 6: charsets, raw spaces, normalisation
