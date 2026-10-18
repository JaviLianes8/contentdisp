"""PyPI 0.2.1 as an oracle: 1.0.0 answers the same, except for the documented changes.

Set CONTENTDISP_V021 to a folder holding the 0.2.1 package (the unpacked wheel:
`pip download contentdisp==0.2.1 --no-deps` and unzip it); those tests skip otherwise.
The pickle test needs nothing: its bytes were written by the 0.2.1 release.
"""

from __future__ import annotations

import importlib.util
import os
import pickle
import random
import sys
import unicodedata
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest
from generators import header, noise, unicode_text

import contentdisp
from contentdisp import ContentDisposition, ContentDispositionError
from contentdisp._grammar import is_token

# pickle.dumps(parse("attachment; filename*=UTF-8''%E2%82%AC.txt; size=3"), 4) as written
# by contentdisp 0.2.1 from PyPI on 2026-10-18; it names contentdisp._model.
PICKLE_0_2_1 = bytes.fromhex(
    "80049576000000000000008c12636f6e74656e74646973702e5f6d6f64656c948c12436f6e74656e7444"
    "6973706f736974696f6e9493942981947d94288c0474797065948c0a6174746163686d656e74948c0670"
    "6172616d73947d94288c0473697a65948c0133948c0866696c656e616d65948c07e282ac2e7478749475"
    "75622e"
)


def test_a_pickle_written_by_0_2_1_still_loads() -> None:
    value = pickle.loads(PICKLE_0_2_1)
    assert type(value) is ContentDisposition
    assert value == ContentDisposition("attachment", {"size": "3", "filename": "\u20ac.txt"})


@pytest.fixture(scope="module")
def old() -> ModuleType:
    folder = os.environ.get("CONTENTDISP_V021")
    if not folder:
        pytest.skip("set CONTENTDISP_V021 to the unpacked 0.2.1 release")
    init = Path(folder) / "contentdisp" / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        "contentdisp_v021", init, submodule_search_locations=[str(init.parent)]
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["contentdisp_v021"] = module
    spec.loader.exec_module(module)
    assert module.__version__ == "0.2.1"
    return module


def _first_segment_name(text: str) -> str | None:
    """The parameter name 1.0.0 reads from a header without a type, if any."""
    for char in "\r\n\0":
        text = text.replace(char, " ")
    name, equals, _ = text.partition("=")
    name = name.strip(" \t")
    return name.lower() if equals and is_token(name) else None


def _removable(char: str) -> bool:
    """A character safe_filename removes (control, surrogate or format but a joiner)."""
    category = unicodedata.category(char)
    return category in ("Cc", "Cs") or (category == "Cf" and char not in "\u200c\u200d")


@pytest.mark.parametrize("strict", [False, True])
def test_parsing_agrees_with_0_2_1_except_where_documented(old: ModuleType, strict: bool) -> None:
    rng = random.Random(21)
    compared = 0
    for _ in range(20_000):
        text = rng.choice([noise, header])(rng)
        try:
            before = old.parse(text, strict=strict)
        except ValueError:
            with pytest.raises(ValueError):
                contentdisp.parse(text, strict=strict)
            continue
        try:
            after = contentdisp.parse(text, strict=strict)
        except ContentDispositionError as error:
            assert strict and "malformed language tag" in str(error), text  # stricter check
            continue
        assert after.type == before.type, text
        extra = {k for k, v in after.params.items() if before.params.get(k) != v}
        assert not strict or not extra, text
        assert extra <= {_first_segment_name(text)}, text
        missing = set(before.params) - set(after.params)
        assert all(not is_token(name) or "\u212a" in text for name in missing), text
        if is_token(after.type):
            assert after.is_attachment == before.is_attachment, text
        else:
            assert not after.is_attachment
        compared += 1
    assert compared > 7000


def test_building_agrees_with_0_2_1(old: ModuleType) -> None:
    rng = random.Random(22)
    for _ in range(5000):
        kind = rng.choice(["attachment", "form-data", "x y", "INLINE", ""])
        name, title = unicode_text(rng), unicode_text(rng)
        outcomes = []
        for module in (old, contentdisp):
            try:
                outcomes.append(module.build(kind, name, title=title))
            except (TypeError, ValueError) as error:
                outcomes.append(type(error).__mro__[-3].__name__)
        assert outcomes[0] == outcomes[1], (kind, name, title)


def test_safe_names_agree_with_0_2_1_unless_its_result_was_not_normalised(old: ModuleType) -> None:
    rng = random.Random(23)
    changed = 0
    for _ in range(30_000):
        name = rng.choice([noise, unicode_text])(rng)
        budget = rng.choice([255, 20, 5])
        before = old.safe_filename(name, max_bytes=budget)
        after = contentdisp.safe_filename(name, max_bytes=budget)
        if before != after:
            normal = unicodedata.normalize("NFKC", name)
            assert any(_removable(char) for char in normal), (name, before, after)
            changed += 1
    assert changed < 300


def _outcome(module: ModuleType, call: Callable[[ModuleType], object]) -> object:
    try:
        return call(module)
    except Exception as error:
        return type(error).__name__


# Every behaviour change of CHANGELOG 1.0.0: (call, result with 0.2.1, result with 1.0.0).
CHANGES: list[tuple[Callable[[ModuleType], object], object, object]] = [
    (
        lambda m: m.parse("x; f*=UTF-8'1'a", strict=True).params,
        {"f": "a"},
        "ContentDispositionError",
    ),
    (lambda m: m.parse("x; a=1; a=2", strict=True), "ValueError", "ContentDispositionError"),
    (lambda m: m.build("a b"), "ValueError", "ContentDispositionError"),
    (lambda m: m.parse("filename=a.txt").filename, None, "a.txt"),
    (lambda m: m.parse('"attachment"').is_attachment, True, False),
    (lambda m: m.parse("").is_attachment, True, False),
    (lambda m: m.ContentDisposition("INLINE").is_attachment, True, False),
    (lambda m: m.parse("x; \N{KELVIN SIGN}ey=v").params, {"key": "v"}, {}),
    (lambda m: m.safe_filename(None, max_bytes=0), "download", "ContentDispositionError"),
    (lambda m: m.safe_filename("a", max_bytes=255.0), "a", "TypeError"),
    (lambda m: m.safe_filename(None, default=None), None, "TypeError"),
    (
        lambda m: m.safe_filename("C\N{ZERO WIDTH SPACE}\N{COMBINING ACUTE ACCENT}"),
        "C\u0301",
        "\u0106",
    ),
    (lambda m: m.ContentDisposition("a", {"x": 1}).params, {"x": 1}, "TypeError"),
    (lambda m: m.ContentDisposition.__module__, "contentdisp_v021._model", "contentdisp"),
]


@pytest.mark.parametrize(("call", "before", "after"), CHANGES)
def test_every_documented_change(
    old: ModuleType, call: Callable[[ModuleType], object], before: object, after: object
) -> None:
    assert _outcome(old, call) == before
    assert _outcome(contentdisp, call) == after


def test_strict_offsets_now_count_from_the_start_of_the_header(old: ModuleType) -> None:
    with pytest.raises(ValueError, match="offset 11"):
        old.parse("  attachment filename=a", strict=True)
    with pytest.raises(ContentDispositionError, match="offset 13"):
        contentdisp.parse("  attachment filename=a", strict=True)


def test_messages_no_longer_quote_the_extended_value(old: ModuleType) -> None:
    header = "attachment; filename*=UTF-8''" + "s3cr3t" * 10 + "%"
    with pytest.raises(ValueError, match="s3cr3t"):
        old.parse(header, strict=True)
    with pytest.raises(ContentDispositionError) as caught:
        contentdisp.parse(header, strict=True)
    assert "s3cr3t" not in str(caught.value)
