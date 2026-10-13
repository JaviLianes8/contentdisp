"""Hand-written cases for the behaviours tests/test_browser_corpus.py checks on tc2231.

These run without the fetched page. The headers are written by hand from the RFC 6266
grammar (https://www.rfc-editor.org/rfc/rfc6266), not copied from the corpus.
"""

from __future__ import annotations

import pytest

from contentdisp import parse, safe_filename

NAIVE = "na\u00efve.txt"

# Hand-written: headers outside the RFC 6266 grammar, refused in strict mode only.
INVALID = [
    "attachment; filename=a b.pdf",
    '"attachment"',
    'attachment; filename="x.pdf"; filename="y.pdf"',
    "attachment filename=x.pdf",
]


@pytest.mark.parametrize("header", INVALID)
def test_strict_mode_refuses_and_lenient_mode_reads(header: str) -> None:
    with pytest.raises(ValueError):
        parse(header, strict=True)
    parse(header)


@pytest.mark.parametrize(
    "header",
    [
        "attachment; filename=\"plain.txt\"; filename*=UTF-8''na%C3%AFve.txt",
        "attachment; filename*=UTF-8''na%C3%AFve.txt; filename=\"plain.txt\"",
    ],
)
def test_the_extended_form_takes_precedence_in_either_order(header: str) -> None:
    assert parse(header, strict=True).filename == NAIVE


def test_an_undecodable_extended_value_is_ignored() -> None:
    assert parse("attachment; filename*=UTF-8''bad%ZZ.txt").filename is None


def test_path_information_is_discarded() -> None:
    name = parse('attachment; filename="/etc/report.pdf"', strict=True).filename
    assert safe_filename(name) == "report.pdf"


def test_a_lookalike_parameter_is_not_a_file_name() -> None:
    result = parse("attachment; xfilename=report.pdf", strict=True)
    assert result.filename is None and result.is_attachment


def test_unknown_parameters_are_skipped() -> None:
    assert parse("attachment; colour=blue; filename=report.pdf").filename == "report.pdf"


def test_disposition_types() -> None:
    assert parse("formdata; filename=report.pdf", strict=True).is_attachment
    assert not parse("INLINE", strict=True).is_attachment
