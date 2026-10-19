from __future__ import annotations

import functools
import hashlib
import html
import json
import re
from pathlib import Path

import pytest

UPSTREAM = Path(__file__).resolve().parent / "upstream"


@functools.cache
def _checked(name: str) -> bytes | None:
    path = UPSTREAM / name
    if not path.is_file():
        return None
    entry = json.loads((UPSTREAM / "MANIFEST.json").read_text(encoding="utf-8"))[name]
    body = path.read_bytes()
    assert hashlib.sha256(body).hexdigest() == entry["sha256"], f"{name} differs from MANIFEST"
    return body


def read_upstream(name: str) -> bytes:
    """Return a third-party test file, checked against tests/upstream/MANIFEST.json.

    The files are not committed: `python scripts/fetch_upstream.py` fetches them. Their
    tests skip while a file is absent and fail if it differs from the manifest.
    """
    body = _checked(name)
    if body is None:
        pytest.skip(f"{name} is not fetched; run python scripts/fetch_upstream.py")
    return body


def upstream_text(name: str) -> str:
    """A fetched specification as text (UTF-8)."""
    return read_upstream(name).decode("utf-8")


def _text(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", fragment))


def tc2231_cases() -> dict[str, dict[str, str]]:
    """Read the cases out of the fetched tc2231 page (ISO-8859-1), keyed by case id.

    Each case keeps the header as shown, the page's syntax marker (``parseerror``,
    ``invalid``, ``invalidsyntax`` or empty) and the expectation text.
    """
    page = read_upstream("tc2231.html").decode("latin-1")
    cases = {}
    for match in re.finditer(r'<div id="([^"]+)">\s*<h4>(.*?)</div>', page, re.S):
        case_id, body = match.groups()
        pre = re.search(
            r'<pre(?: class="([a-z]+)")?><b>Content-Disposition: </b>(.*?)</pre>', body, re.S
        )
        if pre is None:
            continue
        expect = " ".join(_text(em) for em in re.findall(r"<p><em>(.*?)</em></p>", body, re.S))
        cases[case_id] = {
            "header": _text(pre.group(2)),
            "marker": pre.group(1) or "",
            "expect": re.sub(r"\s+", " ", expect).strip(),
        }
    return cases


@pytest.fixture(scope="session")
def tc2231() -> dict[str, dict[str, str]]:
    """The tc2231 cases; skips the test while the page is not fetched."""
    return tc2231_cases()
