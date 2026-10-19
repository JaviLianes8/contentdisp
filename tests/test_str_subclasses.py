"""A str subclass is judged and written by its real characters, whatever it overrides."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from contentdisp import ContentDisposition, ContentDispositionError, build, safe_filename


class _HiddenIter(str):
    def __iter__(self) -> Iterator[str]:
        return iter("clean")


class _FakeStrip(str):
    def strip(self, chars: str | None = None) -> str:
        return "attachment"

    def __iter__(self) -> Iterator[str]:
        return iter("attachment")


class _OtherStr(str):
    def __str__(self) -> str:
        return "other.txt"


class _Default(str):
    pass


class _LyingCase(str):
    """Real characters are a valid token; strip and lower claim a header split."""

    def strip(self, chars: str | None = None) -> str:
        return "attachment\r\nSet-Cookie: x=1"

    def lower(self) -> str:
        return "x\r\nset-cookie: a"


def test_a_name_overriding_iter_cannot_hide_a_newline() -> None:
    hidden = ContentDisposition("inline", {_HiddenIter("x\r\nSet-Cookie: a"): "v"})
    with pytest.raises(ContentDispositionError, match="parameter name must be a token"):
        build(hidden)


@pytest.mark.parametrize("wrap", [lambda t: t, lambda t: ContentDisposition(t)])
def test_a_type_overriding_strip_and_iter_is_checked_by_its_characters(wrap: object) -> None:
    disposition = wrap(_FakeStrip("a\r\nSet-Cookie: x=1"))  # type: ignore[operator]
    with pytest.raises(ContentDispositionError, match="disposition type must be a token"):
        build(disposition)


def test_safe_filename_ignores_an_overridden_str() -> None:
    assert safe_filename(_OtherStr("../../etc/passwd")) == "passwd"
    assert safe_filename(_OtherStr("résumé.pdf")) == "résumé.pdf"


def test_build_checks_the_real_type_not_its_str() -> None:
    with pytest.raises(ContentDispositionError, match="disposition type must be a token"):
        build(_OtherStr("a\r\nb"))
    assert build(_OtherStr("Inline")) == "inline"


def test_build_checks_the_real_name_not_its_str() -> None:
    with pytest.raises(ContentDispositionError, match="parameter name must be a token"):
        build(ContentDisposition("inline", {_OtherStr("a b"): "v"}))
    assert build(ContentDisposition("inline", {_OtherStr("Size"): "1"})) == 'inline; size="1"'


def test_build_checks_and_writes_the_real_value_not_its_str() -> None:
    with pytest.raises(ContentDispositionError, match="control character"):
        build("attachment", _OtherStr("a\r\nb"))
    assert build("attachment", _OtherStr("a.pdf")) == 'attachment; filename="a.pdf"'
    assert build("attachment", x=_OtherStr("€")) == "attachment; x=\"_\"; x*=UTF-8''%E2%82%AC"


@pytest.mark.parametrize("name", [None, "..", "/"])
def test_the_default_comes_back_as_a_plain_str(name: str | None) -> None:
    result = safe_filename(name, default=_Default("dl"))
    assert result == "dl"
    assert type(result) is str
    assert safe_filename(name, default=_OtherStr("dl")) == "dl"


def test_build_writes_the_real_name_not_what_lower_returns() -> None:
    disposition = ContentDisposition("inline", {_LyingCase("Size"): "1"})
    assert build(disposition) == 'inline; size="1"'


@pytest.mark.parametrize("wrap", [lambda t: t, lambda t: ContentDisposition(t)])
def test_build_writes_the_real_type_not_what_strip_or_lower_returns(wrap: object) -> None:
    assert build(wrap(_LyingCase(" Inline "))) == "inline"  # type: ignore[operator]


@pytest.mark.parametrize("name", [None, "..", "/"])
@pytest.mark.parametrize("default", [" dl ", "\tdl\n", "\x00dl\u202e"])
def test_the_default_keeps_its_whitespace_and_controls(name: str | None, default: str) -> None:
    assert safe_filename(name, default=default) == default


class _LowerX(str):
    def lower(self) -> str:
        return "x"

    def strip(self, chars: str | None = None) -> str:
        return "x"


class _ClaimsFormData(str):
    def strip(self, chars: str | None = None) -> str:
        return "form-data"

    def lower(self) -> str:
        return "form-data"


class _ClaimsInline(str):
    def strip(self, chars: str | None = None) -> str:
        return "inline"

    def lower(self) -> str:
        return "inline"


def test_duplicate_names_are_judged_by_their_real_characters() -> None:
    distinct = ContentDisposition("inline", {_LowerX("a"): "1", _LowerX("b"): "2"})
    assert build(distinct) == 'inline; a="1"; b="2"'
    same = ContentDisposition("inline", {_LowerX("A"): "1", _LowerX("a"): "2"})
    with pytest.raises(ContentDispositionError, match="given more than once"):
        build(same)


def test_an_extended_name_is_refused_by_its_real_characters() -> None:
    with pytest.raises(ContentDispositionError, match="not an extended name"):
        build(ContentDisposition("inline", {_LowerX("filename*"): "v"}))


@pytest.mark.parametrize("wrap", [lambda t: t, lambda t: ContentDisposition(t)])
def test_form_data_is_decided_by_the_real_type(wrap: object) -> None:
    with pytest.raises(ContentDispositionError, match="control character"):
        build(wrap(_ClaimsFormData("inline")), "a\r\nb.txt")  # type: ignore[operator]
    real = build(wrap(_ClaimsInline("form-data")), "a\r\nb.txt")  # type: ignore[operator]
    assert real == build("form-data", "a\r\nb.txt")
    assert real.startswith("form-data; ")


@pytest.mark.parametrize("name", [None, "..", "/"])
@pytest.mark.parametrize("default", ["\uff44\uff4c", "\ufb01le", ""])
def test_the_default_is_not_normalized_or_replaced(name: str | None, default: str) -> None:
    assert safe_filename(name, default=default) == default
