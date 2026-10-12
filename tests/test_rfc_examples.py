"""Ground truth copied from the RFC texts as fetched on 2026-10-12.

RFC 6266: https://www.rfc-editor.org/rfc/rfc6266.txt
(sha256 2887d464e7a2a15877aba5d54b2e8e0c06c32294c44c9d95eb8940069ab43d33)
RFC 8187: https://www.rfc-editor.org/rfc/rfc8187.txt
(sha256 af50e65257dc16a27fa85e25ef68d49c8fa2a4abc21094a00469462c8cb89b53)

Field values are copied character for character. Where the RFC folds a value over two
lines, the line break and the indentation are joined into a single space, which is what
a recipient does with obsolete line folding (RFC 9110 5.5). The expected results are
the ones the surrounding prose states.
"""

from __future__ import annotations

import pytest

from contentdisp import parse, safe_filename

# RFC 6266 section 5: field value, disposition type, file name the prose names.
RFC6266_SECTION_5 = [
    ("Attachment; filename=example.html", "attachment", "example.html"),
    ('INLINE; FILENAME= "an example.html"', "inline", "an example.html"),
    ("attachment; filename*= UTF-8''%e2%82%ac%20rates", "attachment", "€ rates"),
    (
        "attachment; filename=\"EURO rates\"; filename*=utf-8''%e2%82%ac%20rates",
        "attachment",
        "€ rates",
    ),
]

# RFC 8187 3.2.3 and 4.2. The examples use a made-up field "foo" whose value is "bar"
# followed by parameters; the parameter syntax is the one Content-Disposition uses.
RFC8187_EXAMPLES = [
    ("bar; title=Economy", "Economy"),
    ('bar; title="US-$ rates"', "US-$ rates"),
    ("bar; title*=utf-8'en'%C2%A3%20rates", "£ rates"),
    ("bar; title*=UTF-8''%c2%a3%20and%20%e2%82%ac%20rates", "£ and € rates"),
    (
        "bar; title=\"EURO exchange rates\"; title*=utf-8''%e2%82%ac%20exchange%20rates",
        "€ exchange rates",
    ),
]


@pytest.mark.parametrize(("header", "kind", "filename"), RFC6266_SECTION_5)
@pytest.mark.parametrize("strict", [True, False])
def test_rfc6266_examples(header: str, kind: str, filename: str, strict: bool) -> None:
    result = parse(header, strict=strict)
    assert (result.type, result.filename) == (kind, filename)


@pytest.mark.parametrize(("header", "title"), RFC8187_EXAMPLES)
@pytest.mark.parametrize("strict", [True, False])
def test_rfc8187_examples(header: str, title: str, strict: bool) -> None:
    assert parse(header, strict=strict).params["title"] == title


def test_rfc6266_section_4_3_names_the_etc_passwd_example() -> None:
    # Section 4.3: never trust folder information, keep only the last path segment.
    assert safe_filename("/etc/passwd") == "passwd"


@pytest.mark.parametrize("name", [".", "..", "~", "|"])
def test_rfc6266_section_4_3_special_names_are_substituted(name: str) -> None:
    # Section 4.3 lists ".", "..", "~" and "|" as names to ignore or substitute.
    assert safe_filename(name) in ("download", "_")
