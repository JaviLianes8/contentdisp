"""Arguments whose class lies: str and bytes subclasses, and a class whose name raises."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from contentdisp import ContentDisposition, ContentDispositionError, build, parse, safe_filename


class _NoReplace(str):
    def replace(self, *args: object, **kwargs: object) -> str:
        return self


class _OddDecode(bytes):
    def decode(self, *args: object, **kwargs: object) -> str:
        return 42  # type: ignore[return-value]


class _OddIndex(str):
    def __getitem__(self, key: object) -> str:
        return "a"


def test_lenient_parsing_replaces_cr_and_lf_whatever_the_str_class() -> None:
    header = _NoReplace('attachment; filename="a\r\nSet-Cookie: evil=1"')
    assert parse(header).filename == "a  Set-Cookie: evil=1"
    assert type(parse(header).filename) is str


def test_parsing_reads_bytes_as_latin_1_whatever_the_bytes_class() -> None:
    assert parse(_OddDecode(b"attachment; filename=caf\xe9")).filename == "caf\xe9"
    assert parse(_OddDecode(b"inline"), strict=True).type == "inline"


def test_strict_parsing_reads_the_real_characters() -> None:
    with pytest.raises(ContentDispositionError) as caught:
        parse(_OddIndex("attachment; filename=a b"), strict=True)
    assert caught.value.position == 23


class _Meta(type):
    @property
    def __name__(cls) -> str:  # type: ignore[override]
        raise RuntimeError("boom")


class _Nameless(metaclass=_Meta):
    pass


CALLS: list[Callable[[object], object]] = [
    lambda value: parse(value),  # type: ignore[arg-type]
    lambda value: build(value),  # type: ignore[arg-type]
    lambda value: build("attachment", value),  # type: ignore[arg-type]
    lambda value: safe_filename(value),  # type: ignore[arg-type]
    lambda value: safe_filename("a", default=value),  # type: ignore[arg-type]
    lambda value: safe_filename("a", max_bytes=value),  # type: ignore[arg-type]
    lambda value: ContentDisposition(value),  # type: ignore[arg-type]
    lambda value: ContentDisposition("a", value),  # type: ignore[arg-type]
]


@pytest.mark.parametrize("call", CALLS)
def test_a_class_whose_name_raises_still_gets_a_type_error(
    call: Callable[[object], object],
) -> None:
    with pytest.raises(TypeError, match="_Nameless"):
        call(_Nameless())


@pytest.mark.parametrize("call", CALLS[:2])
def test_a_class_name_of_the_message_limit_is_shown_whole(
    call: Callable[[object], object],
) -> None:
    with pytest.raises(TypeError) as caught:
        call(type("A" * 40, (), {})())
    assert f" {'A' * 40}" in str(caught.value)
    assert "..." not in str(caught.value)


@pytest.mark.parametrize("call", CALLS[:2])
def test_a_longer_class_name_is_cut_to_the_message_limit(
    call: Callable[[object], object],
) -> None:
    with pytest.raises(TypeError) as caught:
        call(type("B" * 41, (), {})())
    assert f" {'B' * 37}..." in str(caught.value)
    assert "B" * 38 not in str(caught.value)
