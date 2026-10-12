"""Extract the Content-Disposition test cases from a saved copy of the tc2231 page.

Usage:
    curl -sSfL -o tc2231.html http://greenbytes.de/tech/tc2231/
    python scripts/extract_tc2231.py tc2231.html tests/fixtures/tc2231.json

The page is ISO-8859-1. Each case keeps its id, the header exactly as shown, the
page's syntax marker (``parseerror``, ``invalid``, ``invalidsyntax`` or empty) and
the expectation sentences, so the tests read their ground truth from the page itself.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from pathlib import Path

URL = "http://greenbytes.de/tech/tc2231/"


def _text(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", fragment))


def extract(raw: bytes) -> list[dict[str, str]]:
    page = raw.decode("latin-1")
    cases = []
    for match in re.finditer(r'<div id="([^"]+)">\s*<h4>(.*?)</div>', page, re.S):
        case_id, body = match.groups()
        pre = re.search(
            r'<pre(?: class="([a-z]+)")?><b>Content-Disposition: </b>(.*?)</pre>', body, re.S
        )
        if pre is None:
            continue
        expect = " ".join(_text(em) for em in re.findall(r"<p><em>(.*?)</em></p>", body, re.S))
        cases.append(
            {
                "id": case_id,
                "header": _text(pre.group(2)),
                "marker": pre.group(1) or "",
                "expect": re.sub(r"\s+", " ", expect).strip(),
            }
        )
    return cases


def main(source: str, target: str) -> None:
    raw = Path(source).read_bytes()
    document = {
        "source": URL,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "cases": extract(raw),
    }
    text = json.dumps(document, ensure_ascii=True, indent=1) + "\n"
    Path(target).write_text(text, encoding="utf-8", newline="\n")
    print(f"{len(document['cases'])} cases")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
