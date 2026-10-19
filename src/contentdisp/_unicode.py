"""Unicode normalisation in linear time, whatever the input."""

from __future__ import annotations

import functools
import unicodedata
from typing import Literal

# UAX #15, Stream-Safe Text Format: at most 30 non-starters in a row. Normalisation sorts
# each run of non-starters by combining class with an insertion sort, so an unbounded run
# of alternating classes (U+0316 U+0301 ...) costs quadratic time.
MAX_NON_STARTERS = 30


@functools.lru_cache(maxsize=4096)
def _decompose(char: str) -> str:
    return unicodedata.normalize("NFKD", char)


def normalize(form: Literal["NFKC", "NFKD"], text: str) -> str:
    """``unicodedata.normalize(form, text)`` after cutting every run of non-starters to 30.

    Runs are counted on the decomposition, so a starter that decomposes into marks (such
    as U+0F73) cannot hide them. Text without such a run normalises exactly as before.
    """
    if text.isascii():
        return text
    kept: list[str] = []
    run = 0
    for char in text:
        for part in _decompose(char):
            if unicodedata.combining(part):
                run += 1
                if run > MAX_NON_STARTERS:
                    continue
            else:
                run = 0
            kept.append(part)
    return unicodedata.normalize(form, "".join(kept))
