"""Strict parsing against the ABNF of the fetched RFCs, compiled by tests/abnf.py.

The rules are cut from RFC 9110 (Appendix A), RFC 8187 (section 3.2.1), RFC 5646
(section 2.1) and RFC 5234 (Appendix B.1, the core rules) as fetched into tests/upstream
(URLs and sha256 in MANIFEST.json); none is retyped. The tests skip until
`python scripts/fetch_upstream.py` has run.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

import abnf
import pytest
from conftest import upstream_text

from contentdisp import ContentDispositionError, build, parse

SAMPLE = [chr(code) for code in range(0x300)] + ["\ud800", "\U0001f600", "\u20ac", "\uffff"]


@dataclass
class Rules:
    http: abnf.Grammar
    ext: abnf.Grammar
    lang: abnf.Grammar


@pytest.fixture(scope="module")
def rules() -> Rules:
    core = abnf.rules(abnf.region(upstream_text("rfc5234.txt"), "B.1.  Core Rules", "B.2."))
    http = abnf.rules(
        abnf.region(upstream_text("rfc9110.txt"), "Appendix A.  Collected ABNF", "Appendix B.")
    )
    lang = abnf.Grammar(
        core,
        abnf.rules(
            abnf.region(
                upstream_text("rfc5646.txt"),
                "The syntax of the language tag in ABNF [RFC5234] is:",
                "Figure 1: Language Tag ABNF",
            )
        ),
    )
    ext = abnf.rules(
        abnf.region(
            upstream_text("rfc8187.txt"),
            "The ABNF for extended parameter values is specified below:",
            "The value part of an extended parameter",
        )
    )
    prose = {"Language-Tag, see [RFC5646], Section 2.1": lang.regex("Language-Tag")}
    return Rules(abnf.Grammar(core, http), abnf.Grammar(core, ext, prose=prose), lang)


def _accepts(header: str | bytes) -> bool:
    try:
        parse(header, strict=True)
    except ContentDispositionError:
        return False
    return True


def test_tchar_is_exactly_the_rfc_9110_rule(rules: Rules) -> None:
    tchar = rules.http.compile("tchar")
    for char in SAMPLE:
        assert _accepts(f"a{char}b") == bool(tchar.fullmatch(char)), repr(char)


def test_whitespace_around_a_semicolon_is_exactly_ows(rules: Rules) -> None:
    tchar, ows = rules.http.compile("tchar"), rules.http.compile("OWS")
    for char in SAMPLE:
        expected = bool(tchar.fullmatch(char) or ows.fullmatch(char))
        assert _accepts(f"a{char};{char}x={char}y{char}") == expected, repr(char)
        if char != "*":  # a name ending in "*" is an extended parameter
            assert _accepts(f"a;x{char}=y") == expected, repr(char)


def test_qdtext_and_quoted_pair_are_exactly_the_rfc_9110_rules(rules: Rules) -> None:
    qdtext, pair = rules.http.compile("qdtext"), rules.http.compile("quoted-pair")
    for code in range(0x100):
        char = chr(code)
        assert _accepts(b'a; x="' + bytes([code]) + b'"') == bool(qdtext.fullmatch(char))
        assert _accepts(b'a; x="\\' + bytes([code]) + b'"') == bool(pair.fullmatch("\\" + char))


def test_decoded_text_beyond_latin_1_counts_as_obs_text(rules: Rules) -> None:
    qdtext, pair = rules.http.compile("qdtext"), rules.http.compile("quoted-pair")
    for char in SAMPLE:
        extended = ord(char) > 0xFF  # documented: a str holds decoded text
        assert _accepts(f'a; x="{char}"') == bool(qdtext.fullmatch(char) or extended)
        assert _accepts(f'a; x="\\{char}"') == bool(pair.fullmatch("\\" + char) or extended)


def test_quoted_strings_unescape_to_their_content(rules: Rules) -> None:
    quoted = rules.http.compile("quoted-string")
    rng = random.Random(9110)
    pieces = ["a", " ", "\t", "\\\\", '\\"', "\\a", ";", "=", ",", "\xe9", "\\\xe9", '"', "\\"]
    checked = 0
    for _ in range(20_000):
        text = '"' + "".join(rng.choice(pieces) for _ in range(rng.randint(0, 6))) + '"'
        if not quoted.fullmatch(text):
            assert not _accepts(f"a; x={text}"), text
            continue
        assert parse(f"a; x={text}", strict=True).params["x"] == re.sub(r"\\(.)", r"\1", text[1:-1])
        checked += 1
    assert checked > 3000


def _ext_grammar_accepts(value: str) -> bool:
    try:
        parse(f"attachment; x*={value}", strict=True)
    except ContentDispositionError as error:
        return "malformed" not in str(error)
    return True


EXT_PIECES = ["UTF-8", "utf-8", "ISO-8859-1", "x-ext", "'", "''", "en", "en-US", "1", "i-hak"]
EXT_PIECES += ["%41", "%e2%82%ac", "%4", "%", "%zz", "a", "!#$&+-.^_`|~", "{", "*", "'%41", "x-a"]
CHARSETS = ["UTF-8", "utf-8", "ISO-8859-1", "x-ext", "{}~", "", "a b", "*", "%"]
LANGUAGES = ["", "en", "en-US", "1", "i-hak", "x-a", "toolongtag", "-", "en_US", "de-CH-1901"]
CHARS = ["", "%41", "a", "!#$&+-.^_`|~", "%4", "%zz", "*", "'", "%e2%82%ac", "{", "%C3"]


def test_ext_values_are_exactly_the_rfc_8187_rule(rules: Rules) -> None:
    ext_value = rules.ext.compile("ext-value")
    rng = random.Random(8187)
    accepted = 0
    for _ in range(30_000):
        value = "".join(rng.choice(EXT_PIECES) for _ in range(rng.randint(1, 6)))
        if rng.random() < 0.6:  # charset ' language ' value, each part possibly broken
            charset, language = rng.choice(CHARSETS), rng.choice(LANGUAGES)
            chars = "".join(rng.choice(CHARS) for _ in range(rng.randint(0, 3)))
            value = f"{charset}'{language}'{chars}"
        expected = bool(ext_value.fullmatch(value))
        assert _ext_grammar_accepts(value) == expected, value
        accepted += expected
    assert accepted > 3000


LANG_PIECES = ["en", "de", "x", "a", "1", "zh", "Hant", "CH", "419", "1901", "abcde", "a1b2c"]
LANG_PIECES += ["i", "u", "co", "phonebk", "abc", "abcd", "123", "q", "ab", "toolongtag", "", "oed"]


def test_language_tags_are_exactly_the_rfc_5646_rule(rules: Rules) -> None:
    tag_rule = rules.lang.compile("Language-Tag")
    rng = random.Random(5646)
    accepted = 0
    for _ in range(20_000):
        tag = "-".join(rng.choice(LANG_PIECES) for _ in range(rng.randint(1, 6)))
        expected = tag == "" or bool(tag_rule.fullmatch(tag))
        assert _accepts(f"attachment; filename*=UTF-8'{tag}'a") == expected, tag
        accepted += expected
    assert accepted > 3000


def test_the_rfc_5646_example_tags(rules: Rules) -> None:
    text = abnf.region(
        upstream_text("rfc5646.txt"), "Appendix A.  Examples of Language Tags", "Appendix B."
    )
    valid, invalid = text.split("Some Invalid Tags:")
    tags = re.compile(r"^ {6}([A-Za-z0-9-]+)(?= \(|$)", re.M)
    assert len(tags.findall(valid)) == 33
    for tag in tags.findall(valid):
        assert _accepts(f"attachment; filename*=UTF-8'{tag}'a"), tag
    # Section 2.1 governs well-formedness only; the repeated singleton of the third tag
    # makes it invalid by section 2.2.6, beyond the grammar RFC 8187 refers to.
    assert tags.findall(invalid) == ["de-419-DE", "a-DE", "ar-a-aaa-b-bbb-a-ccc"]
    results = [_accepts(f"attachment; filename*=UTF-8'{t}'a") for t in tags.findall(invalid)]
    assert results == [False, False, True]


def test_build_leaves_exactly_the_attr_chars_unencoded(rules: Rules) -> None:
    attr_char = rules.ext.compile("attr-char")
    for code in range(0x20, 0x7F):
        char = chr(code)
        extended = build("attachment", "\xe9" + char).split("filename*=UTF-8''", 1)[1]
        assert (extended == "%C3%A9" + char) == bool(attr_char.fullmatch(char)), repr(char)


def test_built_extended_values_follow_the_rfc_8187_rule(rules: Rules) -> None:
    ext_value = rules.ext.compile("ext-value")
    rng = random.Random(3629)
    for _ in range(2000):
        name = "".join(
            chr(rng.choice([rng.randrange(0x20, 0x7F), rng.randrange(0xA0, 0x3000)]))
            for _ in range(8)
        )
        header = build("attachment", name)
        if "filename*=" in header:
            assert ext_value.fullmatch(header.split("filename*=", 1)[1]), header
        assert parse(header, strict=True).filename == name
