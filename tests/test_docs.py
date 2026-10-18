"""The README and GUIDE examples run and print what they say; docs, versions and files agree."""

from __future__ import annotations

import contextlib
import io
import itertools
import re
import unicodedata
from pathlib import Path

import contentdisp

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
GUIDE = (ROOT / "GUIDE.md").read_text(encoding="utf-8")


def _python_blocks(text: str) -> list[str]:
    return re.findall(r"```python\n(.*?)```", text, flags=re.DOTALL)


def _expected_output(block: str) -> list[str]:
    """Each print line is followed by a comment line that holds what it prints."""
    lines = block.splitlines()
    return [
        following.strip()[2:]
        for line, following in itertools.pairwise(lines)
        if line.strip().startswith("print(") and following.strip().startswith("# ")
    ]


def _run_blocks(text: str) -> int:
    checked = 0
    for block in _python_blocks(text):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            exec(compile(block, "docs", "exec"), {"__name__": "docs"})
        expected = _expected_output(block)
        assert expected, block
        assert out.getvalue().splitlines() == expected
        checked += len(expected)
    return checked


def test_every_readme_example_runs_and_prints_its_comment() -> None:
    assert len(_python_blocks(README)) == 3
    assert _run_blocks(README) == 7


def test_every_guide_example_runs_and_prints_its_comment() -> None:
    assert len(_python_blocks(GUIDE)) == 5
    assert _run_blocks(GUIDE) == 13


def test_every_print_in_the_docs_shows_its_output() -> None:
    for block in _python_blocks(README) + _python_blocks(GUIDE):
        prints = [line for line in block.splitlines() if line.strip().startswith("print(")]
        assert len(prints) == len(_expected_output(block))


def test_the_readme_links_are_absolute_and_reach_guide_and_changelog() -> None:
    for target in re.findall(r"\]\(([^)]+)\)", README):
        assert target.startswith("https://"), target
    assert "blob/main/GUIDE.md" in README and "blob/main/CHANGELOG.md" in README
    assert "](https://lianes8studio.com/certified)" in README


def test_the_api_table_lists_every_public_name() -> None:
    table = README.split("## API", 1)[1].split("\n## ", 1)[0]
    for name in contentdisp.__all__:
        assert f"`{name}" in table, name


def test_version_matches_pyproject() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', text, flags=re.MULTILINE)
    assert match is not None
    assert match.group(1) == contentdisp.__version__


def test_changelog_has_a_dated_entry_for_this_version() -> None:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(
        rf"^## \[{re.escape(contentdisp.__version__)}\] - \d{{4}}-\d\d-\d\d$", text, re.M
    )


SUFFIXES = {".py", ".md", ".toml", ".json", ".mjs", ".ps1", ".txt"}


def _tree() -> list[Path]:
    found = []
    for path in sorted(ROOT.rglob("*")):
        parts = path.relative_to(ROOT).parts
        if not path.is_file() or path.suffix not in SUFFIXES:
            continue
        if parts[:2] == ("tests", "upstream") and path.name != "MANIFEST.json":
            continue
        if any(part.startswith(".") or part in ("__pycache__", "build", "dist") for part in parts):
            continue
        found.append(path)
    return found


def test_no_em_dash_and_no_invisible_character_anywhere_in_the_tree() -> None:
    assert len(_tree()) > 30
    for path in _tree():
        text = path.read_text(encoding="utf-8")
        assert chr(0x2014) not in text, path
        odd = {c for c in text if unicodedata.category(c) in ("Cc", "Cf", "Zl", "Zp") and c != "\n"}
        assert not odd, (path, odd)


def test_source_files_stay_under_two_hundred_lines() -> None:
    for path in [
        *(ROOT / "src").rglob("*.py"),
        *(ROOT / "tests").glob("*.py"),
        *(ROOT / "scripts").glob("*.*"),
    ]:
        assert path.read_text(encoding="utf-8").count("\n") <= 200, path
