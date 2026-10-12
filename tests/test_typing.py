"""The public API is typed: mypy infers the documented types and rejects wrong ones."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

api = pytest.importorskip("mypy.api")

SRC = Path(__file__).resolve().parents[1] / "src"

SNIPPET = """
from contentdisp import build, parse, safe_filename

reveal_type(parse(b"inline"))
reveal_type(parse("inline", strict=True).filename)
reveal_type(parse("inline").params)
reveal_type(build("attachment", "a.txt", name="x"))
reveal_type(safe_filename(None))
parse(3)
build("attachment", name=3)
safe_filename("a", max_bytes="1")
"""


@pytest.fixture(scope="module")
def mypy_output(tmp_path_factory: pytest.TempPathFactory) -> str:
    folder = tmp_path_factory.mktemp("typing")
    target = folder / "snippet.py"
    target.write_text(SNIPPET, encoding="utf-8")
    config = folder / "mypy.ini"
    config.write_text(f"[mypy]\nmypy_path = {SRC.as_posix()}\n", encoding="utf-8")
    cache = str(folder / "cache")
    out, err, _ = api.run(
        ["--strict", "--config-file", str(config), "--cache-dir", cache, str(target)]
    )
    return str(out) + str(err)


def test_parse_returns_a_content_disposition(mypy_output: str) -> None:
    assert _revealed(mypy_output, 4) == "contentdisp._model.ContentDisposition"


def test_filename_is_optional_text(mypy_output: str) -> None:
    assert _revealed(mypy_output, 5) in ("str | None", "Union[str, None]")


def test_params_map_text_to_text(mypy_output: str) -> None:
    assert _revealed(mypy_output, 6) == "dict[str, str]"


def test_build_and_safe_filename_return_text(mypy_output: str) -> None:
    assert _revealed(mypy_output, 7) == "str"
    assert _revealed(mypy_output, 8) == "str"


def test_wrong_argument_types_are_rejected(mypy_output: str) -> None:
    for line in (9, 10, 11):
        assert re.search(rf"snippet\.py:{line}: error: .*\[arg-type\]", mypy_output), line


def _revealed(output: str, line: int) -> str:
    match = re.search(rf"snippet\.py:{line}: note: Revealed type is \"(.+)\"", output)
    assert match, output
    # Older mypy releases spell builtins with their module prefix.
    return match.group(1).replace("builtins.", "")
