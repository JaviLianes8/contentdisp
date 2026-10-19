"""Runs of non-starters are bounded the same way whatever shape the input takes."""

from __future__ import annotations

import unicodedata
from collections.abc import Iterator

import pytest

from contentdisp import ContentDispositionError, build, safe_filename


def test_a_compatibility_decomposition_starts_the_run() -> None:
    # U+00A8 is NFKD space + U+0308, so the run is U+0308, 29 x U+0301 and U+0316: the
    # 31st mark (U+0316) is the one dropped. Counting on NFD would keep it instead.
    result = safe_filename("a\u00a8" + "\u0301" * 29 + "\u0316")
    assert result == "a \u0308" + "\u0301" * 29


def test_spacing_marks_are_starters_and_never_cut() -> None:
    # U+093F is a spacing mark (category Mc) of combining class 0, so it ends a run.
    assert unicodedata.combining("\u093f") == 0
    assert safe_filename("a" + "\u093f" * 40) == "a" + "\u093f" * 40


class _LyingAscii(str):
    def isascii(self) -> bool:
        return True


class _HiddenControl(str):
    def __iter__(self) -> Iterator[str]:
        return iter("clean")


def test_a_str_subclass_cannot_skip_normalisation() -> None:
    assert safe_filename(_LyingAscii("..\uff0f..\uff0fetc\uff0fpasswd")) == "passwd"
    assert safe_filename(_LyingAscii("a\uff3c..\uff3cb")) == "b"


def test_the_result_is_a_plain_str() -> None:
    assert type(safe_filename(_LyingAscii("report.pdf"))) is str


def test_a_str_subclass_cannot_hide_a_control_character() -> None:
    with pytest.raises(ContentDispositionError, match="control character"):
        build("attachment", _HiddenControl("a\r\nSet-Cookie: x=1"))
    with pytest.raises(ContentDispositionError, match="control character"):
        build("attachment", x=_HiddenControl("a\rb"))
