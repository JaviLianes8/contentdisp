"""Positions of an unclosed language part, against a brute-force RFC 5646 prefix oracle."""

from __future__ import annotations

import itertools

import pytest
from langtag_oracle import GRANDFATHERED, language_tag_ok

from contentdisp import ContentDispositionError, parse

# Letters other than "x" play the same part in the tag grammar outside the grandfathered
# tags, so tags over these characters (up to 9 long) give every start of up to 4.
ALPHABET = "ax0-"


def _starts() -> set[str]:
    tags = [
        "".join(chars)
        for size in range(1, 10)
        for chars in itertools.product(ALPHABET, repeat=size)
        if language_tag_ok("".join(chars))
    ]
    return {tag[:end] for tag in [*tags, *GRANDFATHERED] for end in range(len(tag) + 1)}


STARTS = _starts()
LANGUAGES = [
    "".join(chars) for size in range(1, 5) for chars in itertools.product(ALPHABET, repeat=size)
]


def test_an_unclosed_language_is_reported_where_no_tag_can_continue() -> None:
    for language in LANGUAGES:
        header = f"attachment; filename*=UTF-8'{language}"
        viable = max(end for end in range(len(language) + 1) if language[:end] in STARTS)
        with pytest.raises(ContentDispositionError) as caught:
            parse(header, strict=True)
        if viable < len(language):
            message, position = "malformed language tag", 28 + viable
        else:
            message, position = "malformed extended value", len(header)
        assert caught.value.position == position, language
        assert str(caught.value).startswith(message), language
        assert parse(header).params == {}


@pytest.mark.parametrize("tag", sorted(GRANDFATHERED))
def test_every_start_of_a_grandfathered_tag_can_continue(tag: str) -> None:
    for end in range(1, len(tag) + 1):
        header = f"attachment; filename*=UTF-8'{tag[:end].upper()}"
        with pytest.raises(ContentDispositionError, match="malformed extended value"):
            parse(header, strict=True)
