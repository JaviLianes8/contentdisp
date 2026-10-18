"""safe_filename against Windows itself and against Microsoft's own naming rules.

The rules are read from the fetched source of "Naming Files, Paths, and Namespaces"
(tests/upstream/MANIFEST.json, skipped while absent). Python's ntpath.isreserved (3.13
and later) is an independent oracle, and every result is created as a real file in a
temporary folder, which must hold exactly that name afterwards (no device, no stream, no
name the operating system silently changes).
"""

from __future__ import annotations

import ntpath
import os
import random
import re
from pathlib import Path

import pytest
from conftest import upstream_text
from generators import noise, unicode_text

from contentdisp import safe_filename


def _rules() -> tuple[list[str], list[str], str]:
    text = upstream_text("ms-naming-a-file.md")
    names_line = text.split("Do not use the following reserved names for the name of a file:")[1]
    sentence = names_line.strip().split(". Also")[0]
    names = re.split(r",\s*(?:and\s+)?", sentence)
    block = text.split("The following reserved characters:")[1].split("Integer value zero")[0]
    tokens = re.findall(r"^\s+- (\S+) \(", block, re.M)
    chars = [token.replace("\\\\", "\0").replace("\\", "").replace("\0", "\\") for token in tokens]
    return names, chars, " ".join(text.split())


def test_microsofts_reserved_names_get_a_prefix() -> None:
    names, _, text = _rules()
    assert len(names) == 28 and names[:4] == ["CON", "PRN", "AUX", "NUL"]
    assert "NUL.txt and NUL.tar.gz are both equivalent to NUL" in text
    for name in names:
        for variant in (name, name.lower(), f"{name}.txt", f"{name}.tar.gz", f"{name} .txt"):
            assert safe_filename(variant).startswith("_"), variant


def test_microsofts_reserved_characters_never_survive() -> None:
    _, chars, text = _rules()
    assert sorted(chars) == sorted('<>:"/\\|?*')
    assert "range from 1 through 31" in text
    for char in [*chars, *map(chr, range(32))]:
        assert char not in safe_filename(f"a{char}b{char}c.txt"), repr(char)


def test_no_name_ends_with_a_space_or_a_period() -> None:
    _, _, text = _rules()
    assert "Do not end a file or directory name with a space or a period" in text
    rng = random.Random(3)
    for _ in range(20_000):
        result = safe_filename(noise(rng) + rng.choice(["", ".", " ", ". ", " ."]), max_bytes=20)
        assert not result.endswith((" ", ".")), result


def _hostile(rng: random.Random) -> str:
    return rng.choice([unicode_text, noise])(rng) + rng.choice(["", ".txt", "...", "  ", ":x"])


@pytest.mark.skipif(not hasattr(ntpath, "isreserved"), reason="ntpath.isreserved needs Python 3.13")
def test_python_finds_nothing_reserved_in_a_safe_name() -> None:
    isreserved = ntpath.isreserved  # type: ignore[attr-defined,unused-ignore]
    rng = random.Random(13)
    for _ in range(30_000):
        name = _hostile(rng)
        assert not isreserved(safe_filename(name, max_bytes=rng.choice([255, 12, 5]))), name


NAMES = [
    "CON",
    "con.txt",
    "NUL .tar.gz",
    "COM1",
    "lpt\N{SUPERSCRIPT ONE}.log",
    "CONIN$",
    "AUX.",
    "a.txt.",
    "b.txt  ",
    "c.txt:stream",
    "..",
    ".env",
    "-rf",
    "~",
    "|",
    "a<b>c",
    'q"t',
    "dir/file.txt",
    "C:\\Windows\\x.dll",
    "\N{RIGHT-TO-LEFT OVERRIDE}gpj.exe",
    "x\x00y",
    "\N{FULLWIDTH SOLIDUS}etc\N{FULLWIDTH SOLIDUS}passwd",
    "\N{EURO SIGN} rates.pdf",
]


def test_the_operating_system_creates_every_safe_name_as_is(tmp_path: Path) -> None:
    rng = random.Random(4)
    names = NAMES + [_hostile(rng) for _ in range(400)]
    created: set[str] = set()
    for name in names:
        safe = safe_filename(name, max_bytes=80)
        if (tmp_path / safe).exists():
            # Equal to an earlier name under the file system's rules: only by case.
            assert safe.casefold() in {listed.casefold() for listed in os.listdir(tmp_path)}
            continue
        with open(tmp_path / safe, "x", encoding="utf-8") as handle:
            handle.write(name)
        created.add(safe)
        assert (tmp_path / safe).resolve().parent == tmp_path.resolve(), safe
    assert set(os.listdir(tmp_path)) == created and len(created) > 300
    assert all((tmp_path / safe).is_file() for safe in created)
