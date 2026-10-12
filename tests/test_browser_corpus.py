"""The browser test corpus RFC 6266 Appendix D points to, read from its own expectations.

tests/fixtures/tc2231.json was produced by scripts/extract_tc2231.py from
http://greenbytes.de/tech/tc2231/ as fetched on 2026-10-12 (page hash in the fixture).
Headers, syntax markers and expectation sentences are the page's own; the mapping from
each kind of sentence to an assertion below is written by hand.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import pytest

from contentdisp import parse, safe_filename

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "tc2231.json").read_text("utf-8"))
CASES: dict[str, dict[str, Any]] = {case["id"]: case for case in FIXTURE["cases"]}

# RFC 2231 continuations: RFC 6266 does not adopt them, so these expectations are not
# followed and the parameters stay ordinary extension parameters.
CONTINUATIONS = {"attfncont", "attfncontqs", "attfncontenc", "attfncontlz", "attfncontnc"}
CONTINUATIONS |= {"attfnconts1", "attfncontord"}


def _expected_name(case: dict[str, Any]) -> str | None:
    match = re.search(r'download the resource as "(.*?)"\.', case["expect"])
    return None if match is None else match.group(1)


def _invalid(case: dict[str, Any]) -> bool:
    return bool(case["marker"]) or "Error: parseerror" in case["expect"]


def test_the_fixture_is_the_page_fetched_for_this_round() -> None:
    assert FIXTURE["source"] == "http://greenbytes.de/tech/tc2231/"
    assert FIXTURE["sha256"] == "341d2916ce946f670567f40ce570115d08873f51794aac13ad62047b7e7a6896"
    assert len(CASES) == 89


@pytest.mark.parametrize("case_id", sorted(CASES))
def test_strict_mode_rejects_exactly_what_the_corpus_marks_invalid(case_id: str) -> None:
    case = CASES[case_id]
    if _invalid(case):
        with pytest.raises(ValueError):
            parse(case["header"], strict=True)
    else:
        parse(case["header"], strict=True)


@pytest.mark.parametrize("case_id", sorted(CASES))
def test_lenient_mode_never_raises(case_id: str) -> None:
    parse(CASES[case_id]["header"])


NAMED = sorted(i for i, c in CASES.items() if _expected_name(c) and i not in CONTINUATIONS)


@pytest.mark.parametrize("case_id", NAMED)
def test_the_offered_file_name_matches_the_corpus(case_id: str) -> None:
    case = CASES[case_id]
    expected = _expected_name(case)
    for strict in (False, True):
        name = parse(case["header"], strict=strict).filename
        assert name is not None
        # The page shows names as a browser renders them, composed.
        assert unicodedata.normalize("NFC", name) == expected


def test_enough_cases_name_a_file() -> None:
    assert len(NAMED) >= 17


# Cases whose page text names no file; the expected value is derived by hand from the
# RFC 6266 grammar (quoted-string unescaping, no percent or RFC 2047 decoding).
HAND_DERIVED = {
    "attwithasciifilename25": "0000000000111111111122222",
    "attwithasciifnescapedquote": '"quoting" tested.html',
    "attwithquotedsemicolon": "Here's a semicolon;.html",
    "attwithfntokensq": "'foo.bar'",
    "attwithfilenamepctandiso": "ä-%41.html",
    "attwithfn2231dpct": "A-%41.html",
    "attrfc2047quoted": "=?ISO-8859-1?Q?foo-=E4.html?=",
    "attwithasciifilenamenq": "foo.html",
}


@pytest.mark.parametrize("case_id", sorted(HAND_DERIVED))
def test_hand_derived_file_names(case_id: str) -> None:
    for strict in (False, True):
        assert parse(CASES[case_id]["header"], strict=strict).filename == HAND_DERIVED[case_id]


IGNORED_PARAMETER = sorted(i for i, c in CASES.items() if c["marker"] == "invalid")


@pytest.mark.parametrize("case_id", IGNORED_PARAMETER)
def test_an_invalid_extended_parameter_is_ignored(case_id: str) -> None:
    assert "should" in CASES[case_id]["expect"] and "ignore" in CASES[case_id]["expect"]
    assert parse(CASES[case_id]["header"]).filename is None


@pytest.mark.parametrize("case_id", ["attfnboth", "attfnboth2"])
def test_the_extended_form_takes_precedence(case_id: str) -> None:
    assert "should take precedence" in CASES[case_id]["expect"]
    assert parse(CASES[case_id]["header"], strict=True).filename == "foo-ä.html"


@pytest.mark.parametrize(
    "case_id", ["attabspath", "attabspathwin", "attwithfn2231abspathdisguised"]
)
def test_path_information_is_discarded(case_id: str) -> None:
    name = parse(CASES[case_id]["header"], strict=True).filename
    assert safe_filename(name) == "foo.html"


def test_unknown_parameters_are_skipped() -> None:
    assert 'thus "foo.html" be used' in CASES["attnewandfn"]["expect"]
    assert parse(CASES["attnewandfn"]["header"], strict=True).filename == "foo.html"


def test_a_lookalike_parameter_is_not_a_file_name() -> None:
    assert CASES["attconfusedparam"]["expect"] == "Should be treated as unnamed attachment."
    result = parse(CASES["attconfusedparam"]["header"], strict=True)
    assert result.filename is None and result.is_attachment


def test_disposition_types() -> None:
    assert 'equivalent to using "attachment"' in CASES["dispext"]["expect"]
    assert parse(CASES["dispext"]["header"], strict=True).is_attachment
    assert not parse(CASES["inlonly"]["header"], strict=True).is_attachment
    assert parse(CASES["attonlyucase"]["header"], strict=True).type == "attachment"


def test_dates_are_kept_as_parameters() -> None:
    result = parse(CASES["attcdate"]["header"], strict=True)
    assert result.params["creation-date"] == "Wed, 12 Feb 1997 16:29:51 -0500"


@pytest.mark.parametrize("case_id", sorted(CONTINUATIONS))
def test_continuations_are_deliberately_not_joined(case_id: str) -> None:
    assert parse(CASES[case_id]["header"], strict=True).filename is None
