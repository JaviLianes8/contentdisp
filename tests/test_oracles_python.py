"""Independent Python parsers read what build writes; the README's comparisons hold.

werkzeug, aiohttp and multipart are optional: each test skips when its package is not
installed, and the facts the README states are checked against the versions it names
(werkzeug 3.1.9, aiohttp 3.14.5, multipart 2.0.1). Python's email package is always there.
"""

from __future__ import annotations

import email.policy
import importlib.metadata
import random
from types import ModuleType

import pytest
from generators import unicode_text

from contentdisp import build, parse

EURO = "attachment; filename=\"EURO rates\"; filename*=utf-8''%e2%82%ac%20rates"
EURO_REVERSED = "attachment; filename*=utf-8''%e2%82%ac%20rates; filename=\"EURO rates\""
RFC_6266_EXAMPLE = 'INLINE; FILENAME= "an example.html"'


def _names(seed: int, count: int = 3000) -> list[str]:
    rng = random.Random(seed)
    return [unicode_text(rng) for _ in range(count)]


def _package(module: str, distribution: str, version: str | None = None) -> ModuleType:
    found: ModuleType = pytest.importorskip(module)
    if version is not None and importlib.metadata.version(distribution) != version:
        pytest.skip(f"the README states facts about {distribution} {version}")
    return found


def test_werkzeug_reads_back_every_built_header() -> None:
    http = _package("werkzeug.http", "werkzeug")
    for name in _names(1):
        assert http.parse_options_header(build("attachment", name))[1]["filename"] == name


def test_aiohttp_reads_back_every_built_header() -> None:
    multipart = _package("aiohttp.multipart", "aiohttp")
    for name in _names(2):
        header = build("attachment", name)
        params = multipart.parse_content_disposition(header)[1]
        # aiohttp strips leading "/" and "\" from quoted values; a name that needs
        # filename* travels there, unquoted.
        expected = name if "filename*" in header else name.lstrip("/\\")
        assert multipart.content_disposition_filename(params, "filename") == expected


def test_the_werkzeug_facts_in_the_readme() -> None:
    http = _package("werkzeug.http", "werkzeug", "3.1.9")
    utils = _package("werkzeug.utils", "werkzeug", "3.1.9")
    assert parse(EURO).filename == parse(EURO_REVERSED).filename == "\u20ac rates"
    assert http.parse_options_header(EURO)[1]["filename"] == "\u20ac rates"
    assert http.parse_options_header(EURO_REVERSED)[1]["filename"] == "EURO rates"
    assert http.parse_options_header(RFC_6266_EXAMPLE) == ("INLINE", {})
    assert parse(RFC_6266_EXAMPLE, strict=True).filename == "an example.html"
    assert utils.secure_filename("\u6771\u4eac.txt") == "txt"
    assert utils.secure_filename("\u20ac rates.pdf") == "rates.pdf"


def test_the_email_package_keeps_the_first_of_filename_and_filename_star() -> None:
    def read(header: str) -> object:
        return email.policy.HTTP.header_factory("Content-Disposition", header).params["filename"]

    assert read(EURO) == "EURO rates"
    assert read(EURO_REVERSED) == "\u20ac rates"
    # RFC 6266 Appendix D asks for the fallback first, so email reads the fallback.
    assert read(build("attachment", "\u20ac rates.pdf")) == "_ rates.pdf"


def test_multipart_ignores_filename_star() -> None:
    multipart = _package("multipart", "multipart", "2.0.1")
    header = build("attachment", "\u20ac rates.pdf")
    assert multipart.parse_options_header(header) == ("attachment", {"filename": "_ rates.pdf"})
    assert parse(header).filename == "\u20ac rates.pdf"


def test_aiohttp_takes_filename_star_in_either_order() -> None:
    multipart = _package("aiohttp.multipart", "aiohttp", "3.14.5")
    for header in (EURO, EURO_REVERSED):
        params = multipart.parse_content_disposition(header)[1]
        assert multipart.content_disposition_filename(params, "filename") == "\u20ac rates"
