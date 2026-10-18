"""The complete promise of every public name: signature, result and failure types."""

from __future__ import annotations

import copy
import dataclasses
import doctest
import inspect
import pickle
from collections.abc import Callable

import pytest

import contentdisp
from contentdisp import ContentDisposition, ContentDispositionError, build, parse, safe_filename

SIGNATURES = {
    "parse": "(header: 'str | bytes', *, strict: 'bool' = False) -> 'ContentDisposition'",
    "build": "(type: 'str', filename: 'str | None' = None, **params: 'str') -> 'str'",
    "safe_filename": "(name: 'str | None', *, default: 'str' = 'download', "
    "max_bytes: 'int' = 255) -> 'str'",
}


@pytest.mark.parametrize("name", sorted(SIGNATURES))
def test_function_signatures_are_pinned(name: str) -> None:
    assert str(inspect.signature(getattr(contentdisp, name))) == SIGNATURES[name]


def test_the_error_signature_is_pinned() -> None:
    signature = inspect.signature(ContentDispositionError.__init__)
    assert str(signature) == "(self, message: 'str', *, position: 'int | None' = None) -> 'None'"


def test_the_value_is_a_frozen_dataclass_with_pinned_fields() -> None:
    fields = [
        (f.name, f.default, f.default_factory) for f in dataclasses.fields(ContentDisposition)
    ]
    assert fields == [
        ("type", dataclasses.MISSING, dataclasses.MISSING),
        ("params", dataclasses.MISSING, dict),
    ]
    value = ContentDisposition("attachment", {"filename": "a"})
    with pytest.raises(dataclasses.FrozenInstanceError):
        value.type = "inline"  # type: ignore[misc]
    assert ContentDisposition("inline").params == {}
    assert ContentDisposition("a").params is not ContentDisposition("a").params


def test_the_value_keeps_the_dict_it_is_given_and_is_not_hashable() -> None:
    params = {"filename": "a"}
    value = ContentDisposition("attachment", params)
    assert value.params is params
    with pytest.raises(TypeError):
        hash(value)


def test_values_compare_copy_pickle_and_replace() -> None:
    value = parse("attachment; filename*=UTF-8''%E2%82%AC.txt; size=1")
    assert value == ContentDisposition("attachment", {"filename": "\u20ac.txt", "size": "1"})
    assert value != ContentDisposition("inline", value.params)
    for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
        assert pickle.loads(pickle.dumps(value, protocol)) == value
    assert copy.deepcopy(value) == value and copy.copy(value) == value
    assert dataclasses.replace(value, type="inline").is_attachment is False
    assert dataclasses.asdict(value) == {"type": "attachment", "params": value.params}


def test_every_public_name_is_documented_with_an_example() -> None:
    for name in contentdisp.__all__:
        assert ">>> " in (inspect.getdoc(getattr(contentdisp, name)) or ""), name
    for member in ("filename", "is_attachment"):
        assert ">>> " in (inspect.getdoc(getattr(ContentDisposition, member)) or ""), member


def test_doctests_of_the_public_classes_are_found_at_the_package_top() -> None:
    found = [test for test in doctest.DocTestFinder().find(contentdisp) if test.examples]
    names = {test.name.removeprefix("contentdisp.") for test in found}
    expected = {"ContentDisposition", "ContentDisposition.filename"}
    assert expected | {"ContentDisposition.is_attachment", "ContentDispositionError"} <= names


def test_public_classes_live_at_the_package_top() -> None:
    for cls in (ContentDisposition, ContentDispositionError):
        assert cls.__module__ == "contentdisp"
        assert f"contentdisp.{cls.__name__}" in repr(cls)
    assert b"_model" not in pickle.dumps(ContentDisposition("a"))
    assert b"_errors" not in pickle.dumps(ContentDispositionError("x", position=1))


def test_the_error_is_a_value_error_with_a_position_that_pickles() -> None:
    error = ContentDispositionError("bad", position=3)
    assert isinstance(error, ValueError) and error.position == 3 and str(error) == "bad"
    assert ContentDispositionError("x").position is None
    for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
        again = pickle.loads(pickle.dumps(error, protocol))
        assert (type(again), str(again), again.position) == (ContentDispositionError, "bad", 3)
    assert copy.copy(error).position == 3


TYPE_ERRORS: list[Callable[[], object]] = [
    lambda: parse(None),  # type: ignore[arg-type]
    lambda: parse(bytearray(b"inline")),  # type: ignore[arg-type]
    lambda: parse(memoryview(b"inline")),  # type: ignore[arg-type]
    lambda: build(None),  # type: ignore[arg-type]
    lambda: build(b"attachment"),  # type: ignore[arg-type]
    lambda: build("attachment", 3),  # type: ignore[arg-type]
    lambda: build("attachment", b"a"),  # type: ignore[arg-type]
    lambda: build("attachment", title=None),  # type: ignore[arg-type]
    lambda: safe_filename(b"a"),  # type: ignore[arg-type]
    lambda: safe_filename(3),  # type: ignore[arg-type]
    lambda: safe_filename("a", default=None),  # type: ignore[arg-type]
    lambda: safe_filename(None, default=b"x"),  # type: ignore[arg-type]
    lambda: safe_filename("a", max_bytes="9"),  # type: ignore[arg-type]
    lambda: safe_filename("a", max_bytes=9.0),  # type: ignore[arg-type]
    lambda: safe_filename("a", max_bytes=True),
    lambda: ContentDisposition(None),  # type: ignore[arg-type]
    lambda: ContentDisposition("a", [("x", "y")]),  # type: ignore[arg-type]
    lambda: ContentDisposition("a", {"x": 1}),  # type: ignore[dict-item]
    lambda: ContentDisposition("a", {1: "x"}),  # type: ignore[dict-item]
]


@pytest.mark.parametrize("call", TYPE_ERRORS)
def test_wrong_argument_types_raise_type_error(call: Callable[[], object]) -> None:
    with pytest.raises(TypeError):
        call()


VALUE_ERRORS: list[Callable[[], object]] = [
    lambda: parse("attachment; filename=a b", strict=True),
    lambda: build(""),
    lambda: build("attach ment"),
    lambda: build("attachment", "a\r\nb"),
    lambda: build("attachment", **{"a b": "x"}),
    lambda: build("attachment", **{"title*": "x"}),
    lambda: build("attachment", "a", **{"FILENAME": "b"}),
    lambda: build("attachment", "a\ud800"),
    lambda: safe_filename("a", max_bytes=0),
    lambda: safe_filename(None, max_bytes=-1),
]


@pytest.mark.parametrize("call", VALUE_ERRORS)
def test_invalid_values_raise_the_library_error(call: Callable[[], object]) -> None:
    with pytest.raises(ContentDispositionError) as caught:
        call()
    assert caught.value.position is None or caught.value.position >= 0


def test_only_parse_errors_carry_a_position() -> None:
    for call in VALUE_ERRORS[1:]:
        with pytest.raises(ContentDispositionError) as caught:
            call()
        assert caught.value.position is None
