"""Seeded property tests on hostile input: no crash, typed failures, round trips, invariants."""

from __future__ import annotations

import random
import re
import unicodedata

import pytest
from generators import header, noise, unicode_text

from contentdisp import ContentDisposition, ContentDispositionError, build, parse, safe_filename

SEEDS = [11, 12, 13]


@pytest.mark.parametrize("seed", SEEDS)
def test_lenient_parsing_never_fails_and_returns_clean_text(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(8000):
        text = noise(rng)
        for value in (
            text,
            text.encode("utf-8", "surrogatepass"),
            text.encode("latin-1", "replace"),
        ):
            result = parse(value)
            assert isinstance(result, ContentDisposition)
            fields = [result.type, *result.params, *result.params.values()]
            assert all(isinstance(field, str) for field in fields)
            assert not any(char in field for field in fields for char in "\r\n\0"), value


@pytest.mark.parametrize("seed", SEEDS)
def test_strict_parsing_fails_only_with_a_short_positioned_error(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(8000):
        text = rng.choice([noise, header])(rng)
        try:
            parse(text, strict=True)
        except ContentDispositionError as error:
            assert error.position is not None and 0 <= error.position <= len(text), text
            assert str(error).endswith(f" at offset {error.position}") and len(str(error)) < 200


@pytest.mark.parametrize("seed", SEEDS)
def test_lenient_and_strict_agree_on_every_valid_header(seed: int) -> None:
    rng = random.Random(seed)
    compared = 0
    for _ in range(8000):
        text = rng.choice([noise, header])(rng)
        try:
            strict = parse(text, strict=True)
        except ContentDispositionError:
            continue
        assert parse(text) == strict, text
        assert parse(text.encode("latin-1", "replace")) == parse(
            text.encode("latin-1", "replace"), strict=True
        )
        compared += 1
    assert compared > 2000


def _buildable(value: str) -> bool:
    return not any(c != "\t" and unicodedata.category(c) in ("Cc", "Cs") for c in value)


@pytest.mark.parametrize("seed", SEEDS)
def test_built_headers_read_back_exactly_in_both_modes(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(3000):
        name, title = unicode_text(rng), unicode_text(rng)
        kind = rng.choice(["attachment", "inline", "x-zip", "Attachment "])
        if not (_buildable(name) and _buildable(title)):
            with pytest.raises(ContentDispositionError):
                build(kind, name, title=title)
            continue
        written = build(kind, name, title=title, creation_date="d")
        expected = {"filename": name, "title": title, "creation-date": "d"}
        for strict in (True, False):
            assert parse(written, strict=strict) == ContentDisposition(
                kind.strip().lower(), expected
            )
        assert written.isascii()


@pytest.mark.parametrize("seed", SEEDS)
def test_form_data_reads_back_with_the_four_escapes(seed: int) -> None:
    rng = random.Random(seed)
    escapes = {"\n": "%0A", "\r": "%0D", '"': "%22", "\\": "%5C"}
    for _ in range(3000):
        name = unicode_text(rng) + rng.choice(["", "\r\n", '"', "\\"])
        if not _buildable(name.replace("\r", "").replace("\n", "")):
            continue
        written = build("form-data", name, name="f")
        expected = "".join(escapes.get(char, char) for char in name)
        assert parse(written, strict=True).params == {"filename": expected, "name": "f"}
        assert "*" not in re.sub(r'"(?:[^"\\]|\\.)*"', "", written), written  # no name*=


_DEVICE = re.compile(r"(?:con|prn|aux|nul|com[1-9]|lpt[1-9])", re.I)


@pytest.mark.parametrize("seed", SEEDS)
def test_safe_names_keep_every_promise(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(20_000):
        name = rng.choice([noise, unicode_text])(rng)
        budget = rng.choice([255, 40, 9, 5, 3, 1])
        result = safe_filename(name, max_bytes=budget, default="\0default")
        if result == "\0default":
            continue
        assert 0 < len(result.encode("utf-8")) <= budget, (name, result)
        assert not set(result) & set('/\\<>:"|?*'), result
        categories = {
            unicodedata.category(char)
            for char in result.replace("\u200c", "").replace("\u200d", "")
        }
        assert not categories & {"Cc", "Cs", "Cf"}, result
        assert result[0] not in " .~-" and not unicodedata.category(result[0]).startswith("M")
        assert not result.endswith((" ", ".")), result
        assert not _DEVICE.fullmatch(result.split(".", 1)[0].rstrip(" ")), result
        assert unicodedata.normalize("NFKC", result) == result
        assert safe_filename(result, max_bytes=budget) == result, (name, result)
