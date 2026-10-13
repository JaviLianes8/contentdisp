"""The browser test corpus RFC 6266 Appendix D points to, read from its own expectations.

The tc2231 page is not committed. `python scripts/fetch_upstream.py` fetches it as pinned in
tests/upstream/MANIFEST.json; these tests skip until then and fail if the page differs.
Headers, syntax markers and expectation text come from the fetched page; the mapping from
each kind of expectation to an assertion below is written by hand.
"""

from __future__ import annotations

import re
import unicodedata

import pytest

from contentdisp import parse, safe_filename

Cases = dict[str, dict[str, str]]

# RFC 2231 continuations: RFC 6266 does not adopt them, so these expectations are not
# followed and the parameters stay ordinary extension parameters.
CONTINUATIONS = {"attfncont", "attfncontqs", "attfncontenc", "attfncontlz", "attfncontnc"}
CONTINUATIONS |= {"attfnconts1", "attfncontord"}


def _expected_name(case: dict[str, str]) -> str | None:
    match = re.search(r'download the resource as "(.*?)"\.', case["expect"])
    return None if match is None else match.group(1)


def _invalid(case: dict[str, str]) -> bool:
    return bool(case["marker"]) or "Error: parseerror" in case["expect"]


def test_the_page_holds_every_case(tc2231: Cases) -> None:
    assert len(tc2231) == 89


def test_strict_mode_rejects_exactly_what_the_corpus_marks_invalid(tc2231: Cases) -> None:
    for case_id, case in tc2231.items():
        if _invalid(case):
            with pytest.raises(ValueError):
                parse(case["header"], strict=True)
        else:
            assert parse(case["header"], strict=True) is not None, case_id


def test_lenient_mode_never_raises(tc2231: Cases) -> None:
    for case in tc2231.values():
        parse(case["header"])


def test_the_offered_file_name_matches_the_corpus(tc2231: Cases) -> None:
    named = sorted(i for i, c in tc2231.items() if _expected_name(c) and i not in CONTINUATIONS)
    assert len(named) >= 17
    for case_id in named:
        case = tc2231[case_id]
        for strict in (False, True):
            name = parse(case["header"], strict=strict).filename
            assert name is not None, case_id
            # The page shows names as a browser renders them, composed.
            assert unicodedata.normalize("NFC", name) == _expected_name(case), case_id


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


def test_hand_derived_file_names(tc2231: Cases) -> None:
    for case_id, expected in HAND_DERIVED.items():
        for strict in (False, True):
            assert parse(tc2231[case_id]["header"], strict=strict).filename == expected


def test_an_invalid_extended_parameter_is_ignored(tc2231: Cases) -> None:
    ignored = [c for c in tc2231.values() if c["marker"] == "invalid"]
    assert ignored
    for case in ignored:
        assert "should" in case["expect"] and "ignore" in case["expect"]
        assert parse(case["header"]).filename is None


def test_the_extended_form_takes_precedence(tc2231: Cases) -> None:
    for case_id in ["attfnboth", "attfnboth2"]:
        assert "precedence" in tc2231[case_id]["expect"]
        assert parse(tc2231[case_id]["header"], strict=True).filename == "foo-ä.html"


def test_path_information_is_discarded(tc2231: Cases) -> None:
    for case_id in ["attabspath", "attabspathwin", "attwithfn2231abspathdisguised"]:
        name = parse(tc2231[case_id]["header"], strict=True).filename
        assert safe_filename(name) == "foo.html", case_id


def test_unknown_parameters_are_skipped(tc2231: Cases) -> None:
    assert '"foo.html"' in tc2231["attnewandfn"]["expect"]
    assert parse(tc2231["attnewandfn"]["header"], strict=True).filename == "foo.html"


def test_a_lookalike_parameter_is_not_a_file_name(tc2231: Cases) -> None:
    assert "unnamed attachment" in tc2231["attconfusedparam"]["expect"]
    result = parse(tc2231["attconfusedparam"]["header"], strict=True)
    assert result.filename is None and result.is_attachment


def test_disposition_types(tc2231: Cases) -> None:
    assert '"attachment"' in tc2231["dispext"]["expect"]
    assert parse(tc2231["dispext"]["header"], strict=True).is_attachment
    assert not parse(tc2231["inlonly"]["header"], strict=True).is_attachment
    assert parse(tc2231["attonlyucase"]["header"], strict=True).type == "attachment"


def test_dates_are_kept_as_parameters(tc2231: Cases) -> None:
    result = parse(tc2231["attcdate"]["header"], strict=True)
    assert result.params["creation-date"] == "Wed, 12 Feb 1997 16:29:51 -0500"


def test_continuations_are_deliberately_not_joined(tc2231: Cases) -> None:
    for case_id in sorted(CONTINUATIONS):
        assert parse(tc2231[case_id]["header"], strict=True).filename is None, case_id
