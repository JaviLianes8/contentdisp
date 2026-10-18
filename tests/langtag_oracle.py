"""A hand-written check of RFC 5646 section 2.1 language tags, for the oracle tests.

It walks the subtags one by one (type by length and content, as section 2.1 explains)
instead of using a regular expression, so it shares nothing with the library's check.
https://www.rfc-editor.org/rfc/rfc5646.txt; the grandfathered list is copied from the
ABNF there.
"""

from __future__ import annotations

GRANDFATHERED = {
    "en-gb-oed",
    "i-ami",
    "i-bnn",
    "i-default",
    "i-enochian",
    "i-hak",
    "i-klingon",
    "i-lux",
    "i-mingo",
    "i-navajo",
    "i-pwn",
    "i-tao",
    "i-tay",
    "i-tsu",
    "sgn-be-fr",
    "sgn-be-nl",
    "sgn-ch-de",
    "art-lojban",
    "cel-gaulish",
    "no-bok",
    "no-nyn",
    "zh-guoyu",
    "zh-hakka",
    "zh-min",
    "zh-min-nan",
    "zh-xiang",
}


def _alnum(text: str) -> bool:
    return text.isascii() and text.isalnum()


def language_tag_ok(tag: str) -> bool:
    """True when ``tag`` is a well-formed Language-Tag."""
    if tag.lower() in GRANDFATHERED:
        return True
    subtags = tag.lower().split("-")
    if not all(subtag and len(subtag) <= 8 and _alnum(subtag) for subtag in subtags):
        return False
    if subtags[0] == "x":
        return len(subtags) > 1
    first = subtags[0]
    if not first.isalpha() or len(first) < 2:
        return False
    i = 1
    if len(first) <= 3:  # up to three extlang subtags
        while i < len(subtags) and i <= 3 and len(subtags[i]) == 3 and subtags[i].isalpha():
            i += 1
    if i < len(subtags) and len(subtags[i]) == 4 and subtags[i].isalpha():  # script
        i += 1
    if i < len(subtags) and (
        (len(subtags[i]) == 2 and subtags[i].isalpha())
        or (len(subtags[i]) == 3 and subtags[i].isdigit())
    ):  # region
        i += 1
    while i < len(subtags) and (
        len(subtags[i]) >= 5 or (len(subtags[i]) == 4 and subtags[i][0].isdigit())
    ):  # variants
        i += 1
    while i < len(subtags) and len(subtags[i]) == 1 and subtags[i] != "x":  # extensions
        i += 1
        start = i
        while i < len(subtags) and len(subtags[i]) >= 2:
            i += 1
        if i == start:
            return False
    if i < len(subtags) and subtags[i] == "x":  # private use runs to the end
        return i + 1 < len(subtags)
    return i == len(subtags)
