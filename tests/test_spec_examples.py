"""Examples and rules cut from the fetched RFC 6266, RFC 8187, RFC 7578 and WHATWG HTML.

Every header below is read out of the fetched text (URLs and sha256 in
tests/upstream/MANIFEST.json), never retyped; a value the text folds over two lines is
joined with one space, as a recipient unfolds obsolete line folding (RFC 9110 5.5). The
expected results are those the surrounding prose states; extended values are also
decoded with Python's own urllib.parse.unquote as an independent check.
"""

from __future__ import annotations

import html
import re
import unicodedata
from urllib.parse import unquote

import abnf
from conftest import read_upstream, upstream_text
from test_rfc_examples import RFC6266_SECTION_5, RFC8187_EXAMPLES

from contentdisp import build, parse, safe_filename


def _fields(text: str, name: str) -> list[str]:
    """Every ``name: value`` example of a region, continuation lines joined with a space."""
    found = []
    for match in re.finditer(rf"^( +){re.escape(name)}: ?(.*)\n((?:\1 +\S.*\n)*)", text, re.M):
        lines = [match.group(2), *match.group(3).splitlines()]
        found.append(" ".join(line.strip() for line in lines))
    return found


def _decoded(ext_value: str) -> str:
    charset, _, rest = ext_value.partition("'")
    return unquote(rest.partition("'")[2], encoding=charset.lower(), errors="strict")


def test_rfc_6266_section_5_examples() -> None:
    text = abnf.region(upstream_text("rfc6266.txt"), "5.  Examples", "6.  Internationalization")
    headers = _fields(text, "Content-Disposition")
    assert headers == [header for header, _, _ in RFC6266_SECTION_5]  # the offline copies
    stated = re.findall(r'filename of\s+"([^"]+)"|the filename "([^"]+)"', text)
    plain = [first or second for first, second in stated]
    assert plain == ["example.html", "an example.html"]
    expected = [
        ("attachment", plain[0]),
        ("inline", plain[1]),
        ("attachment", _decoded(headers[2].split("filename*=")[1].strip())),
        ("attachment", _decoded(headers[3].split("filename*=")[1].strip())),
    ]
    assert "U+20AC (EURO SIGN)" in text and expected[2][1] == expected[3][1] == "\u20ac rates"
    for header, (disposition, filename) in zip(headers, expected, strict=True):
        for strict in (True, False):
            result = parse(header, strict=strict)
            assert (result.type, result.filename) == (disposition, filename), header


def test_rfc_8187_examples() -> None:
    rfc = upstream_text("rfc8187.txt")
    headers = _fields(abnf.region(rfc, "3.2.3.  Examples", "3.3.  Language"), "foo")
    headers += _fields(abnf.region(rfc, "4.2.  Error Handling", "5.  Security"), "foo")
    assert headers == [header for header, _ in RFC8187_EXAMPLES]  # the offline copies
    expected = ["Economy", "US-$ rates", "\xa3 rates", "\xa3 and \u20ac rates"]
    expected.append("\u20ac exchange rates")
    for header, title in zip(headers, expected, strict=True):
        if "title*=" in header:
            assert _decoded(header.split("title*=")[1]) == title
        for strict in (True, False):
            assert parse(header, strict=strict).params["title"] == title, header


def test_rfc_7578_form_data_example_round_trips() -> None:
    text = abnf.region(upstream_text("rfc7578.txt"), "4.2.  Content-Disposition", "4.3.  Multiple")
    (header,) = _fields(text, "Content-Disposition")
    assert parse(header, strict=True).params == {"name": "user"}
    assert build("form-data", name="user") == header
    assert '"filename*" parameter to the Content-Disposition header field, MUST' in " ".join(
        text.split()
    )
    assert "*" not in build("form-data", "\u20ac.txt", name="f")


def test_rfc_6266_section_4_3_rules_for_file_names() -> None:
    text = " ".join(abnf.region(upstream_text("rfc6266.txt"), "4.3.  Disposition", "4.4.").split())
    separators = re.search(r'path separator characters "(.)" and "(.)"', text)
    assert separators is not None and set(separators.groups()) == {"\\", "/"}
    for separator in separators.groups():
        assert safe_filename(f"..{separator}dir{separator}name.txt") == "name.txt"
    assert '"/etc/passwd"' in text and safe_filename("/etc/passwd") == "passwd"
    special = re.search(r"shell commands, such as (.*?), and also device names", text)
    assert special is not None
    names = re.findall(r'"([^"]+)"', special.group(1))
    assert names == [".", "..", "~", "|"]
    for name in names:
        assert safe_filename(name) in ("download", "_")
    assert "control characters and leading and trailing whitespace" in text
    controls = [chr(code) for code in range(0x110000) if unicodedata.category(chr(code)) == "Cc"]
    assert safe_filename(" \t" + "".join(controls) + "a.txt \n") == "a.txt"


def test_form_data_escapes_are_the_whatwg_ones_plus_backslash() -> None:
    page = read_upstream("whatwg-html.html").decode("utf-8")
    start = page.index("For field names and filenames for file fields")
    sentence = " ".join(html.unescape(re.sub(r"<[^>]+>", "", page[start : start + 600])).split())
    rule = re.findall(
        r"0x([0-9A-F]{2}) \([^)]+\)(?: bytes)? with (?:the byte sequence )?`(%..)`", sentence
    )
    escapes = {chr(int(code, 16)): sequence for code, sequence in rule}
    assert escapes == {"\n": "%0A", "\r": "%0D", '"': "%22"}
    assert "The user agent must not perform any other escapes." in sentence
    for code in [9, 10, 13, *range(0x20, 0x7F)]:
        char = chr(code)
        value = build("form-data", f"a{char}b", name="f").split('"')[1]
        written = escapes.get(char, "%5C" if char == "\\" else char)
        assert value == f"a{written}b", repr(char)
