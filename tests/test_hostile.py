"""Huge and adversarial input: linear time, no crash, short messages (hand-written shapes)."""

from __future__ import annotations

import time
from collections.abc import Callable

import pytest

from contentdisp import ContentDispositionError, build, parse, safe_filename

UNIT = 40_000


def _seconds(work: Callable[[], object]) -> float:
    start = time.perf_counter()
    work()
    return time.perf_counter() - start


def _linear(make: Callable[[int], Callable[[], object]]) -> None:
    """Four times the input may take at most about four times as long (with slack).

    Wall-clock time is noisy when other processes load the machine, so the two sizes are
    timed in turns (load hits both alike), the best of each is kept, and a round that
    looks slow is measured again. A quadratic cost gives about 16 times in every round,
    so only a real blowup fails all of them.
    """
    small_work, large_work = make(UNIT), make(4 * UNIT)
    rounds: list[tuple[float, float]] = []
    for _ in range(4):
        small = large = float("inf")
        for _ in range(3):
            small = min(small, _seconds(small_work))
            large = min(large, _seconds(large_work))
        if large < 10 * max(small, 0.002) + 0.05:
            return
        rounds.append((small, large))
    raise AssertionError(f"not linear in any round: {rounds}")


HEADERS: dict[str, Callable[[int], str]] = {
    "params": lambda n: "a" + ";x=1" * (n // 4),
    "distinct params": lambda n: "a" + "".join(f";n{i}=v" for i in range(n // 8)),
    "semicolons": lambda n: "a" + ";" * n,
    "open quote": lambda n: 'a;x="' + "\\" * n,
    "escapes": lambda n: 'a;x="' + '\\"' * (n // 2) + '"',
    "quotes": lambda n: "a;x=" + '"' * n,
    "equals": lambda n: "a;x" + "=" * n,
    "whitespace": lambda n: " " * n + "a" + "\t" * n,
    "long token": lambda n: "a;x=" + "b" * n,
    "long quoted": lambda n: 'a;x="' + "\xe9" * n + '"',
    "long extended value": lambda n: "a;x*=UTF-8''" + "%41" * (n // 3),
    "broken language": lambda n: "a;x*=UTF-8'" + "a-" * (n // 2) + "'b",
    "variants": lambda n: "a;x*=UTF-8'en" + "-abcde" * (n // 6) + "'b",
    "extensions": lambda n: "a;x*=UTF-8'en-a" + "-bb" * (n // 3) + "'b",
    "private use": lambda n: "a;x*=UTF-8'x" + "-a" * (n // 2) + "'b",
    "unclosed variants": lambda n: "a;x*=UTF-8'en" + "-abcde" * (n // 6) + ")b",
    "unclosed private use": lambda n: "a;x*=UTF-8'x" + "-a" * (n // 2),
    "unclosed late break": lambda n: "a;x*=UTF-8'en" + "-abcde" * (n // 6) + "-abcdefghi",
    "type only": lambda n: "a" * n,
    "controls": lambda n: "a;x=" + "\r\n" * (n // 2),
}


@pytest.mark.parametrize("shape", sorted(HEADERS))
@pytest.mark.parametrize("strict", [False, True])
def test_parsing_time_grows_linearly(shape: str, strict: bool) -> None:
    def make(n: int) -> Callable[[], object]:
        text = HEADERS[shape](n)

        def work() -> None:
            try:
                parse(text, strict=strict)
            except ContentDispositionError as error:
                assert len(str(error)) < 200

        return work

    _linear(make)


BUILDS: dict[str, Callable[[int], Callable[[], object]]] = {
    "long name": lambda n: lambda: build("attachment", "\u20ac" * n),
    "percent signs": lambda n: lambda: build("attachment", "%41" * (n // 3)),
    "form-data": lambda n: lambda: build("form-data", '"\r\n\\' * (n // 4), name="f"),
    "many params": lambda n: lambda: build("attachment", **{f"p{i}": "v" for i in range(n // 20)}),
    # Marks of two alternating classes, which an unbounded normalisation sorts in O(n^2).
    "alternating marks": lambda n: lambda: build("attachment", "a" + "\u0316\u0301" * (n // 2)),
    "decomposing marks": lambda n: lambda: build("attachment", "a" + "\u0f73" * n),
}


@pytest.mark.parametrize("shape", sorted(BUILDS))
def test_building_time_grows_linearly(shape: str) -> None:
    _linear(BUILDS[shape])


NAMES: dict[str, Callable[[int], str]] = {
    "plain": lambda n: "a" * n + ".txt",
    "separators": lambda n: "a/" * (n // 2),
    "leading marks": lambda n: "\u0301" * n + "a",
    "leading dots": lambda n: ". " * (n // 2) + "a",
    "invisible": lambda n: "\u200b" * n + "a",
    "expanding": lambda n: "\ufdfa" * (n // 18),
    "joiners": lambda n: "\u200d" * n + ".env",
    "alternating marks": lambda n: "a" + "\u0316\u0301" * (n // 2),
    "decomposing marks": lambda n: "a" + "\u0f73" * n,
    "marks split by invisibles": lambda n: "a" + ("\u0316\u0301" * 15 + "\u200b") * (n // 31),
}


@pytest.mark.parametrize("shape", sorted(NAMES))
def test_safe_filename_time_grows_linearly(shape: str) -> None:
    _linear(lambda n: lambda: safe_filename(NAMES[shape](n)))


@pytest.mark.parametrize(
    "call",
    [
        lambda big: build("a b" + big),
        lambda big: build("attachment", **{big: "1", big.upper(): "2"}),
        lambda big: build("attachment", big + "\x00"),
        lambda big: build("attachment", **{big + "*": "x"}),
        lambda big: parse(f"a; {big}=1; {big}=2", strict=True),
        lambda big: parse(f"a; x*=UTF-8''{big}%", strict=True),
        lambda big: parse(f'a; x="{big}', strict=True),
    ],
)
def test_huge_input_never_reaches_a_message_whole(call: Callable[[str], object]) -> None:
    with pytest.raises(ContentDispositionError) as caught:
        call("q" * 1_000_000)
    message = str(caught.value)
    assert len(message) < 200 and "q" * 37 not in message
    # The quoted input is cut to exactly 40 characters: its opening quote, 36 more, "...".
    if "'q" in message:
        assert "'" + "q" * 36 + "..." in message


def test_a_four_megabyte_header_is_read_in_both_modes() -> None:
    text = "attachment; filename*=UTF-8''" + "%E2%82%AC" * 450_000
    assert parse(text, strict=True).filename == "\u20ac" * 450_000
    assert parse(text.encode("ascii")).filename == "\u20ac" * 450_000
