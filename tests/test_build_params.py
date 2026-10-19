"""build writes every legal parameter name: a positional type and a value written as is."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from contentdisp import ContentDisposition, ContentDispositionError, build, parse


def test_a_parameter_named_type_is_a_keyword() -> None:
    assert build("attachment", "a.pdf", **{"type": "x"}) == 'attachment; filename="a.pdf"; type="x"'


def test_keyword_names_still_use_hyphens_for_underscores() -> None:
    assert build("inline", creation_date="d") == 'inline; creation-date="d"'


def test_names_of_a_value_are_written_as_they_are_but_lower_cased() -> None:
    value = ContentDisposition("Attachment", {"My_Param": "x"})
    assert build(value) == 'attachment; my_param="x"'


def test_a_value_comes_before_filename_and_keywords() -> None:
    header = build(ContentDisposition("attachment", {"x_y": "1"}), "a.txt", size="2")
    assert header == 'attachment; x_y="1"; filename="a.txt"; size="2"'


@pytest.mark.parametrize(
    "header",
    [
        "attachment; x_y=1; type=2",
        "attachment; params=p; filename*=UTF-8''%E2%82%AC.txt; filename=e.txt",
        'inline; *=star; a_b_c="q\\"uote"',
        "form-data; name=f; filename*=UTF-8''x",
    ],
)
def test_a_parsed_header_is_rebuilt_from_its_value(header: str) -> None:
    parsed = parse(header, strict=True)
    assert parse(build(parsed), strict=True) == parsed


def test_a_bare_star_is_an_ordinary_name() -> None:
    assert build("attachment", **{"*": "foo"}) == 'attachment; *="foo"'
    assert build(ContentDisposition("attachment", {"*": "foo"})) == 'attachment; *="foo"'


@pytest.mark.parametrize("name", ["a*", "**", "title*"])
def test_an_extended_name_is_refused(name: str) -> None:
    with pytest.raises(ContentDispositionError, match="token, not an extended name"):
        build("attachment", **{name: "x"})
    with pytest.raises(ContentDispositionError, match="token, not an extended name"):
        build(ContentDisposition("attachment", {name: "x"}))


@pytest.mark.parametrize(
    "call",
    [
        lambda: build(ContentDisposition("a", {"FileName": "b"}), "a"),
        lambda: build(ContentDisposition("a", {"x": "1"}), X="2"),
        lambda: build(ContentDisposition("a", {"a-b": "1"}), a_b="2"),
    ],
)
def test_a_name_given_twice_across_arguments_is_refused(call: Callable[[], object]) -> None:
    with pytest.raises(ContentDispositionError, match="more than once"):
        call()


def test_a_value_whose_type_is_not_a_token_is_refused() -> None:
    with pytest.raises(ContentDispositionError, match="must be a token"):
        build(parse('"attachment"; filename=a.txt'))


@pytest.mark.parametrize("bad", [None, b"attachment", {"type": "a"}, ("a", {})], ids=repr)
def test_a_type_of_the_wrong_kind_is_a_type_error(bad: object) -> None:
    with pytest.raises(TypeError, match="str or ContentDisposition"):
        build(bad)  # type: ignore[arg-type]


def test_the_type_is_positional_only() -> None:
    with pytest.raises(TypeError):
        build(type="attachment")  # type: ignore[call-arg]


def test_a_lone_surrogate_is_named_as_such() -> None:
    with pytest.raises(ContentDispositionError, match=r"lone surrogate: '\\ud800'"):
        build("attachment", "\ud800")


def test_a_control_character_is_named_as_such() -> None:
    with pytest.raises(ContentDispositionError, match=r"control character: '\\x00'"):
        build("attachment", "\0")


def test_the_fallback_transliterates_compatibility_characters() -> None:
    # NFKD, not NFD: the "fi" ligature U+FB01 becomes "fi", not "_".
    header = build("attachment", "ﬁle.txt")
    assert header == "attachment; filename=\"file.txt\"; filename*=UTF-8''%EF%AC%81le.txt"
