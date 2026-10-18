"""The jshttp content-disposition parsers (the ones Express uses), run live with Node.js.

The 1.0.1 and 3.0.0 releases come from the npm tarballs pinned in tests/upstream/
MANIFEST.json (sha256 checked) and run through scripts/jshttp_oracle.mjs. Release 1.0.1
is a strict RFC 6266 parser with narrower rules in places, listed in DIVERGENCES; on the
grammar both share, strict mode must agree with it exactly. Skips without Node.js or the
fetched tarballs.
"""

from __future__ import annotations

import io
import json
import random
import re
import shutil
import subprocess
import tarfile
from collections.abc import Callable
from pathlib import Path

import pytest
from conftest import read_upstream
from generators import header as random_header
from generators import unicode_text

from contentdisp import ContentDispositionError, build, parse

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "jshttp_oracle.mjs"
Oracle = Callable[[list[list[object]]], list[dict[str, object]]]


@pytest.fixture(scope="module")
def oracle(tmp_path_factory: pytest.TempPathFactory) -> Oracle:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is not installed")
    folders = []
    for version in ("1.0.1", "3.0.0"):
        folder = tmp_path_factory.mktemp(f"jshttp-{version}")
        body = io.BytesIO(read_upstream(f"content-disposition-{version}.tgz"))
        with tarfile.open(fileobj=body) as archive:
            for member in archive.getmembers():
                if member.isfile() and member.name in ("package/index.js", "package/dist/index.js"):
                    source = archive.extractfile(member)
                    assert source is not None
                    target = folder / member.name.removeprefix("package/")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(source.read())
        folders.append(str(folder))

    def run(requests: list[list[object]]) -> list[dict[str, object]]:
        lines = "".join(json.dumps(request) + "\n" for request in requests)
        done = subprocess.run(
            [node, str(SCRIPT), *folders],
            input=lines,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
            timeout=240,
        )
        # JSON.stringify leaves U+2028 and U+0085 raw, which str.splitlines would split on.
        return [json.loads(line) for line in done.stdout.split("\n") if line]

    return run


def _ours(header: str) -> object:
    try:
        result = parse(header, strict=True)
    except ContentDispositionError:
        return None
    return {"type": result.type, "parameters": result.params}


def _shared(header: str) -> bool:
    """False when the header reaches a place where release 1.0.1 is knowingly narrower."""
    if header[:1] in " \t" or "\t" in header or any(ord(char) > 0xFF for char in header):
        return False
    if re.search(r"\\[^\x20-\x7e]", header):
        return False
    if any("*" in segment.partition("=")[0].strip()[:-1] for segment in header.split(";")):
        return False
    for ext in re.findall(r"\*\s*=\s*([^;\s]*)", header):
        charset, _, rest = ext.partition("'")
        language, _, chars = rest.partition("'")
        if charset.lower() not in ("utf-8", "iso-8859-1") or not chars:
            return False
        if not re.fullmatch(r"(?:[A-Za-z]{2,3})?", language) or re.search(
            r"%[89][0-9A-Fa-f]|%[0-7][0-9A-Fa-f]", chars
        ):
            return False
        if charset.lower() == "utf-8" and re.search(r"%[A-Fa-f][0-9A-Fa-f]", chars):
            return False
    return True


def test_strict_mode_agrees_with_release_1_on_the_shared_grammar(oracle: Oracle) -> None:
    rng = random.Random(1001)
    headers = [h for h in (random_header(rng) for _ in range(40_000)) if _shared(h)]
    answers = oracle([["parse1", h] for h in headers])
    accepted = 0
    for header, answer in zip(headers, answers, strict=True):
        theirs = answer.get("ok")
        assert _ours(header) == theirs, (header, answer)
        accepted += theirs is not None
    assert len(headers) > 10_000 and accepted > 3000


# Where release 1.0.1 is narrower than RFC 9110, RFC 8187 and RFC 5646, or decodes
# differently; each is asserted exactly so the list cannot go stale.
DIVERGENCES = [
    (" attachment", None, {"type": "attachment", "parameters": {}}),
    ('a; x="1\t2"', None, {"type": "a", "parameters": {"x": "1\t2"}}),
    ('a; x="\\\xe9"', None, {"type": "a", "parameters": {"x": "\xe9"}}),
    ("a; x*=UTF-8'en-US'%41", None, {"type": "a", "parameters": {"x": "A"}}),
    ("a; x*=UTF-8''", None, {"type": "a", "parameters": {"x": ""}}),
    ("a; x*=x-ext''%41", None, {"type": "a", "parameters": {}}),
    ("a; x*=utf8''%41", {"type": "a", "parameters": {"x": "A"}}, {"type": "a", "parameters": {}}),
    ("a; x*=UTF-8''%FF", {"type": "a", "parameters": {"x": "\ufffd"}}, None),
    ("a; x*=ISO-8859-1''%80", {"type": "a", "parameters": {"x": "?"}}, None),
    ("a; a*b*=c", {"type": "a", "parameters": {"a*b*": "c"}}, None),
    ('a; x="\u20ac"', None, {"type": "a", "parameters": {"x": "\u20ac"}}),
]


def test_every_divergence_from_release_1_is_known(oracle: Oracle) -> None:
    answers = oracle([["parse1", header] for header, _, _ in DIVERGENCES])
    for (header, theirs, ours), answer in zip(DIVERGENCES, answers, strict=True):
        assert answer.get("ok") == theirs, (header, answer)
        assert _ours(header) == ours, header
        assert not _shared(header), header


def test_both_releases_read_back_what_build_writes(oracle: Oracle) -> None:
    rng = random.Random(6266)
    names = [unicode_text(rng).replace("\t", " ") for _ in range(3000)]
    headers = [build("attachment", name, title=name) for name in names]
    for operation in ("parse1", "parse3"):
        answers = oracle([[operation, header] for header in headers])
        for name, header, answer in zip(names, headers, answers, strict=True):
            assert answer["ok"]["parameters"]["filename"] == name, (operation, header)  # type: ignore[index]
            assert answer["ok"]["parameters"]["title"] == name, (operation, header)  # type: ignore[index]


def test_form_data_matches_the_multipart_format_of_release_3(oracle: Oracle) -> None:
    rng = random.Random(7578)
    values = [
        unicode_text(rng).replace("\\", "/") + rng.choice(["", '"', "\r\n"]) for _ in range(3000)
    ]
    requests: list[list[object]] = [
        ["format3multipart", "form-data", {"filename": value, "name": "f"}] for value in values
    ]
    for value, answer in zip(values, oracle(requests), strict=True):
        assert build("form-data", value, name="f") == answer["ok"], value
    readback = oracle(
        [["parse3multipart", build("form-data", value, name="f")] for value in values]
    )
    for value, answer in zip(values, readback, strict=True):
        assert answer["ok"]["parameters"]["filename"] == value  # type: ignore[index]


def test_a_backslash_is_where_form_data_differs_from_release_3(oracle: Oracle) -> None:
    header = build("form-data", "a\\b", name="f")
    (answer,) = oracle([["parse3multipart", header]])
    assert header == 'form-data; filename="a%5Cb"; name="f"'
    assert answer["ok"]["parameters"]["filename"] == "a%5Cb"  # type: ignore[index]
